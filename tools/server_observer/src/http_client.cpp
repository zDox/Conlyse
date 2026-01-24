#include "http_client.hpp"

#include <utility>

#include "async_https_request.hpp"

HttpClient::HttpClient(std::shared_ptr<RequestManager> manager, const std::string& url)
    : manager_(std::move(std::move(manager))),
      timeout_(30),
      verify_ssl_(true) {
    
    if (!manager_) {
        throw std::runtime_error("HttpClient requires a valid RequestManager");
    }

    parse_url(url);
}
HttpClient::~HttpClient() = default;

void HttpClient::enable_server_certificate_verification(bool enable) {
    verify_ssl_ = enable;
}

void HttpClient::set_follow_location(bool follow) {
    follow_redirects_ = follow;
}

void HttpClient::set_connection_timeout(std::chrono::seconds timeout) {
    timeout_ = timeout;
}

void HttpClient::set_url(const std::string &url) {
    parse_url(url);
}

void HttpClient::set_proxy(const std::string& host, int port, 
                           const std::string& username, 
                           const std::string& password) {
    proxy_ = ProxyConfig(host, port, username, password);
}

void HttpClient::clear_proxy() {
    proxy_ = ProxyConfig();
}

HttpResponse HttpClient::Post(
                 const Headers& headers,
                 const std::string& body,
                 const std::string& content_type) {
    
    std::promise<HttpResponse> promise;
    auto future = promise.get_future();
    
    asio::co_spawn(manager_->get_io_context(),
        [this, headers, body, content_type, &promise]() -> asio::awaitable<void> {
            try {
                auto response = co_await Post_async(headers, body, content_type);
                promise.set_value(response);
            } catch (...) {
                promise.set_exception(std::current_exception());
            }
        },
        asio::detached);
    
    return future.get();
}

asio::awaitable<HttpResponse> HttpClient::Post_async(
    const Headers& headers,
    const std::string& body,
    const std::string& content_type) {
    
    // Acquire a request slot (blocks if max in-flight reached)
    RequestManager::RequestSlot slot(*manager_);

    auto request = std::make_shared<AsyncHttpsRequest>(
        manager_->get_io_context(), manager_->get_ssl_context(), timeout_, proxy_);

    co_return co_await request->execute(
        host_, std::to_string(port_), "POST", base_path_,
        headers, body, content_type);
}

HttpResponse HttpClient::Get(const Headers& headers) {
    std::promise<HttpResponse> promise;
    auto future = promise.get_future();
    
    asio::co_spawn(manager_->get_io_context(),
        [this, headers, &promise]() -> asio::awaitable<void> {
            try {
                auto response = co_await Get_async(headers);
                promise.set_value(response);
            } catch (...) {
                promise.set_exception(std::current_exception());
            }
        },
        asio::detached);
    
    return future.get();
}

asio::awaitable<HttpResponse> HttpClient::Get_async(
    const Headers& headers) {
    
    // Acquire a request slot (blocks if max in-flight reached)
    RequestManager::RequestSlot slot(*manager_);

    auto request = std::make_shared<AsyncHttpsRequest>(
        manager_->get_io_context(), manager_->get_ssl_context(), timeout_, proxy_);

    co_return co_await request->execute(
        host_, std::to_string(port_), "GET", base_path_,
        headers, "", "");
}

asio::io_context& HttpClient::get_io_context() {
    return manager_->get_io_context();
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
        } catch (const std::exception&) {
            throw std::runtime_error("Invalid port number in URL: " + url);
        }
    }
}
