#include "observation_api.hpp"


static const int MAX_RETRIES = 3;

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
    json  headers,
                             json  cookies,
                             json  proxy,
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
    , headers_(std::move(headers))
    , cookies_(std::move(cookies))
    , proxy_(std::move(proxy))
{
    cli_ = std::make_unique<HttpClient>(manager, game_server_address);
}

ObservationApi::~ObservationApi() = default;

json ObservationApi::make_game_server_request(const json& parameters) {
    int attempt = 0;
    while (true) {

        // Create HTTPS client
        cli_->enable_server_certificate_verification(false);
        cli_->set_follow_location(true);

        // Build request headers
        Headers req_headers = {
            {"Accept", "text/plain, */*; q=0.01"},
            {"Content-Type", "application/x-www-form-urlencoded; charset=UTF-8"},
            {"Accept-Encoding", "gzip, deflate, br"}
        };

        // Add custom headers
        if (headers_.is_object()) {
            for (auto& [key, value] : headers_.items()) {
                if (value.is_string()) {
                    req_headers.insert({key, value.get<std::string>()});
                }
            }
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
        for (auto& [key, value] : parameters.items()) {
            payload[key] = value;
        }

        request_id_++;

        // Send request
        std::string body = payload.dump();
        auto res = cli_->Post(req_headers, body, "application/json");

        if (res.status_code != 200) {
            throw std::runtime_error("HTTP status: " + std::to_string(res.status_code));
        }

        // Parse response and immediately clear the response body to free memory
        json response_json;
        try {
            response_json = json::parse(res.data);
            // Clear the response body string to free memory
            res.data.clear();
            res.data.shrink_to_fit();
        } catch (const std::exception& e) {
            throw std::runtime_error("Failed to parse response: " + std::string(e.what()));
        }

        // Handle errors
        if (response_json.contains("result") && response_json["result"].is_object()) {
            auto& result = response_json["result"];
            if (result.contains("@c")) {
                std::string err_class = result["@c"].get<std::string>();
                if (err_class == "ultshared.UltAuthentificationException") {
                    throw std::runtime_error("Authentication failed");
                }
                if (err_class == "ultshared.rpc.UltSwitchServerException") {
                    // Update server address
                    if (result.contains("newHostName")) {
                        std::string new_server = "https://" + result["newHostName"].get<std::string>();
                        std::cout << "Switching game server to " << new_server << std::endl;
                        game_server_address_ = new_server;
                        cli_->set_url(game_server_address_);
                    }
                    // Retry
                    if (attempt >= MAX_RETRIES) {
                        throw std::runtime_error("Exceeded retries after server switch suggestion");
                    }
                    attempt++;
                    std::cout << "Retrying after UltSwitchServerException (attempt " << attempt << "/" << MAX_RETRIES << ")" << std::endl;
                    continue;
                }
            }
        }
        
        return response_json;
    }
}

json ObservationApi::request_game_state(std::map<std::string, std::string> &state_ids,
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
    
    json response = make_game_server_request(action);
    
    if (!extract_state_metadata(response, state_ids, time_stamps)) {
        throw std::runtime_error("Game state extraction failed");
    }
    
    return response;
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

json ObservationApi::get_cookies() const {
    return cookies_;
}

json ObservationApi::get_headers() const {
    return headers_;
}
