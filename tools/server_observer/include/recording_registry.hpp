#ifndef RECORDING_REGISTRY_HPP
#define RECORDING_REGISTRY_HPP

#include <string>
#include <map>
#include <mutex>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

class RecordingRegistry {
public:
    RecordingRegistry(const std::string& registry_path);
    
    void mark_recording(int game_id, int scenario_id, const std::string& replay_path);
    void mark_completed(int game_id);
    void mark_failed(int game_id, const std::string& reason);
    
    bool is_known(int game_id) const;
    std::map<int, json> active() const;
    
private:
    std::string path_;
    mutable std::mutex lock_;
    json state_;
    
    void load();
    void save();
};

#endif // RECORDING_REGISTRY_HPP
