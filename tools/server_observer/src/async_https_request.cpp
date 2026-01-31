#include "async_https_request.hpp"
#include "metrics.hpp"
#include <iostream>
#include <zlib.h>
#include <openssl/ssl.h>

namespace {
    // Decompress gzip-encoded data
    std::string gunzip(const std::string& input) {
        z_stream zs{};
        zs.next_in = reinterpret_cast<Bytef*>(const_cast<char*>(input.data()));
        zs.avail_in = input.size();

        if (inflateInit2(&zs, 16 + MAX_WBITS) != Z_OK) {
            throw std::runtime_error("inflateInit failed");
        }

        std::string output;
        constexpr size_t BUFFER_SIZE = 32768;
        char buffer[BUFFER_SIZE];

        int ret;
        do {
            zs.next_out = reinterpret_cast<Bytef*>(buffer);
            zs.avail_out = sizeof(buffer);

            ret = inflate(&zs, 0);
            if (ret != Z_OK && ret != Z_STREAM_END) {
                inflateEnd(&zs);
                throw std::runtime_error("inflate failed");
            }

            output.append(buffer, sizeof(buffer) - zs.avail_out);
        } while (ret != Z_STREAM_END);

        inflateEnd(&zs);
        return output;
    }
}


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
    
    try {
        // Set SNI hostname for proper SSL certificate validation
        if (!SSL_set_tlsext_host_name(ssl_socket_.native_handle(), host.c_str())) {
            throw std::runtime_error("Failed to set SNI hostname");
        }

        // Disable SSL write buffering to ensure immediate transmission
        // Note: Don't use SSL_MODE_AUTO_RETRY in async contexts as it can block
        SSL_set_mode(ssl_socket_.native_handle(), SSL_MODE_ENABLE_PARTIAL_WRITE);
        SSL_set_mode(ssl_socket_.native_handle(), SSL_MODE_ACCEPT_MOVING_WRITE_BUFFER);

        // Step 1: Resolve hostname
        tcp::resolver::results_type endpoints;
        std::string connect_host = proxy_.enabled ? proxy_.host : host;
        std::string connect_port = proxy_.enabled ? std::to_string(proxy_.port) : port;

        if (!co_await resolve_host(connect_host, connect_port, response, endpoints)) {
            co_return response;
        }

        // Step 2: Connect to server
        if (!co_await connect_to_server(endpoints, response)) {
            co_return response;
        }

        // Step 3: Perform proxy CONNECT if needed
        if (proxy_.enabled) {
            if (!co_await perform_proxy_connect(host, port, response)) {
                co_return response;
            }
        }

        // Step 4: SSL handshake
        if (!co_await perform_ssl_handshake(response)) {
            co_return response;
        }

        // Step 5: Send HTTP request
        std::string request = build_http_request(host, method, path, headers, body, content_type);
        if (!co_await send_http_request(request, response)) {
            co_return response;
        }

        // Step 6: Read HTTP response
        asio::streambuf response_buffer;

        if (!co_await read_status_line(response_buffer, response)) {
            co_return response;
        }

        if (!co_await read_headers(response_buffer, response)) {
            co_return response;
        }

        if (!co_await read_body(response_buffer, response)) {
            co_return response;
        }

        // Step 7: Post-processing
        decompress_if_needed(response);

        // Calculate total latency
        auto end_time = std::chrono::steady_clock::now();
        response.latency = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);
        response.timings.total_duration = response.latency;

        response.success = true;

    } catch (const std::exception& e) {
        auto end_time = std::chrono::steady_clock::now();
        response.latency = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);
        response.success = false;
        response.error_message = e.what();
        std::cerr << "Request failed: " << e.what() << std::endl;
    }
    
    // Record latency for metrics (both success and failure cases)
    Metrics::getInstance().recordRequestLatency(
        std::chrono::duration<double>(response.latency).count()
    );

    co_return response;
}

// ==================== Helper Method Implementations ====================

