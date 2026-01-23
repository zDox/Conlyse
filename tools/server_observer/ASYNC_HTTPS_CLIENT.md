# Async HTTPS Client

This directory contains a Boost.Asio-based HTTPS client implementation with C++20 coroutines support.

## Features

- **Asynchronous Operations**: Full support for C++20 coroutines using Boost.Asio awaitables
- **Timeout Support**: Comprehensive timeout handling at every stage (DNS resolution, TCP connection, SSL handshake, read/write operations)
- **Proxy Support**: HTTP CONNECT proxy support with authentication
- **Thread Pool**: Built-in thread pool for handling concurrent requests
- **httplib-like Interface**: Familiar API similar to cpp-httplib for easy adoption
- **SSL/TLS Support**: Full SSL/TLS support with SNI hostname configuration
- **Both Sync and Async APIs**: Provides both synchronous and asynchronous request methods

## Usage Example

### Basic GET Request

```cpp
#include "async_https_client.hpp"

int main() {
    // Create client
    HttpClient client("https://api.example.com");
    
    // Optional: Configure SSL verification
    client.enable_server_certificate_verification(true);
    
    // Optional: Set connection timeout
    client.set_connection_timeout(std::chrono::seconds(30));
    
    // Make GET request
    Headers headers = {
        {"User-Agent", "MyApp/1.0"}
    };
    
    HttpResponse response = client.Get("/endpoint", headers);
    
    if (response.success) {
        std::cout << "Status: " << response.status_code << std::endl;
        std::cout << "Data: " << response.data << std::endl;
        std::cout << "Latency: " << response.latency.count() << "ms" << std::endl;
    } else if (response.timeout) {
        std::cout << "Request timed out: " << response.error_message << std::endl;
    } else {
        std::cout << "Request failed: " << response.error_message << std::endl;
    }
    
    return 0;
}
```

### Using HTTP Proxy

```cpp
#include "async_https_client.hpp"

int main() {
    HttpClient client("https://api.example.com");
    
    // Configure HTTP CONNECT proxy with authentication
    client.set_proxy("proxy.example.com", 8080, "username", "password");
    
    // Or without authentication
    // client.set_proxy("proxy.example.com", 8080);
    
    Headers headers = {{"User-Agent", "MyApp/1.0"}};
    HttpResponse response = client.Get("/endpoint", headers);
    
    if (response.success) {
        std::cout << "Request through proxy succeeded!" << std::endl;
    }
    
    // Clear proxy configuration
    client.clear_proxy();
    
    return 0;
}
```

### POST Request with JSON Body

```cpp
#include "async_https_client.hpp"
#include <nlohmann/json.hpp>

int main() {
    HttpClient client("https://api.example.com");
    
    Headers headers = {
        {"User-Agent", "MyApp/1.0"}
    };
    
    json body = {
        {"key", "value"},
        {"number", 42}
    };
    
    HttpResponse response = client.Post(
        "/api/data",
        headers,
        body.dump(),
        "application/json"
    );
    
    if (response.success && response.status_code == 200) {
        std::cout << "Success!" << std::endl;
    }
    
    return 0;
}
```

### Asynchronous Request with Coroutines

```cpp
#include "async_https_client.hpp"
#include <boost/asio/co_spawn.hpp>
#include <boost/asio/detached.hpp>

asio::awaitable<void> make_request(HttpClient& client) {
    Headers headers = {{"User-Agent", "MyApp/1.0"}};
    
    HttpResponse response = co_await client.Get_async("/endpoint", headers);
    
    if (response.success) {
        std::cout << "Response: " << response.data << std::endl;
    }
}

int main() {
    HttpClient client("https://api.example.com");
    
    asio::co_spawn(
        client.get_io_context(),
        make_request(client),
        asio::detached
    );
    
    // Keep running until work is done
    // The HttpClient destructor will wait for all threads to complete
    
    return 0;
}
```

## Implementation Details

### Classes

#### `ProxyConfig`
Structure for configuring proxy settings:
- `bool enabled`: Whether proxy is enabled
- `std::string host`: Proxy server hostname
- `int port`: Proxy server port
- `std::string username`: Proxy authentication username (optional)
- `std::string password`: Proxy authentication password (optional)

#### `HttpResponse`
Structure containing the response data:
- `bool success`: Whether the request succeeded
- `bool timeout`: Whether the request timed out
- `int status_code`: HTTP status code
- `std::string data`: Response body
- `std::string error_message`: Error description (if failed)
- `std::chrono::milliseconds latency`: Request latency
- `std::map<std::string, std::string> headers`: Response headers

#### `AsyncHttpsRequest`
Low-level class for making individual HTTPS requests with timeout and proxy support. Uses C++20 coroutines and Boost.Asio experimental awaitable operators.

**Key features:**
- HTTP CONNECT proxy support with basic authentication
- Timeout handling for all operations including proxy handshake
- SNI hostname configuration for proper SSL/TLS

#### `HttpClient`
High-level client class providing an httplib-like interface:
- Manages thread pool and IO context
- Provides both synchronous and asynchronous methods
- Handles SSL context configuration
- URL parsing and connection management
- Proxy configuration via `set_proxy()` and `clear_proxy()` methods

## Build Requirements

- C++20 compiler (for coroutines support)
- Boost 1.83 or later (for experimental awaitable_operators)
- OpenSSL (for SSL/TLS support)

Add to your CMakeLists.txt:
```cmake
set(CMAKE_CXX_STANDARD 20)
find_package(Boost REQUIRED COMPONENTS system)
find_package(OpenSSL REQUIRED)

target_link_libraries(your_target
    PRIVATE
    Boost::system
    OpenSSL::SSL
    OpenSSL::Crypto
)
```

## Comparison with cpp-httplib

This implementation provides similar functionality to cpp-httplib but with these differences:

**Advantages:**
- Native C++20 coroutines support
- More granular timeout control
- Lower-level access to async operations
- Thread pool built-in

**Trade-offs:**
- Requires Boost (vs header-only cpp-httplib)
- More complex API for advanced use cases
- Requires C++20 (vs C++11 for cpp-httplib)

## Thread Safety

- `HttpClient` is thread-safe for making concurrent requests
- Each request gets its own `AsyncHttpsRequest` instance
- The thread pool handles concurrent execution automatically
