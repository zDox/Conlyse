#include "server_observer.hpp"
#include <iostream>
#include <iomanip>
#include <chrono>
#include <thread>
#include <filesystem>
#include <algorithm>

namespace fs = std::filesystem;

static const double THREAD_JOIN_TIMEOUT = 1.0;
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

    // Parse configuration
    if (config.contains("scenario_ids") && config["scenario_ids"].is_array()) {
        for (const auto& id : config["scenario_ids"]) {
            scenario_ids_.push_back(id.get<int>());
        }
    }
    
    max_parallel_recordings_ = config.value("max_parallel_recordings", 1);
    max_parallel_updates_ = config.value("max_parallel_updates", 1);
    max_parallel_first_updates_ = config.value("max_parallel_first_updates", 1);
    scan_interval_ = config.value("scan_interval", 30.0);
    update_interval_ = config.value("update_interval", 60.0);
    output_dir_ = config.value("output_dir", "./recordings");
    enabled_scanning_ = config.value("enabled_scanning", true);
    
    if (config.contains("max_guest_games_per_account")) {
        max_guest_per_account_ = config["max_guest_games_per_account"].get<int>();
    } else {
        max_guest_per_account_ = -1;  // No limit
    }
    
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
    
    registry_ = std::make_unique<RecordingRegistry>(registry_path);
    
    // Initialize map cache
    map_cache_ = std::make_shared<StaticMapCache>(output_dir_ + "/static_maps");
    
    // Load known games from registry
    refresh_known_games_from_registry();

    // Initialize dedicated listing interface
    initialize_listing_interface();
}

ServerObserver::~ServerObserver() {
    stop_flag_ = true;
    if (scan_thread_ && scan_thread_->joinable()) {
        scan_thread_->join();
    }
}

void ServerObserver::initialize_listing_interface() {
    try {
        if (!config_.contains("listing_account") || config_["listing_account"].is_null()) {
            std::cerr << "No listing_account configuration found. Please add a dedicated account for listing." << std::endl;
            return;
        }

        auto listing_config = config_["listing_account"];
        std::string username = listing_config.value("username", "");
        std::string password = listing_config.value("password", "");
        std::string proxy_url = listing_config.value("proxy_url", "");

        if (username.empty() || password.empty()) {
            std::cerr << "Invalid listing account configuration: missing username or password" << std::endl;
            return;
        }

        listing_interface_ = std::make_shared<HubInterfaceWrapper>(proxy_url, proxy_url);
        listing_interface_->login(username, password);

        std::cout << "Initialized dedicated listing interface with account: "
                 << username << std::endl;

    } catch (const std::exception& e) {
        std::cerr << "Failed to initialize listing interface: " << e.what() << std::endl;
        listing_interface_ = nullptr;
    }
}

std::shared_ptr<HubInterfaceWrapper> ServerObserver::get_listing_interface() {
    // Simply return the pre-initialized dedicated interface
    // No shared state with account pool interfaces
    if (!listing_interface_) {
        std::cerr << "Listing interface not initialized" << std::endl;
        // Attempt to reinitialize
        initialize_listing_interface();
    }

    return listing_interface_;
}

