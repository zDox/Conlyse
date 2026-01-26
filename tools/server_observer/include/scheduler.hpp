#ifndef SCHEDULER_HPP
#define SCHEDULER_HPP

#include <queue>
#include <map>
#include <unordered_set>
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
 * - Update queuing and scheduling (thread-safe for schedule_update calls from workers)
 * - Worker thread pool management for async coroutines
 * - Concurrency limits (max parallel updates, max parallel first updates)
 * - Update retry logic
 * - Pending new session queue from GameFinder
 *
 * Threading Model:
 * - schedule_update(), schedule_next_update(), schedule_immediate_update():
 *   Thread-safe, called from worker threads when updates complete
 * - get_due_updates(), mark_first_update(), cleanup_first_update_tracking():
 *   Called from main thread only (first-update tracking is NOT thread-safe)
 * - queue_new_session(): Thread-safe, called from GameFinder thread
 * - get_pending_new_sessions(): Main thread only
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
     * Queue a new session to be created (called from GameFinder thread)
     * This is thread-safe and can be called from any thread.
     *
     * @param game_id The game ID
     * @param scenario_id The scenario ID
     */
    void queue_new_session(int game_id, int scenario_id);

    /**
     * Process all pending new sessions queued by GameFinder.
     * Must be called from the main scheduling thread.
     * Returns a vector of (game_id, scenario_id) pairs to create.
     *
     * @return Vector of pending new sessions to create
     */
    std::vector<std::pair<int, int>> get_pending_new_sessions();

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
     * Get the current size of the update queue
     */
    size_t get_queue_size() const { return update_queue_.size(); }

    /**
     * Get the number of first updates being tracked
     */
    size_t get_first_update_count() const { return first_update_sessions_.size(); }

    /**
     * Get the number of first updates currently running
     */
    size_t get_running_first_updates_count() const { return running_first_updates_.size(); }

    /**
     * Get seconds until next due update (returns 0 if queue empty or update is due)
     */
    double get_seconds_until_next_due() const;

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

    // Update queue and tracking (thread-safe - accessed from worker threads via schedule_update)
    std::multimap<std::chrono::system_clock::time_point, ObservationSession*> update_queue_;
    mutable std::mutex update_queue_lock_;

    // Pending new sessions from GameFinder (thread-safe queue)
    std::queue<std::pair<int, int>> pending_new_sessions_;
    std::mutex pending_sessions_lock_;

    // First update tracking (main thread only - accessed during get_due_updates)
    std::unordered_set<int> first_update_sessions_;      // Games that need first update
    std::unordered_set<int> running_first_updates_;      // Games currently running first update

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
