#ifndef GAME_FINDER_HPP
#define GAME_FINDER_HPP

#include <string>
#include <vector>
#include <set>
#include <memory>
#include <functional>
#include <thread>
#include <atomic>
#include <mutex>
#include <nlohmann/json.hpp>
#include "hub_interface_wrapper.hpp"
#include "account_pool.hpp"
#include "recording_registry.hpp"

using json = nlohmann::json;

/**
 * Callback type for when a new observation session should be started
 * Parameters: game_id, scenario_id
 */
using ObservationSessionStarter = std::function<void(int, int)>;

/**
 * Callback type for getting the current number of active sessions
 * Returns: number of active sessions
 */
using ActiveSessionCounter = std::function<size_t()>;

/**
 * GameFinder is responsible for discovering new games and initiating observation sessions.
 * It manages the listing interface and maintains knowledge of already-known games.
 * It also runs a background scanning thread to continuously discover new games.
 */
class GameFinder {
public:
    GameFinder(
        const json& config,
        std::shared_ptr<AccountPool> account_pool,
        std::shared_ptr<RecordingRegistry> registry
    );
    ~GameFinder();

    /**
     * Set the callback that will be invoked when a new game should be observed
     */
    void set_observation_starter(ObservationSessionStarter starter);

    /**
     * Set the callback that will be used to get the current number of active sessions
     */
    void set_active_session_counter(ActiveSessionCounter counter);

    /**
     * Start the background scanning thread
     * This will continuously scan for new games at the configured interval
     */
    void start_scanning();

    /**
     * Stop the background scanning thread
     * Blocks until the thread has finished
     */
    void stop_scanning();

    /**
     * Initialize the dedicated listing interface for game discovery
     */
    void initialize_listing_interface();

    /**
     * Scan for new games and start observation sessions for qualifying games
     * @param max_active_sessions Current number of active observation sessions
     * @param max_parallel_recordings Maximum number of parallel recordings allowed
     */
    void scan_and_start_games(size_t max_active_sessions, size_t max_parallel_recordings);

    /**
     * Refresh the set of known games from the registry
     */
    void refresh_known_games_from_registry();

    /**
     * Get the listing interface (creates if needed)
     */
    std::shared_ptr<HubInterfaceWrapper> get_listing_interface();

    /**
     * Check if scanning is enabled
     */
    bool is_scanning_enabled() const { return enabled_scanning_; }

    /**
     * Get scan interval in seconds
     */
    double get_scan_interval() const { return scan_interval_; }

    /**
     * Mark a game as known (already being observed or completed)
     */
    void mark_game_known(int game_id);

private:
    json config_;
    std::shared_ptr<AccountPool> account_pool_;
    std::shared_ptr<RecordingRegistry> registry_;
    std::shared_ptr<HubInterfaceWrapper> listing_interface_;
    ObservationSessionStarter observation_starter_;
    ActiveSessionCounter active_session_counter_;

    std::vector<int> scenario_ids_;
    double scan_interval_;
    bool enabled_scanning_;
    int max_guest_per_account_;
    int max_parallel_recordings_;
    std::set<int> known_games_;

    // Scan thread management
    std::unique_ptr<std::thread> scan_thread_;
    std::atomic<bool> stop_flag_;

    /**
     * The main scan loop that runs in the background thread
     */
    void scan_loop();

    /**
     * Select games from the available games that should be observed
     */
    std::vector<std::pair<int, HubGameProperties>> select_games(
        std::shared_ptr<HubInterfaceWrapper> interface);

    /**
     * Pick an account to use for a new observation session
     */
    std::shared_ptr<Account> pick_account();
};

#endif // GAME_FINDER_HPP
