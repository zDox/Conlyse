cmake_minimum_required(VERSION 3.15)
project(ServerObserver VERSION 1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find required packages
find_package(Python3 COMPONENTS Interpreter Development REQUIRED)
find_package(Threads REQUIRED)

# JSON library (nlohmann/json)
include(FetchContent)
FetchContent_Declare(
    json
    URL https://github.com/nlohmann/json/releases/download/v3.11.2/json.tar.xz
)
FetchContent_MakeAvailable(json)

# HTTP client library (cpp-httplib)
FetchContent_Declare(
    httplib
    GIT_REPOSITORY https://github.com/yhirose/cpp-httplib.git
    GIT_TAG v0.14.3
)
FetchContent_MakeAvailable(httplib)

# Zstandard compression
find_package(PkgConfig REQUIRED)
pkg_check_modules(ZSTD REQUIRED libzstd)

# OpenSSL for SHA1
find_package(OpenSSL REQUIRED)

# Include directories
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${Python3_INCLUDE_DIRS}
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
    ${Python3_LIBRARIES}
)

target_include_directories(server_observer
    PRIVATE
    ${ZSTD_INCLUDE_DIRS}
)

# Installation
install(TARGETS server_observer DESTINATION bin)
