#include "recording_registry.hpp"
#include <fstream>
#include <filesystem>
#include <iostream>

namespace fs = std::filesystem;

RecordingRegistry::RecordingRegistry(const std::string& registry_path)
    : path_(registry_path)
{
    // Create parent directories if they don't exist
    fs::path path(path_);
    if (path.has_parent_path()) {
        fs::create_directories(path.parent_path());
    }
    
    // Initialize state with default buckets
    state_ = {
        {"recording", json::object()},
        {"completed", json::object()},
        {"failed", json::object()}
    };
    
    load();
}

void RecordingRegistry::load() {
    std::ifstream file(path_);
    if (!file.is_open()) {
        return;  // File doesn't exist yet
    }
    
    try {
        json data;
        file >> data;
        
        if (data.is_object()) {
            for (auto& [key, value] : data.items()) {
                if (state_.contains(key)) {
                    state_[key] = value;
                }
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "Warning: Could not read registry at " << path_ << ": " << e.what() << std::endl;
    }
}

void RecordingRegistry::save() {
    std::ofstream file(path_);
    if (!file.is_open()) {
        std::cerr << "Error: Could not write registry to " << path_ << std::endl;
        return;
    }
    
    file << state_.dump(2);
}

void RecordingRegistry::mark_recording(int game_id, int scenario_id, const std::string& replay_path) {
    std::lock_guard<std::mutex> lock(lock_);
    
    json meta = {
        {"scenario_id", scenario_id}
    };
    
    if (!replay_path.empty()) {
        meta["replay_path"] = replay_path;
    }
    
    state_["recording"][std::to_string(game_id)] = meta;
    save();
}

void RecordingRegistry::mark_completed(int game_id) {
    std::lock_guard<std::mutex> lock(lock_);
    
    std::string game_id_str = std::to_string(game_id);
    json meta;
    
    if (state_["recording"].contains(game_id_str)) {
        meta = state_["recording"][game_id_str];
        state_["recording"].erase(game_id_str);
    }
    
    state_["completed"][game_id_str] = meta;
    save();
}

void RecordingRegistry::mark_failed(int game_id, const std::string& reason) {
    std::lock_guard<std::mutex> lock(lock_);
    
    std::string game_id_str = std::to_string(game_id);
    json meta;
    
    if (state_["recording"].contains(game_id_str)) {
        meta = state_["recording"][game_id_str];
        state_["recording"].erase(game_id_str);
    }
    
    if (!reason.empty()) {
        meta["reason"] = reason;
    }
    
    state_["failed"][game_id_str] = meta;
    save();
}

bool RecordingRegistry::is_known(int game_id) const {
    std::lock_guard<std::mutex> lock(lock_);
    std::string game_id_str = std::to_string(game_id);
    
    for (const auto& [bucket_name, bucket] : state_.items()) {
        if (bucket.is_object() && bucket.contains(game_id_str)) {
            return true;
        }
    }
    
    return false;
}

std::map<int, json> RecordingRegistry::active() const {
    std::lock_guard<std::mutex> lock(lock_);
    std::map<int, json> result;
    
    if (state_.contains("recording") && state_["recording"].is_object()) {
        for (const auto& [key, value] : state_["recording"].items()) {
            try {
                int game_id = std::stoi(key);
                result[game_id] = value;
            } catch (const std::exception&) {
                // Skip invalid game IDs
            }
        }
    }
    
    return result;
}
