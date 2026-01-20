#include "static_map_cache.hpp"
#include <fstream>
#include <filesystem>
#include <iostream>
#include <zstd.h>

namespace fs = std::filesystem;

StaticMapCache::StaticMapCache(const std::string& cache_dir)
    : cache_dir_(cache_dir)
{
    fs::create_directories(cache_dir_);
    
    // Load existing cached map IDs
    for (const auto& entry : fs::directory_iterator(cache_dir_)) {
        if (entry.is_regular_file()) {
            std::string filename = entry.path().stem().string();
            if (filename.find("map_") == 0) {
                try {
                    int map_id = std::stoi(filename.substr(4));
                    saved_ids_.insert(map_id);
                } catch (const std::exception&) {
                    // Skip files with invalid names
                }
            }
        }
    }
}

bool StaticMapCache::is_cached(int map_id) const {
    std::lock_guard<std::mutex> lock(lock_);
    return saved_ids_.find(map_id) != saved_ids_.end();
}

std::string StaticMapCache::save(int map_id, const json& static_map_data) {
    std::lock_guard<std::mutex> lock(lock_);
    
    std::string filename = "map_" + std::to_string(map_id) + ".bin";
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
        
        return path.string();
    } catch (const std::exception& e) {
        std::cerr << "Failed to cache static map data for map_id " << map_id << ": " << e.what() << std::endl;
        return "";
    }
}
