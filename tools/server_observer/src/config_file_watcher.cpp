#include "config_file_watcher.hpp"
#include <iostream>
#include <chrono>
#include <filesystem>

#ifndef __linux__
// Raise error
#error "ConfigFileWatcher is only implemented for Linux using inotify"
#endif

#include <sys/inotify.h>
#include <unistd.h>
#include <poll.h>
#include <cstring>
#include <utility>

namespace fs = std::filesystem;

ConfigFileWatcher::ConfigFileWatcher(std::string  file_path, ChangeCallback callback)
    : file_path_(std::move(file_path))
    , callback_(std::move(callback))
    , running_(false)
{
}

ConfigFileWatcher::~ConfigFileWatcher() {
    stop();
}

void ConfigFileWatcher::start() {
    if (running_.load()) {
        return;
    }

    running_ = true;

    watch_thread_ = std::make_unique<std::thread>(&ConfigFileWatcher::watch_loop_inotify, this);
}

void ConfigFileWatcher::stop() {
    if (!running_.load()) {
        return;
    }

    running_ = false;

    if (watch_thread_ && watch_thread_->joinable()) {
        watch_thread_->join();
    }
}

void ConfigFileWatcher::watch_loop_inotify() {
    // Initialize inotify
    int inotify_fd = inotify_init1(IN_NONBLOCK);
    if (inotify_fd < 0) {
        std::cerr << "Failed to initialize inotify: " << strerror(errno) << std::endl;
        return;
    }

    // Get the directory and filename
    fs::path config_path(file_path_);
    std::string dir_path = config_path.parent_path().string();
    std::string filename = config_path.filename().string();

    // If no parent directory, use current directory
    if (dir_path.empty()) {
        dir_path = ".";
    }

    // Watch the directory containing the config file
    // We watch the directory because the file might be deleted and recreated
    int watch_fd = inotify_add_watch(inotify_fd, dir_path.c_str(), 
                                     IN_MODIFY | IN_CREATE | IN_MOVED_TO | IN_CLOSE_WRITE);
    if (watch_fd < 0) {
        std::cerr << "Failed to add inotify watch for " << dir_path << ": " 
                 << strerror(errno) << std::endl;
        close(inotify_fd);
        return;
    }

    std::cout << "ConfigFileWatcher: Using inotify to watch " << file_path_ << std::endl;

    // Buffer for inotify events
    char buffer[4096] __attribute__((aligned(__alignof__(struct inotify_event))));
    
    struct pollfd pfd{};
    pfd.fd = inotify_fd;
    pfd.events = POLLIN;
    auto last_callback = std::chrono::steady_clock::now() - std::chrono::milliseconds(1000);

    while (running_.load()) {
        // Poll with timeout to allow checking running_ flag
        int poll_result = poll(&pfd, 1, 1000);  // 1 second timeout

        if (poll_result < 0) {
            if (errno != EINTR) {
                std::cerr << "Poll error: " << strerror(errno) << std::endl;
                break;
            }
            continue;
        }

        if (poll_result == 0) {
            // Timeout, check running flag
            continue;
        }

        // Read inotify events
        ssize_t len = read(inotify_fd, buffer, sizeof(buffer));
        if (len < 0) {
            if (errno != EAGAIN) {
                std::cerr << "Read error: " << strerror(errno) << std::endl;
                break;
            }
            continue;
        }

        // Process events
        const struct inotify_event* event;
        for (char* ptr = buffer; ptr < buffer + len; 
             ptr += sizeof(struct inotify_event) + event->len) {
            event = reinterpret_cast<const struct inotify_event*>(ptr);

            // Check if this event is for our config file
            if (event->len > 0 && filename == event->name) {

                // File was modified, created, or moved into place
                if (event->mask & (IN_MODIFY | IN_CREATE | IN_MOVED_TO | IN_CLOSE_WRITE)) {

                    // Small delay to ensure file write is complete
                    std::this_thread::sleep_for(std::chrono::milliseconds(100));

                    auto now = std::chrono::steady_clock::now();
                    // Call the callback
                    if (now - last_callback > std::chrono::seconds(1) && callback_) {
                        std::cout << "ConfigFileWatcher: Detected change to " << file_path_ << std::endl;
                        last_callback = now;
                        callback_();
                    }
                }
            }
        }
    }

    // Cleanup
    inotify_rm_watch(inotify_fd, watch_fd);
    close(inotify_fd);
}