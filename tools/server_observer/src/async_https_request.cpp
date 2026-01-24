#include "async_https_request.hpp"

#include <iostream>

AsyncHttpsRequest::AsyncHttpsRequest(asio::io_context& io_context, 
                                     ssl::context& ssl_context,
                                     std::chrono::seconds timeout,
                                     const ProxyConfig& proxy)
    : resolver_(io_context),
      ssl_socket_(io_context, ssl_context),
      timeout_timer_(io_context),
      timeout_duration_(timeout),
      proxy_(proxy) {}

std::string AsyncHttpsRequest::base64_encode(const std::string& input) {
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

asio::awaitable<HttpResponse> AsyncHttpsRequest::execute(
    const std::string& host, 
    const std::string& port,
    const std::string& method,
    const std::string& path,
    const Headers& headers,
    const std::string& body,
    const std::string& content_type) {
    
    using namespace boost::asio::experimental::awaitable_operators;
    
    HttpResponse response;
    response.success = false;
    response.timeout = false;
    response.status_code = 0;
    
    auto start_time = std::chrono::steady_clock::now();
    
    // Cleanup guard to ensure socket and timer are cleaned up before returning
    auto cleanup = [this]() {
        boost::system::error_code ec;
        timeout_timer_.cancel();
        if (ssl_socket_.lowest_layer().is_open()) {
            ssl_socket_.lowest_layer().close(ec);
        }
    };

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
            resolver_.async_resolve(connect_host, connect_port, asio::as_tuple(asio::use_awaitable)) ||
            timeout_timer_.async_wait(asio::as_tuple(asio::use_awaitable))
        );

        if (resolve_result.index() == 1) {
            response.timeout = true;
            response.error_message = "Resolve timeout";
            cleanup();
            co_return response;
        }
        std::cout << "Resolved " << connect_host << ":" << connect_port << std::endl;

        auto [resolve_ec, endpoints] = std::get<0>(resolve_result);
        if (resolve_ec) {
            throw boost::system::system_error(resolve_ec);
        }

        timeout_timer_.expires_after(timeout_duration_);

        // Connect with timeout
        auto connect_result = co_await (
            asio::async_connect(ssl_socket_.lowest_layer(), endpoints, asio::as_tuple(asio::use_awaitable)) ||
            timeout_timer_.async_wait(asio::as_tuple(asio::use_awaitable))
        );

        if (connect_result.index() == 1) {
            response.timeout = true;
            response.error_message = "Connect timeout";
            cleanup();
            co_return response;
        }
        std::cout << "Connected to " << host << ":" << port << std::endl;

        auto [connect_ec, connected_endpoint] = std::get<0>(connect_result);
        if (connect_ec) {
            throw boost::system::system_error(connect_ec);
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
                asio::async_write(ssl_socket_.next_layer(), asio::buffer(connect_str), asio::as_tuple(asio::use_awaitable)) ||
                timeout_timer_.async_wait(asio::as_tuple(asio::use_awaitable))
            );

            if (proxy_write_result.index() == 1) {
                response.timeout = true;
                response.error_message = "Proxy CONNECT write timeout";
                cleanup();
                co_return response;
            }

            auto [proxy_write_ec, proxy_bytes_written] = std::get<0>(proxy_write_result);
            if (proxy_write_ec) {
                throw boost::system::system_error(proxy_write_ec);
            }

            // Read CONNECT response - read until we have complete headers
            asio::streambuf proxy_response_buf;
            timeout_timer_.expires_after(timeout_duration_);

            auto proxy_read_result = co_await (
                asio::async_read_until(ssl_socket_.next_layer(), proxy_response_buf, "\r\n\r\n", asio::as_tuple(asio::use_awaitable)) ||
                timeout_timer_.async_wait(asio::as_tuple(asio::use_awaitable))
            );

            if (proxy_read_result.index() == 1) {
                response.timeout = true;
                response.error_message = "Proxy CONNECT response timeout";
                cleanup();
                co_return response;
            }

            auto [proxy_read_ec, proxy_bytes_read] = std::get<0>(proxy_read_result);
            if (proxy_read_ec) {
                throw boost::system::system_error(proxy_read_ec);
            }

            // Parse proxy response
            std::istream proxy_stream(&proxy_response_buf);
            std::string http_version;
            int proxy_status;
            proxy_stream >> http_version >> proxy_status;

            if (proxy_status != 200) {
                response.error_message = "Proxy CONNECT failed with status: " + std::to_string(proxy_status);
                cleanup();
                co_return response;
            }

            // Consume the rest of the CONNECT response headers
            std::string line;
            while (std::getline(proxy_stream, line) && line != "\r") {
                // Discard proxy response headers
            }
        }
        std::cout << "Starting SSL handshake with " << host << std::endl;

        // SSL handshake with timeout
        timeout_timer_.expires_after(timeout_duration_);

        auto handshake_result = co_await (
            ssl_socket_.async_handshake(ssl::stream_base::client, asio::as_tuple(asio::use_awaitable)) ||
            timeout_timer_.async_wait(asio::as_tuple(asio::use_awaitable))
        );

        if (handshake_result.index() == 1) {
            response.timeout = true;
            response.error_message = "SSL handshake timeout";
            cleanup();
            co_return response;
        }
        std::cout << "SSL Handshake completed with " << host << std::endl;

        auto [handshake_ec] = std::get<0>(handshake_result);
        if (handshake_ec) {
            throw boost::system::system_error(handshake_ec);
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
            asio::async_write(ssl_socket_, asio::buffer(request_str), asio::as_tuple(asio::use_awaitable)) ||
            timeout_timer_.async_wait(asio::as_tuple(asio::use_awaitable))
        );

        if (write_result.index() == 1) {
            response.timeout = true;
            response.error_message = "Write timeout";
            cleanup();
            co_return response;
        }
        std::cout << "HTTP request sent to " << host << std::endl;

        auto [write_ec, bytes_written] = std::get<0>(write_result);
        if (write_ec) {
            throw boost::system::system_error(write_ec);
        }

        // Read response with timeout
        asio::streambuf response_buffer;
        timeout_timer_.expires_after(timeout_duration_);

        // Read status line
        auto read_result = co_await (
            asio::async_read_until(ssl_socket_, response_buffer, "\r\n", asio::as_tuple(asio::use_awaitable)) ||
            timeout_timer_.async_wait(asio::as_tuple(asio::use_awaitable))
        );


        if (read_result.index() == 1) {
            response.timeout = true;
            response.error_message = "Read timeout (status line)";
            cleanup();
            co_return response;
        }
        std::cout << "Reading status line from " << host << std::endl;

        auto [read_ec, bytes_read] = std::get<0>(read_result);
        if (read_ec) {
            throw boost::system::system_error(read_ec);
        }

        // Parse status line
        std::istream response_stream(&response_buffer);
        std::string http_version;
        response_stream >> http_version >> response.status_code;
        std::string status_message;
        std::getline(response_stream, status_message);

        // Read headers
        timeout_timer_.expires_after(timeout_duration_);

        std::cout << "Reading headers from " << host << std::endl;
        auto headers_result = co_await (
            asio::async_read_until(ssl_socket_, response_buffer, "\r\n\r\n", asio::as_tuple(asio::use_awaitable)) ||
            timeout_timer_.async_wait(asio::as_tuple(asio::use_awaitable))
        );

        if (headers_result.index() == 1) {
            response.timeout = true;
            response.error_message = "Read timeout (headers)";
            cleanup();
            co_return response;
        }

        auto [headers_ec, headers_bytes] = std::get<0>(headers_result);
        if (headers_ec) {
            throw boost::system::system_error(headers_ec);
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
        std::cout << "Headers received from " << host << std::endl;

        // Read body
        std::ostringstream body_stream;

        // First, add any data already in the buffer
        if (response_buffer.size() > 0) {
            body_stream << &response_buffer;
        }

        // Read remaining data until EOF
        timeout_timer_.expires_after(timeout_duration_);
        std::cout << "Reading body from " << host << std::endl;
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
                    cleanup();
                    co_return response;
                }
                break;
            }

            auto [read_ec, bytes_transferred] = std::get<0>(body_result);
            if (read_ec == asio::error::eof ||
                read_ec == asio::ssl::error::stream_truncated) {
                // Connection closed by server (expected)
                // stream_truncated happens when server closes SSL connection without proper shutdown
                body_stream << &response_buffer;
                break;
            } else if (read_ec) {
                // Other error
                throw boost::system::system_error(read_ec);
            }

            body_stream << &response_buffer;
        }
        std::cout << "Body received from " << host << std::endl;
        response.data = body_stream.str();

        auto end_time = std::chrono::steady_clock::now();
        response.latency = std::chrono::duration_cast<std::chrono::milliseconds>(
            end_time - start_time);

        response.success = true;
        std::cout << "Request to " << host << " completed successfully" << std::endl;

        // Attempt graceful SSL shutdown with short timeout
        // Since we use "Connection: close", the server likely already closed the connection
        timeout_timer_.expires_after(std::chrono::seconds(2));
        auto shutdown_result = co_await (
            ssl_socket_.async_shutdown(asio::as_tuple(asio::use_awaitable)) ||
            timeout_timer_.async_wait(asio::as_tuple(asio::use_awaitable))
        );

        if (shutdown_result.index() == 0) {
            auto [shutdown_ec] = std::get<0>(shutdown_result);
            if (!shutdown_ec) {
                std::cout << "SSL shutdown completed cleanly for " << host << std::endl;
            }
        }
        // Ignore shutdown errors/timeouts - connection is already done

        // Clean up everything before returning
        cleanup();

    } catch (const std::exception& e) {
        auto end_time = std::chrono::steady_clock::now();
        response.latency = std::chrono::duration_cast<std::chrono::milliseconds>(
            end_time - start_time);
        response.success = false;
        response.error_message = e.what();

        // Clean up everything
        cleanup();
    }

    co_return response;
}