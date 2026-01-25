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

    // Helper method to handle timeout operations
    template<typename AsyncOp>
    asio::awaitable<std::variant<typename AsyncOp::result_type, boost::system::error_code>>
    with_timeout(AsyncOp&& operation);

    // Connection phase helpers
    asio::awaitable<bool> resolve_host(const std::string& host, const std::string& port,
                                        HttpResponse& response, tcp::resolver::results_type& endpoints);
    asio::awaitable<bool> connect_to_server(const tcp::resolver::results_type& endpoints,
                                             HttpResponse& response);
    asio::awaitable<bool> perform_proxy_connect(const std::string& host, const std::string& port,
                                                 HttpResponse& response);
    asio::awaitable<bool> perform_ssl_handshake(HttpResponse& response);

    // HTTP request/response helpers
    std::string build_http_request(const std::string& host, const std::string& method,
                                   const std::string& path, const Headers& headers,
                                   const std::string& body, const std::string& content_type);
    asio::awaitable<bool> send_http_request(const std::string& request, HttpResponse& response);
    asio::awaitable<bool> read_status_line(asio::streambuf& buffer, HttpResponse& response);
    asio::awaitable<bool> read_headers(asio::streambuf& buffer, HttpResponse& response);
    asio::awaitable<bool> read_body(asio::streambuf& buffer, HttpResponse& response);

    void decompress_if_needed(HttpResponse& response);
    void record_timing(std::chrono::steady_clock::time_point start,
                      std::chrono::milliseconds& timing_field);

    tcp::resolver resolver_;
    ssl::stream<tcp::socket> ssl_socket_;
    asio::steady_timer timeout_timer_;
    std::chrono::seconds timeout_duration_;
    ProxyConfig proxy_;
};

#endif // ASYNC_HTTPS_REQUEST_HPP
