#include "observation_session.hpp"
#include "observation_api.hpp"
#include <iostream>
#include <thread>
#include <chrono>
#include <utility>

static const int MAX_RETRIES = 3;
static const int TIME_TILL_RETRY = 10;


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

void ObservationSession::set_proxy(const ProxyConfig& proxy_config) {
    package_.proxy = proxy_config;
}

bool ObservationSession::needs_update(std::chrono::system_clock::time_point now) const {
    return now >= next_update_at;
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
            account->proxy_config,
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

        // Create an observation package with data from GameApi
        ObservationPackage pkg;
        pkg.game_id = game_id;
        pkg.headers = headers_map;
        pkg.cookies = cookies_map;
        pkg.proxy = *account->proxy_config;
        pkg.auth = game_data.auth;
        pkg.client_version = game_data.client_version;
        pkg.game_server_address = game_data.game_server_address;

        api_ = std::make_unique<ObservationApi>(
            manager_,
            pkg.headers,
            pkg.cookies,
            account->proxy_config,
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

asio::awaitable<ObservationResult> ObservationSession::run_update_async() {
    std::cout << "Starting update for game " << game_id << " (attempt " << attempt_ << ")" << std::endl;

    // Setup storage logging - use RAII pattern to ensure teardown
    ensure_storage()->setup_logging();
    
    // RAII guard to ensure teardown_logging is always called
    struct LoggingGuard {
        RecordingStorage* storage;
        
        explicit LoggingGuard(RecordingStorage* s) : storage(s) {}
        
        // Prevent copying
        LoggingGuard(const LoggingGuard&) = delete;
        LoggingGuard& operator=(const LoggingGuard&) = delete;
        
        ~LoggingGuard() noexcept { 
            if (storage) storage->teardown_logging(); 
        }
    };
    LoggingGuard guard(ensure_storage());

    if (!ensure_observation_package()) {
        std::cerr << "Failed to create observation package" << std::endl;
        co_return ObservationResult::make_package_failed();
    }

    try {
        // Fetch game state asynchronously (returns raw HTTP response)
        HttpResponse response = co_await api_->request_game_state_async(package_.state_ids, package_.time_stamps);

        // Parse and validate response, extracting state metadata
        GameServerResult result = api_->parse_and_validate_response(response, package_.state_ids, package_.time_stamps);

        api_->update_package(package_);

        // Check if the request was successful
        if (!result.success()) {
            
            // Increment attempt counter for all other failures that should be retried
            attempt_++;
            
            // Convert GameServerError to ObservationResult
            switch (result.error_code) {
                case GameServerError::AUTH_ERROR:
                    reset_package();
                    co_return ObservationResult::make_auth_failed(false, result.error_message);
                case GameServerError::HTTP_ERROR:
                    co_return ObservationResult::make_server_error(result.error_message);
                case GameServerError::NETWORK_ERROR:
                    co_return ObservationResult::make_network_error(false, result.error_message);
                case GameServerError::PARSE_ERROR:
                case GameServerError::SERVER_SWITCH:
                case GameServerError::UNKNOWN_ERROR:
                default:
                    co_return ObservationResult::make_unknown_error(result.error_message);
            }
        }

        // Reset attempt counter on success
        attempt_ = 0;

        // Save raw response string to storage.
        // We move the raw string to storage, avoiding the need to dump JSON.
        ensure_storage()->update_resume_metadata(package_.to_json());
        ensure_storage()->save_response(std::move(result.raw_response));

        // Check if game ended in this update
        if (result.game_ended) {
            co_return ObservationResult::make_game_ended();
        }

        co_return ObservationResult::make_success(false);
    } catch (const std::runtime_error &e) {
        std::string error = e.what();
        co_return ObservationResult::make_unknown_error(error);
    }
}

void ObservationSession::set_attempt(const int attempt) {
    attempt_ = attempt;
}

int ObservationSession::get_attempt() {
    return attempt_;
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
