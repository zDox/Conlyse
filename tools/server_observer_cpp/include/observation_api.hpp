#ifndef OBSERVATION_API_HPP
#define OBSERVATION_API_HPP

#include <string>
#include <map>
#include <memory>
#include <nlohmann/json.hpp>
#include "hub_interface_wrapper.hpp"

using json = nlohmann::json;

class ObservationApi {
public:
    ObservationApi(const json& headers,
                  const json& cookies,
                  const json& proxy,
                  const AuthDetails& auth_details,
                  int game_id,
                  const std::string& game_server_address,
                  int client_version = 207);
    
    ~ObservationApi();
    
    json request_game_state(std::map<int, std::string>& state_ids,
                           std::map<int, int>& time_stamps);
    
    json get_static_map_data(int map_id);
    
    AuthDetails get_auth() const { return auth_; }
    json get_cookies() const;
    json get_headers() const;
    std::string get_game_server_address() const { return game_server_address_; }
    
private:
    int game_id_;
    int player_id_;
    AuthDetails auth_;
    int request_id_;
    int client_version_;
    std::string game_server_address_;
    json headers_;
    json cookies_;
    json proxy_;
    
    json make_game_server_request(const json& parameters);
    void update_server_time(int64_t t_stamp_now);
    bool extract_state_metadata(const json& response,
                               std::map<int, std::string>& state_ids,
                               std::map<int, int>& time_stamps);
};

#endif // OBSERVATION_API_HPP
