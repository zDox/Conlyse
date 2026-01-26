# Proxy Testing Guide

This document describes how to run the proxy tests for AsyncHttpsRequest.

## CMake Integration

The proxy tests are fully integrated with the CMake build system. You can configure proxy settings during the CMake configuration phase, and use convenient make targets to run different test suites.

**Quick Start:**
```bash
# Build with default proxy settings (127.0.0.1:8080)
mkdir build && cd build
cmake ..
make

# Check if proxy is reachable
make check-proxy

# Run only proxy tests
make test-proxy
```

**Configuration Options:**
- `BUILD_TESTS` - Enable/disable test building (default: ON)
- `ENABLE_PROXY_TESTS` - Enable proxy tests (default: OFF, for documentation purposes)
- `TEST_PROXY_HOST` - Proxy hostname (default: 127.0.0.1)
- `TEST_PROXY_PORT` - Proxy port (default: 8080)
- `TEST_PROXY_USER` - Proxy username for authentication (default: empty)
- `TEST_PROXY_PASS` - Proxy password for authentication (default: empty)

## Overview

The test suite includes comprehensive proxy tests that verify:
- Requests through a proxy without authentication
- Requests through a proxy with authentication
- Proxy connection failure handling
- Proxy timing measurements
- POST requests through proxy
- Verification that non-proxy requests have zero proxy timing

## Test Cases

### 1. `ProxyConfigCreation`
Tests the creation and configuration of proxy settings. This test always runs and requires no setup.

### 2. `RequestThroughProxyWithoutAuth`
Tests making HTTPS requests through a proxy server without authentication.

**Requirements:**
- A proxy server accessible without authentication
- Set environment variables (optional):
  - `TEST_PROXY_HOST` - proxy hostname/IP (default: 127.0.0.1)
  - `TEST_PROXY_PORT` - proxy port (default: 8080)

**Note:** This test will be skipped if the proxy is not reachable.

### 3. `RequestThroughProxyWithAuth`
Tests making HTTPS requests through a proxy server with authentication.

**Requirements:**
- A proxy server that requires authentication
- Set environment variables:
  - `TEST_PROXY_HOST` - proxy hostname/IP
  - `TEST_PROXY_PORT` - proxy port
  - `TEST_PROXY_USER` - proxy username
  - `TEST_PROXY_PASS` - proxy password

**Note:** This test will be skipped if any required environment variables are not set or if the proxy is not reachable.

### 4. `ProxyConnectionFailure`
Tests handling of proxy connection failures. This test always runs and uses an invalid proxy address.

### 5. `NoProxyTimingVerification`
Tests that proxy timing is zero when not using a proxy. This test always runs and requires no setup.

### 6. `PostRequestThroughProxy`
Tests POST requests through a proxy.

**Requirements:**
- Same as `RequestThroughProxyWithoutAuth`

## Setting Up a Local Proxy for Testing

### Option 1: Using SSH Dynamic Port Forwarding (SOCKS proxy)

```bash
# Create a SOCKS proxy on port 8080
ssh -D 8080 -N -f user@remote-host
```

**Note:** The current implementation expects an HTTP CONNECT proxy, not a SOCKS proxy. SOCKS proxies require different protocol handling.

### Option 2: Using Squid (HTTP proxy)

1. Install Squid:
```bash
# On Ubuntu/Debian
sudo apt-get install squid

# On macOS
brew install squid
```

2. Configure Squid (edit `/etc/squid/squid.conf` or `/usr/local/etc/squid.conf`):
```
http_port 8080
acl localnet src 127.0.0.1
http_access allow localnet
http_access deny all
```

3. Start Squid:
```bash
# On Ubuntu/Debian
sudo systemctl start squid

# On macOS
brew services start squid
```

### Option 3: Using Tinyproxy (Lightweight HTTP proxy)

1. Install Tinyproxy:
```bash
# On Ubuntu/Debian
sudo apt-get install tinyproxy

# On macOS
brew install tinyproxy
```

2. Configure Tinyproxy (edit `/etc/tinyproxy/tinyproxy.conf` or `/usr/local/etc/tinyproxy/tinyproxy.conf`):
```
Port 8080
Allow 127.0.0.1
```

3. Start Tinyproxy:
```bash
# On Ubuntu/Debian
sudo systemctl start tinyproxy

# On macOS
brew services start tinyproxy
```

