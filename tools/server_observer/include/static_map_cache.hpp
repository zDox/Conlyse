#ifndef STATIC_MAP_CACHE_HPP
#define STATIC_MAP_CACHE_HPP

#include <string>
#include <set>
#include <mutex>
#include <memory>
#include <nlohmann/json.hpp>
#include "s3_client.hpp"

using json = nlohmann::json;

class StaticMapCache {
public:
    StaticMapCache(const std::string& cache_dir);
    StaticMapCache(const std::string& cache_dir, const S3Config& s3_config);
    ~StaticMapCache();
    
    bool is_cached(int map_id) const;
    std::string save(int map_id, const json& static_map_data);
    
private:
    bool upload_to_s3(const std::string& local_path, int map_id);
    void ensure_bucket_exists();
    
    std::string cache_dir_;
    std::set<int> saved_ids_;
    mutable std::mutex lock_;
    
    // S3 support
    bool s3_enabled_;
    std::shared_ptr<S3Client> s3_client_;
};

#endif // STATIC_MAP_CACHE_HPP
