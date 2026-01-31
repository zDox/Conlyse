#include "proxy_config.hpp"
#include <sstream>

ProxyConfig ProxyConfig::from_url(const std::string& proxy_url) {
    ProxyConfig proxy_config;

    if (proxy_url.empty()) {
        return proxy_config;
    }

    // Parse proxy URL format: http://[username:password@]host:port
    size_t proto_end = proxy_url.find("://");
    if (proto_end != std::string::npos) {
        std::string proxy_part = proxy_url.substr(proto_end + 3);

        // Check for authentication
        size_t at_pos = proxy_part.find('@');
        if (at_pos != std::string::npos) {
            std::string auth_part = proxy_part.substr(0, at_pos);
            proxy_part = proxy_part.substr(at_pos + 1);

            size_t colon_pos = auth_part.find(':');
            if (colon_pos != std::string::npos) {
                proxy_config.username = auth_part.substr(0, colon_pos);
                proxy_config.password = auth_part.substr(colon_pos + 1);
            }
        }

        // Parse host:port
        size_t colon_pos = proxy_part.find(':');
        if (colon_pos != std::string::npos) {
            proxy_config.host = proxy_part.substr(0, colon_pos);
            proxy_config.port = std::stoi(proxy_part.substr(colon_pos + 1));
            proxy_config.enabled = true;
        }
    }

    return proxy_config;
}

std::string ProxyConfig::to_url() const {
    if (!enabled || host.empty() || port == 0) {
        return "";
    }

    std::ostringstream url;
    url << "http://";

    if (!username.empty()) {
        url << username;
        if (!password.empty()) {
            url << ":" << password;
        }
        url << "@";
    }

    url << host << ":" << port;

    return url.str();
}

