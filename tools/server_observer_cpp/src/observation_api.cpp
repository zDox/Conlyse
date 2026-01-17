#include "observation_api.hpp"
#include <httplib.h>
#include <iostream>
#include <chrono>
#include <sstream>
#include <iomanip>
#include <openssl/sha.h>

static const int SUPPORTED_CLIENT_VERSION = 207;
static const int MAX_RETRIES = 3;

static std::string sha1_hex(const std::string& input) {
    unsigned char hash[SHA_DIGEST_LENGTH];
    SHA1(reinterpret_cast<const unsigned char*>(input.c_str()), input.size(), hash);
    
    std::stringstream ss;
    for (int i = 0; i < SHA_DIGEST_LENGTH; i++) {
        ss << std::hex << std::setw(2) << std::setfill('0') << static_cast<int>(hash[i]);
    }
    return ss.str();
}

static int64_t current_time_ms() {
    auto now = std::chrono::system_clock::now();
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch());
    return ms.count();
}

ObservationApi::ObservationApi(const json& headers,
                             const json& cookies,
                             const json& proxy,
                             const AuthDetails& auth_details,
                             int game_id,
                             const std::string& game_server_address,
                             int client_version)
    : game_id_(game_id)
    , player_id_(0)
    , auth_(auth_details)
    , request_id_(0)
    , client_version_(client_version)
    , game_server_address_(game_server_address)
    , headers_(headers)
    , cookies_(cookies)
    , proxy_(proxy)
{
}

ObservationApi::~ObservationApi() {
}

json ObservationApi::make_game_server_request(const json& parameters) {
    int attempt = 0;
    
    while (true) {
        // Parse game server address
        std::string host, path;
        int port = 443;
        bool use_ssl = true;
        
        if (game_server_address_.find("https://") == 0) {
            host = game_server_address_.substr(8);
            use_ssl = true;
            port = 443;
        } else if (game_server_address_.find("http://") == 0) {
            host = game_server_address_.substr(7);
            use_ssl = false;
            port = 80;
        } else {
            host = game_server_address_;
        }
        
        // Extract path if present
        size_t slash_pos = host.find('/');
        if (slash_pos != std::string::npos) {
            path = host.substr(slash_pos);
            host = host.substr(0, slash_pos);
        } else {
            path = "/";
        }
        
        // Create HTTP client
        httplib::Client cli(host.c_str(), port);
        cli.set_follow_location(true);
        
        if (use_ssl) {
            cli.enable_server_certificate_verification(false);
        }
        
        // Build request headers
        httplib::Headers req_headers = {
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
        auto res = cli.Post(path.c_str(), req_headers, body, "application/json");
        
        if (!res) {
            throw std::runtime_error("HTTP request failed");
        }
        
        if (res->status != 200) {
            throw std::runtime_error("HTTP status: " + std::to_string(res->status));
        }
        
        // Parse response
        json response_json;
        try {
            response_json = json::parse(res->body);
        } catch (const std::exception& e) {
            throw std::runtime_error("Failed to parse response: " + std::string(e.what()));
        }
        
        // Update server time
        if (response_json.contains("result")) {
            auto& result = response_json["result"];
            if (result.is_object() && result.contains("timeStamp")) {
                update_server_time(result["timeStamp"].get<int64_t>());
            } else {
                update_server_time(0);
            }
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
                    }
                    
                    // Retry
                    if (attempt >= MAX_RETRIES) {
                        throw std::runtime_error("Exceeded retries after server switch suggestion");
                    }
                    attempt++;
                    std::cout << "Retrying after UltSwitchServerException (attempt " 
                             << attempt << "/" << MAX_RETRIES << ")" << std::endl;
                    continue;
                }
            }
        }
        
        return response_json;
    }
}

void ObservationApi::update_server_time(int64_t t_stamp_now) {
    // In C++, we don't need to track server time offset for observation
    // This is a simplified implementation
}

json ObservationApi::request_game_state(std::map<int, std::string>& state_ids,
                                        std::map<int, int>& time_stamps) {
    bool include_state_meta = !state_ids.empty() && !time_stamps.empty();
    
    // Build state_ids and time_stamps as JSON objects
    json state_ids_json = json::object();
    json time_stamps_json = json::object();
    
    if (include_state_meta) {
        for (const auto& [key, value] : state_ids) {
            state_ids_json[std::to_string(key)] = value;
        }
        for (const auto& [key, value] : time_stamps) {
            time_stamps_json[std::to_string(key)] = value;
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
        action["stateIDs"] = {
            {"@c", "java.util.HashMap"},
            {"@m", state_ids_json}
        };
        action["timeStamps"] = {
            {"@c", "java.util.HashMap"},
            {"@m", time_stamps_json}
        };
    }
    
    action["actions"] = {
        {"@c", "java.util.LinkedList"}
    };
    
    json response = make_game_server_request(action);
    
    if (!extract_state_metadata(response, state_ids, time_stamps)) {
        throw std::runtime_error("Game state extraction failed");
    }
    
    return response;
}

bool ObservationApi::extract_state_metadata(const json& response,
                                            std::map<int, std::string>& state_ids,
                                            std::map<int, int>& time_stamps) {
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
            try {
                int state_type = state["stateType"].get<int>();
                
                if (state.contains("stateID") && state["stateID"].is_string()) {
                    state_ids[state_type] = state["stateID"].get<std::string>();
                }
                
                if (state.contains("timeStamp")) {
                    time_stamps[state_type] = state["timeStamp"].get<int>();
                }
            } catch (const std::exception&) {
                continue;
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
    
    return json::parse(res->body);
}

json ObservationApi::get_cookies() const {
    return cookies_;
}

json ObservationApi::get_headers() const {
    return headers_;
}
