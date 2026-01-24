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
        
        // Stop the io_context to cancel any pending operations
        if (io_context_) {
            io_context_->stop();
            // Give pending operations a chance to complete
            io_context_->poll();
        }
        
        // Now destroy the contexts in the correct order
        io_context_.reset();
        ssl_context_.reset();
    }

    // Helper function to run a coroutine and get the result
    // This ensures the awaitable is fully executed and completed before returning
    template<typename Awaitable>
    auto runAwaitable(Awaitable&& awaitable) -> decltype(auto) {
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
        
        // Reset io_context for next use
        io_context_->restart();

        if (exception) {
            std::rethrow_exception(exception);
        }

        return std::move(*result);
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

int main(int argc, char **argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}