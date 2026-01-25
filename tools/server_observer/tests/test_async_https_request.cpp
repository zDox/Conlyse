#include <gtest/gtest.h>
#include <boost/asio.hpp>
#include <boost/asio/ssl.hpp>
#include <boost/asio/co_spawn.hpp>
#include <boost/asio/detached.hpp>
#include "../include/async_https_request.hpp"
#include "../include/http_response.hpp"
#include "../include/proxy_config.hpp"
#include <memory>
#include <chrono>
#include <future>
#include <vector>

namespace asio = boost::asio;
namespace ssl = asio::ssl;

class AsyncHttpsRequestTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Create IO context and SSL context for each test
        io_context_ = std::make_unique<asio::io_context>();
        ssl_context_ = std::make_unique<ssl::context>(ssl::context::tlsv12_client);

        // Configure SSL context to use system default certificates
        ssl_context_->set_default_verify_paths();
        ssl_context_->set_verify_mode(ssl::verify_peer);
    }

    void TearDown() override {
        // IMPORTANT: Ensure all AsyncHttpsRequest objects are destroyed first
        // before destroying io_context and ssl_context to avoid segfault.
        // The request objects hold references to these contexts.
        
        // After test body completes, io_context might have pending cleanup handlers
        // from the AsyncHttpsRequest destructor. Reset the io_context to allow
        // it to run again, then poll to process any such handlers.
        if (io_context_ && io_context_->stopped()) {
            io_context_->restart();
        }
        if (io_context_) {
            io_context_->poll();
        }
        
        // Now destroy the contexts in the correct order
        io_context_.reset();
        ssl_context_.reset();
    }

    // Helper function to run a coroutine and get the result
    // This ensures the awaitable is fully executed and completed before returning
    template<typename Awaitable>
    auto runAwaitable(Awaitable&& awaitable) -> typename std::decay_t<Awaitable>::value_type {
        using ResultType = typename std::decay_t<Awaitable>::value_type;
        std::optional<ResultType> result;
        std::exception_ptr exception;

        asio::co_spawn(
            *io_context_,
            [&]() -> asio::awaitable<void> {
                try {
                    result = co_await std::forward<Awaitable>(awaitable);
                } catch (...) {
                    exception = std::current_exception();
                }
            },
            asio::detached
        );

        // Run the io_context until all work is complete
        io_context_->run();
        
        // DO NOT call restart() here - the io_context will be in a stopped state
        // after run() completes. Calling restart() can cause issues with cleanup
        // handlers that are posted during object destruction. Instead, we let the
        // TearDown handle any necessary restart/poll cycle.

        if (exception) {
            std::rethrow_exception(exception);
        }

        return *result;
    }

    std::unique_ptr<asio::io_context> io_context_;
    std::unique_ptr<ssl::context> ssl_context_;
};

// Test successful HTTPS GET request to a reliable endpoint
TEST_F(AsyncHttpsRequestTest, SuccessfulGetRequest) {
    HttpResponse response;
    {
        // Scope the request to ensure it's destroyed before test ends
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(30)
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";

        response = runAwaitable(
            request->execute(
                "www.google.com",
                "443",
                "GET",
                "/",
                headers,
                "",
                ""
            )
        );
        // request goes out of scope here and is destroyed
    }

    EXPECT_TRUE(response.success) << "Error: " << response.error_message;
    EXPECT_FALSE(response.timeout);
    EXPECT_EQ(response.status_code, 200);
    EXPECT_FALSE(response.data.empty());
    EXPECT_GT(response.latency.count(), 0);
}

// Test HTTPS GET request with custom path
TEST_F(AsyncHttpsRequestTest, GetRequestWithPath) {
    HttpResponse response;
    {
        // Scope the request to ensure it's destroyed before test ends
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(30)
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";

        response = runAwaitable(
            request->execute(
                "httpbin.org",
                "443",
                "GET",
                "/get",
                headers,
                "",
                ""
            )
        );
        // request goes out of scope here and is destroyed
    }

    EXPECT_TRUE(response.success) << "Error: " << response.error_message;
    EXPECT_FALSE(response.timeout);
    EXPECT_EQ(response.status_code, 200);
    EXPECT_FALSE(response.data.empty());
    EXPECT_GT(response.latency.count(), 0);
}

