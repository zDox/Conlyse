#ifndef RECORDING_STORAGE_HPP
#define RECORDING_STORAGE_HPP

#include <string>
#include <fstream>
#include <mutex>
#include <vector>
#include <cstdint>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

class RecordingStorage {
public:
    RecordingStorage(const std::string& output_path,
                    const std::string& metadata_path = "",
                    const std::string& long_term_storage_path = "",
                    int file_size_threshold = 0);
    
    void save_response(std::string&& response_str);
    void update_resume_metadata(const json& resume);
    json get_resume_metadata() const;
    bool has_resume_metadata() const;
    void flush_metadata();  // Save cached metadata to disk
    
    void setup_logging();
    void teardown_logging();
    
private:
    std::string output_path_;
    std::string metadata_path_;
    std::string long_term_storage_path_;
    int file_size_threshold_;
    int file_sequence_;
    
    std::string responses_file_;
    std::string metadata_file_;
    std::string recorder_log_file_;
    
    json metadata_cache_;
    json resume_metadata_;
    mutable std::mutex lock_;
    
    void init_files();
    void save_metadata(const json& metadata);
    json load_metadata();
    void restore_file_sequence();
    void update_file_sequence();
    size_t get_file_size(const std::string& file_path);
    bool should_rotate_file();
    void rotate_to_long_term_storage();
    void append_bytes_to_file(const std::string& file_path, uint64_t timestamp, const std::vector<uint8_t>& data);
};

#endif // RECORDING_STORAGE_HPP
