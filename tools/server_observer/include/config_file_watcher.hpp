#ifndef CONFIG_FILE_WATCHER_HPP
#define CONFIG_FILE_WATCHER_HPP

#include <string>
#include <functional>
#include <atomic>
#include <thread>
#include <memory>

/**
 * ConfigFileWatcher monitors a configuration file for changes
 * On Linux, uses inotify for efficient file monitoring
 * On other platforms, falls back to polling
 */
class ConfigFileWatcher {
public:
    using ChangeCallback = std::function<void()>;

    ConfigFileWatcher(std::string  file_path, ChangeCallback callback);
    ~ConfigFileWatcher();

    /**
     * Start watching the config file for changes
     */
    void start();

    /**
     * Stop watching the config file
     */
    void stop();

    /**
     * Check if the watcher is currently running
     */
    bool is_running() const { return running_.load(); }

private:
    std::string file_path_;
    ChangeCallback callback_;
    std::atomic<bool> running_;
    std::unique_ptr<std::thread> watch_thread_;

    /**
     * Watch loop implementation for Linux (inotify)
     */
    void watch_loop_inotify();

    /**
     * Watch loop implementation fallback (polling)
     */
    void watch_loop_polling();
};

#endif // CONFIG_FILE_WATCHER_HPP
