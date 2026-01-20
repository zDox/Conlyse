#ifndef OBSERVATION_SESSION_HPP
#define OBSERVATION_SESSION_HPP

#include <string>
#include <memory>
#include <chrono>
#include <nlohmann/json.hpp>
#include "account.hpp"
#include "static_map_cache.hpp"
#include "recording_storage.hpp"
#include "observation_api.hpp"

using json = nlohmann::json;

struct ObservationPackage {
    int game_id = 0;
    json headers;
    json cookies;
    json proxy;
    AuthDetails auth;
    int client_version = 0;
    std::string game_server_address;
    std::map<std::string, std::string> time_stamps;
    std::map<std::string, std::string> state_ids;
    
    json to_json() const;
    static ObservationPackage from_json(const json& j);
};

class ObservationSession {
public:
    ObservationSession(int game_id,
                      std::shared_ptr<Account> account,
                      std::shared_ptr<StaticMapCache> map_cache,
                      const std::string& storage_path,
                      const std::string& metadata_path = "",
                      const std::string& long_term_storage_path = "",
                      int file_size_threshold = 0);
    
    ~ObservationSession();
    
    int game_id;
    std::shared_ptr<Account> account;
    std::chrono::system_clock::time_point next_update_at;
    
    bool needs_update(std::chrono::system_clock::time_point now) const;
    bool run_update();
    void reset();
    
private:
    std::shared_ptr<StaticMapCache> map_cache_;
    std::string storage_path_;
    std::string metadata_path_;
    std::string long_term_storage_path_;
    int file_size_threshold_;
    ObservationPackage package_;
    std::unique_ptr<RecordingStorage> storage_;
    
    RecordingStorage* ensure_storage();
    bool ensure_observation_package();
    ObservationPackage create_observation_package();
    void reset_package();
    bool ensure_static_map_data(ObservationApi& api, int map_id);
    bool is_game_ended(const json& response);
    void on_request_response(json&& response);
};

#endif // OBSERVATION_SESSION_HPP
