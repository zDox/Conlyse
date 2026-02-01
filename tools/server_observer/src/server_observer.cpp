#include "server_observer.hpp"
#include "game_finder.hpp"
#include "metrics.hpp"
#include <iostream>
#include <iomanip>
#include <fstream>
#include <chrono>
#include <algorithm>
#include <magic_enum/magic_enum.hpp>

namespace fs = std::filesystem;

static const int MAX_UPDATE_RETRIES = 3;
ServerObserver::ServerObserver(const json& config, std::shared_ptr<AccountPool> account_pool)
    : ServerObserver(config, account_pool, "")
{
}

ServerObserver::ServerObserver(const json& config, std::shared_ptr<AccountPool> account_pool, const std::string& config_path)
    : config_(config)
    , account_pool_(account_pool)
    , stop_flag_(false)
    , total_updates_completed_(0)
    , config_file_path_(config_path)
    , last_config_modified_time_()  // Initialize to default
    , last_config_check_time_()     // Initialize to default
{
    // Initialize statistics timing
    stats_start_time_ = std::chrono::system_clock::now();
    last_stats_print_time_ = stats_start_time_;
    last_config_check_time_ = stats_start_time_;

    max_parallel_recordings_ = config.value("max_parallel_recordings", 1);
    int max_parallel_updates = config.value("max_parallel_updates", 1);
    int max_parallel_first_updates = config.value("max_parallel_first_updates", 1);
    update_interval_ = config.value("update_interval", 60.0);
    int num_update_worker_threads = config.value("update_worker_threads", 4);
    output_dir_ = config.value("output_dir", "./recordings");

    if (config.contains("output_metadata_dir") && !config["output_metadata_dir"].is_null()) {
        output_metadata_dir_ = config["output_metadata_dir"].get<std::string>();
    }
    
    if (config.contains("long_term_storage_path") && !config["long_term_storage_path"].is_null()) {
        long_term_storage_path_ = config["long_term_storage_path"].get<std::string>();
    }
    
    if (config.contains("file_size_threshold")) {
        file_size_threshold_ = config["file_size_threshold"].get<int>();
    } else {
        file_size_threshold_ = 0;
    }
    
    // Initialize registry
    std::string registry_default_dir = output_metadata_dir_.empty() ? output_dir_ : output_metadata_dir_;
    std::string registry_path = config.value("registry_path", 
        registry_default_dir + "/server_observer_registry.json");
    
    registry_ = std::make_shared<RecordingRegistry>(registry_path);

    // Initialize map cache
    map_cache_ = std::make_shared<StaticMapCache>(output_dir_ + "/static_maps");

    request_manager_ = std::make_shared<RequestManager>(
        config.value("request_manager_threads", 1)
    );
    
    // Initialize Scheduler
    scheduler_ = std::make_unique<Scheduler>(
        max_parallel_updates,
        max_parallel_first_updates,
        update_interval_,
        num_update_worker_threads
    );

    // Initialize GameFinder
    game_finder_ = std::make_unique<GameFinder>(config, account_pool_, registry_);

    // Set the callback for starting observation sessions
    // GameFinder runs in a separate thread, so it queues sessions instead of creating them directly
    game_finder_->set_observation_starter([this](int game_id, int scenario_id) {
        this->scheduler_->queue_new_session(game_id, scenario_id);
    });

    // Set the callback for getting active session count
    game_finder_->set_active_session_counter([this]() -> size_t {
        std::lock_guard<std::mutex> lock(sessions_lock_);
        return observer_sessions_.size();
    });

    // Set the callback for when an account's proxy is reset
    account_pool_->set_proxy_reset_callback([this](std::shared_ptr<Account> account) {
        this->reset_sessions_for_account(account);
    });

    // Initialize config file modification time tracking
    if (!config_file_path_.empty() && fs::exists(config_file_path_)) {
        try {
            last_config_modified_time_ = fs::last_write_time(config_file_path_);
            
            // Start the config file watcher
            config_watcher_ = std::make_unique<ConfigFileWatcher>(
                config_file_path_,
                [this]() {
                    this->reload_config_from_file();
                }
            );
            config_watcher_->start();
            std::cout << "Config file watcher started for: " << config_file_path_ << std::endl;
        } catch (const std::exception& e) {
            std::cerr << "Warning: Could not get initial modification time for config file: " 
                     << e.what() << std::endl;
        }
    }
}

