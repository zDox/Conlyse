#ifndef HTTP_CLIENT_HPP
#define HTTP_CLIENT_HPP

#include "http_response.hpp"
#include "proxy_config.hpp"
#include "request_manager.hpp"
#include <boost/asio.hpp>
#include <boost/asio/ssl.hpp>
#include <boost/asio/awaitable.hpp>
#include <string>
#include <chrono>
#include <future>
#include <memory>

namespace asio = boost::asio;
namespace ssl = asio::ssl;

/**
 * HttpClient handles HTTP/HTTPS requests for a single observation API endpoint.
 * It uses a shared RequestManager for thread pool and in-flight request management.
 */
class HttpClient {
public:
    // Constructor takes a shared RequestManager and URL
    HttpClient(std::shared_ptr<RequestManager> manager, const std::string &url);

    ~HttpClient();

    void set_connection_timeout(std::chrono::seconds timeout);

    void set_url(const std::string &url);

    void set_proxy(const std::string &host, int port,
                   const std::string &username = "",
                   const std::string &password = "");

    void clear_proxy();

    // Synchronous POST request
    HttpResponse Post(
        const Headers &headers,
        const std::string &body,
        const std::string &content_type);

    // Asynchronous POST request
    asio::awaitable<HttpResponse> Post_async(
        const Headers &headers,
        const std::string &body,
        const std::string &content_type);

    // Synchronous GET request
    HttpResponse Get(const Headers &headers = {});

    // Asynchronous GET request
    asio::awaitable<HttpResponse> Get_async(
        const Headers &headers = {});

    asio::io_context &get_io_context();

private:
    void parse_url(const std::string &url);

    std::shared_ptr<RequestManager> manager_;
    std::string host_;
    std::string base_path_;
    int port_{};
    std::chrono::seconds timeout_;
    ProxyConfig proxy_;
};

#endif // HTTP_CLIENT_HPP
