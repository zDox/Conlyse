#include "scheduler.hpp"
#include <iostream>
#include <algorithm>
#include <boost/asio/co_spawn.hpp>
#include <boost/asio/detached.hpp>

Scheduler::Scheduler(int max_parallel_updates,
                     int max_parallel_first_updates,
                     double update_interval,
                     int num_worker_threads)
    : max_parallel_updates_(max_parallel_updates)
    , max_parallel_first_updates_(max_parallel_first_updates)
    , update_interval_(update_interval)
    , num_worker_threads_(num_worker_threads)
    , active_coroutines_(0)
    , stop_flag_(false)
{
    // Initialize worker threads for update coroutines
    work_guard_ = std::make_unique<asio::executor_work_guard<asio::io_context::executor_type>>(
        asio::make_work_guard(io_context_)
    );

    std::cout << "Starting " << num_worker_threads_ << " scheduler worker threads" << std::endl;
    for (int i = 0; i < num_worker_threads_; ++i) {
        worker_threads_.emplace_back([this]() {
            io_context_.run();
        });
    }
}

Scheduler::~Scheduler() {
    if (!stop_flag_) {
        stop();
    }
}

void Scheduler::stop(int timeout_seconds) {
    std::cout << "Stopping Scheduler..." << std::endl;
    stop_flag_ = true;

    // Wait for all active coroutines to complete with a timeout
    std::cout << "Waiting for " << active_coroutines_.load()
              << " active coroutines to complete..." << std::endl;

    auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(timeout_seconds);
    while (active_coroutines_.load() > 0 &&
           std::chrono::steady_clock::now() < deadline) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }

    if (active_coroutines_.load() > 0) {
        std::cerr << "Warning: " << active_coroutines_.load()
                  << " coroutines still active after timeout" << std::endl;
    }

    // Stop the io_context and join worker threads
    work_guard_.reset();  // Release the work guard to allow io_context to finish
    io_context_.stop();   // Stop the io_context

    std::cout << "Waiting for " << worker_threads_.size()
              << " scheduler worker threads to finish..." << std::endl;

    // Join all worker threads
    for (auto& thread : worker_threads_) {
        if (thread.joinable()) {
            thread.join();
        }
    }

    std::cout << "Scheduler stopped successfully" << std::endl;
}

void Scheduler::schedule_update(ObservationSession* session) {
    std::lock_guard lock(queue_lock_);
    update_queue_.push(session);
}

void Scheduler::schedule_immediate_update(ObservationSession* session) {
    session->next_update_at = std::chrono::system_clock::now();
    schedule_update(session);
}

void Scheduler::schedule_next_update(ObservationSession* session) {
    session->next_update_at = std::chrono::system_clock::now() +
        std::chrono::seconds(static_cast<int>(update_interval_));
    schedule_update(session);
}

void Scheduler::mark_first_update(int game_id) {
    std::lock_guard lock(first_update_lock_);
    first_update_sessions_.insert(game_id);
}

void Scheduler::cleanup_first_update_tracking(int game_id) {
    std::lock_guard lock(first_update_lock_);
    first_update_sessions_.erase(game_id);
    running_first_updates_.erase(game_id);
}

bool Scheduler::can_start_update(ObservationSession* session) {
    std::lock_guard lock(first_update_lock_);

    if (first_update_sessions_.contains(session->game_id)) {
        // Count currently running first updates
        int running_first_updates_count = static_cast<int>(running_first_updates_.size());

        if (running_first_updates_count >= max_parallel_first_updates_) {
            std::cout << "Deferring first update for game " << session->game_id
                     << " due to max parallel first updates limit (currently running: "
                     << running_first_updates_count << ")." << std::endl;
            return false;
        }
    }

    return true;
}

void Scheduler::mark_first_update_running(int game_id) {
    std::lock_guard lock(first_update_lock_);
    running_first_updates_.insert(game_id);
}

std::vector<ObservationSession*> Scheduler::get_due_updates() {
    auto now = std::chrono::system_clock::now();
    std::vector<ObservationSession*> ready;
    std::vector<ObservationSession*> deferred;

    while (true) {
        // Check if we've reached the limit of concurrent coroutines
        if (active_coroutines_.load() >= max_parallel_updates_) {
            break;
        }

        ObservationSession* observer = nullptr;
        {
            std::lock_guard<std::mutex> lock(queue_lock_);
            if (update_queue_.empty()) {
                break;
            }
            observer = update_queue_.front();
            update_queue_.pop();
        }

        if (!observer->needs_update(now)) {
            deferred.push_back(observer);
            continue;
        }

        // Check if this update can start (respecting first-update limits)
        if (!can_start_update(observer)) {
            deferred.push_back(observer);
            continue;
        }

        // Mark as running first update if needed
        {
            std::lock_guard lock(first_update_lock_);
            if (first_update_sessions_.contains(observer->game_id)) {
                mark_first_update_running(observer->game_id);
            }
        }

        ready.push_back(observer);
    }

    // Re-queue deferred updates
    {
        std::lock_guard<std::mutex> lock(queue_lock_);
        for (auto* observer : deferred) {
            update_queue_.push(observer);
        }
    }

    return ready;
}

void Scheduler::process_due_updates() {
    auto now = std::chrono::system_clock::now();
    std::vector<ObservationSession*> deferred;

    // Collect deferred updates to calculate wait time
    {
        std::lock_guard<std::mutex> lock(queue_lock_);
        auto temp_queue = update_queue_;
        while (!temp_queue.empty()) {
            auto* obs = temp_queue.front();
            temp_queue.pop();
            if (!obs->needs_update(now)) {
                deferred.push_back(obs);
            }
        }
    }

    // If we have deferred updates, wait a bit
    if (!deferred.empty()) {
        double min_wait = update_interval_;
        for (auto* obs : deferred) {
            auto wait_duration = obs->next_update_at - now;
            double wait_seconds = std::chrono::duration<double>(wait_duration).count();
            if (wait_seconds > 0 && wait_seconds < min_wait) {
                min_wait = wait_seconds;
            }
        }

        if (min_wait > 0) {
            std::cout << "Waiting " << min_wait
                     << " seconds for next due update..." << std::endl;
            std::this_thread::sleep_for(
                std::chrono::duration<double>(std::min(min_wait, update_interval_)));
        }
    }
}

void Scheduler::spawn_update_coroutine(asio::awaitable<void> update_coro) {
    asio::co_spawn(
        io_context_,
        std::move(update_coro),
        asio::detached
    );
}