ServerObserver::~ServerObserver() {
    // Stop the config file watcher
    if (config_watcher_) {
        config_watcher_->stop();
        config_watcher_.reset();
    }

    // Ensure stop() has been called
    if (!stop_flag_) {
        stop();
    }

    std::cout << "ServerObserver destructor complete" << std::endl;
}

void ServerObserver::stop() {
    std::cout << "Stopping ServerObserver..." << std::endl;
    stop_flag_ = true;
    
    // Stop GameFinder's scanning thread
    if (game_finder_) {
        game_finder_->stop_scanning();
    }
    
    // Stop the scheduler
    if (scheduler_) {
        scheduler_->stop();
    }

    // Clear observer sessions (this will destroy Python objects)
    {
        std::lock_guard<std::mutex> lock(sessions_lock_);
        std::cout << "Clearing " << observer_sessions_.size()
                  << " observer sessions..." << std::endl;
        observer_sessions_.clear();
    }

    // Clear the game finder (contains Python objects via listing interface)
    if (game_finder_) {
        std::cout << "Clearing game finder..." << std::endl;
        game_finder_.reset();
    }

    std::cout << "ServerObserver stopped successfully" << std::endl;
}

void ServerObserver::start_observation_session(int game_id, int scenario_id) {
    auto account = account_pool_->next_guest_account(-1);
    if (!account && account_pool_) {
        std::cerr << "No free account available to start new observation" << std::endl;
        return;
    }

    std::cout << "Starting observation session for game " << game_id
             << " with scenario " << scenario_id << std::endl;

    // Determine metadata path
    std::string metadata_path;
    if (!output_metadata_dir_.empty()) {
        metadata_path = output_metadata_dir_ + "/game_" + std::to_string(game_id);
    }
    auto observer = std::make_unique<ObservationSession>(
        request_manager_,
        game_id,
        account,
        map_cache_,
        output_dir_ + "/game_" + std::to_string(game_id),
        metadata_path,
        long_term_storage_path_,
        file_size_threshold_
    );

    registry_->mark_recording(game_id, scenario_id, "");

    // Mark game as known in the game finder
    if (game_finder_) {
        game_finder_->mark_game_known(game_id);
    }

    account_pool_->increment_guest_join(account);

    observer->next_update_at = std::chrono::system_clock::now();

    // Mark as first update and schedule
    scheduler_->mark_first_update(game_id);
    scheduler_->schedule_update(observer.get());

    {
        std::lock_guard<std::mutex> lock(sessions_lock_);
        observer_sessions_[game_id] = std::move(observer);
    }
    
    // Record game started metric
    Metrics::getInstance().recordGameStarted(scenario_id);
    
    // Update active games metrics
    update_active_games_metrics();
}

void ServerObserver::resume_active() {
    auto active = registry_->active();
    std::cout << "Resuming " << active.size() << " active observations" << std::endl;

    for (const auto& [game_id, meta] : active) {
        if (!meta.contains("scenario_id")) {
            std::cerr << "Skipping resume for game " << game_id
                     << " without scenario metadata" << std::endl;
            continue;
        }

        {
            std::lock_guard<std::mutex> lock(sessions_lock_);
            if (observer_sessions_.find(game_id) != observer_sessions_.end()) {
                continue;
            }

            std::cout << "Resuming observation for game " << game_id << std::endl;

            if (observer_sessions_.size() >= static_cast<size_t>(max_parallel_recordings_)) {
                std::cerr << "Skipping resume for game " << game_id
                         << " due to max parallel limit reached " << observer_sessions_.size() << " observations" << std::endl;
                continue;
            }
        }

        int scenario_id = meta["scenario_id"].get<int>();
        start_observation_session(game_id, scenario_id);
    }
}

