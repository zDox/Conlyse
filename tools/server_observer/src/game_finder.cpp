#include "game_finder.hpp"
#include <iostream>

GameFinder::GameFinder(
    const json& config,
    std::shared_ptr<AccountPool> account_pool,
    std::shared_ptr<RecordingRegistry> registry)
    : config_(config)
    , account_pool_(account_pool)
    , registry_(registry)
    , listing_interface_(nullptr)
    , observation_starter_(nullptr)
    , active_session_counter_(nullptr)
    , stop_flag_(false)
{
    // Parse configuration
    if (config.contains("scenario_ids") && config["scenario_ids"].is_array()) {
        for (const auto& id : config["scenario_ids"]) {
            scenario_ids_.push_back(id.get<int>());
        }
    }

    scan_interval_ = config.value("scan_interval", 30.0);
    enabled_scanning_ = config.value("enabled_scanning", true);
    max_parallel_recordings_ = config.value("max_parallel_recordings", 1);

    if (config.contains("max_guest_games_per_account")) {
        max_guest_per_account_ = config["max_guest_games_per_account"].get<int>();
    } else {
        max_guest_per_account_ = -1;  // No limit
    }

    // Load known games from registry
    refresh_known_games_from_registry();

    // Initialize dedicated listing interface
    initialize_listing_interface();
}

GameFinder::~GameFinder() {
    // Stop scanning thread if running
    stop_scanning();

    // Clear the listing interface (contains Python objects)
    if (listing_interface_) {
        listing_interface_.reset();
    }
}

void GameFinder::set_observation_starter(ObservationSessionStarter starter) {
    observation_starter_ = starter;
}

void GameFinder::set_active_session_counter(ActiveSessionCounter counter) {
    active_session_counter_ = counter;
}

void GameFinder::start_scanning() {
    if (!enabled_scanning_) {
        std::cout << "Scanning is disabled, not starting scan thread" << std::endl;
        return;
    }

    if (scan_thread_ && scan_thread_->joinable()) {
        std::cerr << "Scan thread already running" << std::endl;
        return;
    }

    stop_flag_ = false;
    scan_thread_ = std::make_unique<std::thread>([this]() {
        try {
            scan_loop();
        } catch (const std::exception& e) {
            std::cerr << "ERROR: GameFinder scan thread crashed with exception: " << e.what() << std::endl;
        } catch (...) {
            std::cerr << "ERROR: GameFinder scan thread crashed with unknown exception" << std::endl;
        }
    });

    std::cout << "GameFinder scan thread started" << std::endl;
}

void GameFinder::stop_scanning() {
    if (!scan_thread_) {
        return;
    }

    std::cout << "Stopping GameFinder scan thread..." << std::endl;
    stop_flag_ = true;

    if (scan_thread_->joinable()) {
        scan_thread_->join();
    }

    scan_thread_.reset();
    std::cout << "GameFinder scan thread stopped" << std::endl;
}

void GameFinder::scan_loop() {
    while (!stop_flag_) {
        if (enabled_scanning_) {
            // Get current number of active sessions
            size_t active_sessions = 0;
            if (active_session_counter_) {
                active_sessions = active_session_counter_();
            }

            // Scan and start games
            scan_and_start_games(active_sessions, max_parallel_recordings_);
        }

        // Sleep for scan interval (check stop flag more frequently)
        auto sleep_duration = std::chrono::duration<double>(scan_interval_);
        auto sleep_start = std::chrono::steady_clock::now();
        auto sleep_end = sleep_start + sleep_duration;

        while (!stop_flag_ && std::chrono::steady_clock::now() < sleep_end) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
    }
}

void GameFinder::initialize_listing_interface() {
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
}

std::shared_ptr<HubInterfaceWrapper> GameFinder::get_listing_interface() {
    if (!listing_interface_) {
        std::cerr << "Listing interface not initialized" << std::endl;
        // Attempt to reinitialize
        initialize_listing_interface();
    }

    return listing_interface_;
}

std::vector<std::pair<int, HubGameProperties>> GameFinder::select_games(
    std::shared_ptr<HubInterfaceWrapper> interface) {

    std::vector<std::pair<int, HubGameProperties>> selected;
    std::set<int> seen_games;

    std::cout << "Scanning for games" << std::endl;

    try {
        auto games = interface->get_global_games();

        for (int scenario_id : scenario_ids_) {
            std::vector<HubGameProperties> new_candidates;

            {
                std::lock_guard<std::mutex> lock(known_games_mutex_);
                for (const auto& game : games) {
                    if (game.scenario_id == scenario_id &&
                        known_games_.find(game.game_id) == known_games_.end()) {
                        new_candidates.push_back(game);
                    }
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

void GameFinder::refresh_known_games_from_registry() {
    std::lock_guard<std::mutex> lock(known_games_mutex_);
    known_games_.clear();

    auto active = registry_->active();
    for (const auto& [game_id, meta] : active) {
        known_games_.insert(game_id);
    }
}

std::shared_ptr<Account> GameFinder::pick_account() {
    if (!account_pool_) {
        return nullptr;
    }

    // Simply get the next available guest account
    auto account = account_pool_->next_guest_account(max_guest_per_account_);

    if (!account) {
        std::cerr << "No free account available to start new observation" << std::endl;
    }

    return account;
}

void GameFinder::scan_and_start_games(size_t max_active_sessions, size_t max_parallel_recordings) {
    if (!enabled_scanning_) {
        return;
    }

    auto interface = get_listing_interface();
    if (!interface) {
        std::cerr << "Cannot scan: listing interface not available" << std::endl;
        return;
    }

    auto games = select_games(interface);

    for (const auto& [scenario_id, game] : games) {
        // Check if we've already reached the max parallel recordings
        if (max_active_sessions >= max_parallel_recordings) {
            std::cout << "Maximum parallel recordings reached. Skipping remaining games." << std::endl;
            break;
        }

        // Start the observation session via callback
        if (observation_starter_) {
            observation_starter_(game.game_id, scenario_id);
            max_active_sessions++;  // Update local counter

            // Mark the game as known so we don't try to start it again
            mark_game_known(game.game_id);
        } else {
            std::cerr << "Warning: No observation starter callback set" << std::endl;
        }
    }
}

void GameFinder::mark_game_known(int game_id) {
    std::lock_guard<std::mutex> lock(known_games_mutex_);
    known_games_.insert(game_id);
}

void GameFinder::set_scan_interval(double interval) {
    if (interval > 0.0) {
        scan_interval_ = interval;
        std::cout << "GameFinder: Updated scan_interval to " << interval << " seconds" << std::endl;
    } else {
        std::cerr << "GameFinder: Invalid scan_interval " << interval << ", must be > 0" << std::endl;
    }
}

void GameFinder::set_scenario_ids(const std::vector<int>& scenario_ids) {
    scenario_ids_ = scenario_ids;
    std::cout << "GameFinder: Updated scenario_ids to [";
    for (size_t i = 0; i < scenario_ids.size(); ++i) {
        if (i > 0) std::cout << ", ";
        std::cout << scenario_ids[i];
    }
    std::cout << "]" << std::endl;
}

void GameFinder::set_max_parallel_recordings(int max_recordings) {
    if (max_recordings >= 1) {
        max_parallel_recordings_ = max_recordings;
        std::cout << "GameFinder: Updated max_parallel_recordings to " << max_recordings << std::endl;
    } else {
        std::cerr << "GameFinder: Invalid max_parallel_recordings " << max_recordings 
                 << ", must be >= 1" << std::endl;
    }
}
