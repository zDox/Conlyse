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
        httplib::httplib
        ${ZSTD_LIBRARIES}
        OpenSSL::SSL
        OpenSSL::Crypto
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
        Threads::Threads
    )

    target_include_directories(test_async_https_request
        PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        ${boost_SOURCE_DIR}
    )

    # Register tests with CTest
    include(GoogleTest)
    gtest_discover_tests(test_async_https_request)
endif()