asio::awaitable<void> ServerObserver::run_single_update_async(ObservationSession* session) {
    int game_id = session->game_id;
    
    // Record game update started for metrics
    Metrics::getInstance().recordGameUpdateStarted();
    
    // Calculate scheduled latency (how late we are vs. scheduled time)
    auto now = std::chrono::system_clock::now();
    auto scheduled_time = session->next_update_at;
    if (now > scheduled_time) {
        auto latency = std::chrono::duration<double>(now - scheduled_time).count();
        
        // Record scheduled update latency metric
        Metrics::getInstance().recordScheduledUpdateLatency(latency);
        
        // Record missed interval if more than 10 seconds late
        if (latency > 10.0) {
            Metrics::getInstance().recordMissedInterval();
        }
    }

    // Execute the update
    ObservationResult result = co_await session->run_update_async();

    std::cout << "Finished update for game " << game_id << std::endl;

    // Record completion statistics
    record_update_completion();

    // Handle the result based on game state
    if (result.game_ended) {
        handle_game_ended(session);
    } else if (result.error_code == ObservationError::SUCCESS) {
        handle_successful_update(session);
    } else {
        handle_failed_update(session, result);
    }

    // Cleanup first update tracking
    scheduler_->cleanup_first_update_tracking(game_id);

    // Record game update completed for metrics
    Metrics::getInstance().recordGameUpdateCompleted();
    
    // Decrement the active coroutine counter to allow new updates to start
    scheduler_->decrement_active_coroutines();
}

void ServerObserver::record_update_completion() {
    ++total_updates_completed_;
    std::lock_guard lock(stats_lock_);
    update_timestamps_.push_back(std::chrono::system_clock::now());
}

void ServerObserver::handle_game_ended(ObservationSession* session) {
    int game_id = session->game_id;
    std::cout << "Finished recording game " << game_id << " (game ended)" << std::endl;

    // Get scenario_id before marking complete
    int scenario_id = registry_->get_scenario_id(game_id);
    
    // Mark game complete in registry
    registry_->mark_completed(game_id);
    
    // Record game completed metric
    if (scenario_id >= 0) {
        Metrics::getInstance().recordGameCompleted(scenario_id);
    }
    
    // Release account resources
    account_pool_->decrement_guest_join(session->account);

    // Remove session from active tracking
    {
        std::lock_guard lock(sessions_lock_);
        observer_sessions_.erase(game_id);
    }

    // Mark game as known in the game finder
    if (game_finder_) {
        game_finder_->mark_game_known(game_id);
    }
    
    // Update active games metrics
    update_active_games_metrics();
}

void ServerObserver::handle_successful_update(ObservationSession* session) {
    // Schedule next update at standard interval
    scheduler_->schedule_next_update(session);
}

void ServerObserver::handle_failed_update(ObservationSession* session, const ObservationResult& result) {
    int game_id = session->game_id;

    if (session->get_attempt() >= MAX_UPDATE_RETRIES) {
        std::cout << "Max retries reached for game " << game_id
                 << ". Ending observation due to: " << result.error_message << std::endl;
        
        // Convert error code to string for metrics
        std::string error_type = std::string(magic_enum::enum_name(result.error_code));

        // Record game failed metric
        Metrics::getInstance().recordGameFailed(error_type);

        // Clean up resources when max retries reached
        // Release account resources
        account_pool_->decrement_guest_join(session->account);

        // Mark as failed in registry
        registry_->mark_failed(game_id, result.error_message);

        // Remove session from active tracking
        {
            std::lock_guard lock(sessions_lock_);
            observer_sessions_.erase(game_id);
        }

        // Update active games metrics
        update_active_games_metrics();

        return;
    }
    if (result.error_code == ObservationError::NETWORK_ERROR) {
        // Reset Proxy
        if (account_pool_->reset_account_proxy(session->account)) {
            std::cout << "Reset proxy for account " << session->account->username
                     << " due to network error on game " << game_id << std::endl;
        } else {
            std::cerr << "Failed to reset proxy for account " << session->account->username
                     << " on game " << game_id << std::endl;
        }
    }

    // Determine retry timing based on error type
    bool immediate_retry = should_retry_immediately(result.error_code);
    schedule_retry(session, immediate_retry, result.error_message);
}

bool ServerObserver::should_retry_immediately(ObservationError error_code) const {
    return error_code == ObservationError::AUTH_FAILED ||
           error_code == ObservationError::SERVER_ERROR;
}

