#ifndef METRICS_HPP
#define METRICS_HPP

#include <memory>
#include <string>
#include <atomic>
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
 * - Inflight requests (gauge) - Prometheus will calculate min/max/avg over time
 * - Request counter (counter) - Prometheus will calculate rate/rps over time
 * - Missed update intervals (counter)
 * - HTTP request latency (histogram)
 * - Scheduled update latency (histogram)
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
    prometheus::Counter* missed_intervals_;
    
    prometheus::Family<prometheus::Gauge>* inflight_requests_gauge_;
    prometheus::Gauge* inflight_requests_current_;
    
    prometheus::Family<prometheus::Counter>* requests_total_family_;
    prometheus::Counter* requests_total_counter_;
    
    prometheus::Family<prometheus::Histogram>* request_latency_family_;
    prometheus::Histogram* request_latency_histogram_;
    
    prometheus::Family<prometheus::Histogram>* scheduled_update_latency_family_;
    prometheus::Histogram* scheduled_update_latency_histogram_;
    
    // Simple atomic counter for inflight tracking
    std::atomic<size_t> current_inflight_;
};

#endif // METRICS_HPP