asio::awaitable<bool> AsyncHttpsRequest::resolve_host(
    const std::string& host,
    const std::string& port,
    HttpResponse& response,
    tcp::resolver::results_type& endpoints) {

    using namespace boost::asio::experimental::awaitable_operators;

    auto start = std::chrono::steady_clock::now();
    timeout_timer_.expires_after(timeout_duration_);

    // Use resolver flags to prefer IPv4 and improve connection speed
    tcp::resolver::flags resolve_flags = tcp::resolver::address_configured;

    auto resolve_result = co_await (
        resolver_.async_resolve(host, port, resolve_flags, asio::as_tuple(asio::use_awaitable)) ||
        timeout_timer_.async_wait(asio::as_tuple(asio::use_awaitable))
    );

    if (resolve_result.index() == 1) {
        response.timeout = true;
        response.error_message = "DNS resolution timeout";
        co_return false;
    }

    auto [ec, results] = std::get<0>(resolve_result);
    if (ec) {
        throw boost::system::system_error(ec);
    }

    endpoints = results;
    timeout_timer_.cancel();

    record_timing(start, response.timings.resolve_duration);
    co_return true;
}

asio::awaitable<bool> AsyncHttpsRequest::connect_to_server(
    const tcp::resolver::results_type& endpoints,
    HttpResponse& response) {

    using namespace boost::asio::experimental::awaitable_operators;

    auto start = std::chrono::steady_clock::now();
    timeout_timer_.expires_after(timeout_duration_);

    auto connect_result = co_await (
        asio::async_connect(ssl_socket_.lowest_layer(), endpoints, asio::as_tuple(asio::use_awaitable)) ||
        timeout_timer_.async_wait(asio::as_tuple(asio::use_awaitable))
    );

    if (connect_result.index() == 1) {
        response.timeout = true;
        response.error_message = "Connection timeout";
        co_return false;
    }

    auto [ec, connected_endpoint] = std::get<0>(connect_result);
    if (ec) {
        throw boost::system::system_error(ec);
    }

    // Disable Nagle's algorithm to avoid buffering delays
    ssl_socket_.lowest_layer().set_option(tcp::no_delay(true));

    // Set socket options for better performance
    ssl_socket_.lowest_layer().set_option(tcp::socket::keep_alive(true));

    // Set send/receive buffer sizes for optimal performance
    ssl_socket_.lowest_layer().set_option(boost::asio::socket_base::send_buffer_size(65536));
    ssl_socket_.lowest_layer().set_option(boost::asio::socket_base::receive_buffer_size(65536));

    timeout_timer_.cancel();
    record_timing(start, response.timings.connect_duration);
    co_return true;
}

asio::awaitable<bool> AsyncHttpsRequest::perform_proxy_connect(
    const std::string& host,
    const std::string& port,
    HttpResponse& response) {

    using namespace boost::asio::experimental::awaitable_operators;

    auto start = std::chrono::steady_clock::now();

    // Build CONNECT request
    std::ostringstream connect_request;
    connect_request << "CONNECT " << host << ":" << port << " HTTP/1.1\r\n";
    connect_request << "Host: " << host << ":" << port << "\r\n";

    // Add proxy authentication if credentials provided
    if (!proxy_.username.empty()) {
        std::string auth_str = proxy_.username + ":" + proxy_.password;
        connect_request << "Proxy-Authorization: Basic " << base64_encode(auth_str) << "\r\n";
    }

    connect_request << "\r\n";
    std::string connect_str = connect_request.str();

    // Send CONNECT request
    timeout_timer_.expires_after(timeout_duration_);
    auto write_result = co_await (
        asio::async_write(ssl_socket_.next_layer(), asio::buffer(connect_str),
                         asio::as_tuple(asio::use_awaitable)) ||
        timeout_timer_.async_wait(asio::as_tuple(asio::use_awaitable))
    );

    if (write_result.index() == 1) {
        response.timeout = true;
        response.error_message = "Proxy CONNECT write timeout";
        co_return false;
    }

    auto [write_ec, bytes_written] = std::get<0>(write_result);
    if (write_ec) {
        throw boost::system::system_error(write_ec);
    }

    timeout_timer_.cancel();

    // Read CONNECT response
    asio::streambuf proxy_response_buf;
    timeout_timer_.expires_after(timeout_duration_);

    auto read_result = co_await (
        asio::async_read_until(ssl_socket_.next_layer(), proxy_response_buf, "\r\n\r\n",
                              asio::as_tuple(asio::use_awaitable)) ||
        timeout_timer_.async_wait(asio::as_tuple(asio::use_awaitable))
    );

    if (read_result.index() == 1) {
        response.timeout = true;
        response.error_message = "Proxy CONNECT response timeout";
        co_return false;
    }

    auto [read_ec, bytes_read] = std::get<0>(read_result);
    if (read_ec) {
        throw boost::system::system_error(read_ec);
    }

    // Parse proxy response
    std::istream proxy_stream(&proxy_response_buf);
    std::string http_version;
    int proxy_status;
    proxy_stream >> http_version >> proxy_status;

    if (proxy_status != 200) {
        response.error_message = "Proxy CONNECT failed with status: " + std::to_string(proxy_status);
        co_return false;
    }

    // Consume remaining headers
    std::string line;
    while (std::getline(proxy_stream, line) && line != "\r") {
        // Discard proxy response headers
    }

    timeout_timer_.cancel();
    record_timing(start, response.timings.proxy_connect_duration);

    co_return true;
}

