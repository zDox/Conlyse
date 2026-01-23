#ifndef HTTP_CLIENT_HPP
#define HTTP_CLIENT_HPP

#include "http_response.hpp"
#include "proxy_config.hpp"
#include "async_https_request.hpp"
#include <boost/asio.hpp>
#include <boost/asio/ssl.hpp>
#include <boost/asio/awaitable.hpp>
#include <boost/asio/co_spawn.hpp>
#include <boost/asio/detached.hpp>
#include <string>
#include <chrono>
#include <vector>
#include <thread>
#include <future>

namespace asio = boost::asio;
namespace ssl = asio::ssl;

// httplib-like Client class
class HttpClient {
public:
    HttpClient(const std::string& url, size_t num_threads = 4);
    ~HttpClient();
    
    void enable_server_certificate_verification(bool enable);
    void set_follow_location(bool follow);
    void set_connection_timeout(std::chrono::seconds timeout);
    void set_proxy(const std::string& host, int port, 
                   const std::string& username = "", 
                   const std::string& password = "");
    void clear_proxy();
    
    // Synchronous POST request
    HttpResponse Post(const std::string& path,
                     const Headers& headers,
                     const std::string& body,
                     const std::string& content_type);
    
    // Asynchronous POST request
    asio::awaitable<HttpResponse> Post_async(
        const std::string& path,
        const Headers& headers,
        const std::string& body,
        const std::string& content_type);
    
    // Synchronous GET request
    HttpResponse Get(const std::string& path, const Headers& headers = {});
    
    // Asynchronous GET request
    asio::awaitable<HttpResponse> Get_async(
        const std::string& path,
        const Headers& headers = {});
    
    asio::io_context& get_io_context();
    
private:
    void parse_url(const std::string& url);
    
    asio::io_context io_context_;
    asio::executor_work_guard<asio::io_context::executor_type> work_guard_;
    ssl::context ssl_context_;
    std::vector<std::thread> threads_;
    
    std::string host_;
    std::string base_path_;
    int port_;
    std::chrono::seconds timeout_;
    bool verify_ssl_;
    bool follow_redirects_ = false;
    ProxyConfig proxy_;
};

#endif // HTTP_CLIENT_HPP
