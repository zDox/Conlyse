#ifndef ASYNC_HTTPS_CLIENT_HPP
#define ASYNC_HTTPS_CLIENT_HPP

#include <boost/asio.hpp>
#include <boost/asio/ssl.hpp>
#include <boost/asio/awaitable.hpp>
#include <boost/asio/co_spawn.hpp>
#include <boost/asio/detached.hpp>
#include <boost/asio/use_awaitable.hpp>
#include <boost/asio/experimental/awaitable_operators.hpp>
#include <memory>
#include <string>
#include <chrono>
#include <vector>
#include <thread>
#include <map>
#include <sstream>

namespace asio = boost::asio;
using tcp = asio::ip::tcp;
namespace ssl = asio::ssl;

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

// Awaitable HTTPS request class with timeout support
class AsyncHttpsRequest : public std::enable_shared_from_this<AsyncHttpsRequest> {
public:
    AsyncHttpsRequest(asio::io_context& io_context, 
                     ssl::context& ssl_context,
                     std::chrono::seconds timeout,
                     const ProxyConfig& proxy = ProxyConfig())
        : resolver_(io_context),
          ssl_socket_(io_context, ssl_context),
          timeout_timer_(io_context),
          timeout_duration_(timeout),
          proxy_(proxy) {}
    
