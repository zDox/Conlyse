#ifndef HTTP_RESPONSE_HPP
#define HTTP_RESPONSE_HPP

#include <string>
#include <map>
#include <chrono>
#include <sstream>
#include <iomanip>

// Detailed timing information for each step of the request
struct RequestTimings {
    std::chrono::milliseconds resolve_duration{0};
    std::chrono::milliseconds connect_duration{0};
    std::chrono::milliseconds proxy_connect_duration{0};
    std::chrono::milliseconds ssl_handshake_duration{0};
    std::chrono::milliseconds write_duration{0};
    std::chrono::milliseconds time_to_first_byte{0};  // Server processing + network time
    std::chrono::milliseconds read_status_duration{0};  // Actual time to read status line
    std::chrono::milliseconds read_headers_duration{0};
    std::chrono::milliseconds read_body_duration{0};
    std::chrono::milliseconds decompress_duration{0};
    std::chrono::milliseconds total_duration{0};

    // Get a formatted string with all timing information
    std::string to_string() const {
        std::ostringstream oss;
        oss << "Request Timing Breakdown:\n"
            << "  Resolve:        " << std::setw(6) << resolve_duration.count() << " ms\n"
            << "  Connect:        " << std::setw(6) << connect_duration.count() << " ms\n";

        if (proxy_connect_duration.count() > 0) {
            oss << "  Proxy Connect:  " << std::setw(6) << proxy_connect_duration.count() << " ms\n";
        }

        oss << "  SSL Handshake:  " << std::setw(6) << ssl_handshake_duration.count() << " ms\n"
            << "  Write Request:  " << std::setw(6) << write_duration.count() << " ms\n"
            << "  Time to 1st Byte:" << std::setw(5) << time_to_first_byte.count() << " ms (server processing)\n"
            << "  Read Status:    " << std::setw(6) << read_status_duration.count() << " ms\n"
            << "  Read Headers:   " << std::setw(6) << read_headers_duration.count() << " ms\n"
            << "  Read Body:      " << std::setw(6) << read_body_duration.count() << " ms\n";

        if (decompress_duration.count() > 0) {
            oss << "  Decompress:     " << std::setw(6) << decompress_duration.count() << " ms\n";
        }

        oss << "  ----------------------------------------\n"
            << "  Total:          " << std::setw(6) << total_duration.count() << " ms";

        return oss.str();
    }
};

// Result structure
struct HttpResponse {
    bool success;
    bool timeout;
    int status_code;
    std::string data;
    std::string error_message;
    std::chrono::milliseconds latency;  // Kept for backward compatibility
    std::map<std::string, std::string> headers;
    RequestTimings timings;  // Detailed timing information
};

using Headers = std::map<std::string, std::string>;

#endif // HTTP_RESPONSE_HPP
