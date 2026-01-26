# AsyncHttpsRequest Tests

This directory contains unit tests for the AsyncHttpsRequest class.

## Building Tests

The tests are built automatically when you build the project with the `BUILD_TESTS` option enabled (which is ON by default).

```bash
cd tools/server_observer
mkdir -p build
cd build
cmake ..
make test_async_https_request
```

## Running Tests

After building, you can run the tests using either:

### Method 1: Direct execution
```bash
./test_async_https_request
```

### Method 2: Using CTest
```bash
ctest --verbose
```

### Method 3: Using CTest with specific test filter
```bash
ctest -R AsyncHttpsRequest --verbose
```

## Test Coverage

The test suite covers the following scenarios:

1. **Basic Functionality**
   - Successful GET request
   - GET request with custom path
   - POST request with body
   - PUT request
   - DELETE request

2. **Error Handling**
   - Request timeout
   - Invalid host
   - Network errors

3. **HTTP Features**
   - Custom headers
   - Response headers parsing
   - Different HTTP status codes (200, 404, 500)
   - Request/response body handling

4. **Performance**
   - Latency measurement
   - Large response body handling
   - Multiple sequential requests

5. **Configuration**
   - Proxy configuration (without actual proxy testing)
   - SSL/TLS connections

## Requirements

The tests require an active internet connection as they make real HTTPS requests to:
- `www.google.com` - Basic connectivity test
- `httpbin.org` - Various HTTP testing endpoints

## Notes

- Tests use `httpbin.org` which is a free HTTP testing service
- Some tests intentionally cause timeouts or errors to verify error handling
- The timeout test uses `/delay/10` endpoint which delays response by 10 seconds
- Tests are designed to be independent and can run in any order