// Test POST request with body
TEST_F(AsyncHttpsRequestTest, PostRequestWithBody) {
    HttpResponse response;
    {
        // Scope the request to ensure it's destroyed before test ends
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(30)
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";

        std::string body = R"({"test": "data", "key": "value"})";

        response = runAwaitable(
            request->execute(
                "httpbin.org",
                "443",
                "POST",
                "/post",
                headers,
                body,
                "application/json"
            )
        );
        // request goes out of scope here and is destroyed
    }

    EXPECT_TRUE(response.success) << "Error: " << response.error_message;
    EXPECT_FALSE(response.timeout);
    EXPECT_EQ(response.status_code, 200);
    EXPECT_FALSE(response.data.empty());

    // Verify the response contains our posted data
    EXPECT_NE(response.data.find("test"), std::string::npos);
    EXPECT_NE(response.data.find("data"), std::string::npos);
}

// Test request timeout
TEST_F(AsyncHttpsRequestTest, RequestTimeout) {
    HttpResponse response;
    {
        // Scope the request to ensure it's destroyed before test ends
        // Use a very short timeout to force timeout
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(1)  // Very short timeout
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";

        // Use a host that's known to be slow or unresponsive
        // httpbin.org/delay/10 delays response by 10 seconds
        response = runAwaitable(
            request->execute(
                "httpbin.org",
                "443",
                "GET",
                "/delay/10",  // 10 second delay
                headers,
                "",
                ""
            )
        );
        // request goes out of scope here and is destroyed
    }

    EXPECT_FALSE(response.success);
    EXPECT_TRUE(response.timeout);
}

// Test invalid host
TEST_F(AsyncHttpsRequestTest, InvalidHost) {
    HttpResponse response;
    {
        // Scope the request to ensure it's destroyed before test ends
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(10)
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";

        response = runAwaitable(
            request->execute(
                "invalid-host-that-does-not-exist-12345.com",
                "443",
                "GET",
                "/",
                headers,
                "",
                ""
            )
        );
        // request goes out of scope here and is destroyed
    }

    EXPECT_FALSE(response.success);
    EXPECT_FALSE(response.error_message.empty());
}

// Test response headers parsing
TEST_F(AsyncHttpsRequestTest, ResponseHeadersParsing) {
    HttpResponse response;
    {
        // Scope the request to ensure it's destroyed before test ends
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(30)
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";

        response = runAwaitable(
            request->execute(
                "httpbin.org",
                "443",
                "GET",
                "/response-headers?Test-Header=TestValue",
                headers,
                "",
                ""
            )
        );
        // request goes out of scope here and is destroyed
    }

    EXPECT_TRUE(response.success) << "Error: " << response.error_message;
    EXPECT_FALSE(response.headers.empty());

    // Check for common headers
    EXPECT_TRUE(response.headers.find("Content-Type") != response.headers.end() ||
                response.headers.find("content-type") != response.headers.end());
}

// Test custom headers are sent
TEST_F(AsyncHttpsRequestTest, CustomHeadersSent) {
    HttpResponse response;
    {
        // Scope the request to ensure it's destroyed before test ends
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(30)
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";
        headers["X-Custom-Header"] = "CustomValue";
        headers["Authorization"] = "Bearer test-token";

        response = runAwaitable(
            request->execute(
                "httpbin.org",
                "443",
                "GET",
                "/headers",
                headers,
                "",
                ""
            )
        );
        // request goes out of scope here and is destroyed
    }

    EXPECT_TRUE(response.success) << "Error: " << response.error_message;
    EXPECT_EQ(response.status_code, 200);

    // httpbin.org/headers echoes back the headers we sent
    EXPECT_NE(response.data.find("X-Custom-Header"), std::string::npos);
    EXPECT_NE(response.data.find("CustomValue"), std::string::npos);
}

