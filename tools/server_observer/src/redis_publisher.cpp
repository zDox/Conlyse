#include "redis_publisher.hpp"
#include <iostream>
#include <cstring>

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
    
    // Use XADD to add to stream
    // XADD stream_name * timestamp <ts> game_id <gid> player_id <pid> response <response>
    redisReply* reply = static_cast<redisReply*>(
        redisCommand(context_, 
            "XADD %s * timestamp %lld game_id %d player_id %d response %s",
            stream_name_.c_str(),
            static_cast<long long>(timestamp),
            game_id,
            player_id,
            response.c_str()
        )
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