    asio::awaitable<HttpResponse> execute(
        const std::string& host, 
        const std::string& port,
        const std::string& method,
        const std::string& path,
        const Headers& headers,
        const std::string& body,
        const std::string& content_type) {
        
        using namespace boost::asio::experimental::awaitable_operators;
        
        auto self = shared_from_this();
        HttpResponse response;
        response.success = false;
        response.timeout = false;
        response.status_code = 0;
        
        auto start_time = std::chrono::steady_clock::now();
        
        try {
            // Set SNI hostname
            if (!SSL_set_tlsext_host_name(ssl_socket_.native_handle(), host.c_str())) {
                throw std::runtime_error("Failed to set SNI hostname");
            }
            
            // Set up timeout
            timeout_timer_.expires_after(timeout_duration_);
            
            // Determine connection target (proxy or direct)
            std::string connect_host = proxy_.enabled ? proxy_.host : host;
            std::string connect_port = proxy_.enabled ? std::to_string(proxy_.port) : port;
            
            // Resolve with timeout
            auto resolve_result = co_await (
                resolver_.async_resolve(connect_host, connect_port, asio::use_awaitable) ||
                timeout_timer_.async_wait(asio::use_awaitable)
            );
            
            if (resolve_result.index() == 1) {
                response.timeout = true;
                response.error_message = "Resolve timeout";
                co_return response;
            }
            
            auto endpoints = std::get<0>(resolve_result);
            timeout_timer_.expires_after(timeout_duration_);
            
            // Connect with timeout
            auto connect_result = co_await (
                asio::async_connect(ssl_socket_.lowest_layer(), endpoints, asio::use_awaitable) ||
                timeout_timer_.async_wait(asio::use_awaitable)
            );
            
            if (connect_result.index() == 1) {
                response.timeout = true;
                response.error_message = "Connect timeout";
                co_return response;
            }
            
            // If using proxy, perform CONNECT handshake
            if (proxy_.enabled) {
                // Build CONNECT request
                std::ostringstream connect_request;
                connect_request << "CONNECT " << host << ":" << port << " HTTP/1.1\r\n";
                connect_request << "Host: " << host << ":" << port << "\r\n";
                
                // Add proxy authentication if credentials provided
                if (!proxy_.username.empty()) {
                    std::string auth_str = proxy_.username + ":" + proxy_.password;
                    std::string auth_header = "Proxy-Authorization: Basic " + base64_encode(auth_str) + "\r\n";
                    connect_request << auth_header;
                }
                
                connect_request << "\r\n";
                
                std::string connect_str = connect_request.str();
                
                // Write CONNECT request with timeout - use next_layer() to access the TCP socket
                timeout_timer_.expires_after(timeout_duration_);
                
                auto proxy_write_result = co_await (
                    asio::async_write(ssl_socket_.next_layer(), asio::buffer(connect_str), asio::use_awaitable) ||
                    timeout_timer_.async_wait(asio::use_awaitable)
                );
                
                if (proxy_write_result.index() == 1) {
                    response.timeout = true;
                    response.error_message = "Proxy CONNECT write timeout";
                    co_return response;
                }
                
                // Read CONNECT response - read until we have complete headers
                asio::streambuf proxy_response_buf;
                timeout_timer_.expires_after(timeout_duration_);
                
                auto proxy_read_result = co_await (
                    asio::async_read_until(ssl_socket_.next_layer(), proxy_response_buf, "\r\n\r\n", asio::use_awaitable) ||
                    timeout_timer_.async_wait(asio::use_awaitable)
                );
                
                if (proxy_read_result.index() == 1) {
                    response.timeout = true;
                    response.error_message = "Proxy CONNECT response timeout";
                    co_return response;
                }
                
                // Parse proxy response
                std::istream proxy_stream(&proxy_response_buf);
                std::string http_version;
                int proxy_status;
                proxy_stream >> http_version >> proxy_status;
                
                if (proxy_status != 200) {
                    response.error_message = "Proxy CONNECT failed with status: " + std::to_string(proxy_status);
                    co_return response;
                }
                
                // Consume the rest of the CONNECT response headers
                std::string line;
                while (std::getline(proxy_stream, line) && line != "\r") {
                    // Discard proxy response headers
                }
            }
            
            // SSL handshake with timeout
            timeout_timer_.expires_after(timeout_duration_);
            
            auto handshake_result = co_await (
                ssl_socket_.async_handshake(ssl::stream_base::client, asio::use_awaitable) ||
                timeout_timer_.async_wait(asio::use_awaitable)
            );
            
            if (handshake_result.index() == 1) {
                response.timeout = true;
                response.error_message = "SSL handshake timeout";
                co_return response;
            }
            
            // Build HTTP request
            std::ostringstream request_stream;
            request_stream << method << " " << path << " HTTP/1.1\r\n";
            request_stream << "Host: " << host << "\r\n";
            
            // Add custom headers
            for (const auto& [key, value] : headers) {
                request_stream << key << ": " << value << "\r\n";
            }
            
            // Add body if present
            if (!body.empty()) {
                request_stream << "Content-Type: " << content_type << "\r\n";
                request_stream << "Content-Length: " << body.length() << "\r\n";
            }
            
            request_stream << "Connection: close\r\n";
            request_stream << "\r\n";
            
            if (!body.empty()) {
                request_stream << body;
            }
            
            std::string request_str = request_stream.str();
            
            // Write request with timeout
            timeout_timer_.expires_after(timeout_duration_);
            
            auto write_result = co_await (
                asio::async_write(ssl_socket_, asio::buffer(request_str), asio::use_awaitable) ||
                timeout_timer_.async_wait(asio::use_awaitable)
            );
            
            if (write_result.index() == 1) {
                response.timeout = true;
                response.error_message = "Write timeout";
                co_return response;
            }
            
            // Read response with timeout
            asio::streambuf response_buffer;
            timeout_timer_.expires_after(timeout_duration_);
            
            // Read status line
            auto read_result = co_await (
                asio::async_read_until(ssl_socket_, response_buffer, "\r\n", asio::use_awaitable) ||
                timeout_timer_.async_wait(asio::use_awaitable)
            );
            
            if (read_result.index() == 1) {
                response.timeout = true;
                response.error_message = "Read timeout (status line)";
                co_return response;
            }
            
            // Parse status line
            std::istream response_stream(&response_buffer);
            std::string http_version;
            response_stream >> http_version >> response.status_code;
            std::string status_message;
            std::getline(response_stream, status_message);
            
            // Read headers
            timeout_timer_.expires_after(timeout_duration_);
            
            auto headers_result = co_await (
                asio::async_read_until(ssl_socket_, response_buffer, "\r\n\r\n", asio::use_awaitable) ||
                timeout_timer_.async_wait(asio::use_awaitable)
            );
            
            if (headers_result.index() == 1) {
                response.timeout = true;
                response.error_message = "Read timeout (headers)";
                co_return response;
            }
            
            // Parse headers
            std::string header_line;
            while (std::getline(response_stream, header_line) && header_line != "\r") {
                size_t colon_pos = header_line.find(':');
                if (colon_pos != std::string::npos) {
                    std::string key = header_line.substr(0, colon_pos);
                    std::string value = header_line.substr(colon_pos + 2);
                    // Remove trailing \r if present
                    if (!value.empty() && value.back() == '\r') {
                        value.pop_back();
                    }
                    response.headers[key] = value;
                }
            }
            
            // Read body
            std::ostringstream body_stream;
            
            // First, add any data already in the buffer
            if (response_buffer.size() > 0) {
                body_stream << &response_buffer;
            }
            
            // Read remaining data until EOF
            timeout_timer_.expires_after(timeout_duration_);
            
            boost::system::error_code ec;
            while (true) {
                auto body_result = co_await (
                    asio::async_read(ssl_socket_, response_buffer, 
                                    asio::transfer_at_least(1), 
                                    asio::as_tuple(asio::use_awaitable)) ||
                    timeout_timer_.async_wait(asio::as_tuple(asio::use_awaitable))
                );
                
                if (body_result.index() == 1) {
                    // Timeout
                    auto [timer_ec] = std::get<1>(body_result);
                    if (!timer_ec) {
                        response.timeout = true;
                        response.error_message = "Read timeout (body)";
                        co_return response;
                    }
                    break;
                }
                
                auto [read_ec, bytes_transferred] = std::get<0>(body_result);
                if (read_ec == asio::error::eof) {
                    // Connection closed by server (expected)
                    body_stream << &response_buffer;
                    break;
                } else if (read_ec) {
                    // Other error
                    throw boost::system::system_error(read_ec);
                }
                
                body_stream << &response_buffer;
            }
            
            response.data = body_stream.str();
            
            auto end_time = std::chrono::steady_clock::now();
            response.latency = std::chrono::duration_cast<std::chrono::milliseconds>(
                end_time - start_time);
            
            response.success = true;
            timeout_timer_.cancel();
            
            // Graceful SSL shutdown
            co_await ssl_socket_.async_shutdown(asio::as_tuple(asio::use_awaitable));
            
        } catch (const std::exception& e) {
            auto end_time = std::chrono::steady_clock::now();
            response.latency = std::chrono::duration_cast<std::chrono::milliseconds>(
                end_time - start_time);
            response.success = false;
            response.error_message = e.what();
            timeout_timer_.cancel();
        }
        
        co_return response;
    }
    
private:
    // Simple base64 encoding for proxy authentication
    static std::string base64_encode(const std::string& input) {
        static const char* base64_chars = 
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "abcdefghijklmnopqrstuvwxyz"
            "0123456789+/";
        
        std::string result;
        int val = 0;
        int valb = -6;
        
        for (unsigned char c : input) {
            val = (val << 8) + c;
            valb += 8;
            while (valb >= 0) {
                result.push_back(base64_chars[(val >> valb) & 0x3F]);
                valb -= 6;
            }
        }
        
        if (valb > -6) {
            result.push_back(base64_chars[((val << 8) >> (valb + 8)) & 0x3F]);
        }
        
        while (result.size() % 4) {
            result.push_back('=');
        }
        
        return result;
    }