// Test different HTTP methods
TEST_F(AsyncHttpsRequestTest, PutRequest) {
    HttpResponse response;
    {
        // Scope the request to ensure it's destroyed before test ends
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(30)
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";

        std::string body = R"({"update": "test"})";

        response = runAwaitable(
            request->execute(
                "httpbin.org",
                "443",
                "PUT",
                "/put",
                headers,
                body,
                "application/json"
            )
        );
        // request goes out of scope here and is destroyed
    }

    EXPECT_TRUE(response.success) << "Error: " << response.error_message;
    EXPECT_EQ(response.status_code, 200);
}

TEST_F(AsyncHttpsRequestTest, DeleteRequest) {
    HttpResponse response;
    {
        // Scope the request to ensure it's destroyed before test ends
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(30)
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";

        response = runAwaitable(
            request->execute(
                "httpbin.org",
                "443",
                "DELETE",
                "/delete",
                headers,
                "",
                ""
            )
        );
        // request goes out of scope here and is destroyed
    }

    EXPECT_TRUE(response.success) << "Error: " << response.error_message;
    EXPECT_EQ(response.status_code, 200);
}

// Test timing information
TEST_F(AsyncHttpsRequestTest, TimingInformation) {
    HttpResponse response;
    {
        // Scope the request to ensure it's destroyed before test ends
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(30)
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";
        headers["Accept-Encoding"] = "gzip";  // Test decompression timing

        response = runAwaitable(
            request->execute(
                "httpbin.org",
                "443",
                "GET",
                "/gzip",  // This endpoint returns gzip-compressed data
                headers,
                "",
                ""
            )
        );
        // request goes out of scope here and is destroyed
    }

    EXPECT_TRUE(response.success) << "Error: " << response.error_message;
    EXPECT_EQ(response.status_code, 200);

    // Verify timing information is recorded
    EXPECT_GT(response.timings.total_duration.count(), 0) << "Total duration should be positive";
    EXPECT_GT(response.timings.resolve_duration.count(), 0) << "Resolve duration should be positive";
    EXPECT_GE(response.timings.connect_duration.count(), 0) << "Connect duration should be non-negative";
    EXPECT_GE(response.timings.ssl_handshake_duration.count(), 0) << "SSL handshake duration should be non-negative";
    EXPECT_GE(response.timings.write_duration.count(), 0) << "Write duration should be non-negative";
    EXPECT_GE(response.timings.read_status_duration.count(), 0) << "Read status duration should be non-negative";
    EXPECT_GE(response.timings.read_headers_duration.count(), 0) << "Read headers duration should be non-negative";
    EXPECT_GE(response.timings.read_body_duration.count(), 0) << "Read body duration should be non-negative";

    // For gzip endpoint, decompression should have happened
    if (response.headers["Content-Encoding"] == "gzip") {
        EXPECT_GT(response.timings.decompress_duration.count(), 0) << "Decompress duration should be positive for gzip response";
    }

    // Proxy connect duration should be zero when not using proxy
    EXPECT_EQ(response.timings.proxy_connect_duration.count(), 0) << "Proxy connect duration should be 0 without proxy";

    // Total duration should be greater than or equal to sum of individual steps
    auto sum_of_steps = response.timings.resolve_duration.count() +
                        response.timings.connect_duration.count() +
                        response.timings.ssl_handshake_duration.count() +
                        response.timings.write_duration.count() +
                        response.timings.read_status_duration.count() +
                        response.timings.read_headers_duration.count() +
                        response.timings.read_body_duration.count() +
                        response.timings.decompress_duration.count();
    EXPECT_GE(response.timings.total_duration.count(), sum_of_steps) << "Total should be >= sum of steps";

    // Also verify backward compatibility with latency field
    EXPECT_GT(response.latency.count(), 0) << "Legacy latency field should still be set";
}

// Test status codes
TEST_F(AsyncHttpsRequestTest, NotFoundStatus) {
    HttpResponse response;
    {
        // Scope the request to ensure it's destroyed before test ends
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(30)
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";

        response = runAwaitable(
            request->execute(
                "httpbin.org",
                "443",
                "GET",
                "/status/404",
                headers,
                "",
                ""
            )
        );
        // request goes out of scope here and is destroyed
    }

    EXPECT_TRUE(response.success) << "Error: " << response.error_message;
    EXPECT_EQ(response.status_code, 404);
}

