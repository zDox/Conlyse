#include "static_map_cache.hpp"
#include "db_client.hpp"
#include <fstream>
#include <filesystem>
#include <iostream>
#include <vector>
#include <zstd.h>

namespace fs = std::filesystem;

StaticMapCache::StaticMapCache(const std::string& cache_dir)
    : cache_dir_(cache_dir)
    , s3_enabled_(false)
{
    fs::create_directories(cache_dir_);
    
    // Load existing cached map IDs
    for (const auto& entry : fs::directory_iterator(cache_dir_)) {
        if (entry.is_regular_file()) {
            std::string filename = entry.path().stem().string();
            if (filename.find("map_") == 0) {
                std::string map_id = filename.substr(4);
                saved_ids_.insert(map_id);
            }
        }
    }
}

StaticMapCache::StaticMapCache(const std::string& cache_dir, const S3Config& s3_config)
    : cache_dir_(cache_dir)
    , s3_enabled_(true)
    , db_client_(nullptr)
{
    fs::create_directories(cache_dir_);
    
    // Initialize S3 client
    s3_client_ = std::make_shared<S3Client>(s3_config);
    
    // Ensure bucket exists
    ensure_bucket_exists();
    
    // Load existing cached map IDs
    for (const auto& entry : fs::directory_iterator(cache_dir_)) {
        if (entry.is_regular_file()) {
            std::string filename = entry.path().stem().string();
            if (filename.find("map_") == 0) {
                std::string map_id = filename.substr(4);
                saved_ids_.insert(map_id);
            }
        }
    }
}

StaticMapCache::StaticMapCache(const std::string& cache_dir, const S3Config& s3_config, std::shared_ptr<DbClient> db_client)
    : cache_dir_(cache_dir)
    , s3_enabled_(true)
    , db_client_(db_client)
{
    fs::create_directories(cache_dir_);
    
    // Initialize S3 client
    s3_client_ = std::make_shared<S3Client>(s3_config);
    
    // Ensure bucket exists
    ensure_bucket_exists();
    
    // Load existing cached map IDs
    for (const auto& entry : fs::directory_iterator(cache_dir_)) {
        if (entry.is_regular_file()) {
            std::string filename = entry.path().stem().string();
            if (filename.find("map_") == 0) {
                std::string map_id = filename.substr(4);
                saved_ids_.insert(map_id);
            }
        }
    }
}

StaticMapCache::~StaticMapCache() {
    // Destructor
}

bool StaticMapCache::is_cached(const std::string& map_id) const {
    std::lock_guard<std::mutex> lock(lock_);
    return saved_ids_.find(map_id) != saved_ids_.end();
}

std::string StaticMapCache::save(const std::string& map_id, const json& static_map_data) {
    std::lock_guard<std::mutex> lock(lock_);
    
    std::string filename = "map_" + map_id + ".bin";
    fs::path path = fs::path(cache_dir_) / filename;
    
    // Check if already cached
    if (saved_ids_.find(map_id) != saved_ids_.end() && fs::exists(path)) {
        return path.string();
    }
    
    try {
        // Serialize JSON to string
        std::string json_str = static_map_data.dump();
        
        // Compress using zstd
        size_t compressed_size = ZSTD_compressBound(json_str.size());
        std::vector<uint8_t> compressed(compressed_size);
        
        size_t actual_size = ZSTD_compress(
            compressed.data(), compressed_size,
            json_str.data(), json_str.size(),
            3  // compression level
        );
        
        if (ZSTD_isError(actual_size)) {
            std::cerr << "Compression failed: " << ZSTD_getErrorName(actual_size) << std::endl;
            return "";
        }
        
        compressed.resize(actual_size);
        
        // Write to file
        std::ofstream file(path, std::ios::binary);
        if (!file.is_open()) {
            std::cerr << "Failed to open file for writing: " << path << std::endl;
            return "";
        }
        
        file.write(reinterpret_cast<const char*>(compressed.data()), compressed.size());
        file.close();
        
        saved_ids_.insert(map_id);
        std::cout << "Cached static map data for map_id " << map_id << " at " << path << std::endl;
        
        // Upload to S3 if enabled
        std::string s3_key;
        if (s3_enabled_) {
            s3_key = "static_maps/map_" + map_id + ".bin";
            if (upload_to_s3(path.string(), map_id)) {
                std::cout << "Uploaded static map data for map_id " << map_id << " to S3" << std::endl;
            } else {
                std::cerr << "Failed to upload static map data for map_id " << map_id << " to S3" << std::endl;
            }
        }
        
        // Record in database if enabled
        if (db_client_ && db_client_->is_connected()) {
            if (!db_client_->map_exists(map_id)) {
                // Extract version from static_map_data if available
                std::optional<std::string> version = std::nullopt;
                if (static_map_data.contains("version") && !static_map_data["version"].is_null()) {
                    version = static_map_data["version"].get<std::string>();
                }
                
                if (db_client_->insert_map(map_id, s3_key, version)) {
                    std::cout << "Recorded static map " << map_id << " in database" << std::endl;
                } else {
                    std::cerr << "Failed to record static map " << map_id << " in database" << std::endl;
                }
            }
        }
        
        return path.string();
    } catch (const std::exception& e) {
        std::cerr << "Failed to cache static map data for map_id " << map_id << ": " << e.what() << std::endl;
        return "";
    }
}

bool StaticMapCache::upload_to_s3(const std::string& local_path, const std::string& map_id) {
    if (!s3_client_) {
        std::cerr << "S3 client not initialized" << std::endl;
        return false;
    }
    
    try {
        std::string s3_key = "static_maps/map_" + map_id + ".bin";
        return s3_client_->upload_file(local_path, s3_key);
    } catch (const std::exception& e) {
        std::cerr << "Exception during S3 upload: " << e.what() << std::endl;
        return false;
    }
}

void StaticMapCache::ensure_bucket_exists() {
    if (!s3_client_) {
        return;
    }
    
    try {
        if (!s3_client_->bucket_exists()) {
            std::cout << "Creating S3 bucket..." << std::endl;
            if (!s3_client_->create_bucket()) {
                std::cerr << "Failed to create S3 bucket" << std::endl;
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "Exception checking/creating S3 bucket: " << e.what() << std::endl;
    }
}
