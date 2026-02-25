#ifndef OBSERVATION_API_HPP
#define OBSERVATION_API_HPP

#include <string>
#include <map>
#include <memory>
#include <nlohmann/json.hpp>
#include <chrono>
#include <httplib.h>
#include <boost/asio/awaitable.hpp>

#include "http_client.hpp"
#include "hub_interface_wrapper.hpp"
#include "observation_package.hpp"
#include "proxy_config.hpp"

using json = nlohmann::json;
namespace asio = boost::asio;

// Error codes for game server requests
enum class GameServerError {
    SUCCESS = 0,
    HTTP_ERROR,
    PARSE_ERROR,
    AUTH_ERROR,
    SERVER_SWITCH,
    CLIENT_VERSION_MISMATCH,
    NETWORK_ERROR,
    UNKNOWN_ERROR
};

// Result structure for game server requests
struct GameServerResult {
    GameServerError error_code;
    std::string error_message;
    json data;
    std::string raw_response;  // Raw JSON response string
    bool game_ended = false;  // Whether the game has ended (extracted during parsing)
    std::string map_id;       // Static map identifier (string) if available

    bool success() const { return error_code == GameServerError::SUCCESS; }
};

class ObservationApi {
public:
    ObservationApi(
                std::shared_ptr<RequestManager> manager,
                const std::map<std::string, std::string>& headers,
                const std::map<std::string, std::string>& cookies,
                std::shared_ptr<ProxyConfig> proxy,
                AuthDetails auth_details,
                int game_id,
                const std::string& game_server_address,
                int client_version);
    
    ~ObservationApi();
    
    HttpResponse request_game_state(std::map<std::string, std::string> &state_ids,
                                    std::map<std::string, std::string> &time_stamps);

    asio::awaitable<HttpResponse> request_game_state_async(std::map<std::string, std::string> &state_ids,
                                                            std::map<std::string, std::string> &time_stamps);

    GameServerResult parse_and_validate_response(HttpResponse& response,
                                                  std::map<std::string, std::string> &state_ids,
                                                  std::map<std::string, std::string> &time_stamps);

    json get_static_map_data(const std::string &map_id);

    void update_package(ObservationPackage& pkg) const;
    void update_server_address(const std::string & url);
private:
    int game_id_;
    int player_id_;
    AuthDetails auth_;
    int request_id_;
    int client_version_;
    std::string game_server_address_;
    std::map<std::string, std::string> headers_;
    std::map<std::string, std::string> cookies_;
    std::shared_ptr<ProxyConfig> proxy_;
    std::unique_ptr<HttpClient> cli_;
};

#endif // OBSERVATION_API_HPP