TEST_F(AsyncHttpsRequestTest, ServerErrorStatus) {
    HttpResponse response;
    {
        // Scope the request to ensure it's destroyed before test ends
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(30)
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";

        response = runAwaitable(
            request->execute(
                "httpbin.org",
                "443",
                "GET",
                "/status/500",
                headers,
                "",
                ""
            )
        );
        // request goes out of scope here and is destroyed
    }

    EXPECT_TRUE(response.success) << "Error: " << response.error_message;
    EXPECT_EQ(response.status_code, 500);
}

// Test latency measurement
TEST_F(AsyncHttpsRequestTest, LatencyMeasurement) {
    HttpResponse response;
    {
        // Scope the request to ensure it's destroyed before test ends
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(30)
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";

        response = runAwaitable(
            request->execute(
                "httpbin.org",
                "443",
                "GET",
                "/delay/1",  // 1 second delay
                headers,
                "",
                ""
            )
        );
        // request goes out of scope here and is destroyed
    }

    EXPECT_TRUE(response.success) << "Error: " << response.error_message;
    EXPECT_GE(response.latency.count(), 1000);  // At least 1 second
    EXPECT_LT(response.latency.count(), 5000);   // Less than 5 seconds
}

// Test Base64 encoding for proxy authentication (indirect test through proxy config)
TEST_F(AsyncHttpsRequestTest, ProxyConfigCreation) {
    // Test proxy config without authentication
    ProxyConfig proxy1("proxy.example.com", 8080);
    EXPECT_TRUE(proxy1.enabled);
    EXPECT_EQ(proxy1.host, "proxy.example.com");
    EXPECT_EQ(proxy1.port, 8080);
    EXPECT_TRUE(proxy1.username.empty());
    EXPECT_TRUE(proxy1.password.empty());

    // Test proxy config with authentication
    ProxyConfig proxy2("proxy.example.com", 8080, "user", "pass");
    EXPECT_TRUE(proxy2.enabled);
    EXPECT_EQ(proxy2.host, "proxy.example.com");
    EXPECT_EQ(proxy2.port, 8080);
    EXPECT_EQ(proxy2.username, "user");
    EXPECT_EQ(proxy2.password, "pass");

    // Test disabled proxy
    ProxyConfig proxy3;
    EXPECT_FALSE(proxy3.enabled);
}

// Test multiple sequential requests
TEST_F(AsyncHttpsRequestTest, MultipleSequentialRequests) {
    Headers headers;
    headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";

    for (int i = 0; i < 3; ++i) {
        // Create fresh contexts for each iteration
        auto local_io_context = std::make_unique<asio::io_context>();
        auto local_ssl_context = std::make_unique<ssl::context>(ssl::context::tlsv12_client);
        local_ssl_context->set_default_verify_paths();
        local_ssl_context->set_verify_mode(ssl::verify_peer);

        auto request = std::make_shared<AsyncHttpsRequest>(
            *local_io_context,
            *local_ssl_context,
            std::chrono::seconds(30)
        );

        std::optional<HttpResponse> result;
        std::exception_ptr exception;

        asio::co_spawn(
            *local_io_context,
            [&]() -> asio::awaitable<void> {
                try {
                    result = co_await request->execute(
                        "httpbin.org",
                        "443",
                        "GET",
                        "/get",
                        headers,
                        "",
                        ""
                    );
                } catch (...) {
                    exception = std::current_exception();
                }
            },
            asio::detached
        );

        local_io_context->run();

        if (exception) {
            std::rethrow_exception(exception);
        }

        ASSERT_TRUE(result.has_value());
        EXPECT_TRUE(result->success) << "Request " << i << " failed: " << result->error_message;
        EXPECT_EQ(result->status_code, 200);
    }
}

// Test large response body handling
TEST_F(AsyncHttpsRequestTest, LargeResponseBody) {
    HttpResponse response;
    {
        // Scope the request to ensure it's destroyed before test ends
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(30)
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";

        // Request a large amount of data (100KB)
        response = runAwaitable(
            request->execute(
                "httpbin.org",
                "443",
                "GET",
                "/bytes/102400",  // 100KB of random bytes
                headers,
                "",
                ""
            )
        );
        // request goes out of scope here and is destroyed
    }

    EXPECT_TRUE(response.success) << "Error: " << response.error_message;
    EXPECT_EQ(response.status_code, 200);
    EXPECT_GE(response.data.size(), 100000);  // At least 100KB
}