### Option 4: Using mitmproxy (For debugging)

```bash
# Install mitmproxy
pip install mitmproxy

# Run on port 8080
mitmproxy -p 8080
```

## Running the Tests

The test suite is integrated with CMake and provides several convenience targets.

### Building the Tests

First, build the project with tests enabled:

```bash
mkdir build && cd build
cmake ..
make
```

### Running All Tests

```bash
# Using CMake/CTest
ctest --output-on-failure

# Or using the custom target
make test

# Or run the test executable directly
./test_async_https_request
```

### Running Tests Without Proxy Tests

```bash
make test-no-proxy
```

This will run all tests except the proxy-related ones.

### Configuring Proxy Settings

You can configure proxy settings at CMake configuration time:

#### With a local proxy at default location (127.0.0.1:8080)
```bash
cmake ..
make
make test-proxy  # Run only proxy tests
```

#### With a custom proxy location
```bash
cmake -DTEST_PROXY_HOST=proxy.example.com -DTEST_PROXY_PORT=3128 ..
make
make test-proxy
```

#### With an authenticated proxy
```bash
cmake \
  -DTEST_PROXY_HOST=proxy.example.com \
  -DTEST_PROXY_PORT=3128 \
  -DTEST_PROXY_USER=myusername \
  -DTEST_PROXY_PASS=mypassword \
  ..
make
make test-proxy
```

#### Using ccmake for interactive configuration
```bash
mkdir build && cd build
ccmake ..
# Set TEST_PROXY_HOST, TEST_PROXY_PORT, TEST_PROXY_USER, TEST_PROXY_PASS
# Press 'c' to configure, 'g' to generate
make
make test-proxy
```

### Running Only Proxy Tests

```bash
# Using the custom target (recommended)
make test-proxy

# Or directly with the executable
./test_async_https_request --gtest_filter="*Proxy*"
```

### Checking Proxy Connectivity

Before running proxy tests, you can verify the proxy is reachable:

```bash
make check-proxy
```

### Using Environment Variables (Alternative Method)

You can also override proxy settings using environment variables:

```bash
export TEST_PROXY_HOST=proxy.example.com
export TEST_PROXY_PORT=3128
export TEST_PROXY_USER=myusername
export TEST_PROXY_PASS=mypassword
./test_async_https_request
```

### Available Make Targets

- `make test` - Run all tests (using CTest)
- `make run-tests` - Run all tests (alternative)
- `make test-no-proxy` - Run tests excluding proxy tests
- `make test-proxy` - Run only proxy tests (uses CMake-configured proxy settings)
- `make test-verbose` - Run all tests with verbose output
- `make check-proxy` - Check if the configured proxy is reachable

## Example Test Output

### When proxy is available:
```
[ RUN      ] AsyncHttpsRequestTest.RequestThroughProxyWithoutAuth
[       OK ] AsyncHttpsRequestTest.RequestThroughProxyWithoutAuth (1234 ms)
```

### When proxy is not available:
```
[ RUN      ] AsyncHttpsRequestTest.RequestThroughProxyWithoutAuth
[  SKIPPED ] AsyncHttpsRequestTest.RequestThroughProxyWithoutAuth (0 ms)
```

## Troubleshooting

### Test is skipped
- Verify your proxy server is running
- Check firewall settings
- Verify environment variables are set correctly
- Test proxy connectivity manually:
  ```bash
  curl -x http://localhost:8080 https://httpbin.org/get
  ```

### Connection timeout
- Increase the timeout in the test (currently 30 seconds)
- Check if the proxy can reach the target host (httpbin.org)
- Verify the proxy is configured to allow HTTPS CONNECT requests

### Authentication failures
- Verify username and password are correct
- Check proxy logs for authentication errors
- Ensure the proxy supports basic authentication

## Implementation Details

The proxy tests verify:
1. **Connection establishment**: The request successfully connects through the proxy
2. **HTTPS tunneling**: The CONNECT method is used to establish an SSL tunnel
3. **Authentication**: Proxy-Authorization header is sent when credentials are provided
4. **Timing**: Proxy connection duration is measured and recorded
5. **Error handling**: Failed proxy connections are handled gracefully

The proxy implementation uses the HTTP CONNECT method for HTTPS tunneling, which is the standard approach for HTTPS through HTTP proxies.
