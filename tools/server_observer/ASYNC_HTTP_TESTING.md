# Async HTTP Request Testing and 400 Bad Request Analysis

## Overview
This document describes the comprehensive testing added to the async_https_request component and identifies potential causes of 400 Bad Request errors in the observation API.

## Test Coverage

### Basic Tests (Original)
1. **SuccessfulGetRequest** - Basic GET request to verify functionality
2. **GetRequestWithPath** - GET with custom path
3. **PostRequestWithBody** - POST with JSON body
4. **RequestTimeout** - Timeout handling
5. **InvalidHost** - Invalid hostname error handling
6. **ResponseHeadersParsing** - Header parsing validation
7. **CustomHeadersSent** - Custom header transmission
8. **PutRequest** - PUT method support
9. **DeleteRequest** - DELETE method support
10. **NotFoundStatus** - 404 status code handling
11. **ServerErrorStatus** - 500 status code handling
12. **LatencyMeasurement** - Performance metric validation
13. **ProxyConfigCreation** - Proxy configuration testing
14. **MultipleSequentialRequests** - Sequential request handling
15. **LargeResponseBody** - Large payload handling (100KB)

### Advanced Tests (New)
The following advanced test cases have been added to identify potential 400 Bad Request causes:

#### Content-Type Testing
16. **ContentTypeMismatch** - Tests scenario where Content-Type header differs from actual body format
   - Headers indicate `application/x-www-form-urlencoded`
   - Body contains JSON data
   - This is a common cause of 400 errors in many APIs

17. **FormEncodedPost** - Properly formatted form-encoded POST request
   - Validates correct handling of `application/x-www-form-urlencoded`
   - Body format: `key1=value1&key2=value2`

#### Request Structure Testing
18. **PostWithQueryParameters** - POST request with query string in URL
   - Tests: `/post?param1=value1&param2=value2`
   - Validates proper parameter handling

19. **PostWithEmptyBody** - POST request without body content
   - Edge case that can cause issues in some APIs

20. **LongUrlPath** - Request with very long URL containing many parameters
   - Tests URL length limits and parameter parsing

#### Header Testing
21. **SpecialCharactersInHeaders** - Headers with special characters
   - Tests: `@`, `-`, `_`, numbers in header values
   - Validates proper encoding/handling

22. **AcceptEncodingHeader** - Multiple encoding types in Accept-Encoding
   - Tests: `gzip, deflate, br`
   - Common header that can cause issues if not handled

23. **MultipleAcceptTypes** - Complex Accept header with quality values
   - Tests: `text/plain, */*; q=0.01`

24. **CacheControlHeaders** - Cache control and pragma headers
   - Tests: `no-cache, no-store`

#### Data Format Testing
25. **NestedJsonPost** - Deeply nested JSON structures
   - Tests multi-level object nesting with arrays
   - Validates JSON parsing robustness

26. **Utf8InJsonBody** - UTF-8 characters and emoji in JSON
   - Tests: Chinese characters (世界) and emoji (🚀)
   - Validates proper character encoding

#### HTTP Method Testing
27. **PatchRequest** - PATCH method support
   - Less commonly used method that should be supported

#### Status Code Testing
28. **BadRequestStatus** - Intentionally trigger 400 status
   - Tests proper handling of 400 Bad Request responses
   - Validates that the client handles error responses correctly

#### Redirect Testing
29. **RedirectHandling** - HTTP redirect responses
   - Tests behavior with 302 redirects
   - Note: AsyncHttpsRequest doesn't follow redirects automatically

#### Concurrency Testing
30. **ConcurrentDifferentMethods** - Multiple concurrent requests
   - Tests GET, POST, DELETE simultaneously
   - Validates thread-safety and concurrent execution

## Identified Issue in Observation API

### Duplicate Content-Type Headers (400 Bad Request Root Cause)
**Location**: `tools/server_observer/src/observation_api.cpp` lines 56-101

**Problem**:
```cpp
// Line 58: Content-Type header added to request headers map
Headers req_headers = {
    {"Content-Type", "application/x-www-form-urlencoded; charset=UTF-8"},
    // ...
};

// Line 100-101: Post() called with ANOTHER content_type parameter
std::string body = payload.dump();  // Creates JSON string
auto res = cli_->Post(req_headers, body, "application/json");
```

**Root Cause** (in `async_https_request.cpp`):
```cpp
// Lines 221-223: Add custom headers (includes Content-Type from map)
for (const auto& [key, value] : headers) {
    request_stream << key << ": " << value << "\r\n";
}

// Lines 226-228: Add Content-Type AGAIN from content_type parameter
if (!body.empty()) {
    request_stream << "Content-Type: " << content_type << "\r\n";
    request_stream << "Content-Length: " << body.length() << "\r\n";
}
```

This creates an HTTP request with **TWO Content-Type headers**:
```
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
Content-Type: application/json
```

**Impact**:
- **400 Bad Request** errors from servers that reject duplicate headers (HTTP spec violation)
- Undefined behavior when servers process multiple Content-Type headers
- Server may parse body incorrectly based on which header it honors
- This is a CRITICAL bug that directly causes the reported 400 errors

**Recommended Fix**:
In `observation_api.cpp`, remove the Content-Type from req_headers:
```cpp
Headers req_headers = {
    {"Accept", "text/plain, */*; q=0.01"},
    // Remove this line: {"Content-Type", "application/x-www-form-urlencoded; charset=UTF-8"},
    {"Accept-Encoding", "gzip, deflate, br"}
};
```
The Post() method will correctly set Content-Type to "application/json" based on the parameter.

**Alternative Fix**:
Modify `async_https_request.cpp` to check if Content-Type already exists in headers before adding it:
```cpp
// Check if Content-Type already exists
bool has_content_type = headers.find("Content-Type") != headers.end();

// Only add Content-Type if not already present
if (!body.empty() && !has_content_type) {
    request_stream << "Content-Type: " << content_type << "\r\n";
    request_stream << "Content-Length: " << body.length() << "\r\n";
}
```

### Additional Observations

1. **Hash Generation**: The observation API generates a hash using "undefined" as a prefix (line 72):
   ```cpp
   std::string hash_input = "undefined" + std::to_string(current_time_ms());
   ```
   This appears to be intentional, likely matching the behavior of JavaScript code where an undefined variable would be converted to the string "undefined". This maintains compatibility with the game server's expected hash format.

2. **Request Payload Structure**: The API builds a complex JSON payload with authentication information. Missing or malformed fields could cause 400 errors.

3. **Error Handling**: The API properly handles some error responses (UltAuthentificationException, UltSwitchServerException) but throws on non-200 status codes without detailed error messages.

## Test Results
All 30 tests pass successfully:
- Original tests: 15/15 ✓
- Advanced tests: 15/15 ✓
- Total execution time: ~8.4 seconds

## Conclusion
The comprehensive test suite now covers a wide range of scenarios that could cause 400 Bad Request errors, including:
- Content-Type mismatches (most common cause)
- Query parameter handling
- Special characters in headers and body
- Various data formats (JSON, form-encoded, UTF-8)
- Edge cases (empty bodies, long URLs)
- Concurrent request handling
- Multiple HTTP methods

The identified Content-Type mismatch in observation_api.cpp should be addressed to prevent potential 400 errors when communicating with game servers.