// ============== Advanced Request Tests ==============

// Test Content-Type header mismatch with body content
TEST_F(AsyncHttpsRequestTest, ContentTypeMismatch) {
    HttpResponse response;
    {
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(30)
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";
        // Set Content-Type in headers to form-encoded
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8";

        // But send JSON body - this mimics the observation API issue
        std::string body = R"({"key": "value"})";

        response = runAwaitable(
            request->execute(
                "httpbin.org",
                "443",
                "POST",
                "/post",
                headers,
                body,
                "application/json"  // This will override the header
            )
        );
    }

    // The request should succeed - httpbin is lenient
    EXPECT_TRUE(response.success) << "Error: " << response.error_message;
    EXPECT_EQ(response.status_code, 200);
}

// Test POST with query parameters in URL
TEST_F(AsyncHttpsRequestTest, PostWithQueryParameters) {
    HttpResponse response;
    {
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(30)
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";

        std::string body = R"({"data": "test"})";

        response = runAwaitable(
            request->execute(
                "httpbin.org",
                "443",
                "POST",
                "/post?param1=value1&param2=value2",
                headers,
                body,
                "application/json"
            )
        );
    }

    EXPECT_TRUE(response.success) << "Error: " << response.error_message;
    EXPECT_EQ(response.status_code, 200);
    // Verify query params are in the response
    EXPECT_NE(response.data.find("param1"), std::string::npos);
    EXPECT_NE(response.data.find("value1"), std::string::npos);
}

// Test special characters in headers
TEST_F(AsyncHttpsRequestTest, SpecialCharactersInHeaders) {
    HttpResponse response;
    {
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(30)
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";
        // Test headers with special characters (properly encoded)
        headers["X-Custom-Value"] = "test@example.com";
        headers["X-Special-Chars"] = "hello-world_123";

        response = runAwaitable(
            request->execute(
                "httpbin.org",
                "443",
                "GET",
                "/headers",
                headers,
                "",
                ""
            )
        );
    }

    EXPECT_TRUE(response.success) << "Error: " << response.error_message;
    EXPECT_EQ(response.status_code, 200);
    EXPECT_NE(response.data.find("X-Custom-Value"), std::string::npos);
}

// Test POST with form-encoded data (proper format)
TEST_F(AsyncHttpsRequestTest, FormEncodedPost) {
    HttpResponse response;
    {
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(30)
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";

        // Proper form-encoded body
        std::string body = "key1=value1&key2=value2&key3=test%20data";

        response = runAwaitable(
            request->execute(
                "httpbin.org",
                "443",
                "POST",
                "/post",
                headers,
                body,
                "application/x-www-form-urlencoded"
            )
        );
    }

    EXPECT_TRUE(response.success) << "Error: " << response.error_message;
    EXPECT_EQ(response.status_code, 200);
    // Verify the form data is in the response
    EXPECT_NE(response.data.find("key1"), std::string::npos);
    EXPECT_NE(response.data.find("value1"), std::string::npos);
}

// Test empty body with POST
TEST_F(AsyncHttpsRequestTest, PostWithEmptyBody) {
    HttpResponse response;
    {
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(30)
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";

        response = runAwaitable(
            request->execute(
                "httpbin.org",
                "443",
                "POST",
                "/post",
                headers,
                "",  // Empty body
                ""
            )
        );
    }

    EXPECT_TRUE(response.success) << "Error: " << response.error_message;
    EXPECT_EQ(response.status_code, 200);
}

// Test PATCH method
TEST_F(AsyncHttpsRequestTest, PatchRequest) {
    HttpResponse response;
    {
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(30)
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";

        std::string body = R"({"field": "updated"})";

        response = runAwaitable(
            request->execute(
                "httpbin.org",
                "443",
                "PATCH",
                "/patch",
                headers,
                body,
                "application/json"
            )
        );
    }

    EXPECT_TRUE(response.success) << "Error: " << response.error_message;
    EXPECT_EQ(response.status_code, 200);
}