void ServerObserver::schedule_retry(ObservationSession* session, bool immediate,
                                    const std::string& error_message) {
    int game_id = session->game_id;

    if (immediate) {
        std::cout << "Retrying update for game " << game_id
                 << " immediately due to: " << error_message << std::endl;
        scheduler_->schedule_immediate_update(session);
    } else {
        std::cout << "Retrying update for game " << game_id
                 << " after interval due to: " << error_message << std::endl;
        scheduler_->schedule_next_update(session);
    }
}

void ServerObserver::reset_sessions_for_account(std::shared_ptr<Account> account) {
    if (!account) {
        return;
    }

    std::lock_guard<std::mutex> lock(sessions_lock_);

    for (auto& [game_id, session] : observer_sessions_) {
        if (session && session->account == account) {
            std::cout << "Resetting proxy for game " << game_id
                     << " (account: " << account->username << ")" << std::endl;
            session->set_proxy(*account->proxy_config);
        }
    }
}

void ServerObserver::start_due_updates() {
    // Get all sessions that are due for update
    auto due_sessions = scheduler_->get_due_updates();

    // Spawn coroutines for each due session
    for (auto* session : due_sessions) {
        // Increment the active coroutine counter before spawning
        scheduler_->increment_active_coroutines();

        // Spawn async coroutine
        scheduler_->spawn_update_coroutine(run_single_update_async(session));
    }

    // Let scheduler handle waiting for next updates
    scheduler_->process_due_updates();
}


void ServerObserver::print_update_statistics() {
    auto now = std::chrono::system_clock::now();

    std::lock_guard<std::mutex> lock(stats_lock_);

    // Calculate time since last print
    auto duration_since_last = std::chrono::duration_cast<std::chrono::seconds>(
        now - last_stats_print_time_).count();

    // Only print every 10 seconds
    if (duration_since_last < 10) {
        return;
    }

    // Remove timestamps older than 30 seconds from the rolling window
    auto window_start = now - std::chrono::seconds(30);
    while (!update_timestamps_.empty() && update_timestamps_.front() < window_start) {
        update_timestamps_.pop_front();
    }

    // Calculate rolling window statistics
    size_t updates_in_window = update_timestamps_.size();
    double window_rate = updates_in_window / 30.0;  // Updates per second in the last 30 seconds

    // Calculate overall statistics
    auto total_duration = std::chrono::duration_cast<std::chrono::seconds>(
        now - stats_start_time_).count();

    uint64_t total_updates = total_updates_completed_.load();

    double overall_rate = (total_duration > 0) ?
        static_cast<double>(total_updates) / total_duration : 0.0;

    // Get current active sessions count
    size_t active_sessions = 0;
    {
        std::lock_guard<std::mutex> session_lock(sessions_lock_);
        active_sessions = observer_sessions_.size();
    }

    std::cout << "=== Update Statistics ===" << std::endl;
    std::cout << "Total updates completed: " << total_updates << std::endl;
    std::cout << "Total runtime: " << total_duration << " seconds" << std::endl;
    std::cout << "Overall average updates/sec: " << std::fixed << std::setprecision(3)
              << overall_rate << std::endl;
    std::cout << "Rolling 30s window: " << updates_in_window << " updates, "
              << std::fixed << std::setprecision(3) << window_rate << " updates/sec" << std::endl;
    std::cout << "Active observation sessions: " << active_sessions << std::endl;

    // Scheduler metrics
    std::cout << "--- Scheduler Metrics ---" << std::endl;
    std::cout << "Update queue size: " << scheduler_->get_queue_size() << std::endl;
    std::cout << "Active coroutines: " << scheduler_->get_active_coroutines() << std::endl;
    std::cout << "First updates tracked: " << scheduler_->get_first_update_count() << std::endl;
    std::cout << "First updates running: " << scheduler_->get_running_first_updates_count() << std::endl;
    double next_due = scheduler_->get_seconds_until_next_due();
    if (next_due > 0) {
        std::cout << "Next update due in: " << std::fixed << std::setprecision(1)
                  << next_due << " seconds" << std::endl;
    } else if (scheduler_->get_queue_size() > 0) {
        std::cout << "Updates available for processing now" << std::endl;
    }

    std::cout << "=========================" << std::endl;

    last_stats_print_time_ = now;

    // Update active games metrics
    update_active_games_metrics();
}