std::vector<std::pair<int, HubGameProperties>> ServerObserver::select_games(
    std::shared_ptr<HubInterfaceWrapper> interface) {

    std::vector<std::pair<int, HubGameProperties>> selected;
    std::set<int> seen_games;

    std::cout << "Scanning for games" << std::endl;

    try {
        auto games = interface->get_global_games();

        for (int scenario_id : scenario_ids_) {
            std::vector<HubGameProperties> new_candidates;

            for (const auto& game : games) {
                if (game.scenario_id == scenario_id &&
                    known_games_.find(game.game_id) == known_games_.end()) {
                    new_candidates.push_back(game);
                }
            }

            std::vector<HubGameProperties> joinable;
            for (const auto& game : new_candidates) {
                if (game.open_slots >= 1) {
                    joinable.push_back(game);
                }
            }

            std::cout << "Scenario " << scenario_id << ": " << new_candidates.size()
                     << " new games, " << joinable.size()
                     << " potentially joinable before sampling" << std::endl;

            for (const auto& game : joinable) {
                if (seen_games.find(game.game_id) != seen_games.end()) {
                    continue;
                }
                seen_games.insert(game.game_id);
                selected.emplace_back(scenario_id, game);
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "Error selecting games: " << e.what() << std::endl;
    }

    return selected;
}

void ServerObserver::refresh_known_games_from_registry() {
    known_games_.clear();

    auto active = registry_->active();
    for (const auto& [game_id, meta] : active) {
        known_games_.insert(game_id);
    }
}

std::shared_ptr<Account> ServerObserver::pick_account() {
    if (!account_pool_) {
        return nullptr;
    }

    // Simply get the next available guest account
    // No need to check against listing_account_ since listing interface is separate
    auto account = account_pool_->next_guest_account(max_guest_per_account_);

    if (!account) {
        std::cerr << "No free account available to start new observation" << std::endl;
    }

    return account;
}

void ServerObserver::start_observation_session(int game_id, int scenario_id) {
    auto account = pick_account();
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
        game_id,
        account,
        map_cache_,
        output_dir_ + "/game_" + std::to_string(game_id),
        metadata_path,
        long_term_storage_path_,
        file_size_threshold_
    );

    registry_->mark_recording(game_id, scenario_id, "");
    known_games_.insert(game_id);

    if (account_pool_) {
        account_pool_->increment_guest_join(account);
    }

    observer->next_update_at = std::chrono::system_clock::now();

    {
        std::lock_guard<std::mutex> lock(threads_lock_);
        first_update_sessions_.insert(game_id);
    }

    {
        std::lock_guard<std::mutex> lock(queue_lock_);
        update_queue_.push(observer.get());
    }

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

void ServerObserver::run_single_update(ObservationSession* session) {
    int game_id = session->game_id;
    int attempt = 1;

    while (true) {
        try {
            auto worker = session->create_worker();
            bool keep_running = worker->run();
            session->update_package(worker->get_package());
            std::cout << "Finished update for game " << game_id << std::endl;
            malloc_trim(0);

            // Increment update counter and record timestamp
            total_updates_completed_++;
            {
                std::lock_guard<std::mutex> lock(stats_lock_);
                update_timestamps_.push_back(std::chrono::system_clock::now());
            }

            if (keep_running) {
                // Schedule next update based on the previous scheduled time, not current time
                // This ensures we maintain the actual update_interval_ between updates
                session->next_update_at = session->next_update_at +
                    std::chrono::seconds(static_cast<int>(update_interval_));

                std::lock_guard<std::mutex> lock(queue_lock_);
                update_queue_.push(session);
            } else {
                std::cout << "Finished recording game " << game_id << std::endl;
                registry_->mark_completed(game_id);
                if (account_pool_) {
                    account_pool_->decrement_guest_join(session->account);
                }

                {
                    std::lock_guard<std::mutex> lock(sessions_lock_);
                    observer_sessions_.erase(game_id);
                }

                known_games_.insert(game_id);
            }

            {
                std::lock_guard<std::mutex> lock(threads_lock_);
                first_update_sessions_.erase(game_id);
                running_first_updates_.erase(game_id);
                active_threads_.erase(std::this_thread::get_id());
            }

            break;  // Success

        } catch (const std::exception& e) {
            if (attempt < MAX_UPDATE_RETRIES) {
                std::cerr << "Observation for game " << game_id
                         << " failed, retrying attempt " << attempt
                         << "/" << MAX_UPDATE_RETRIES << "..." << std::endl;
                attempt++;
                continue;
            }

            std::cerr << "Observation for game " << game_id
                     << " failed after " << MAX_UPDATE_RETRIES
                     << " retries, marking as failed." << std::endl;

            registry_->mark_failed(game_id, e.what());

            if (account_pool_) {
                account_pool_->decrement_guest_join(session->account);
            }

            {
                std::lock_guard<std::mutex> lock(sessions_lock_);
                observer_sessions_.erase(game_id);
            }

            known_games_.insert(game_id);

            {
                std::lock_guard<std::mutex> lock(threads_lock_);
                first_update_sessions_.erase(game_id);
                running_first_updates_.erase(game_id);
                active_threads_.erase(std::this_thread::get_id());
            }

            break;
        }
    }
}

void ServerObserver::start_due_updates() {
    auto now = std::chrono::system_clock::now();
    std::vector<ObservationSession*> deferred;

    while (true) {
        {
            std::lock_guard<std::mutex> lock(threads_lock_);
            if (active_threads_.size() >= static_cast<size_t>(max_parallel_updates_)) {
                break;
            }
        }

        ObservationSession* observer = nullptr;
        {
            std::lock_guard<std::mutex> lock(queue_lock_);
            if (update_queue_.empty()) {
                break;
            }
            observer = update_queue_.front();
            update_queue_.pop();
        }

        if (!observer->needs_update(now)) {
            deferred.push_back(observer);
            continue;
        }

        // Check first-update limit
        {
            std::lock_guard<std::mutex> lock(threads_lock_);
            const bool is_first_update = first_update_sessions_.find(observer->game_id) !=
                                   first_update_sessions_.end();

            if (is_first_update) {
                // Count currently running first updates using the tracking set
                int running_first_updates_count = static_cast<int>(running_first_updates_.size());

                if (running_first_updates_count >= max_parallel_first_updates_) {
                    std::cout << "Deferring first update for game " << observer->game_id
                             << " due to max parallel first updates limit (currently running: "
                             << running_first_updates_count << ")." << std::endl;
                    deferred.push_back(observer);
                    continue;
                }

                // Mark this game as now running its first update
                running_first_updates_.insert(observer->game_id);
            }
        }

        std::cout << "Starting thread for game " << observer->game_id << std::endl;

        // Start update thread
        std::thread thread([this, observer]() {
            run_single_update(observer);
        });

        {
            std::lock_guard<std::mutex> lock(threads_lock_);
            active_threads_.insert(thread.get_id());
        }

        thread.detach();
    }

    // Re-queue deferred updates
    {
        std::lock_guard<std::mutex> lock(queue_lock_);
        for (auto* observer : deferred) {
            update_queue_.push(observer);
        }
    }

    // If we have deferred updates, wait a bit
    if (!deferred.empty()) {
        double min_wait = update_interval_;
        for (auto* obs : deferred) {
            auto wait_duration = obs->next_update_at - now;
            double wait_seconds = std::chrono::duration<double>(wait_duration).count();
            if (wait_seconds > 0 && wait_seconds < min_wait) {
                min_wait = wait_seconds;
            }
        }

        if (min_wait > 0) {
            std::cout << "Waiting " << min_wait
                     << " seconds for next due update..." << std::endl;
            std::this_thread::sleep_for(
                std::chrono::duration<double>(std::min(min_wait, update_interval_)));
        }
    }
}

void ServerObserver::clean_finished_threads() {
    // Threads clean themselves up in run_single_update by removing from active_threads_
}

void ServerObserver::scan_loop() {
    auto interface = get_listing_interface();

    if (!interface) {
        std::cerr << "Cannot start scan loop: listing interface not available" << std::endl;
        return;
    }

    while (!stop_flag_) {
        if (enabled_scanning_) {
            auto games = select_games(interface);

            for (const auto& [scenario_id, game] : games) {
                {
                    std::lock_guard<std::mutex> lock(sessions_lock_);
                    if (observer_sessions_.find(game.game_id) != observer_sessions_.end()) {
                        continue;
                    }

                    if (observer_sessions_.size() >= static_cast<size_t>(max_parallel_recordings_)) {
                        continue;
                    }
                }

                start_observation_session(game.game_id, scenario_id);
            }
        }

        std::this_thread::sleep_for(std::chrono::duration<double>(scan_interval_));
    }
}

void ServerObserver::print_update_statistics() {
    auto now = std::chrono::system_clock::now();

    std::lock_guard<std::mutex> lock(stats_lock_);

    // Calculate time since last print
    auto duration_since_last = std::chrono::duration_cast<std::chrono::seconds>(
        now - last_stats_print_time_).count();

    // Only print every 60 seconds
    if (duration_since_last < 60) {
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

    // Start scan thread
    scan_thread_ = std::make_unique<std::thread>([this]() {
        try {
            scan_loop();
        } catch (const std::exception& e) {
            std::cerr << "ERROR: Scan thread crashed with exception: " << e.what() << std::endl;
        } catch (...) {
            std::cerr << "ERROR: Scan thread crashed with unknown exception" << std::endl;
        }
    });

    try {
        while (!stop_flag_) {
            clean_finished_threads();
            start_due_updates();
            print_update_statistics();
        }
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Error in main loop: " << e.what() << std::endl;
        stop_flag_ = true;

        if (scan_thread_ && scan_thread_->joinable()) {
            scan_thread_->join();
        }

        return false;
    }
}