asio::awaitable<bool> AsyncHttpsRequest::perform_ssl_handshake(HttpResponse& response) {
    using namespace boost::asio::experimental::awaitable_operators;

    auto start = std::chrono::steady_clock::now();
    timeout_timer_.expires_after(timeout_duration_);


    auto handshake_result = co_await (
        ssl_socket_.async_handshake(ssl::stream_base::client, asio::as_tuple(asio::use_awaitable)) ||
        timeout_timer_.async_wait(asio::as_tuple(asio::use_awaitable))
    );

    if (handshake_result.index() == 1) {
        response.timeout = true;
        response.error_message = "SSL handshake timeout";
        co_return false;
    }

    auto [ec] = std::get<0>(handshake_result);
    if (ec) {
        throw boost::system::system_error(ec);
    }

    timeout_timer_.cancel();
    record_timing(start, response.timings.ssl_handshake_duration);

    co_return true;
}

std::string AsyncHttpsRequest::build_http_request(
    const std::string& host,
    const std::string& method,
    const std::string& path,
    const Headers& headers,
    const std::string& body,
    const std::string& content_type) {

    std::string real_path = path.empty() ? "/" : path;
    std::ostringstream request_stream;

    // Request line
    request_stream << method << " " << real_path << " HTTP/1.1\r\n";
    request_stream << "Host: " << host << "\r\n";

    // Add default headers if not provided by user
    bool has_accept = false;
    bool has_accept_encoding = false;
    bool has_user_agent = false;

    for (const auto& [key, value] : headers) {
        if (key == "Accept") has_accept = true;
        if (key == "Accept-Encoding") has_accept_encoding = true;
        if (key == "User-Agent") has_user_agent = true;
    }

    // Add defaults similar to Python requests
    if (!has_accept) {
        request_stream << "Accept: */*\r\n";
    }
    if (!has_accept_encoding) {
        request_stream << "Accept-Encoding: gzip, deflate\r\n";
    }
    if (!has_user_agent) {
        request_stream << "User-Agent: AsyncHttpsClient/1.0\r\n";
    }

    // Custom headers
    for (const auto& [key, value] : headers) {
        request_stream << key << ": " << value << "\r\n";
    }

    // Body-related headers
    if (!body.empty()) {
        request_stream << "Content-Type: " << content_type << "\r\n";
        request_stream << "Content-Length: " << body.size() << "\r\n";
    }

    request_stream << "Connection: close\r\n";
    request_stream << "\r\n";

    // Body
    if (!body.empty()) {
        request_stream << body;
    }

    return request_stream.str();
}

asio::awaitable<bool> AsyncHttpsRequest::send_http_request(
    const std::string& request,
    HttpResponse& response) {

    using namespace boost::asio::experimental::awaitable_operators;

    auto start = std::chrono::steady_clock::now();
    timeout_timer_.expires_after(timeout_duration_);


    auto write_result = co_await (
        asio::async_write(ssl_socket_, asio::buffer(request), asio::as_tuple(asio::use_awaitable)) ||
        timeout_timer_.async_wait(asio::as_tuple(asio::use_awaitable))
    );

    if (write_result.index() == 1) {
        response.timeout = true;
        response.error_message = "HTTP request write timeout";
        co_return false;
    }

    auto [ec, bytes_written] = std::get<0>(write_result);
    if (ec) {
        throw boost::system::system_error(ec);
    }

    timeout_timer_.cancel();
    record_timing(start, response.timings.write_duration);

    co_return true;
}

