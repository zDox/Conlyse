#include "observation_api.hpp"
#include <openssl/sha.h>
#include <chrono>
#include <sstream>
#include <iomanip>
#include <simdjson.h>
#include <regex>
#include <utility>


static std::string sha1_hex(const std::string& input) {
    unsigned char hash[SHA_DIGEST_LENGTH];
    SHA1(reinterpret_cast<const unsigned char*>(input.c_str()), input.size(), hash);
    
    std::stringstream ss;
    for (unsigned char i : hash) {
        ss << std::hex << std::setw(2) << std::setfill('0') << static_cast<int>(i);
    }
    return ss.str();
}

static int64_t current_time_ms() {
    auto now = std::chrono::system_clock::now();
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch());
    return ms.count();
}

ObservationApi::ObservationApi(
    std::shared_ptr<RequestManager> manager,
    const std::map<std::string, std::string>& headers,
    const std::map<std::string, std::string>& cookies,
    std::shared_ptr<ProxyConfig> proxy,
    AuthDetails  auth_details,
    int game_id,
    const std::string& game_server_address,
    int client_version)
    : game_id_(game_id)
    , player_id_(0)
    , auth_(std::move(auth_details))
    , request_id_(0)
    , client_version_(client_version)
    , game_server_address_(game_server_address)
    , headers_(headers)
    , cookies_(cookies)
    , proxy_(std::move(std::move(proxy)))
{
    cli_ = std::make_unique<HttpClient>(manager, game_server_address);
}

ObservationApi::~ObservationApi() = default;

asio::awaitable<HttpResponse> ObservationApi::request_game_state_async(std::map<std::string, std::string> &state_ids,
                                                                        std::map<std::string, std::string> &time_stamps) {
    bool include_state_meta = !state_ids.empty() && !time_stamps.empty();
    
    // Build state_ids and time_stamps as JSON objects
    json state_ids_json = json::object();
    json time_stamps_json = json::object();
    
    if (include_state_meta) {
        for (const auto& [key, value] : state_ids) {
            state_ids_json[key] = value;
        }
        for (const auto& [key, value] : time_stamps) {
            time_stamps_json[key] = value;
        }
    }
    
    // Build action
    json action = {
        {"@c", "ultshared.action.UltUpdateGameStateAction"},
        {"stateType", 0},
        {"stateID", "0"},
        {"addStateIDsOnSent", include_state_meta}
    };

    if (include_state_meta) {
        action["stateIDs"] = state_ids_json;
        action["stateIDs"]["@c"] = "java.util.HashMap";

        action["timeStamps"] = time_stamps_json;
        action["timeStamps"]["@c"] = "java.util.HashMap";
    }

    action["actions"] = json::array({
        "java.util.LinkedList",
        json::array()
    });
    
    // Configure proxy if provided
    if (proxy_->enabled) {
        cli_->set_proxy(proxy_->host, proxy_->port, proxy_->username, proxy_->password);
    }

    // Build request headers
    Headers req_headers = {
        {"Accept", "text/plain, */*; q=0.01"},
        {"Accept-Encoding", "gzip, deflate, br"}
    };

    // Add custom headers
    for (const auto& [key, value] : headers_) {
        req_headers.insert({key, value});
    }

    // Build payload
    std::string hash_input = "undefined" + std::to_string(current_time_ms());
    std::string hash_hex = sha1_hex(hash_input);

    json payload = {
        {"requestID", request_id_},
        {"language", "en"},
        {"version", client_version_},
        {"tstamp", std::to_string(auth_.auth_tstamp)},
        {"client", "con-client"},
        {"hash", hash_hex},
        {"sessionTstamp", 0},
        {"gameID", std::to_string(game_id_)},
        {"playerID", player_id_},
        {"siteUserID", std::to_string(auth_.user_id)},
        {"adminLevel", nullptr},
        {"rights", auth_.rights},
        {"userAuth", auth_.auth},
        {"lastCallDuration", 0}
    };

    // Merge parameters into payload
    for (auto& [key, value] : action.items()) {
        payload[key] = value;
    }

    request_id_++;

    // Send request asynchronously and return awaitable response
    std::string body = payload.dump();
    co_return co_await cli_->Post_async(req_headers, body, "application/json");
}

