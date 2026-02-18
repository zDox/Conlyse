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

bool RedisPublisher::publish_compressed_response(int64_t timestamp, int game_id, int player_id,
                                                 const std::vector<char>& compressed_response) {
    if (!connected_ || !context_) {
        // Try to reconnect
        if (!connect()) {
            return false;
        }
    }
    
    // Prepare string values that must persist for the duration of the Redis command
    std::string ts_str = std::to_string(timestamp);
    std::string gid_str = std::to_string(game_id);
    std::string pid_str = std::to_string(player_id);
    
    // Build command with static array first, then add compressed response
    const char* argv[9];
    size_t argvlen[9];
    
    argv[0] = "XADD"; argvlen[0] = 4;
    argv[1] = stream_name_.c_str(); argvlen[1] = stream_name_.length();
    argv[2] = "*"; argvlen[2] = 1;
    argv[3] = "timestamp"; argvlen[3] = 9;
    argv[4] = ts_str.c_str(); argvlen[4] = ts_str.length();
    argv[5] = "game_id"; argvlen[5] = 7;
    argv[6] = gid_str.c_str(); argvlen[6] = gid_str.length();
    argv[7] = "player_id"; argvlen[7] = 9;
    argv[8] = pid_str.c_str(); argvlen[8] = pid_str.length();
    
    // Append response field and compressed data
    std::vector<const char*> full_argv(argv, argv + 9);
    std::vector<size_t> full_argvlen(argvlen, argvlen + 9);
    full_argv.push_back("response");
    full_argvlen.push_back(8);
    full_argv.push_back(compressed_response.data());
    full_argvlen.push_back(compressed_response.size());
    
    redisReply* reply = static_cast<redisReply*>(
        redisCommandArgv(context_, full_argv.size(), full_argv.data(), full_argvlen.data())
    );
    
    if (reply == nullptr) {
        std::cerr << "Redis XADD command failed: " << context_->errstr << std::endl;
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