// Test very long URL path
TEST_F(AsyncHttpsRequestTest, LongUrlPath) {
    HttpResponse response;
    {
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(30)
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";

        // Create a long path with multiple segments
        std::string long_path = "/get?";
        for (int i = 0; i < 20; ++i) {
            if (i > 0) long_path += "&";
            long_path += "param" + std::to_string(i) + "=value" + std::to_string(i);
        }

        response = runAwaitable(
            request->execute(
                "httpbin.org",
                "443",
                "GET",
                long_path,
                headers,
                "",
                ""
            )
        );
    }

    EXPECT_TRUE(response.success) << "Error: " << response.error_message;
    EXPECT_EQ(response.status_code, 200);
}

// Test request with Accept-Encoding header
TEST_F(AsyncHttpsRequestTest, AcceptEncodingHeader) {
    HttpResponse response;
    {
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(30)
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";
        headers["Accept-Encoding"] = "gzip, deflate, br";
        headers["Accept"] = "application/json";

        response = runAwaitable(
            request->execute(
                "httpbin.org",
                "443",
                "GET",
                "/get",
                headers,
                "",
                ""
            )
        );
    }

    EXPECT_TRUE(response.success) << "Error: " << response.error_message;
    EXPECT_EQ(response.status_code, 200);
}

// Test JSON with nested objects
TEST_F(AsyncHttpsRequestTest, NestedJsonPost) {
    HttpResponse response;
    {
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(30)
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";

        std::string body = R"({
            "level1": {
                "level2": {
                    "level3": {
                        "data": "nested",
                        "array": [1, 2, 3]
                    }
                }
            }
        })";

        response = runAwaitable(
            request->execute(
                "httpbin.org",
                "443",
                "POST",
                "/post",
                headers,
                body,
                "application/json"
            )
        );
    }

    EXPECT_TRUE(response.success) << "Error: " << response.error_message;
    EXPECT_EQ(response.status_code, 200);
    EXPECT_NE(response.data.find("nested"), std::string::npos);
}

// Test request with multiple accept types
TEST_F(AsyncHttpsRequestTest, MultipleAcceptTypes) {
    HttpResponse response;
    {
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(30)
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";
        headers["Accept"] = "text/plain, */*; q=0.01";

        response = runAwaitable(
            request->execute(
                "httpbin.org",
                "443",
                "GET",
                "/get",
                headers,
                "",
                ""
            )
        );
    }

    EXPECT_TRUE(response.success) << "Error: " << response.error_message;
    EXPECT_EQ(response.status_code, 200);
}

// Test redirects (httpbin should handle this)
TEST_F(AsyncHttpsRequestTest, RedirectHandling) {
    HttpResponse response;
    {
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(30)
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";

        // This endpoint returns a 302 redirect to /get
        response = runAwaitable(
            request->execute(
                "httpbin.org",
                "443",
                "GET",
                "/redirect-to?url=/get",
                headers,
                "",
                ""
            )
        );
    }

    // AsyncHttpsRequest does NOT follow redirects automatically (by design).
    // It treats redirect responses as successful responses with the redirect status code.
    // The client receives the 302 response and would need to manually handle the redirect.
    EXPECT_TRUE(response.success) << "Error: " << response.error_message;
    EXPECT_EQ(response.status_code, 302) << "Expected redirect status code";
    // The Location header would contain the redirect URL
}

// Test UTF-8 characters in JSON body
TEST_F(AsyncHttpsRequestTest, Utf8InJsonBody) {
    HttpResponse response;
    {
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(30)
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";

        std::string body = R"({"message": "Hello 世界", "emoji": "🚀"})";

        response = runAwaitable(
            request->execute(
                "httpbin.org",
                "443",
                "POST",
                "/post",
                headers,
                body,
                "application/json; charset=UTF-8"
            )
        );
    }

    EXPECT_TRUE(response.success) << "Error: " << response.error_message;
    EXPECT_EQ(response.status_code, 200);
}

