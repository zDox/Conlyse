#ifndef HTTP_RESPONSE_HPP
#define HTTP_RESPONSE_HPP

#include <string>
#include <map>
#include <chrono>

// Result structure
struct HttpResponse {
    bool success;
    bool timeout;
    int status_code;
    std::string data;
    std::string error_message;
    std::chrono::milliseconds latency;
    std::map<std::string, std::string> headers;
};

using Headers = std::map<std::string, std::string>;

#endif // HTTP_RESPONSE_HPP
