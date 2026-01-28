#ifndef PROXY_CONFIG_HPP
#define PROXY_CONFIG_HPP

#include <string>

// Proxy configuration structure
struct ProxyConfig {
    std::string proxy_id;
    bool enabled = false;
    std::string host;
    int port = 0;
    std::string username;
    std::string password;
    
    ProxyConfig() = default;
    ProxyConfig(const std::string& proxy_host, int proxy_port, 
                const std::string& proxy_username = "", 
                const std::string& proxy_password = "",
                const std::string& id = "")
        : proxy_id(id), enabled(true), host(proxy_host), port(proxy_port),
          username(proxy_username), password(proxy_password) {}

    // Parse proxy URL format: http://[username:password@]host:port
    static ProxyConfig from_url(const std::string& proxy_url);

    // Convert to proxy URL format: http://[username:password@]host:port
    std::string to_url() const;
};

#endif // PROXY_CONFIG_HPP
