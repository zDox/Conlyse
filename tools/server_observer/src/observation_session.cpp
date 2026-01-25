#include "observation_session.hpp"
#include <iostream>
#include <thread>
#include <chrono>
#include <utility>

static const int MAX_RETRIES = 3;
static const int TIME_TILL_RETRY = 10;

json ObservationPackage::to_json() const {
    json j = {
        {"game_id", game_id},
        {"headers", headers},
        {"cookies", cookies},
        {"proxy", proxy},
        {"auth", auth.to_json()},
        {"client_version", client_version},
        {"game_server_address", game_server_address}
    };

    // Convert time_stamps map to JSON
    json ts = json::object();
    for (const auto &[key, value]: time_stamps) {
        ts[key] = value;
    }
    j["time_stamps"] = ts;

    // Convert state_ids map to JSON
    json si = json::object();
    for (const auto &[key, value]: state_ids) {
        si[key] = value;
    }
    j["state_ids"] = si;

    return j;
}

ObservationPackage ObservationPackage::from_json(const json &j) {
    ObservationPackage pkg;
    pkg.game_id = j.value("game_id", 0);
    pkg.headers = j.value("headers", json::object());
    pkg.cookies = j.value("cookies", json::object());
    pkg.proxy = j.value("proxy", json::object());
    pkg.client_version = j.value("client_version", 207);
    pkg.game_server_address = j.value("game_server_address", "");

    if (j.contains("auth")) {
        pkg.auth = AuthDetails::from_json(j["auth"]);
    }

    // Convert time_stamps from JSON to map
    if (j.contains("time_stamps") && j["time_stamps"].is_object()) {
        for (const auto &[key, value]: j["time_stamps"].items()) {
            try {
                pkg.time_stamps[key] = value.get<std::string>();
            } catch (...) {
            }
        }
    }

    // Convert state_ids from JSON to map
    if (j.contains("state_ids") && j["state_ids"].is_object()) {
        for (const auto &[key, value]: j["state_ids"].items()) {
            try {
                pkg.state_ids[key] = value.get<std::string>();
            } catch (...) {
            }
        }
    }

    return pkg;
}

ObservationSession::ObservationSession(
    std::shared_ptr<RequestManager> manager,
    int game_id,
    std::shared_ptr<Account> account,
    std::shared_ptr<StaticMapCache> map_cache,
    std::string storage_path,
    std::string metadata_path,
    std::string long_term_storage_path,
    int file_size_threshold)
    : game_id(game_id)
      , account(std::move(account))
      , manager_(std::move(manager))
      , map_cache_(std::move(map_cache))
      , storage_path_(std::move(storage_path))
      , metadata_path_(std::move(metadata_path))
      , long_term_storage_path_(std::move(long_term_storage_path))
      , file_size_threshold_(file_size_threshold)
      , package_(), storage_(nullptr), api_(nullptr) {
    next_update_at = std::chrono::system_clock::now();
}

ObservationSession::~ObservationSession() {
    if (storage_) {
        storage_->teardown_logging();
    }
}

bool ObservationSession::needs_update(std::chrono::system_clock::time_point now) const {
    return now >= next_update_at;
}

void ObservationSession::on_request_response(json &&response) {
    ensure_storage()->update_resume_metadata(package_.to_json());
    ensure_storage()->save_response(std::move(response));
}

bool ObservationSession::ensure_observation_package() {
    if (package_.game_id != 0) {
        return true;
    }

    json resume_metadata = ensure_storage()->get_resume_metadata();
    if (!resume_metadata.empty() && resume_metadata.contains("auth")) {
        std::cout << "Resuming from Storage for game " << game_id << std::endl;
        package_ = ObservationPackage::from_json(resume_metadata);
        api_ = std::make_unique<ObservationApi>(
            manager_,
            package_.headers,
            package_.cookies,
            package_.proxy,
            package_.auth,
            game_id,
            package_.game_server_address,
            package_.client_version);
        return true;
    }

    std::cout << "Observation package not yet created, building package for game "
            << game_id << std::endl;
    package_ = create_observation_package();
    return package_.game_id != 0;
}

ObservationPackage ObservationSession::create_observation_package() {
    auto hub_itf = account->get_interface();
    if (!hub_itf) {
        return {};
    }

    // Join the game as guest and load game site to get server address and auth
    std::cout << "Joining game " << game_id << " as guest to get game server data..." << std::endl;

    try {
        auto game_data = hub_itf->join_game_as_guest(game_id);

        // Build proxy dict
        json proxy = json::object();
        if (!hub_itf->get_proxy_http().empty()) {
            proxy["http"] = hub_itf->get_proxy_http();
        }
        if (!hub_itf->get_proxy_https().empty()) {
            proxy["https"] = hub_itf->get_proxy_https();
        }

        // Create an observation package with data from GameApi
        ObservationPackage pkg;
        pkg.game_id = game_id;
        pkg.headers = game_data.headers;
        pkg.cookies = game_data.cookies;
        pkg.proxy = proxy;
        pkg.auth = game_data.auth;
        pkg.client_version = game_data.client_version;
        pkg.game_server_address = game_data.game_server_address;

        std::cout << "Successfully joined game " << game_id << std::endl;
        std::cout << "  Game server: " << pkg.game_server_address << std::endl;
        std::cout << "  Client version: " << pkg.client_version << std::endl;
        std::cout << "  Map ID: " << game_data.map_id << std::endl;

        api_ = std::make_unique<ObservationApi>(
            manager_,
            pkg.headers,
            pkg.cookies,
            pkg.proxy,
            pkg.auth,
            game_id,
            pkg.game_server_address,
            pkg.client_version);
        return pkg;
    } catch (const std::exception &e) {
        std::cerr << "Failed to join game " << game_id << ": " << e.what() << std::endl;
        return {};
    }
}