// Test concurrent requests with different methods
TEST_F(AsyncHttpsRequestTest, ConcurrentDifferentMethods) {
    Headers headers;
    headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";

    // Run 3 different requests concurrently
    std::vector<std::future<HttpResponse>> futures;
    
    for (int i = 0; i < 3; ++i) {
        futures.push_back(std::async(std::launch::async, [this, i, headers]() {
            auto local_io = std::make_unique<asio::io_context>();
            auto local_ssl = std::make_unique<ssl::context>(ssl::context::tlsv12_client);
            local_ssl->set_default_verify_paths();
            local_ssl->set_verify_mode(ssl::verify_peer);

            auto request = std::make_shared<AsyncHttpsRequest>(
                *local_io, *local_ssl, std::chrono::seconds(30)
            );

            std::optional<HttpResponse> result;
            std::string method, path;
            
            switch (i % 3) {
                case 0:
                    method = "GET";
                    path = "/get";
                    break;
                case 1:
                    method = "POST";
                    path = "/post";
                    break;
                case 2:
                    method = "DELETE";
                    path = "/delete";
                    break;
            }

            asio::co_spawn(
                *local_io,
                [&]() -> asio::awaitable<void> {
                    result = co_await request->execute(
                        "httpbin.org", "443", method, path, headers, "", ""
                    );
                },
                asio::detached
            );

            local_io->run();
            return *result;
        }));
    }

    // Wait for all requests to complete
    for (auto& future : futures) {
        auto response = future.get();
        EXPECT_TRUE(response.success) << "Error: " << response.error_message;
        EXPECT_EQ(response.status_code, 200);
    }
}

// Test status code 400 (Bad Request) - intentionally trigger it
TEST_F(AsyncHttpsRequestTest, BadRequestStatus) {
    HttpResponse response;
    {
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(30)
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";

        // This endpoint returns 400
        response = runAwaitable(
            request->execute(
                "httpbin.org",
                "443",
                "GET",
                "/status/400",
                headers,
                "",
                ""
            )
        );
    }

    EXPECT_TRUE(response.success) << "Error: " << response.error_message;
    EXPECT_EQ(response.status_code, 400);
}

// Test duplicate Content-Type headers (reproduces observation API bug)
TEST_F(AsyncHttpsRequestTest, DuplicateContentTypeHeaders) {
    HttpResponse response;
    {
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(30)
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";
        // Add Content-Type in headers - this will create a duplicate!
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8";

        std::string body = R"({"key": "value"})";

        // This will add ANOTHER Content-Type header (application/json)
        // resulting in duplicate headers which can cause 400 errors
        // NOTE: We cannot easily verify the duplicate headers are sent without
        // a network capture, but the code path in async_https_request.cpp
        // (lines 221-228) clearly shows both headers are added.
        response = runAwaitable(
            request->execute(
                "httpbin.org",
                "443",
                "POST",
                "/post",
                headers,
                body,
                "application/json"  // This creates the duplicate
            )
        );
    }

    // httpbin.org is lenient and accepts duplicate headers, so the request succeeds.
    // However, strict servers (like some game servers) would return 400 here.
    // This test demonstrates the bug scenario that occurs in observation_api.cpp.
    EXPECT_TRUE(response.success) << "Error: " << response.error_message;
    // Note: Strict servers would return 400 here due to duplicate Content-Type headers
}

// Test request with cache control headers
TEST_F(AsyncHttpsRequestTest, CacheControlHeaders) {
    HttpResponse response;
    {
        auto request = std::make_shared<AsyncHttpsRequest>(
            *io_context_,
            *ssl_context_,
            std::chrono::seconds(30)
        );

        Headers headers;
        headers["User-Agent"] = "AsyncHttpsRequestTest/1.0";
        headers["Cache-Control"] = "no-cache, no-store";
        headers["Pragma"] = "no-cache";

        response = runAwaitable(
            request->execute(
                "httpbin.org",
                "443",
                "GET",
                "/cache",
                headers,
                "",
                ""
            )
        );
    }

    EXPECT_TRUE(response.success) << "Error: " << response.error_message;
    EXPECT_EQ(response.status_code, 200);
}

int main(int argc, char **argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}