#ifndef PROXY_CONFIG_HPP
#define PROXY_CONFIG_HPP

#include <string>

// Proxy configuration structure
struct ProxyConfig {
    bool enabled = false;
    std::string host;
    int port = 0;
    std::string username;
    std::string password;
    
    ProxyConfig() = default;
    ProxyConfig(const std::string& proxy_host, int proxy_port, 
                const std::string& proxy_username = "", 
                const std::string& proxy_password = "")
        : enabled(true), host(proxy_host), port(proxy_port), 
          username(proxy_username), password(proxy_password) {}
};

#endif // PROXY_CONFIG_HPP
