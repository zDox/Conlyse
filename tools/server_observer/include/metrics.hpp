#ifndef METRICS_HPP
#define METRICS_HPP

#include <memory>
#include <string>
#include <atomic>
#include <mutex>
#include <deque>
#include <chrono>
#include <prometheus/registry.h>
#include <prometheus/counter.h>
#include <prometheus/gauge.h>
#include <prometheus/histogram.h>
#include <prometheus/exposer.h>

/**
 * Metrics singleton for Prometheus telemetry.
 * Provides metrics for monitoring game recording server with Grafana.
 * 
 * Metrics exposed:
 * - Completed games (counter, by scenario_id)
 * - Failed games (counter, by error type)
 * - Started games (counter, by scenario_id)
 * - Active games (gauge, by scenario_id)
 * - Inflight requests (gauge with histogram for min/max/avg over 300s)
 * - Requests per second (histogram for min/max/avg over 300s)
 * - Missed update intervals (counter)
 * - HTTP request latency (histogram)
 */
class Metrics {
public:
    // Get singleton instance
    static Metrics& getInstance();
    
    // Initialize metrics exposition on the given port
    // Returns true if successful, false otherwise
    bool initialize(int port);
    
    // Shutdown metrics exposition
    void shutdown();
    
    // Check if metrics are enabled
    bool isEnabled() const { return enabled_; }
    
    // Game lifecycle metrics
    void recordGameStarted(int scenario_id);
    void recordGameCompleted(int scenario_id);
    void recordGameFailed(const std::string& error_type);
    void setActiveGames(int scenario_id, int count);
    
    // Request metrics
    void recordRequestStarted();
    void recordRequestCompleted();
    void recordRequestLatency(double duration_seconds);
    
    // Update interval metrics
    void recordMissedInterval();
    void recordScheduledUpdateLatency(double latency_seconds);
    
    // Rolling window metrics for requests per second and inflight count
    void updateRequestMetrics();
    
private:
    Metrics();
    ~Metrics();
    
    // Prevent copying
    Metrics(const Metrics&) = delete;
    Metrics& operator=(const Metrics&) = delete;
    
    bool enabled_;
    std::unique_ptr<prometheus::Exposer> exposer_;
    std::shared_ptr<prometheus::Registry> registry_;
    
    // Metric families and metrics
    prometheus::Family<prometheus::Counter>* games_started_family_;
    prometheus::Family<prometheus::Counter>* games_completed_family_;
    prometheus::Family<prometheus::Counter>* games_failed_family_;
    prometheus::Family<prometheus::Gauge>* active_games_family_;
    prometheus::Family<prometheus::Counter>* missed_intervals_counter_;
    
    prometheus::Family<prometheus::Gauge>* inflight_requests_family_;
    prometheus::Gauge* inflight_requests_current_;
    prometheus::Gauge* inflight_requests_min_;
    prometheus::Gauge* inflight_requests_max_;
    prometheus::Gauge* inflight_requests_avg_;
    
    prometheus::Family<prometheus::Gauge>* requests_per_second_family_;
    prometheus::Gauge* requests_per_second_current_;
    prometheus::Gauge* requests_per_second_min_;
    prometheus::Gauge* requests_per_second_max_;
    prometheus::Gauge* requests_per_second_avg_;
    
    prometheus::Family<prometheus::Histogram>* request_latency_family_;
    prometheus::Histogram* request_latency_histogram_;
    
    prometheus::Family<prometheus::Histogram>* scheduled_update_latency_family_;
    prometheus::Histogram* scheduled_update_latency_histogram_;
    
    // Rolling window tracking for min/max/avg calculations
    std::mutex rolling_window_mutex_;
    
    struct RequestSnapshot {
        std::chrono::system_clock::time_point timestamp;
        size_t inflight_count;
    };
    
    struct RpsSnapshot {
        std::chrono::system_clock::time_point timestamp;
        size_t completed_count;
    };
    
    std::deque<RequestSnapshot> inflight_snapshots_;
    std::deque<RpsSnapshot> rps_snapshots_;
    std::atomic<size_t> total_requests_completed_;
    std::atomic<size_t> current_inflight_;
    
    // Helper to calculate min/max/avg from rolling window
    void updateInflightMetrics();
    void updateRpsMetrics();
};

#endif // METRICS_HPP
