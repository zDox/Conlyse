#ifndef ASYNC_HTTPS_REQUEST_HPP
#define ASYNC_HTTPS_REQUEST_HPP

#include "http_response.hpp"
#include "proxy_config.hpp"
#include <boost/asio.hpp>
#include <boost/asio/ssl.hpp>
#include <boost/asio/awaitable.hpp>
#include <boost/asio/use_awaitable.hpp>
#include <boost/asio/experimental/awaitable_operators.hpp>
#include <memory>
#include <string>
#include <chrono>
#include <sstream>

namespace asio = boost::asio;
using tcp = asio::ip::tcp;
namespace ssl = asio::ssl;

// Awaitable HTTPS request class with timeout support
class AsyncHttpsRequest {
public:
    AsyncHttpsRequest(asio::io_context& io_context, 
                     ssl::context& ssl_context,
                     std::chrono::seconds timeout,
                     const ProxyConfig& proxy = ProxyConfig());
    
    asio::awaitable<HttpResponse> execute(
        const std::string& host, 
        const std::string& port,
        const std::string& method,
        const std::string& path,
        const Headers& headers,
        const std::string& body,
        const std::string& content_type);
    
private:
    // Simple base64 encoding for proxy authentication
    static std::string base64_encode(const std::string& input);

    tcp::resolver resolver_;
    ssl::stream<tcp::socket> ssl_socket_;
    asio::steady_timer timeout_timer_;
    std::chrono::seconds timeout_duration_;
    ProxyConfig proxy_;
};

#endif // ASYNC_HTTPS_REQUEST_HPP
