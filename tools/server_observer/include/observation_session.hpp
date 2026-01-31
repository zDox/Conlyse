#ifndef OBSERVATION_SESSION_HPP
#define OBSERVATION_SESSION_HPP

#include <string>
#include <memory>
#include <chrono>
#include <boost/asio/awaitable.hpp>
#include <nlohmann/json.hpp>
#include "account.hpp"
#include "observation_api.hpp"
#include "static_map_cache.hpp"
#include "recording_storage.hpp"
#include "observation_package.hpp"
#include "request_manager.hpp"
#include "proxy_config.hpp"
#include <magic_enum.hpp>

using json = nlohmann::json;
namespace asio = boost::asio;

// Forward declaration
class ObservationApi;

// Error codes for observation updates
enum class ObservationError {
    SUCCESS = 0,
    GAME_ENDED,
    AUTH_FAILED,
    SERVER_ERROR,
    NETWORK_ERROR,
    PACKAGE_CREATION_FAILED,
    UNKNOWN_ERROR
};

// Result structure for observation updates
struct ObservationResult {
    ObservationError error_code;
    std::string error_message;
    bool game_ended; // True -> stop observing, False -> reschedule

    explicit ObservationResult(ObservationError code, bool game_ended = false, std::string msg = "")
        : error_code(code), error_message(std::move(msg)), game_ended(game_ended) {}

    static ObservationResult make_success(bool game_ended) {
        return ObservationResult(ObservationError::SUCCESS, game_ended, "");
    }

    static ObservationResult make_game_ended() {
        return ObservationResult(ObservationError::GAME_ENDED, true, "Game has ended");
    }

    static ObservationResult make_auth_failed(bool game_ended = true, const std::string& msg = "Authentication failed") {
        return ObservationResult(ObservationError::AUTH_FAILED, game_ended, msg);
    }

    static ObservationResult make_server_error(const std::string& msg = "Server error") {
        return ObservationResult(ObservationError::SERVER_ERROR, false, msg);
    }

    static ObservationResult make_network_error(bool game_ended = true, const std::string& msg = "Network error") {
        return ObservationResult(ObservationError::NETWORK_ERROR, game_ended, msg);
    }

    static ObservationResult make_package_failed(const std::string& msg = "Failed to create observation package") {
        return ObservationResult(ObservationError::PACKAGE_CREATION_FAILED, false, msg);
    }

    static ObservationResult make_unknown_error(const std::string& msg = "Unknown error") {
        return ObservationResult(ObservationError::UNKNOWN_ERROR, false, msg);
    }

    bool is_success() const { return error_code == ObservationError::SUCCESS; }
};

class ObservationSession {
public:
    ObservationSession(
        std::shared_ptr<RequestManager> manager,
        int game_id,
        std::shared_ptr<Account> account,
        std::shared_ptr<StaticMapCache> map_cache,
        std::string storage_path,
        std::string metadata_path = "",
        std::string long_term_storage_path = "",
        int file_size_threshold = 0);

    ~ObservationSession();

    void set_proxy(const ProxyConfig &proxy_config);

    int game_id;
    std::shared_ptr<Account> account;
    std::chrono::system_clock::time_point next_update_at;

    bool needs_update(std::chrono::system_clock::time_point now) const;
    void reset_package();

    asio::awaitable<ObservationResult> run_update_async();
    void set_attempt(int attempt);
    int get_attempt();
private:
    // RAII guard for storage logging lifecycle
    class LoggingGuard {
    public:
        explicit LoggingGuard(RecordingStorage* storage);
        ~LoggingGuard() noexcept;

        LoggingGuard(const LoggingGuard&) = delete;
        LoggingGuard& operator=(const LoggingGuard&) = delete;
    private:
        RecordingStorage* storage_;
    };

    std::shared_ptr<RequestManager> manager_;
    std::shared_ptr<StaticMapCache> map_cache_;
    std::unique_ptr<ObservationApi> api_;
    std::string storage_path_;
    std::string metadata_path_;
    std::string long_term_storage_path_;
    int file_size_threshold_;
    ObservationPackage package_;
    std::unique_ptr<RecordingStorage> storage_;
    int attempt_;

    RecordingStorage *ensure_storage();

    bool ensure_observation_package();

    ObservationPackage create_observation_package();

    bool ensure_static_map_data(ObservationApi &api, int map_id);

    void on_request_response(std::string&& response_str);

    // Helper methods for run_update_async
    ObservationResult handle_game_server_error(const GameServerResult& result);

    void process_successful_response(GameServerResult& result);
};

#endif // OBSERVATION_SESSION_HPP
