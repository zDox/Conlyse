#include "server_observer.hpp"
#include "game_finder.hpp"
#include <iostream>
#include <iomanip>
#include <chrono>
#include <algorithm>

namespace fs = std::filesystem;

static const int MAX_UPDATE_RETRIES = 3;

ServerObserver::ServerObserver(const json& config, std::shared_ptr<AccountPool> account_pool)
    : config_(config)
    , account_pool_(account_pool)
    , stop_flag_(false)
    , total_updates_completed_(0)
{
    // Initialize statistics timing
    stats_start_time_ = std::chrono::system_clock::now();
    last_stats_print_time_ = stats_start_time_;

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
        config.value("request_manager_threads", 1),
        config.value("max_in_flight_requests", 100)
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
    game_finder_->set_observation_starter([this](int game_id, int scenario_id) {
        this->start_observation_session(game_id, scenario_id);
    });

    // Set the callback for getting active session count
    game_finder_->set_active_session_counter([this]() -> size_t {
        std::lock_guard<std::mutex> lock(sessions_lock_);
        return observer_sessions_.size();
    });
}

ServerObserver::~ServerObserver() {
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
    auto account = account_pool_ ? account_pool_->next_guest_account(-1) : nullptr;
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

    if (account_pool_) {
        account_pool_->increment_guest_join(account);
    }

    observer->next_update_at = std::chrono::system_clock::now();

    // Mark as first update and schedule
    scheduler_->mark_first_update(game_id);
    scheduler_->schedule_update(observer.get());

    observer_sessions_[game_id] = std::move(observer);
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

        if (observer_sessions_.find(game_id) != observer_sessions_.end()) {
            continue;
        }

        std::cout << "Resuming observation for game " << game_id << std::endl;

        if (observer_sessions_.size() >= static_cast<size_t>(max_parallel_recordings_)) {
            std::cerr << "Skipping resume for game " << game_id
                     << " due to max parallel limit reached " << observer_sessions_.size() << "observations"<< std::endl;
            continue;
        }

        int scenario_id = meta["scenario_id"].get<int>();
        start_observation_session(game_id, scenario_id);
    }
}

asio::awaitable<void> ServerObserver::run_single_update_async(ObservationSession* session) {
    int game_id = session->game_id;

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

    // Release account resources
    if (account_pool_) {
        account_pool_->decrement_guest_join(session->account);
    }

    // Remove session from active tracking
    {
        std::lock_guard lock(sessions_lock_);
        observer_sessions_.erase(game_id);
    }

    // Mark game as known in the game finder
    if (game_finder_) {
        game_finder_->mark_game_known(game_id);
    }
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
        return;
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

    // Only print every 60 seconds
    if (duration_since_last < 30) {
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
    std::cout << "=========================" << std::endl;

    last_stats_print_time_ = now;
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