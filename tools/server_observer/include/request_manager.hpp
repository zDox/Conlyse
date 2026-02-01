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
 * RequestManager manages the shared thread pool for HTTP requests.
 * It provides a shared io_context and SSL context for all HttpClient instances.
 */
class RequestManager {
public:
    explicit RequestManager(size_t num_threads = 0);
    ~RequestManager();

    // Get the shared io_context
    asio::io_context& get_io_context() { return io_context_; }

    // Get the shared SSL context
    ssl::context& get_ssl_context() { return ssl_context_; }

private:
    asio::io_context io_context_;
    ssl::context ssl_context_;
    asio::executor_work_guard<asio::io_context::executor_type> work_guard_;
    std::vector<std::thread> threads_;
};



#endif //REQUEST_MANAGER_HPP
