#ifndef SERVER_OBSERVER_HPP
#define SERVER_OBSERVER_HPP

#include <string>
#include <vector>
#include <map>
#include <set>
#include <memory>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <queue>
#include <atomic>
#include <nlohmann/json.hpp>
#include "account_pool.hpp"
#include "observation_session.hpp"
#include "recording_registry.hpp"
#include "static_map_cache.hpp"

using json = nlohmann::json;

class ServerObserver {
public:
    ServerObserver(const json& config, std::shared_ptr<AccountPool> account_pool);
    ~ServerObserver();
    
    bool run();
    
private:
    json config_;
    std::shared_ptr<AccountPool> account_pool_;
    
    std::vector<int> scenario_ids_;
    int max_parallel_recordings_;
    int max_parallel_updates_;
    int max_parallel_first_updates_;
    double scan_interval_;
    int max_guest_per_account_;
    double update_interval_;
    std::string output_dir_;
    std::string output_metadata_dir_;
    std::string long_term_storage_path_;
    int file_size_threshold_;
    bool enabled_scanning_;
    
    std::map<int, std::unique_ptr<ObservationSession>> observer_sessions_;
    std::unique_ptr<RecordingRegistry> registry_;
    std::shared_ptr<HubInterfaceWrapper> listing_interface_;
    std::shared_ptr<Account> listing_account_;
    std::set<std::thread::id> active_threads_;
    std::set<int> first_update_sessions_;
    std::mutex threads_lock_;
    std::atomic<bool> stop_flag_;
    std::condition_variable stop_cv_;
    std::queue<ObservationSession*> update_queue_;
    std::mutex queue_lock_;
    std::unique_ptr<std::thread> scan_thread_;
    std::shared_ptr<StaticMapCache> map_cache_;
    std::set<int> known_games_;
    
    std::shared_ptr<HubInterfaceWrapper> get_listing_interface();
    std::vector<std::pair<int, HubGameProperties>> select_games(std::shared_ptr<HubInterfaceWrapper> interface);
    void refresh_known_games_from_registry();
    std::shared_ptr<Account> pick_account();
    void start_observation_session(int game_id, int scenario_id);
    void resume_active();
    void run_single_update(ObservationSession* session);
    void start_due_updates();
    void clean_finished_threads();
    void scan_loop();
};

#endif // SERVER_OBSERVER_HPP
