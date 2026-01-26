#ifndef SCHEDULER_HPP
#define SCHEDULER_HPP

#include <queue>
#include <set>
#include <mutex>
#include <atomic>
#include <chrono>
#include <vector>
#include <thread>
#include <memory>
#include <boost/asio/awaitable.hpp>
#include <boost/asio/io_context.hpp>
#include "observation_session.hpp"

namespace asio = boost::asio;

/**
 * Scheduler manages the scheduling and execution of observation updates.
 * It handles:
 * - Update queuing and scheduling
 * - Worker thread pool management
 * - Concurrency limits (max parallel updates, max parallel first updates)
 * - Update retry logic
 */
class Scheduler {
public:
    /**
     * Construct a new Scheduler
     *
     * @param max_parallel_updates Maximum number of updates that can run simultaneously
     * @param max_parallel_first_updates Maximum number of first updates that can run simultaneously
     * @param update_interval Default interval (in seconds) between updates
     * @param num_worker_threads Number of worker threads for the async executor
     */
    Scheduler(int max_parallel_updates,
              int max_parallel_first_updates,
              double update_interval,
              int num_worker_threads);

    ~Scheduler();

    /**
     * Schedule a session for update
     *
     * @param session The observation session to schedule
     */
    void schedule_update(ObservationSession* session);

    /**
     * Schedule a session for immediate update (used for retries)
     *
     * @param session The observation session to schedule
     */
    void schedule_immediate_update(ObservationSession* session);

    /**
     * Schedule a session for update after the standard interval
     *
     * @param session The observation session to schedule
     */
    void schedule_next_update(ObservationSession* session);

    /**
     * Mark a session as requiring first update tracking
     *
     * @param game_id The game ID to track
     */
    void mark_first_update(int game_id);

    /**
     * Remove first update tracking for a game
     *
     * @param game_id The game ID to stop tracking
     */
    void cleanup_first_update_tracking(int game_id);

    /**
     * Get all sessions that are due for update and ready to run.
     * This respects concurrency limits and marks sessions as running.
     *
     * @return Vector of sessions ready to be updated
     */
    std::vector<ObservationSession*> get_due_updates();

    /**
     * Start processing scheduled updates.
     * This will process all due updates respecting concurrency limits.
     */
    void process_due_updates();

    /**
     * Get the update interval in seconds
     */
    double get_update_interval() const { return update_interval_; }

    /**
     * Get the number of active coroutines
     */
    int get_active_coroutines() const { return active_coroutines_.load(); }

    /**
     * Stop the scheduler and wait for all updates to complete
     *
     * @param timeout_seconds Maximum time to wait for completion (default: 5 seconds)
     */
    void stop(int timeout_seconds = 5);

    /**
     * Spawn an async update coroutine for the given session
     *
     * @param update_coro The coroutine to spawn
     */
    void spawn_update_coroutine(asio::awaitable<void> update_coro);

    /**
     * Increment the active coroutine counter
     */
    void increment_active_coroutines() { ++active_coroutines_; }

    /**
     * Decrement the active coroutine counter
     */
    void decrement_active_coroutines() { --active_coroutines_; }

private:
    // Configuration
    int max_parallel_updates_;
    int max_parallel_first_updates_;
    double update_interval_;
    int num_worker_threads_;

    // Worker thread pool for async updates
    asio::io_context io_context_;
    std::unique_ptr<asio::executor_work_guard<asio::io_context::executor_type>> work_guard_;
    std::vector<std::thread> worker_threads_;

    // Update queue and tracking
    std::queue<ObservationSession*> update_queue_;
    std::mutex queue_lock_;

    // First update tracking
    std::set<int> first_update_sessions_;      // Games that need first update
    std::set<int> running_first_updates_;      // Games currently running first update
    std::mutex first_update_lock_;

    // Active coroutines counter
    std::atomic<int> active_coroutines_;

    // Stop flag
    std::atomic<bool> stop_flag_;

    /**
     * Check if a session can start its update based on concurrency limits
     *
     * @param session The session to check
     * @return true if the session can start, false otherwise
     */
    bool can_start_update(ObservationSession* session);

    /**
     * Mark a game as running its first update
     *
     * @param game_id The game ID
     */
    void mark_first_update_running(int game_id);
};

#endif // SCHEDULER_HPP
