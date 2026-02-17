#ifndef REDIS_PUBLISHER_HPP
#define REDIS_PUBLISHER_HPP

#include <string>
#include <memory>
#include <vector>
#include <nlohmann/json.hpp>
#include <hiredis/hiredis.h>

using json = nlohmann::json;

/**
 * Redis publisher for streaming game responses
 */
class RedisPublisher {
public:
    /**
     * Initialize Redis publisher
     * @param host Redis host
     * @param port Redis port
     * @param stream_name Name of the Redis stream to publish to
     */
    RedisPublisher(const std::string& host, int port, const std::string& stream_name);
    
    /**
     * Initialize with optional password
     */
    RedisPublisher(const std::string& host, int port, const std::string& stream_name, 
                   const std::string& password);
    
    ~RedisPublisher();
    
    /**
     * Connect to Redis server
     * @return true if connection successful
     */
    bool connect();
    
    /**
     * Disconnect from Redis server
     */
    void disconnect();
    
    /**
     * Check if connected to Redis
     */
    bool is_connected() const;
    
    /**
     * Publish a game response to the Redis stream
     * @param timestamp Unix timestamp in milliseconds
     * @param game_id Game ID
     * @param player_id Player ID
     * @param response JSON response data
     * @return true if publish successful
     */
    bool publish_response(int64_t timestamp, int game_id, int player_id, 
                         const std::string& response);
    
    /**
     * Publish an already-compressed game response to the Redis stream
     * @param timestamp Unix timestamp in milliseconds
     * @param game_id Game ID
     * @param player_id Player ID
     * @param compressed_response Pre-compressed response data
     * @return true if publish successful
     */
    bool publish_compressed_response(int64_t timestamp, int game_id, int player_id,
                                     const std::vector<char>& compressed_response);
    
private:
    std::string host_;
    int port_;
    std::string stream_name_;
    std::string password_;
    redisContext* context_;
    bool connected_;
    
    bool authenticate();
    std::vector<char> compress_data(const std::string& data);
};

#endif // REDIS_PUBLISHER_HPP
