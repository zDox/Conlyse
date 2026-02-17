#include "redis_publisher.hpp"
#include <iostream>
#include <cstring>
#include <zstd.h>
#include <stdexcept>

RedisPublisher::RedisPublisher(const std::string& host, int port, const std::string& stream_name)
    : host_(host), port_(port), stream_name_(stream_name), password_(""),
      context_(nullptr), connected_(false) {
}

RedisPublisher::RedisPublisher(const std::string& host, int port, const std::string& stream_name,
                               const std::string& password)
    : host_(host), port_(port), stream_name_(stream_name), password_(password),
      context_(nullptr), connected_(false) {
}

RedisPublisher::~RedisPublisher() {
    disconnect();
}

bool RedisPublisher::connect() {
    if (connected_) {
        return true;
    }
    
    // Connect to Redis
    context_ = redisConnect(host_.c_str(), port_);
    
    if (context_ == nullptr || context_->err) {
        if (context_) {
            std::cerr << "Redis connection error: " << context_->errstr << std::endl;
            redisFree(context_);
            context_ = nullptr;
        } else {
            std::cerr << "Redis connection error: can't allocate redis context" << std::endl;
        }
        return false;
    }
    
    // Authenticate if password provided
    if (!password_.empty() && !authenticate()) {
        disconnect();
        return false;
    }
    
    connected_ = true;
    std::cout << "Connected to Redis at " << host_ << ":" << port_ << std::endl;
    return true;
}

void RedisPublisher::disconnect() {
    if (context_) {
        redisFree(context_);
        context_ = nullptr;
    }
    connected_ = false;
}

bool RedisPublisher::is_connected() const {
    return connected_;
}

bool RedisPublisher::authenticate() {
    if (!context_) {
        return false;
    }
    
    redisReply* reply = static_cast<redisReply*>(
        redisCommand(context_, "AUTH %s", password_.c_str())
    );
    
    if (reply == nullptr) {
        std::cerr << "Redis AUTH command failed" << std::endl;
        return false;
    }
    
    bool success = (reply->type == REDIS_REPLY_STATUS && 
                   strcmp(reply->str, "OK") == 0);
    
    freeReplyObject(reply);
    
    if (!success) {
        std::cerr << "Redis authentication failed" << std::endl;
    }
    
    return success;
}

bool RedisPublisher::publish_response(int64_t timestamp, int game_id, int player_id,
                                     const std::string& response) {
    if (!connected_ || !context_) {
        // Try to reconnect
        if (!connect()) {
            return false;
        }
    }
    
    // Compress the JSON response
    std::vector<char> compressed_data;
    try {
        compressed_data = compress_data(response);
    } catch (const std::exception& e) {
        std::cerr << "Failed to compress response: " << e.what() << std::endl;
        return false;
    }
    
    // Prepare string values that must persist for the duration of the Redis command
    std::string ts_str = std::to_string(timestamp);
    std::string gid_str = std::to_string(game_id);
    std::string pid_str = std::to_string(player_id);
    
    // Build argv array with binary-safe data handling
    std::vector<const char*> argv;
    std::vector<size_t> argvlen;
    
    // Command: XADD
    argv.push_back("XADD");
    argvlen.push_back(4);
    
    // Stream name
    argv.push_back(stream_name_.c_str());
    argvlen.push_back(stream_name_.length());
    
    // Auto-generate ID with *
    argv.push_back("*");
    argvlen.push_back(1);
    
    // Field: timestamp
    argv.push_back("timestamp");
    argvlen.push_back(9);
    
    // Value: timestamp
    argv.push_back(ts_str.c_str());
    argvlen.push_back(ts_str.length());
    
    // Field: game_id
    argv.push_back("game_id");
    argvlen.push_back(7);
    
    // Value: game_id
    argv.push_back(gid_str.c_str());
    argvlen.push_back(gid_str.length());
    
    // Field: player_id
    argv.push_back("player_id");
    argvlen.push_back(9);
    
    // Value: player_id
    argv.push_back(pid_str.c_str());
    argvlen.push_back(pid_str.length());
    
    // Field: response
    argv.push_back("response");
    argvlen.push_back(8);
    
    // Value: compressed binary data
    argv.push_back(compressed_data.data());
    argvlen.push_back(compressed_data.size());
    
    // Execute Redis command
    redisReply* reply = static_cast<redisReply*>(
        redisCommandArgv(context_, argv.size(), argv.data(), argvlen.data())
    );
    
    if (reply == nullptr) {
        std::cerr << "Redis XADD command failed: " << context_->errstr << std::endl;
        // Connection might be lost, mark as disconnected
        connected_ = false;
        return false;
    }
    
    bool success = (reply->type == REDIS_REPLY_STRING);
    
    if (!success) {
        std::cerr << "Redis XADD failed, unexpected reply type: " << reply->type << std::endl;
    }
    
    freeReplyObject(reply);
    return success;
}

std::vector<char> RedisPublisher::compress_data(const std::string& data) {
    // Get the maximum compressed size
    size_t max_compressed_size = ZSTD_compressBound(data.size());
    
    // Allocate buffer for compressed data
    std::vector<char> compressed(max_compressed_size);
    
    // Compress the data using default compression level (3)
    size_t compressed_size = ZSTD_compress(
        compressed.data(), 
        compressed.size(),
        data.data(), 
        data.size(),
        3  // Compression level (1-22, 3 is default and good balance)
    );
    
    // Check for compression error
    if (ZSTD_isError(compressed_size)) {
        throw std::runtime_error(
            std::string("Zstd compression failed: ") + ZSTD_getErrorName(compressed_size)
        );
    }
    
    // Resize to actual compressed size
    compressed.resize(compressed_size);
    
    return compressed;
}