    tcp::resolver resolver_;
    ssl::stream<tcp::socket> ssl_socket_;
    asio::steady_timer timeout_timer_;
    std::chrono::seconds timeout_duration_;
    ProxyConfig proxy_;
};

// httplib-like Client class
class HttpClient {
public:
    HttpClient(const std::string& url, size_t num_threads = 4)
        : work_guard_(asio::make_work_guard(io_context_)),
          ssl_context_(ssl::context::tls_client),
          timeout_(30),
          verify_ssl_(true) {
        
        parse_url(url);
        
        // Configure SSL context
        ssl_context_.set_default_verify_paths();
        ssl_context_.set_verify_mode(ssl::verify_peer);
        
        // Start worker threads
        for (size_t i = 0; i < num_threads; ++i) {
            threads_.emplace_back([this]() {
                io_context_.run();
            });
        }
    }
    
    ~HttpClient() {
        work_guard_.reset();
        for (auto& t : threads_) {
            if (t.joinable()) t.join();
        }
    }
    
    void enable_server_certificate_verification(bool enable) {
        verify_ssl_ = enable;
        if (!enable) {
            ssl_context_.set_verify_mode(ssl::verify_none);
        } else {
            ssl_context_.set_verify_mode(ssl::verify_peer);
        }
    }
    
