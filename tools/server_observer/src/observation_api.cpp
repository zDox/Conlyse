#include "observation_api.hpp"


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
    const ProxyConfig& proxy,
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
    , proxy_(proxy)
{
    cli_ = std::make_unique<HttpClient>(manager, game_server_address);
}

ObservationApi::~ObservationApi() = default;

json ObservationApi::parse_response(const std::string& response_data) {
    json response_json;
    try {
        response_json = json::parse(response_data);
    } catch (const std::exception& e) {
        throw std::runtime_error("Failed to parse response: " + std::string(e.what()));
    }
    return response_json;
}

HttpResponse ObservationApi::request_game_state(std::map<std::string, std::string> &state_ids,
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
    
    // Create HTTPS client
    cli_->enable_server_certificate_verification(false);
    cli_->set_follow_location(true);

    // Configure proxy if provided
    if (proxy_.enabled) {
        cli_->set_proxy(proxy_.host, proxy_.port, proxy_.username, proxy_.password);
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

    // Send request and return raw response
    std::string body = payload.dump();
    return cli_->Post(req_headers, body, "application/json");
}

GameServerResult ObservationApi::parse_and_validate_response(HttpResponse& response,
                                                             std::map<std::string, std::string> &state_ids,
                                                             std::map<std::string, std::string> &time_stamps) {
    GameServerResult result;
    result.error_code = GameServerError::SUCCESS;
    result.error_message = "";

    // Check for HTTP errors
    if (response.status_code != 200) {
        result.error_code = GameServerError::HTTP_ERROR;
        result.error_message = "HTTP status: " + std::to_string(response.status_code);
        return result;
    }

    // Parse JSON response
    json game_state;
    try {
        game_state = json::parse(response.data);
    } catch (const std::exception& e) {
        result.error_code = GameServerError::PARSE_ERROR;
        result.error_message = "JSON parse error: " + std::string(e.what());
        return result;
    }

    // Clear the response data to free memory
    response.data.clear();
    response.data.shrink_to_fit();

    // Validate response structure
    if (!game_state.contains("result") || !game_state["result"].is_object()) {
        result.error_code = GameServerError::UNKNOWN_ERROR;
        result.error_message = "No result object in response";
        return result;
    }

    const auto& response_result = game_state["result"];
    if (!response_result.contains("@c")) {
        result.error_code = GameServerError::UNKNOWN_ERROR;
        result.error_message = "No @c field in result";
        return result;
    }

    std::string result_class = response_result["@c"].get<std::string>();
    std::cout << "Error class: " << result_class << std::endl;

    // Check for authentication errors
    if (result_class == "ultshared.UltAuthentificationException") {
        result.error_code = GameServerError::AUTH_ERROR;
        result.error_message = "Authentication failed: " + result_class;
        if (response_result.contains("message")) {
            result.error_message += " - " + response_result["message"].get<std::string>();
        }
        return result;
    }

    // Check for server switch
    if (result_class == "ultshared.rpc.UltSwitchServerException") {
        result.error_code = GameServerError::SERVER_SWITCH;
        result.error_message = "Server switch required";
        if (response_result.contains("newHostName")) {
            std::string new_server = response_result["newHostName"].get<std::string>();
            result.error_message += ": " + new_server;
            result.data["newHostName"] = new_server;
        }
        result.data = game_state;
        return result;
    }

    // Check for valid game state
    if (result_class != "ultshared.UltAutoGameState" && result_class != "ultshared.UltGameState") {
        result.error_code = GameServerError::UNKNOWN_ERROR;
        result.error_message = "Unknown error class: " + result_class;
        if (response_result.contains("message")) {
            result.error_message += " - " + response_result["message"].get<std::string>();
        }
        return result;
    }

    // Extract state metadata
    if (!extract_state_metadata(game_state, state_ids, time_stamps)) {
        result.error_code = GameServerError::UNKNOWN_ERROR;
        result.error_message = "Game state extraction failed";
        return result;
    }

    // Success - return the game state
    result.error_code = GameServerError::SUCCESS;
    result.error_message = "";
    result.data = game_state;
    return result;
}

bool ObservationApi::extract_state_metadata(const json& response,
                                            std::map<std::string, std::string> &state_ids,
                                            std::map<std::string, std::string> &time_stamps) {

    if (!response.contains("result") || !response["result"].is_object()) {
        return false;
    }
    
    const auto& result = response["result"];
    if (!result.contains("states") || !result["states"].is_object()) {
        return false;
    }
    
    const auto& states = result["states"];
    
    for (const auto& [key, state] : states.items()) {
        if (!state.is_object()) {
            continue;
        }
        
        if (state.contains("stateType")) {
            if (state.contains("stateID") && state["stateID"].is_string()) {
                state_ids[key] = state["stateID"].get<std::string>();
            }

            if (state.contains("timeStamp")) {
                time_stamps[key] = state["timeStamp"].get<std::string>();
            }
        }
    }
    
    return !state_ids.empty() && !time_stamps.empty();
}

json ObservationApi::get_static_map_data(int map_id) {
    std::string url = "https://static1.bytro.com/fileadmin/mapjson/live/" +
                      std::to_string(map_id) + ".json";
    httplib::Client cli("https://static1.bytro.com");
    cli.set_follow_location(true);

    // Configure proxy if provided
    if (proxy_.enabled) {
        cli.set_proxy(proxy_.host.c_str(), proxy_.port);

        // Set proxy authentication if provided
        if (!proxy_.username.empty() && !proxy_.password.empty()) {
            cli.set_proxy_basic_auth(proxy_.username.c_str(), proxy_.password.c_str());
        }
    }

    httplib::Headers headers = {
        {"Accept", "application/json, text/javascript, */*; q=0.01"}
    };

    std::string path = "/fileadmin/mapjson/live/" + std::to_string(map_id) + ".json";
    auto res = cli.Get(path.c_str(), headers);

    if (!res || res->status != 200) {
        throw std::runtime_error("Failed to fetch static map data");
    }

    // Parse and immediately clear the response body to free memory
    json result = json::parse(res->body);
    res->body.clear();
    res->body.shrink_to_fit();
    return result;
}

std::map<std::string, std::string> ObservationApi::get_cookies() const {
    return cookies_;
}

std::map<std::string, std::string> ObservationApi::get_headers() const {
    return headers_;
}