GameServerResult ObservationApi::parse_and_validate_response(HttpResponse& response,
                                                             std::map<std::string, std::string> &state_ids,
                                                             std::map<std::string, std::string> &time_stamps) {
    GameServerResult result;
    result.error_code = GameServerError::SUCCESS;
    result.error_message = "";
    
    // Check for timeout first
    if (response.timeout) {
        result.error_code = GameServerError::NETWORK_ERROR;
        result.error_message = response.error_message.empty() ? "Request timed out" : response.error_message;
        return result;
    }
    
    // Check for HTTP errors
    if (response.status_code != 200) {
        result.error_code = GameServerError::HTTP_ERROR;
        result.error_message = "HTTP status: " + std::to_string(response.status_code);
        if (!response.error_message.empty()) {
            result.error_message += " - " + response.error_message;
        }
        return result;
    }

    // Store the raw response string before parsing
    result.raw_response = std::move(response.data);

    // Parse JSON response using simdjson
    simdjson::dom::parser parser;
    simdjson::dom::element game_state;
    try {
        game_state = parser.parse(result.raw_response);
    } catch (const simdjson::simdjson_error& e) {
        result.error_code = GameServerError::PARSE_ERROR;
        result.error_message = "JSON parse error: " + std::string(e.what());
        return result;
    }

    // Validate response structure
    simdjson::dom::object result_obj;
    if (game_state["result"].get(result_obj) != simdjson::SUCCESS) {
        result.error_code = GameServerError::UNKNOWN_ERROR;
        result.error_message = "No result object in response";
        return result;
    }

    std::string_view result_class_view;
    if (result_obj["@c"].get(result_class_view) != simdjson::SUCCESS) {
        result.error_code = GameServerError::UNKNOWN_ERROR;
        result.error_message = "No @c field in result";
        return result;
    }

    std::string result_class(result_class_view);

    // Check for authentication errors
    if (result_class == "ultshared.UltAuthentificationException") {
        result.error_code = GameServerError::AUTH_ERROR;
        result.error_message = "Authentication failed: " + result_class;
        std::string_view message_view;
        if (result_obj["message"].get(message_view) == simdjson::SUCCESS) {
            result.error_message += " - " + std::string(message_view);
        }
        return result;
    }

    // Check for server switch
    if (result_class == "ultshared.rpc.UltSwitchServerException") {
        result.error_code = GameServerError::SERVER_SWITCH;
        result.error_message = "Server switch required";
        std::string_view new_server_view;
        if (result_obj["newHostName"].get(new_server_view) == simdjson::SUCCESS) {
            std::string new_server(new_server_view);
            result.error_message += ": " + new_server;
            cli_->set_url("https://" + new_server);
        }
        return result;
    }

    // Check for client version mismatch
    if (result_class == "ultshared.UltClientVersionMismatchException") {
        result.error_code = GameServerError::CLIENT_VERSION_MISMATCH;
        result.error_message = "Client version mismatch";

        std::string_view message_view;
        if (result_obj["detailMessage"].get(message_view) == simdjson::SUCCESS) {
            int old_client_version = -1;
            int new_client_version = -1;
            std::string message(message_view); // convert string_view to string for regex

            std::regex re1("con-client: #(\\d+)");
            std::regex re2("con-client_live\\.txt: #(\\d+)");

            std::smatch match1, match2;

            if (std::regex_search(message, match1, re1)) {
                old_client_version = std::stoi(match1[1]);
            }

            if (std::regex_search(message, match2, re2)) { // use 'message' here
                new_client_version = std::stoi(match2[1]);
            }
            if (old_client_version != -1 && new_client_version != -1) {
                result.error_message += ": old version " + std::to_string(old_client_version) +
                                        ", new version " + std::to_string(new_client_version);
                client_version_ = new_client_version;
            }
            else {
                result.error_message += ": " + message;
            }
        }
    }
    // Check for valid game state
    if (result_class != "ultshared.UltAutoGameState" && result_class != "ultshared.UltGameState") {
        result.error_code = GameServerError::UNKNOWN_ERROR;
        result.error_message = "Unknown error class: " + result_class;
        std::string_view message_view;
        if (result_obj["message"].get(message_view) == simdjson::SUCCESS) {
            result.error_message += " - " + std::string(message_view);
        }
        return result;
    }

    // Extract state metadata using simdjson
    simdjson::dom::object states_obj;
    if (result_obj["states"].get(states_obj) != simdjson::SUCCESS) {
        result.error_code = GameServerError::UNKNOWN_ERROR;
        result.error_message = "Game state extraction failed";
        return result;
    }

    // Process states to extract metadata
    bool game_ended = false;
    for (auto [key, state_val] : states_obj) {
        simdjson::dom::object state;
        if (state_val.get(state) != simdjson::SUCCESS) {
            continue;
        }

        // Check if state has stateType field
        uint64_t state_type;
        if (state["stateType"].get(state_type) != simdjson::SUCCESS) {
            continue;
        }

        std::string_view state_id_view;
        if (state["stateID"].get(state_id_view) == simdjson::SUCCESS) {
            state_ids[std::string(key)] = std::string(state_id_view);
        }

        std::string_view timestamp_view;
        if (state["timeStamp"].get(timestamp_view) == simdjson::SUCCESS) {
            time_stamps[std::string(key)] = std::string(timestamp_view);
        }

        // Check if game has ended
        bool ended;
        if (state["gameEnded"].get(ended) == simdjson::SUCCESS && ended) {
            game_ended = true;
        }
    }

    if (state_ids.empty() || time_stamps.empty()) {
        result.error_code = GameServerError::UNKNOWN_ERROR;
        result.error_message = "Game state extraction failed";
        return result;
    }

    // Success - return with minimal JSON parsing
    result.error_code = GameServerError::SUCCESS;
    result.error_message = "";
    result.game_ended = game_ended;
    // No need to parse the full JSON for data field in the success case
    return result;
}

json ObservationApi::get_static_map_data(int map_id) {
    std::string url = "https://static1.bytro.com/fileadmin/mapjson/live/" +
                      std::to_string(map_id) + ".json";
    httplib::Client cli("https://static1.bytro.com");
    cli.set_follow_location(true);

    // Configure proxy if provided
    if (proxy_->enabled) {
        cli.set_proxy(proxy_->host, proxy_->port);

        // Set proxy authentication if provided
        if (!proxy_->username.empty() && !proxy_->password.empty()) {
            cli.set_proxy_basic_auth(proxy_->username, proxy_->password);
        }
    }

    httplib::Headers headers = {
        {"Accept", "application/json, text/javascript, */*; q=0.01"}
    };

    std::string path = "/fileadmin/mapjson/live/" + std::to_string(map_id) + ".json";
    auto res = cli.Get(path, headers);

    if (!res || res->status != 200) {
        throw std::runtime_error("Failed to fetch static map data");
    }

    // Parse and immediately clear the response body to free memory
    json result = json::parse(res->body);
    res->body.clear();
    res->body.shrink_to_fit();
    return result;
}

void ObservationApi::update_package(ObservationPackage &pkg) const {
    pkg.client_version = client_version_;
    pkg.game_server_address = game_server_address_;
    pkg.headers = headers_;
    pkg.cookies = cookies_;
    pkg.auth = auth_;
}