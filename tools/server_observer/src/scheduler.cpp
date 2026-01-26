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
    , update_interval_(std::chrono::milliseconds(static_cast<int64_t>(update_interval * 1000)))
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
    // Thread-safe - can be called from worker threads (via handle_successful_update)
    std::lock_guard<std::mutex> lock(update_queue_lock_);
    update_queue_.insert({session->next_update_at, session});
}

void Scheduler::schedule_immediate_update(ObservationSession* session) {
    session->next_update_at = std::chrono::system_clock::now();
    schedule_update(session);
}

void Scheduler::schedule_next_update(ObservationSession* session) {
    session->next_update_at += update_interval_;
    schedule_update(session);
}

void Scheduler::mark_first_update(int game_id) {
    // No lock needed - called only from main thread
    first_update_sessions_.insert(game_id);
}

void Scheduler::cleanup_first_update_tracking(int game_id) {
    // No lock needed - called only from main thread
    first_update_sessions_.erase(game_id);
    running_first_updates_.erase(game_id);
}

bool Scheduler::can_start_update(ObservationSession* session) {
    // No lock needed - called only from main thread
    if (first_update_sessions_.count(session->game_id)) {
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
    running_first_updates_.insert(game_id);
}

std::vector<ObservationSession*> Scheduler::get_due_updates() {
    auto now = std::chrono::system_clock::now();
    std::vector<ObservationSession*> ready;

    std::lock_guard<std::mutex> lock(update_queue_lock_);

    // Process sessions in time order from the multimap
    while (!update_queue_.empty()) {
        // Check if we've reached the limit of concurrent coroutines
        if (active_coroutines_.load() >= max_parallel_updates_) {
            break;
        }

        // Get the earliest scheduled session
        auto it = update_queue_.begin();
        auto* observer = it->second;

        // Check if it's due yet
        if (!observer->needs_update(now)) {
            // No more sessions are due (since they're time-ordered)
            break;
        }

        // Remove from queue
        update_queue_.erase(it);

        // Check if this update can start (respecting first-update limits)
        if (!can_start_update(observer)) {
            // Re-insert at the end with same time (will be retried next iteration)
            update_queue_.insert({observer->next_update_at, observer});
            continue;
        }

        // Mark as running first update if needed
        if (first_update_sessions_.count(observer->game_id)) {
            mark_first_update_running(observer->game_id);
        }

        ready.push_back(observer);
    }


    return ready;
}

void Scheduler::process_due_updates() {
    auto now = std::chrono::system_clock::now();

    std::chrono::system_clock::time_point next_due_time;
    bool queue_empty;

    {
        std::lock_guard<std::mutex> lock(update_queue_lock_);
        queue_empty = update_queue_.empty();
        if (!queue_empty) {
            next_due_time = update_queue_.begin()->first;
        }
    }

    // Check if queue is empty
    if (queue_empty) {
        // No updates pending, sleep briefly to avoid busy-waiting
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        return;
    }

    // Check if we're at the concurrency limit
    if (active_coroutines_.load() >= max_parallel_updates_) {
        // At limit, wait a short time for some to complete
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        return;
    }


    // Calculate wait time
    if (next_due_time > now) {
        auto wait_duration = next_due_time - now;
        double wait_seconds = std::chrono::duration<double>(wait_duration).count();

        // Cap the wait time at update_interval to allow periodic checks
        double actual_wait = std::min(wait_seconds, update_interval_);

        if (actual_wait > 0.1) {  // Only log if waiting more than 100ms
            std::cout << "Waiting " << actual_wait
                     << " seconds for next due update..." << std::endl;
        }

        std::this_thread::sleep_for(std::chrono::duration<double>(actual_wait));
    }
}

void Scheduler::spawn_update_coroutine(asio::awaitable<void> update_coro) {
    asio::co_spawn(
        io_context_,
        std::move(update_coro),
        asio::detached
    );
}

void Scheduler::queue_new_session(int game_id, int scenario_id) {
    // Thread-safe - can be called from GameFinder thread
    std::lock_guard<std::mutex> lock(pending_sessions_lock_);
    pending_new_sessions_.push({game_id, scenario_id});
}

std::vector<std::pair<int, int>> Scheduler::get_pending_new_sessions() {
    // Called from main thread only
    std::vector<std::pair<int, int>> result;

    std::lock_guard<std::mutex> lock(pending_sessions_lock_);
    while (!pending_new_sessions_.empty()) {
        result.push_back(pending_new_sessions_.front());
        pending_new_sessions_.pop();
    }

    return result;
}

double Scheduler::get_seconds_until_next_due() const {
    std::lock_guard<std::mutex> lock(update_queue_lock_);

    if (update_queue_.empty()) {
        return 0.0;
    }

    auto now = std::chrono::system_clock::now();
    auto next_due = update_queue_.begin()->first;

    if (next_due <= now) {
        return 0.0;
    }

    auto duration = next_due - now;
    return std::chrono::duration<double>(duration).count();
}

