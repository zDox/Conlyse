#include "recording_storage.hpp"
#include <fstream>
#include <filesystem>
#include <iostream>
#include <chrono>
#include <zstd.h>
#include <ctime>
#include <iomanip>

namespace fs = std::filesystem;

RecordingStorage::RecordingStorage(const std::string& output_path,
                                 const std::string& metadata_path,
                                 const std::string& long_term_storage_path,
                                 int file_size_threshold)
    : output_path_(output_path)
    , metadata_path_(metadata_path.empty() ? output_path : metadata_path)
    , long_term_storage_path_(long_term_storage_path)
    , file_size_threshold_(file_size_threshold)
    , file_sequence_(0)
    , updates_since_last_flush_(0)
{
    // Validate configuration
    if ((long_term_storage_path_.empty() && file_size_threshold_ > 0) ||
        (!long_term_storage_path_.empty() && file_size_threshold_ <= 0)) {
        throw std::invalid_argument(
            "Both 'long_term_storage_path' and 'file_size_threshold' must be provided together, "
            "or neither should be provided. Cannot use one without the other."
        );
    }
    
    if (file_size_threshold_ < 0) {
        throw std::invalid_argument("file_size_threshold must be positive");
    }
    
    // Create directories
    fs::create_directories(output_path_);
    fs::create_directories(metadata_path_);
    
    // Set file paths
    responses_file_ = (fs::path(output_path_) / "responses.jsonl.zst").string();
    metadata_file_ = (fs::path(metadata_path_) / "metadata.json").string();
    recorder_log_file_ = (fs::path(metadata_path_) / "recording.log").string();
    
    // Initialize or load metadata
    if (!fs::exists(metadata_file_)) {
        init_files();
    }
    
    metadata_cache_ = load_metadata();
    restore_file_sequence();
    
    // Load resume metadata if available
    if (metadata_cache_.contains("resume")) {
        resume_metadata_ = metadata_cache_["resume"];
    }
}

void RecordingStorage::init_files() {
    auto now = std::chrono::system_clock::now();
    auto now_time_t = std::chrono::system_clock::to_time_t(now);
    std::stringstream ss;
    ss << std::put_time(std::gmtime(&now_time_t), "%Y-%m-%dT%H:%M:%SZ");
    
    json metadata = {
        {"version", "1.0"},
        {"created_at", ss.str()},
        {"updates", json::array()}
    };
    
    save_metadata(metadata);
}

void RecordingStorage::save_metadata(const json& metadata) {
    std::lock_guard<std::mutex> lock(lock_);
    
    std::ofstream file(metadata_file_);
    if (!file.is_open()) {
        std::cerr << "Error: Could not write metadata to " << metadata_file_ << std::endl;
        return;
    }
    
    file << metadata.dump(2);
    metadata_cache_ = metadata;
}

json RecordingStorage::load_metadata() {
    std::lock_guard<std::mutex> lock(lock_);
    
    if (!fs::exists(metadata_file_)) {
        return {{"version", "1.0"}, {"updates", json::array()}};
    }
    
    std::ifstream file(metadata_file_);
    if (!file.is_open()) {
        std::cerr << "Warning: Metadata file not found: " << metadata_file_ << std::endl;
        return {{"version", "1.0"}, {"updates", json::array()}};
    }
    
    try {
        json metadata;
        file >> metadata;
        return metadata;
    } catch (const std::exception& e) {
        std::cerr << "Error reading metadata: " << e.what() << std::endl;
        return {{"version", "1.0"}, {"updates", json::array()}};
    }
}

void RecordingStorage::update_resume_metadata(const json& resume) {
    metadata_cache_["resume"] = resume;
    resume_metadata_ = resume;
}

json RecordingStorage::get_resume_metadata() const {
    return resume_metadata_;
}

bool RecordingStorage::has_resume_metadata() const {
    return !resume_metadata_.empty() && resume_metadata_.contains("auth");
}

void RecordingStorage::flush_metadata() {
    // Save the cached metadata to disk
    save_metadata(metadata_cache_);
}

void RecordingStorage::restore_file_sequence() {
    json metadata = metadata_cache_;
    if (metadata.contains("file_sequence")) {
        file_sequence_ = metadata["file_sequence"].get<int>();
    }
}

void RecordingStorage::update_file_sequence() {
    file_sequence_++;
    metadata_cache_["file_sequence"] = file_sequence_;
}

size_t RecordingStorage::get_file_size(const std::string& file_path) {
    try {
        if (fs::exists(file_path)) {
            return fs::file_size(file_path);
        }
    } catch (const std::exception& e) {
        std::cerr << "Failed to get file size for " << file_path << ": " << e.what() << std::endl;
    }
    return 0;
}

bool RecordingStorage::should_rotate_file() {
    if (long_term_storage_path_.empty() || file_size_threshold_ <= 0) {
        return false;
    }
    
    size_t current_size = get_file_size(responses_file_);
    return current_size >= static_cast<size_t>(file_size_threshold_);
}

