cmake_minimum_required(VERSION 3.15)
project(ServerObserver VERSION 1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Include FetchContent module
include(FetchContent)
cmake_policy(SET CMP0135 NEW)

# Find required packages
find_package(Python3 COMPONENTS Interpreter Development REQUIRED)
find_package(Threads REQUIRED)

# pybind11
FetchContent_Declare(
        pybind11
        GIT_REPOSITORY https://github.com/pybind/pybind11.git
        GIT_TAG v2.11.1
        DOWNLOAD_EXTRACT_TIMESTAMP TRUE
)
FetchContent_MakeAvailable(pybind11)

# JSON library (nlohmann/json)
include(FetchContent)
FetchContent_Declare(
        json
        URL https://github.com/nlohmann/json/releases/download/v3.11.2/json.tar.xz
        DOWNLOAD_EXTRACT_TIMESTAMP TRUE
)
FetchContent_MakeAvailable(json)

# simdjson library (for fast JSON parsing)
FetchContent_Declare(
        simdjson
        GIT_REPOSITORY https://github.com/simdjson/simdjson.git
        GIT_TAG v3.10.1
        DOWNLOAD_EXTRACT_TIMESTAMP TRUE
)
FetchContent_MakeAvailable(simdjson)

# HTTP client library (cpp-httplib)
FetchContent_Declare(
        httplib
        GIT_REPOSITORY https://github.com/yhirose/cpp-httplib.git
        GIT_TAG v0.14.3
        DOWNLOAD_EXTRACT_TIMESTAMP TRUE
)
FetchContent_MakeAvailable(httplib)

# Boost headers only (header-only libraries)
FetchContent_Declare(
        boost
        URL https://archives.boost.io/release/1.90.0/source/boost_1_90_0.tar.gz
        DOWNLOAD_EXTRACT_TIMESTAMP TRUE
)

FetchContent_MakeAvailable(boost)

# Zstandard compression
find_package(PkgConfig REQUIRED)
pkg_check_modules(ZSTD REQUIRED libzstd)

# Zlib for gzip decompression
find_package(ZLIB REQUIRED)

# OpenSSL for SHA1
find_package(OpenSSL REQUIRED)

# Include directories
include_directories(
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# Source files
set(SOURCES
        src/main.cpp
        src/server_observer.cpp
        src/account.cpp
        src/account_pool.cpp
        src/observation_session.cpp
        src/observation_api.cpp
        src/recording_registry.cpp
        src/static_map_cache.cpp
        src/recording_storage.cpp
        src/hub_interface_wrapper.cpp
        src/async_https_request.cpp
        src/http_client.cpp
        src/request_manager.cpp
)

# Create executable
add_executable(server_observer ${SOURCES})

# Link libraries
target_link_libraries(server_observer
        PRIVATE
        nlohmann_json::nlohmann_json
        simdjson::simdjson
        httplib::httplib
        ${ZSTD_LIBRARIES}
        OpenSSL::SSL
        OpenSSL::Crypto
        ZLIB::ZLIB
        Threads::Threads
        pybind11::embed
)

target_include_directories(server_observer
        PRIVATE
        ${ZSTD_INCLUDE_DIRS}
        ${boost_SOURCE_DIR}
)

# Installation
install(TARGETS server_observer DESTINATION bin)

# ============== Testing ==============
option(BUILD_TESTS "Build the tests" ON)

# Proxy test configuration options
option(ENABLE_PROXY_TESTS "Enable proxy tests (requires a proxy server)" OFF)
set(TEST_PROXY_HOST "127.0.0.1" CACHE STRING "Proxy host for testing")
set(TEST_PROXY_PORT "8080" CACHE STRING "Proxy port for testing")
set(TEST_PROXY_USER "" CACHE STRING "Proxy username for authenticated tests")
set(TEST_PROXY_PASS "" CACHE STRING "Proxy password for authenticated tests")

if(BUILD_TESTS)
    enable_testing()

    # Fetch Google Test
    FetchContent_Declare(
        googletest
        GIT_REPOSITORY https://github.com/google/googletest.git
        GIT_TAG v1.14.0
        DOWNLOAD_EXTRACT_TIMESTAMP TRUE
    )
    # For Windows: Prevent overriding the parent project's compiler/linker settings
    set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
    FetchContent_MakeAvailable(googletest)

    # Test executable
    add_executable(test_async_https_request
        tests/test_async_https_request.cpp
        src/async_https_request.cpp
    )

    target_link_libraries(test_async_https_request
        PRIVATE
        gtest
        gtest_main
        OpenSSL::SSL
        OpenSSL::Crypto
        ZLIB::ZLIB
        Threads::Threads
    )

    target_include_directories(test_async_https_request
        PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        ${boost_SOURCE_DIR}
    )

    # Register tests with CTest
    include(GoogleTest)
    gtest_discover_tests(test_async_https_request
        PROPERTIES
            ENVIRONMENT "TEST_PROXY_HOST=${TEST_PROXY_HOST};TEST_PROXY_PORT=${TEST_PROXY_PORT};TEST_PROXY_USER=${TEST_PROXY_USER};TEST_PROXY_PASS=${TEST_PROXY_PASS}"
    )

    # Custom test targets
    # Run all tests (note: use "make test" for CTest, or "make run-tests" for this target)
    add_custom_target(run-tests
        COMMAND ${CMAKE_CTEST_COMMAND} --output-on-failure
        DEPENDS test_async_https_request
        WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
        COMMENT "Running all tests..."
    )

    # Run only non-proxy tests
    add_custom_target(test-no-proxy
        COMMAND test_async_https_request --gtest_filter=-*Proxy*:*RequestThroughProxy*
        DEPENDS test_async_https_request
        WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
        COMMENT "Running tests without proxy tests..."
    )

    # Run only proxy tests
    add_custom_target(test-proxy
        COMMAND ${CMAKE_COMMAND} -E env
            TEST_PROXY_HOST=${TEST_PROXY_HOST}
            TEST_PROXY_PORT=${TEST_PROXY_PORT}
            TEST_PROXY_USER=${TEST_PROXY_USER}
            TEST_PROXY_PASS=${TEST_PROXY_PASS}
            $<TARGET_FILE:test_async_https_request> --gtest_filter=*Proxy*
        DEPENDS test_async_https_request
        WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
        COMMENT "Running proxy tests with TEST_PROXY_HOST=${TEST_PROXY_HOST}:${TEST_PROXY_PORT}..."
    )

    # Verbose test output
    add_custom_target(test-verbose
        COMMAND ${CMAKE_CTEST_COMMAND} --output-on-failure --verbose
        DEPENDS test_async_https_request
        WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
        COMMENT "Running all tests with verbose output..."
    )

    # Helper target to check proxy connectivity
    add_custom_target(check-proxy
        COMMAND ${CMAKE_COMMAND} -E echo "Checking proxy connectivity at ${TEST_PROXY_HOST}:${TEST_PROXY_PORT}..."
        COMMAND bash -c "timeout 2 bash -c '</dev/tcp/${TEST_PROXY_HOST}/${TEST_PROXY_PORT}' 2>/dev/null && echo 'Proxy is reachable!' || echo 'Proxy is NOT reachable. Tests may be skipped.'"
        COMMENT "Testing proxy connectivity..."
    )

    # Print test configuration
    message(STATUS "Test Configuration:")
    message(STATUS "  BUILD_TESTS: ${BUILD_TESTS}")
    message(STATUS "  ENABLE_PROXY_TESTS: ${ENABLE_PROXY_TESTS}")
    message(STATUS "  TEST_PROXY_HOST: ${TEST_PROXY_HOST}")
    message(STATUS "  TEST_PROXY_PORT: ${TEST_PROXY_PORT}")
    if(TEST_PROXY_USER)
        message(STATUS "  TEST_PROXY_USER: ${TEST_PROXY_USER} (authenticated)")
    else()
        message(STATUS "  TEST_PROXY_USER: (not set - auth tests will be skipped)")
    endif()
    message(STATUS "")
    message(STATUS "Available test targets:")
    message(STATUS "  make test               - Run all tests (CTest)")
    message(STATUS "  make run-tests          - Run all tests (alternative)")
    message(STATUS "  make test-no-proxy      - Run tests excluding proxy tests")
    message(STATUS "  make test-proxy         - Run only proxy tests")
    message(STATUS "  make test-verbose       - Run all tests with verbose output")
    message(STATUS "  make check-proxy        - Check if proxy is reachable")
endif()

