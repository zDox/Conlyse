//
// Created by zdox on 24.01.26.
//

#ifndef REQUEST_MANAGER_HPP
#define REQUEST_MANAGER_HPP
#include <thread>
#include <memory>
#include <atomic>
#include <mutex>
#include <condition_variable>
#include <vector>
#include <boost/asio/io_context.hpp>
#include <boost/asio/ssl/context.hpp>
#include <boost/asio/awaitable.hpp>


namespace asio = boost::asio;
namespace ssl = asio::ssl;

/**
 * RequestManager manages the shared thread pool and enforces maximum in-flight requests.
 * It provides a shared io_context and SSL context for all HttpClient instances.
 */
class RequestManager {
public:
    explicit RequestManager(size_t num_threads = 0, size_t max_in_flight = 100);
    ~RequestManager();

    // Get the shared io_context
    asio::io_context& get_io_context() { return io_context_; }

    // Get the shared SSL context
    ssl::context& get_ssl_context() { return ssl_context_; }

    // Acquire a slot for an in-flight request (blocks if max reached)
    void acquire_slot();

    // Release a slot after request completes
    void release_slot();

    // Get current number of in-flight requests
    [[nodiscard]] size_t get_in_flight_count() const { return in_flight_requests_.load(); }

    // Get max in-flight requests
    [[nodiscard]] size_t get_max_in_flight() const { return max_in_flight_; }

    // RAII helper for managing request slots
    class RequestSlot {
    public:
        explicit RequestSlot(RequestManager& manager) : manager_(manager) {
            manager_.acquire_slot();
        }
        ~RequestSlot() {
            manager_.release_slot();
        }
        RequestSlot(const RequestSlot&) = delete;
        RequestSlot& operator=(const RequestSlot&) = delete;
    private:
        RequestManager& manager_;
    };

private:
    asio::io_context io_context_;
    ssl::context ssl_context_;
    asio::executor_work_guard<asio::io_context::executor_type> work_guard_;
    std::vector<std::thread> threads_;

    size_t max_in_flight_;
    std::atomic<size_t> in_flight_requests_;
    std::mutex slot_mutex_;
    std::condition_variable slot_cv_;
};



#endif //REQUEST_MANAGER_HPP
