#include "observation_session.hpp"
#include <iostream>
#include <thread>
#include <chrono>
#include <utility>

static const int MAX_RETRIES = 3;
static const int TIME_TILL_RETRY = 10;

json ObservationPackage::to_json() const {
    // Convert headers map to JSON
    json headers_json = json::object();
    for (const auto &[key, value]: headers) {
        headers_json[key] = value;
    }

    // Convert cookies map to JSON
    json cookies_json = json::object();
    for (const auto &[key, value]: cookies) {
        cookies_json[key] = value;
    }

    // Convert ProxyConfig to JSON
    json proxy_json = json::object();
    if (proxy.enabled) {
        proxy_json["host"] = proxy.host;
        proxy_json["port"] = proxy.port;
        if (!proxy.username.empty()) {
            proxy_json["username"] = proxy.username;
        }
        if (!proxy.password.empty()) {
            proxy_json["password"] = proxy.password;
        }
    }

    json j = {
        {"game_id", game_id},
        {"headers", headers_json},
        {"cookies", cookies_json},
        {"proxy", proxy_json},
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
    pkg.client_version = j.value("client_version", 207);
    pkg.game_server_address = j.value("game_server_address", "");

    // Convert headers from JSON to map
    if (j.contains("headers") && j["headers"].is_object()) {
        for (const auto &[key, value]: j["headers"].items()) {
            try {
                pkg.headers[key] = value.get<std::string>();
            } catch (...) {
            }
        }
    }

    // Convert cookies from JSON to map
    if (j.contains("cookies") && j["cookies"].is_object()) {
        for (const auto &[key, value]: j["cookies"].items()) {
            try {
                pkg.cookies[key] = value.get<std::string>();
            } catch (...) {
            }
        }
    }

    // Convert proxy from JSON to ProxyConfig
    if (j.contains("proxy") && j["proxy"].is_object()) {
        const auto &proxy_json = j["proxy"];
        if (proxy_json.contains("host") && proxy_json.contains("port")) {
            pkg.proxy.enabled = true;
            pkg.proxy.host = proxy_json["host"].get<std::string>();
            pkg.proxy.port = proxy_json["port"].get<int>();
            if (proxy_json.contains("username")) {
                pkg.proxy.username = proxy_json["username"].get<std::string>();
            }
            if (proxy_json.contains("password")) {
                pkg.proxy.password = proxy_json["password"].get<std::string>();
            }
        }
    }

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
      , package_(), storage_(nullptr), api_(nullptr), attempt_(1) {
    next_update_at = std::chrono::system_clock::now();
}

ObservationSession::~ObservationSession() {
    if (storage_) {
        storage_->flush_metadata();  // Save metadata when session closes
        storage_->teardown_logging();
    }
}

bool ObservationSession::needs_update(std::chrono::system_clock::time_point now) const {
    return now >= next_update_at;
}

void ObservationSession::on_request_response(std::string &&response_str) {
    ensure_storage()->update_resume_metadata(package_.to_json());
    ensure_storage()->save_response(std::move(response_str));
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

        // Convert JSON headers to std::map
        std::map<std::string, std::string> headers_map;
        if (game_data.headers.is_object()) {
            for (const auto &[key, value]: game_data.headers.items()) {
                if (value.is_string()) {
                    headers_map[key] = value.get<std::string>();
                }
            }
        }

        // Convert JSON cookies to std::map
        std::map<std::string, std::string> cookies_map;
        if (game_data.cookies.is_object()) {
            for (const auto &[key, value]: game_data.cookies.items()) {
                if (value.is_string()) {
                    cookies_map[key] = value.get<std::string>();
                }
            }
        }

        // Build ProxyConfig from proxy strings
        ProxyConfig proxy_config;
        std::string proxy_https = hub_itf->get_proxy_https();
        if (!proxy_https.empty()) {
            // Parse proxy URL format: http://[username:password@]host:port
            size_t proto_end = proxy_https.find("://");
            if (proto_end != std::string::npos) {
                std::string proxy_part = proxy_https.substr(proto_end + 3);

                // Check for authentication
                size_t at_pos = proxy_part.find('@');
                if (at_pos != std::string::npos) {
                    std::string auth_part = proxy_part.substr(0, at_pos);
                    proxy_part = proxy_part.substr(at_pos + 1);

                    size_t colon_pos = auth_part.find(':');
                    if (colon_pos != std::string::npos) {
                        proxy_config.username = auth_part.substr(0, colon_pos);
                        proxy_config.password = auth_part.substr(colon_pos + 1);
                    }
                }

                // Parse host:port
                size_t colon_pos = proxy_part.find(':');
                if (colon_pos != std::string::npos) {
                    proxy_config.host = proxy_part.substr(0, colon_pos);
                    proxy_config.port = std::stoi(proxy_part.substr(colon_pos + 1));
                    proxy_config.enabled = true;
                }
            }
        }

        // Create an observation package with data from GameApi
        ObservationPackage pkg;
        pkg.game_id = game_id;
        pkg.headers = headers_map;
        pkg.cookies = cookies_map;
        pkg.proxy = proxy_config;
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
    if (storage_) {
        storage_->flush_metadata();  // Save metadata when package is reset
    }
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

asio::awaitable<bool> ObservationSession::run_update_async() {
    std::cout << "Starting update for game " << game_id << " (attempt " << attempt_ << ")" << std::endl;

    // Setup storage logging
    ensure_storage()->setup_logging();

    if (!ensure_observation_package()) {
        std::cerr << "Failed to create observation package" << std::endl;
        ensure_storage()->teardown_logging();
        co_return false;
    }

    try {
        // Fetch game state asynchronously (returns raw HTTP response)
        HttpResponse response = co_await api_->request_game_state_async(package_.state_ids, package_.time_stamps);

        // Parse and validate response, extracting state metadata
        GameServerResult result = api_->parse_and_validate_response(response, package_.state_ids, package_.time_stamps);

        // Check if the request was successful
        if (!result.success()) {
            throw std::runtime_error(result.error_message);
        }

        // Update package with new auth and connection details
        package_.auth = api_->get_auth();
        package_.cookies = api_->get_cookies();
        package_.headers = api_->get_headers();
        package_.game_server_address = api_->get_game_server_address();

        // Save raw response string to storage.
        // We move the raw string to storage, avoiding the need to dump JSON.
        on_request_response(std::move(result.raw_response));

        // Teardown storage logging before returning
        ensure_storage()->teardown_logging();

        // Reset attempt counter on success
        attempt_ = 1;

        // Check if game ended (extracted during simdjson parsing)
        if (result.game_ended) {
            co_return false;
        }

        co_return true;
    } catch (const std::runtime_error &e) {
        std::string error = e.what();

        // Handle authentication failure
        if (error.find("Authentication failed") != std::string::npos) {
            if (attempt_ >= MAX_RETRIES) {
                std::cerr << "Authentication failed after " << MAX_RETRIES
                        << " retries" << std::endl;
                ensure_storage()->teardown_logging();
                co_return false;
            }

            std::cerr << "Authentication failed, resetting package and will retry..."
                    << std::endl;
            reset_package();
            attempt_++;
            ensure_storage()->teardown_logging();
            co_return true; // Return true to indicate session should be requeued
        }

        // Handle server errors
        if (error.find("HTTP status: 5") != std::string::npos) {
            std::cerr << "GameServer returned error, will retry in "
                    << TIME_TILL_RETRY << " seconds..." << std::endl;
            ensure_storage()->teardown_logging();
            co_return true; // Return true to indicate session should be requeued
        }

        // Handle network errors
        if (error.find("failed") != std::string::npos ||
            error.find("timeout") != std::string::npos) {
            std::cerr << "GameServer is not responding, resetting package and will retry..." << std::endl;
            reset_package();
            attempt_++;
            ensure_storage()->teardown_logging();
            co_return true; // Return true to indicate session should be requeued
        }

        // Unknown error - don't retry
        ensure_storage()->teardown_logging();
        throw;
    }
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