asio::awaitable<bool> AsyncHttpsRequest::read_status_line(
    asio::streambuf& buffer,
    HttpResponse& response) {

    using namespace boost::asio::experimental::awaitable_operators;

    auto ttfb_start = std::chrono::steady_clock::now();
    auto read_start = std::chrono::steady_clock::now();
    timeout_timer_.expires_after(timeout_duration_);

    auto read_result = co_await (
        asio::async_read_until(ssl_socket_, buffer, "\r\n", asio::as_tuple(asio::use_awaitable)) ||
        timeout_timer_.async_wait(asio::as_tuple(asio::use_awaitable))
    );

    auto read_end = std::chrono::steady_clock::now();

    if (read_result.index() == 1) {
        response.timeout = true;
        response.error_message = "Read timeout (status line)";
        co_return false;
    }

    auto [ec, bytes_read] = std::get<0>(read_result);
    if (ec) {
        throw boost::system::system_error(ec);
    }

    // Record timings
    response.timings.time_to_first_byte = std::chrono::duration_cast<std::chrono::milliseconds>(
        read_end - ttfb_start);
    response.timings.read_status_duration = std::chrono::duration_cast<std::chrono::milliseconds>(
        read_end - read_start);

    timeout_timer_.cancel();

    // Parse status line
    std::istream response_stream(&buffer);
    std::string http_version;
    response_stream >> http_version >> response.status_code;
    std::string status_message;
    std::getline(response_stream, status_message);
    co_return true;
}

asio::awaitable<bool> AsyncHttpsRequest::read_headers(
    asio::streambuf& buffer,
    HttpResponse& response) {

    using namespace boost::asio::experimental::awaitable_operators;

    auto start = std::chrono::steady_clock::now();
    timeout_timer_.expires_after(timeout_duration_);

    auto read_result = co_await (
        asio::async_read_until(ssl_socket_, buffer, "\r\n\r\n", asio::as_tuple(asio::use_awaitable)) ||
        timeout_timer_.async_wait(asio::as_tuple(asio::use_awaitable))
    );

    if (read_result.index() == 1) {
        response.timeout = true;
        response.error_message = "Read timeout (headers)";
        co_return false;
    }

    auto [ec, bytes_read] = std::get<0>(read_result);
    if (ec) {
        throw boost::system::system_error(ec);
    }

    timeout_timer_.cancel();
    record_timing(start, response.timings.read_headers_duration);

    // Parse headers
    std::istream response_stream(&buffer);
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
    co_return true;
}

asio::awaitable<bool> AsyncHttpsRequest::read_body(
    asio::streambuf& buffer,
    HttpResponse& response) {

    using namespace boost::asio::experimental::awaitable_operators;

    auto start = std::chrono::steady_clock::now();
    std::ostringstream body_stream;

    // Add any data already in the buffer
    if (buffer.size() > 0) {
        body_stream << &buffer;
    }

    // Read remaining data until EOF
    timeout_timer_.expires_after(timeout_duration_);
    while (true) {
        auto read_result = co_await (
            asio::async_read(ssl_socket_, buffer, asio::transfer_at_least(1),
                            asio::as_tuple(asio::use_awaitable)) ||
            timeout_timer_.async_wait(asio::as_tuple(asio::use_awaitable))
        );

        if (read_result.index() == 1) {
            // Check if it's a real timeout or just timer cancellation
            auto [timer_ec] = std::get<1>(read_result);
            if (!timer_ec) {
                response.timeout = true;
                response.error_message = "Read timeout (body)";
                co_return false;
            }
            break;
        }

        auto [ec, bytes_transferred] = std::get<0>(read_result);

        // EOF or SSL stream truncation is expected (server closed connection)
        if (ec == asio::error::eof || ec == asio::ssl::error::stream_truncated) {
            body_stream << &buffer;
            break;
        } else if (ec) {
            throw boost::system::system_error(ec);
        }

        body_stream << &buffer;
    }

    response.data = body_stream.str();
    timeout_timer_.cancel();

    record_timing(start, response.timings.read_body_duration);
    co_return true;
}

void AsyncHttpsRequest::decompress_if_needed(HttpResponse& response) {
    if (response.headers["Content-Encoding"] == "gzip") {
        auto start = std::chrono::steady_clock::now();
        response.data = gunzip(response.data);
        record_timing(start, response.timings.decompress_duration);
    }
}

void AsyncHttpsRequest::record_timing(
    std::chrono::steady_clock::time_point start,
    std::chrono::milliseconds& timing_field) {

    auto end = std::chrono::steady_clock::now();
    timing_field = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
}

