#ifndef STATIC_MAP_CACHE_HPP
#define STATIC_MAP_CACHE_HPP

#include <string>
#include <set>
#include <mutex>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

class StaticMapCache {
public:
    StaticMapCache(const std::string& cache_dir);
    
    bool is_cached(int map_id) const;
    std::string save(int map_id, const json& static_map_data);
    
private:
    std::string cache_dir_;
    std::set<int> saved_ids_;
    mutable std::mutex lock_;
};

#endif // STATIC_MAP_CACHE_HPP