void RecordingStorage::rotate_to_long_term_storage() {
    if (!fs::exists(responses_file_)) {
        return;
    }
    
    size_t file_size = get_file_size(responses_file_);
    
    // Create long-term storage directory
    fs::path output_path(output_path_);
    std::string game_dir_name = output_path.filename().string();
    fs::path lts_game_dir = fs::path(long_term_storage_path_) / game_dir_name;
    fs::create_directories(lts_game_dir);
    
    // Generate filename with sequence number
    update_file_sequence();
    char filename[64];
    snprintf(filename, sizeof(filename), "responses_%04d.jsonl.zst", file_sequence_);
    fs::path lts_file_path = lts_game_dir / filename;
    
    try {
        // Try to move the file (rename may fail across filesystems)
        try {
            fs::rename(responses_file_, lts_file_path);
        } catch (const fs::filesystem_error& e) {
            // If rename fails (e.g., across filesystems), use copy + remove
            std::cout << "Rename failed, using copy for cross-filesystem move: " << e.what() << std::endl;
            fs::copy_file(responses_file_, lts_file_path, fs::copy_options::overwrite_existing);
            fs::remove(responses_file_);
        }
        std::cout << "Rotated responses file to long-term storage: " << lts_file_path << std::endl;
        
        // Log the rotation in metadata
        auto now = std::chrono::system_clock::now();
        auto now_time_t = std::chrono::system_clock::to_time_t(now);
        std::stringstream ss;
        ss << std::put_time(std::gmtime(&now_time_t), "%Y-%m-%dT%H:%M:%SZ");
        
        if (!metadata_cache_.contains("rotations")) {
            metadata_cache_["rotations"] = json::array();
        }
        
        metadata_cache_["rotations"].push_back({
            {"sequence", file_sequence_},
            {"timestamp", std::chrono::duration_cast<std::chrono::seconds>(
                now.time_since_epoch()).count()},
            {"datetime", ss.str()},
            {"destination", lts_file_path.string()},
            {"size_bytes", file_size}
        });
    } catch (const std::exception& e) {
        std::cerr << "Failed to rotate file to long-term storage: " << e.what() << std::endl;
        throw;
    }
}

void RecordingStorage::append_bytes_to_file(const std::string& file_path, 
                                            uint64_t timestamp, 
                                            const std::vector<uint8_t>& data) {
    std::ofstream file(file_path, std::ios::binary | std::ios::app);
    if (!file.is_open()) {
        throw std::runtime_error("Failed to open file for appending: " + file_path);
    }
    
    // Write timestamp (8 bytes, big-endian)
    for (int i = 7; i >= 0; i--) {
        uint8_t byte = (timestamp >> (i * 8)) & 0xFF;
        file.write(reinterpret_cast<const char*>(&byte), 1);
    }
    
    // Write length (4 bytes, big-endian)
    uint32_t length = data.size();
    for (int i = 3; i >= 0; i--) {
        uint8_t byte = (length >> (i * 8)) & 0xFF;
        file.write(reinterpret_cast<const char*>(&byte), 1);
    }
    
    // Write compressed data
    file.write(reinterpret_cast<const char*>(data.data()), data.size());
}

void RecordingStorage::save_response(std::string&& response_str) {
    // Check if file rotation is needed
    if (should_rotate_file()) {
        rotate_to_long_term_storage();
    }
    
    // The response string is moved to us, so we own it.
    // We'll use it for compression and then it will be automatically freed.
    
    size_t compressed_size = ZSTD_compressBound(response_str.size());
    std::vector<uint8_t> compressed(compressed_size);
    
    size_t actual_size = ZSTD_compress(
        compressed.data(), compressed_size,
        response_str.data(), response_str.size(),
        3  // compression level
    );
    
    if (ZSTD_isError(actual_size)) {
        std::cerr << "Compression failed: " << ZSTD_getErrorName(actual_size) << std::endl;
        return;
    }
    
    compressed.resize(actual_size);
    
    // The response_str will be automatically freed when this function returns
    // since it's an rvalue reference parameter
    
    // Get current timestamp
    auto now = std::chrono::system_clock::now();
    uint64_t timestamp = std::chrono::duration_cast<std::chrono::seconds>(
        now.time_since_epoch()).count();
    
    // Append to file
    append_bytes_to_file(responses_file_, timestamp, compressed);
    
    // Update metadata
    auto now_time_t = std::chrono::system_clock::to_time_t(now);
    std::stringstream ss;
    ss << std::put_time(std::gmtime(&now_time_t), "%Y-%m-%dT%H:%M:%SZ");
    
    if (!metadata_cache_.contains("updates")) {
        metadata_cache_["updates"] = json::array();
    }
    metadata_cache_["updates"].push_back({
        {"timestamp", timestamp},
        {"datetime", ss.str()}
    });
    
    // Periodically flush metadata to disk for crash recovery
    updates_since_last_flush_++;
    if (updates_since_last_flush_ >= METADATA_FLUSH_INTERVAL) {
        save_metadata(metadata_cache_);
        updates_since_last_flush_ = 0;
    }
}

void RecordingStorage::setup_logging() {
    // Create log file
    std::ofstream log_file(recorder_log_file_, std::ios::app);
    if (log_file.is_open()) {
        auto now = std::chrono::system_clock::now();
        auto now_time_t = std::chrono::system_clock::to_time_t(now);
        log_file << "=== Logging started at " 
                 << std::put_time(std::localtime(&now_time_t), "%Y-%m-%d %H:%M:%S")
                 << " ===" << std::endl;
    }
}

void RecordingStorage::teardown_logging() {
    // Flush any remaining data
    std::ofstream log_file(recorder_log_file_, std::ios::app);
    if (log_file.is_open()) {
        auto now = std::chrono::system_clock::now();
        auto now_time_t = std::chrono::system_clock::to_time_t(now);
        log_file << "=== Logging ended at " 
                 << std::put_time(std::localtime(&now_time_t), "%Y-%m-%d %H:%M:%S")
                 << " ===" << std::endl;
    }
}
