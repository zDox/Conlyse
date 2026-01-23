#include "http_client.hpp"

HttpClient::HttpClient(const std::string& url, size_t num_threads)
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

HttpClient::~HttpClient() {
    work_guard_.reset();
    for (auto& t : threads_) {
        if (t.joinable()) t.join();
    }
}

void HttpClient::enable_server_certificate_verification(bool enable) {
    verify_ssl_ = enable;
    if (!enable) {
        ssl_context_.set_verify_mode(ssl::verify_none);
    } else {
        ssl_context_.set_verify_mode(ssl::verify_peer);
    }
}

void HttpClient::set_follow_location(bool follow) {
    follow_redirects_ = follow;
}

void HttpClient::set_connection_timeout(std::chrono::seconds timeout) {
    timeout_ = timeout;
}

void HttpClient::set_proxy(const std::string& host, int port, 
               const std::string& username, 
               const std::string& password) {
    proxy_ = ProxyConfig(host, port, username, password);
}

void HttpClient::clear_proxy() {
    proxy_ = ProxyConfig();
}

HttpResponse HttpClient::Post(const std::string& path,
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

asio::awaitable<HttpResponse> HttpClient::Post_async(
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

HttpResponse HttpClient::Get(const std::string& path, const Headers& headers) {
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

asio::awaitable<HttpResponse> HttpClient::Get_async(
    const std::string& path,
    const Headers& headers) {
    
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

asio::io_context& HttpClient::get_io_context() {
    return io_context_;
}

void HttpClient::parse_url(const std::string& url) {
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