void ObservationSession::reset_package() {
    account->reset_interface();
    package_ = create_observation_package();
}

bool ObservationSession::ensure_static_map_data(ObservationApi &api, int map_id) {
    if (map_cache_->is_cached(map_id)) {
        return true;
    }

    try {
        json static_map_data = api.get_static_map_data(map_id);
        map_cache_->save(map_id, static_map_data);
        return true;
    } catch (const std::exception &e) {
        std::cerr << "Failed to get static map data: " << e.what() << std::endl;
        return false;
    }
}

bool ObservationSession::is_game_ended(const json &response) {
    if (!response.is_object()) {
        return false;
    }

    if (!response.contains("result") || !response["result"].is_object()) {
        return false;
    }

    const auto &result = response["result"];
    if (!result.contains("states") || !result["states"].is_object()) {
        return false;
    }

    const auto &states = result["states"];
    for (const auto &[key, state]: states.items()) {
        if (state.is_object() && state.contains("gameEnded") &&
            state["gameEnded"].is_boolean() && state["gameEnded"].get<bool>()) {
            return true;
        }
    }

    return false;
}

bool ObservationSession::run_update() {
    int attempt = 1;

    // Setup storage logging
    ensure_storage()->setup_logging();

    while (true) {
        std::cout << "Starting update for game " << game_id << std::endl;

        if (!ensure_observation_package()) {
            std::cerr << "Failed to create observation package" << std::endl;
            ensure_storage()->teardown_logging();
            return false;
        }

        try {
            // Fetch game state
            json game_state = api_->request_game_state(package_.state_ids, package_.time_stamps);

            // Update package with new auth and connection details
            package_.auth = api_->get_auth();
            package_.cookies = api_->get_cookies();
            package_.headers = api_->get_headers();
            package_.game_server_address = api_->get_game_server_address();

            // Check if game ended before processing and moving the JSON.
            // We store the result now because game_state will be moved below.
            bool game_ended = is_game_ended(game_state);
            std::cout << "Game ended status: " << (game_ended ? "true" : "false") << std::endl;
            // Extract map ID before moving game_state (if we need it).
            // This avoids accessing the JSON after it's been moved.
            std::string map_id_to_fetch = "-1";
            try {
                if (game_state.contains("result") && game_state["result"].is_object()) {
                    const auto &result = game_state["result"];
                    if (result.contains("states") && result["states"].is_object()) {
                        const auto &states = result["states"];
                        if (states.contains("3") && states["3"].is_object()) {
                            const auto &state3 = states["3"];
                            if (state3.contains("map") && state3["map"].is_object()) {
                                const auto &map = state3["map"];
                                if (map.contains("mapID")) {
                                    map_id_to_fetch = map["mapID"].get<std::string>();
                                }
                            }
                        }
                    }
                }
            } catch (const std::exception &e) {
                // Map data not available or invalid
            }

            // Save response and release the large JSON immediately.
            // After this point, game_state is in a moved-from state and should not be accessed.
            on_request_response(std::move(game_state));

            // Fetch map data if needed (safe to do after game_state is moved)
            if (map_id_to_fetch != "-1") {
                // ensure_static_map_data(api, map_id_to_fetch);
            }

            // Teardown storage logging before returning
            ensure_storage()->teardown_logging();

            // Check if game ended (using the bool we stored before the move)
            if (game_ended) {
                return false;
            }

            return true;
        } catch (const std::runtime_error &e) {
            std::string error = e.what();

            // Handle authentication failure
            if (error.find("Authentication failed") != std::string::npos) {
                if (attempt >= MAX_RETRIES) {
                    std::cerr << "Authentication failed after " << MAX_RETRIES
                            << " retries" << std::endl;
                    ensure_storage()->teardown_logging();
                    return false;
                }

                std::cerr << "Authentication failed, resetting package and retrying..."
                        << std::endl;
                reset_package();
                attempt++;
                continue;
            }

            // Handle server errors
            if (error.find("HTTP status: 5") != std::string::npos) {
                std::cerr << "GameServer returned error, retrying in "
                        << TIME_TILL_RETRY << " seconds..." << std::endl;
                std::this_thread::sleep_for(std::chrono::seconds(TIME_TILL_RETRY));
                continue;
            }

            // Handle network errors
            if (error.find("failed") != std::string::npos ||
                error.find("timeout") != std::string::npos) {
                std::cerr << "GameServer is not responding, resetting package and retrying..." << std::endl;
                reset_package();
                attempt++;
                continue;
            }

            // Unknown error
            ensure_storage()->teardown_logging();
            throw;
        }
    }
}

void ObservationSession::reset() {
    package_ = ObservationPackage();
    ensure_storage()->update_resume_metadata(json::object());
}

RecordingStorage *ObservationSession::ensure_storage() {
    if (!storage_) {
        storage_ = std::make_unique<RecordingStorage>(
            storage_path_,
            metadata_path_,
            long_term_storage_path_,
            file_size_threshold_
        );
    }
    return storage_.get();
}
