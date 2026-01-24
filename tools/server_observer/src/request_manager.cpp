//
// Created by zdox on 24.01.26.
//

#include "request_manager.hpp"

RequestManager::RequestManager(size_t num_threads, size_t max_in_flight)
    : ssl_context_(ssl::context::tls_client),
      work_guard_(asio::make_work_guard(io_context_)),
      max_in_flight_(max_in_flight),
      in_flight_requests_(0) {

    // Configure SSL context
    ssl_context_.set_default_verify_paths();
    ssl_context_.set_verify_mode(ssl::verify_peer);

    // Determine number of threads (default to hardware concurrency)
    if (num_threads == 0) {
        num_threads = std::thread::hardware_concurrency();
        if (num_threads == 0) num_threads = 4; // Fallback
    }

    // Start worker threads
    threads_.reserve(num_threads);
    for (size_t i = 0; i < num_threads; ++i) {
        threads_.emplace_back([this]() {
            io_context_.run();
        });
    }
}

RequestManager::~RequestManager() {
    work_guard_.reset();
    for (auto& t : threads_) {
        if (t.joinable()) t.join();
    }
}

void RequestManager::acquire_slot() {
    std::unique_lock<std::mutex> lock(slot_mutex_);
    slot_cv_.wait(lock, [this]() {
        return in_flight_requests_.load() < max_in_flight_;
    });
    in_flight_requests_++;
}

void RequestManager::release_slot() {
    in_flight_requests_--;
    slot_cv_.notify_one();
}
