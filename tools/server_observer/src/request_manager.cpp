//
// Created by zdox on 24.01.26.
//

#include "request_manager.hpp"
#include "metrics.hpp"
#include <openssl/ssl.h>

RequestManager::RequestManager(size_t num_threads)
    : ssl_context_(ssl::context::tls_client),
      work_guard_(asio::make_work_guard(io_context_)) {

    // Configure SSL context
    ssl_context_.set_default_verify_paths();
    ssl_context_.set_verify_mode(ssl::verify_peer);

    // Enable SSL session caching for better performance on repeated connections
    SSL_CTX_set_session_cache_mode(ssl_context_.native_handle(), SSL_SESS_CACHE_CLIENT);

    // Set SSL options for better performance
    ssl_context_.set_options(
        ssl::context::default_workarounds |
        ssl::context::no_sslv2 |
        ssl::context::no_sslv3 |
        ssl::context::single_dh_use
    );

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
