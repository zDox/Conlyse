#ifndef SERVER_OBSERVER_HPP
#define SERVER_OBSERVER_HPP

#include <string>
#include <map>
#include <memory>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <deque>
#include <atomic>
#include <chrono>
#include <filesystem>
#include <boost/asio/awaitable.hpp>
#include <nlohmann/json.hpp>
#include "account_pool.hpp"
#include "observation_session.hpp"
#include "recording_registry.hpp"
#include "static_map_cache.hpp"
#include "game_finder.hpp"
#include "scheduler.hpp"

using json = nlohmann::json;
namespace asio = boost::asio;

class ServerObserver {
public:
    ServerObserver(const json& config, std::shared_ptr<AccountPool> account_pool);
    ServerObserver(const json& config, std::shared_ptr<AccountPool> account_pool, const std::string& config_path);
    ~ServerObserver();

    bool run();
    void stop();

    // Reset proxy for all sessions using the specified account
    void reset_sessions_for_account(std::shared_ptr<Account> account);

private:
    json config_;
    std::shared_ptr<AccountPool> account_pool_;
    std::shared_ptr<RequestManager> request_manager_;
    std::mutex sessions_lock_;
    
    // Scheduler for managing update execution
    std::unique_ptr<Scheduler> scheduler_;

    std::atomic<int> max_parallel_recordings_;
    double update_interval_;
    std::string output_dir_;
    std::string output_metadata_dir_;
    std::string long_term_storage_path_;
    int file_size_threshold_;

    std::map<int, std::unique_ptr<ObservationSession>> observer_sessions_;
    std::shared_ptr<RecordingRegistry> registry_;
    std::unique_ptr<GameFinder> game_finder_;
    std::atomic<bool> stop_flag_;
    std::condition_variable stop_cv_;
    std::shared_ptr<StaticMapCache> map_cache_;

    // Statistics tracking
    std::atomic<uint64_t> total_updates_completed_;
    std::chrono::system_clock::time_point stats_start_time_;
    std::chrono::system_clock::time_point last_stats_print_time_;
    std::mutex stats_lock_;
    std::deque<std::chrono::system_clock::time_point> update_timestamps_;  // Rolling window of update times

    // Config file watching
    std::string config_file_path_;
    std::filesystem::file_time_type last_config_modified_time_;
    std::chrono::system_clock::time_point last_config_check_time_;

    void start_observation_session(int game_id, int scenario_id);
    void resume_active();
    asio::awaitable<void> run_single_update_async(ObservationSession* session);
    void start_due_updates();

    void print_update_statistics();

    // Helper methods for run_single_update_async
    void record_update_completion();
    void handle_game_ended(ObservationSession* session);
    void handle_successful_update(ObservationSession* session);
    void handle_failed_update(ObservationSession* session, const ObservationResult& result);
    bool should_retry_immediately(ObservationError error_code) const;
    void schedule_retry(ObservationSession* session, bool immediate, const std::string& error_message);

    // Config reload functionality
    void check_and_reload_config();
    void reload_config(const json& new_config);
};

#endif // SERVER_OBSERVER_HPP