void ServerObserver::update_active_games_metrics() {
    // Update active games metrics by scenario
    std::map<int, int> active_by_scenario;
    {
        std::lock_guard<std::mutex> session_lock(sessions_lock_);
        for (const auto& [game_id, session] : observer_sessions_) {
            int scenario_id = registry_->get_scenario_id(game_id);
            if (scenario_id >= 0) {
                active_by_scenario[scenario_id]++;
            }
        }
    }

    // Set active games gauge for each scenario
    for (const auto& [scenario_id, count] : active_by_scenario) {
        Metrics::getInstance().setActiveGames(scenario_id, count);
    }
}

bool ServerObserver::run() {
    stop_flag_ = false;

    resume_active();

    // Refresh GameFinder's known games from registry before scanning
    if (game_finder_) {
        game_finder_->refresh_known_games_from_registry();
        // Start GameFinder's scanning thread
        game_finder_->start_scanning();
    }

    try {
        while (!stop_flag_) {
            // Process any new sessions queued by GameFinder
            auto pending_sessions = scheduler_->get_pending_new_sessions();
            for (const auto& [game_id, scenario_id] : pending_sessions) {
                // Check if we haven't exceeded max parallel recordings
                bool can_start = false;
                {
                    std::lock_guard<std::mutex> lock(sessions_lock_);
                    can_start = observer_sessions_.size() < static_cast<size_t>(max_parallel_recordings_);
                }

                if (can_start) {
                    start_observation_session(game_id, scenario_id);
                } else {
                    std::cout << "Max parallel recordings limit reached. Skipping game "
                             << game_id << std::endl;
                }
            }

            start_due_updates();
            print_update_statistics();
        }
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Error in main loop: " << e.what() << std::endl;
        stop_flag_ = true;
        return false;
    }
}

void ServerObserver::check_and_reload_config() {
    // Skip if no config file path was provided
    if (config_file_path_.empty()) {
        return;
    }

    // Rate limit config file checks to once per second
    auto now = std::chrono::system_clock::now();
    auto duration_since_last_check = std::chrono::duration_cast<std::chrono::seconds>(
        now - last_config_check_time_).count();

    if (duration_since_last_check < 1) {
        return;
    }

    last_config_check_time_ = now;

    try {
        // Check if config file exists
        if (!fs::exists(config_file_path_)) {
            return;
        }

        // Get current modification time
        auto current_modified_time = fs::last_write_time(config_file_path_);

        // Compare with last known modification time
        if (current_modified_time != last_config_modified_time_) {
            std::cout << "Config file change detected, reloading..." << std::endl;

            // Load the new config
            std::ifstream config_stream(config_file_path_);
            if (!config_stream.is_open()) {
                std::cerr << "Error: Could not open config file for reload: "
                         << config_file_path_ << std::endl;
                return;
            }

            json new_config;
            try {
                config_stream >> new_config;
            } catch (const std::exception& e) {
                std::cerr << "Error parsing config file during reload: " << e.what() << std::endl;
                return;
            }

            // Apply the new config
            reload_config(new_config);

            // Update the last modified time
            last_config_modified_time_ = current_modified_time;

            std::cout << "Config reloaded successfully" << std::endl;
        }
    } catch (const std::exception& e) {
        std::cerr << "Error checking config file: " << e.what() << std::endl;
    }
}