    void set_follow_location(bool follow) {
        follow_redirects_ = follow;
    }
    
    void set_connection_timeout(std::chrono::seconds timeout) {
        timeout_ = timeout;
    }
    
    void set_proxy(const std::string& host, int port, 
                   const std::string& username = "", 
                   const std::string& password = "") {
        proxy_ = ProxyConfig(host, port, username, password);
    }
    
    void clear_proxy() {
        proxy_ = ProxyConfig();
    }
    
    // Synchronous POST request
    HttpResponse Post(const std::string& path,
                     const Headers& headers,
                     const std::string& body,
                     const std::string& content_type) {
        
        std::promise<HttpResponse> promise;
        auto future = promise.get_future();
        
        asio::co_spawn(io_context_,
            [this, path, headers, body, content_type, &promise]() -> asio::awaitable<void> {
                try {
                    auto response = co_await Post_async(path, headers, body, content_type);
                    promise.set_value(response);
                } catch (...) {
                    promise.set_exception(std::current_exception());
                }
            },
            asio::detached);
        
        return future.get();
    }
    
    // Asynchronous POST request
    asio::awaitable<HttpResponse> Post_async(
        const std::string& path,
        const Headers& headers,
        const std::string& body,
        const std::string& content_type) {
        
        auto request = std::make_shared<AsyncHttpsRequest>(
            io_context_, ssl_context_, timeout_, proxy_);
        
        std::string full_path = path;
        if (!base_path_.empty() && path[0] != '/') {
            full_path = base_path_ + "/" + path;
        } else if (!base_path_.empty()) {
            full_path = base_path_ + path;
        }
        
        co_return co_await request->execute(
            host_, std::to_string(port_), "POST", full_path, 
            headers, body, content_type);
    }
    
    // Synchronous GET request
    HttpResponse Get(const std::string& path, const Headers& headers = {}) {
        std::promise<HttpResponse> promise;
        auto future = promise.get_future();
        
        asio::co_spawn(io_context_,
            [this, path, headers, &promise]() -> asio::awaitable<void> {
                try {
                    auto response = co_await Get_async(path, headers);
                    promise.set_value(response);
                } catch (...) {
                    promise.set_exception(std::current_exception());
                }
            },
            asio::detached);
        
        return future.get();
    }
    
    // Asynchronous GET request
    asio::awaitable<HttpResponse> Get_async(
        const std::string& path,
        const Headers& headers = {}) {
        
        auto request = std::make_shared<AsyncHttpsRequest>(
            io_context_, ssl_context_, timeout_, proxy_);
        
        std::string full_path = path;
        if (!base_path_.empty() && path[0] != '/') {
            full_path = base_path_ + "/" + path;
        } else if (!base_path_.empty()) {
            full_path = base_path_ + path;
        }
        
        co_return co_await request->execute(
            host_, std::to_string(port_), "GET", full_path, 
            headers, "", "");
    }
    
    asio::io_context& get_io_context() { return io_context_; }
    
private:
    void parse_url(const std::string& url) {
        std::string remaining;
        
        if (url.find("https://") == 0) {
            remaining = url.substr(8);
            port_ = 443;
        } else if (url.find("http://") == 0) {
            remaining = url.substr(7);
            port_ = 80;
        } else {
            remaining = url;
            port_ = 443;
        }
        
        // Extract path if present
        size_t slash_pos = remaining.find('/');
        if (slash_pos != std::string::npos) {
            base_path_ = remaining.substr(slash_pos);
            host_ = remaining.substr(0, slash_pos);
        } else {
            base_path_ = "";
            host_ = remaining;
        }
        
        // Extract port if present
        size_t colon_pos = host_.find(':');
        if (colon_pos != std::string::npos) {
            try {
                port_ = std::stoi(host_.substr(colon_pos + 1));
                host_ = host_.substr(0, colon_pos);
            } catch (const std::exception& e) {
                throw std::runtime_error("Invalid port number in URL: " + url);
            }
        }
    }
    
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

#endif // ASYNC_HTTPS_CLIENT_HPP