void ServerObserver::reload_config(const json& new_config) {
    // Update the stored config
    config_ = new_config;

    // Reload max_parallel_recordings with validation
    int new_max_parallel_recordings = new_config.value("max_parallel_recordings", 1);
    if (new_max_parallel_recordings < 1) {
        std::cerr << "Warning: Invalid max_parallel_recordings value "
                 << new_max_parallel_recordings << ", must be >= 1. Keeping current value." << std::endl;
    } else if (new_max_parallel_recordings != max_parallel_recordings_.load()) {
        std::cout << "Updated max_parallel_recordings: " << max_parallel_recordings_.load()
                 << " -> " << new_max_parallel_recordings << std::endl;
        max_parallel_recordings_.store(new_max_parallel_recordings);

        // Update GameFinder as well
        if (game_finder_) {
            game_finder_->set_max_parallel_recordings(new_max_parallel_recordings);
        }
    }

    // Reload update_interval with validation
    double new_update_interval = new_config.value("update_interval", 60.0);
    if (new_update_interval <= 0.0) {
        std::cerr << "Warning: Invalid update_interval value "
                 << new_update_interval << ", must be > 0. Keeping current value." << std::endl;
    } else if (new_update_interval != update_interval_) {
        update_interval_ = new_update_interval;

        // Update scheduler with new interval
        if (scheduler_) {
            scheduler_->set_update_interval(new_update_interval);
        }
    }

    // Reload GameFinder scan_interval
    if (game_finder_ && new_config.contains("scan_interval")) {
        double new_scan_interval = new_config.value("scan_interval", 30.0);
        if (new_scan_interval > 0.0) {
            game_finder_->set_scan_interval(new_scan_interval);
        }
    }

    // Reload GameFinder scenario_ids
    if (game_finder_ && new_config.contains("scenario_ids") && new_config["scenario_ids"].is_array()) {
        std::vector<int> new_scenario_ids;
        for (const auto& id : new_config["scenario_ids"]) {
            new_scenario_ids.push_back(id.get<int>());
        }
        game_finder_->set_scenario_ids(new_scenario_ids);
    }

    // Reload max_parallel_updates
    if (scheduler_ && new_config.contains("max_parallel_updates")) {
        int new_max_parallel_updates = new_config.value("max_parallel_updates", 1);
        if (new_max_parallel_updates >= 1) {
            scheduler_->set_max_parallel_updates(new_max_parallel_updates);
        }
    }

    // Reload max_parallel_first_updates
    if (scheduler_ && new_config.contains("max_parallel_first_updates")) {
        int new_max_parallel_first_updates = new_config.value("max_parallel_first_updates", 1);
        if (new_max_parallel_first_updates >= 1) {
            scheduler_->set_max_parallel_first_updates(new_max_parallel_first_updates);
        }
    }

    // Reload max_guest_games_per_account
    if (game_finder_ && new_config.contains("max_guest_games_per_account")) {
        int new_max_guest = new_config.value("max_guest_games_per_account", -1);
        game_finder_->set_max_guest_per_account(new_max_guest);
    }

    // Reload enabled_scanning
    if (game_finder_ && new_config.contains("enabled_scanning")) {
        bool new_enabled_scanning = new_config.value("enabled_scanning", true);
        game_finder_->set_enabled_scanning(new_enabled_scanning);
    }

    // Reload file_size_threshold
    if (new_config.contains("file_size_threshold")) {
        int new_file_size_threshold = new_config.value("file_size_threshold", 0);
        if (new_file_size_threshold != file_size_threshold_) {
            std::cout << "Updated file_size_threshold: " << file_size_threshold_
                     << " -> " << new_file_size_threshold << std::endl;
            std::cout << "Note: file_size_threshold change only affects new observation sessions" << std::endl;
            file_size_threshold_ = new_file_size_threshold;
        }
    }

    // Note: update_worker_threads and request_manager_threads cannot be changed at runtime
    // as they control thread pool sizes that are set during initialization
    if (new_config.contains("update_worker_threads") || new_config.contains("request_manager_threads")) {
        std::cout << "Note: update_worker_threads and request_manager_threads changes require restart to take effect" << std::endl;
    }
}

void ServerObserver::reload_config_from_file() {
    if (config_file_path_.empty()) {
        return;
    }

    try {
        // Check if config file exists
        if (!fs::exists(config_file_path_)) {
            std::cerr << "Config file not found: " << config_file_path_ << std::endl;
            return;
        }

        std::cout << "Reloading config from: " << config_file_path_ << std::endl;

        // Load the new config
        std::ifstream config_stream(config_file_path_);
        if (!config_stream.is_open()) {
            std::cerr << "Error: Could not open config file for reload: "
                     << config_file_path_ << std::endl;
            return;
        }

        json new_config;
        try {
            config_stream >> new_config;
        } catch (const std::exception& e) {
            std::cerr << "Error parsing config file during reload: " << e.what() << std::endl;
            return;
        }

        // Apply the new config
        reload_config(new_config);

        std::cout << "Config reloaded successfully" << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "Error reloading config file: " << e.what() << std::endl;
    }
}
