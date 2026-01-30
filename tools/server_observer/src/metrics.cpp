#include "metrics.hpp"
#include <iostream>

// Histogram buckets for request latency (in seconds)
// Covers 10ms to 60s with exponential buckets
static const std::vector<double> LATENCY_BUCKETS = {
    0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0
};

Metrics& Metrics::getInstance() {
    static Metrics instance;
    return instance;
}

Metrics::Metrics()
    : enabled_(false)
    , exposer_(nullptr)
    , registry_(nullptr)
    , games_started_family_(nullptr)
    , games_completed_family_(nullptr)
    , games_failed_family_(nullptr)
    , active_games_family_(nullptr)
    , missed_intervals_counter_(nullptr)
    , missed_intervals_(nullptr)
    , inflight_requests_gauge_(nullptr)
    , inflight_requests_current_(nullptr)
    , requests_total_family_(nullptr)
    , requests_total_counter_(nullptr)
    , request_latency_family_(nullptr)
    , request_latency_histogram_(nullptr)
    , scheduled_update_latency_family_(nullptr)
    , scheduled_update_latency_histogram_(nullptr)
    , current_inflight_(0)
{
}

Metrics::~Metrics() {
    shutdown();
}

bool Metrics::initialize(int port) {
    if (enabled_) {
        std::cerr << "Metrics already initialized" << std::endl;
        return false;
    }
    
    try {
        // Create exposer on the specified port
        std::string bind_address = "0.0.0.0:" + std::to_string(port);
        exposer_ = std::make_unique<prometheus::Exposer>(bind_address);
        
        // Create registry
        registry_ = std::make_shared<prometheus::Registry>();
        
        // Register registry with exposer
        exposer_->RegisterCollectable(registry_);
        
        // Initialize metric families
        
        // Games started counter (by scenario_id)
        games_started_family_ = &prometheus::BuildCounter()
            .Name("games_started_total")
            .Help("Total number of games started for recording")
            .Register(*registry_);
        
        // Games completed counter (by scenario_id)
        games_completed_family_ = &prometheus::BuildCounter()
            .Name("games_completed_total")
            .Help("Total number of games completed successfully")
            .Register(*registry_);
        
        // Games failed counter (by error_type)
        games_failed_family_ = &prometheus::BuildCounter()
            .Name("games_failed_total")
            .Help("Total number of games that failed during recording")
            .Register(*registry_);
        
        // Active games gauge (by scenario_id)
        active_games_family_ = &prometheus::BuildGauge()
            .Name("active_games")
            .Help("Number of currently active game recordings")
            .Register(*registry_);
        
        // Missed intervals counter
        missed_intervals_counter_ = &prometheus::BuildCounter()
            .Name("missed_update_intervals_total")
            .Help("Number of update intervals missed (>10s off schedule)")
            .Register(*registry_);
        
        missed_intervals_ = &missed_intervals_counter_->Add({});
        
        // Inflight requests gauge (Prometheus will calculate min/max/avg over time)
        inflight_requests_gauge_ = &prometheus::BuildGauge()
            .Name("inflight_requests")
            .Help("Current number of in-flight HTTP requests")
            .Register(*registry_);
        
        inflight_requests_current_ = &inflight_requests_gauge_->Add({});
        
        // Total requests counter (Prometheus will calculate rate/rps using rate() function)
        requests_total_family_ = &prometheus::BuildCounter()
            .Name("http_requests_total")
            .Help("Total number of HTTP requests completed")
            .Register(*registry_);
        
        requests_total_counter_ = &requests_total_family_->Add({});
        
        // Request latency histogram
        request_latency_family_ = &prometheus::BuildHistogram()
            .Name("http_request_duration_seconds")
            .Help("HTTP request latency in seconds")
            .Register(*registry_);
        
        request_latency_histogram_ = &request_latency_family_->Add(
            {{"client", "httpclient"}},
            LATENCY_BUCKETS
        );
        
        // Scheduled update latency histogram (time between scheduled and actual execution)
        scheduled_update_latency_family_ = &prometheus::BuildHistogram()
            .Name("scheduled_update_latency_seconds")
            .Help("Latency between scheduled update time and actual execution in seconds")
            .Register(*registry_);
        
        scheduled_update_latency_histogram_ = &scheduled_update_latency_family_->Add(
            {},
            LATENCY_BUCKETS
        );
        
        enabled_ = true;
        std::cout << "Metrics exposition started on " << bind_address << std::endl;
        std::cout << "Use Prometheus queries like:" << std::endl;
        std::cout << "  - rate(http_requests_total[5m]) for requests per second" << std::endl;
        std::cout << "  - min_over_time(inflight_requests[5m]) for min inflight requests" << std::endl;
        std::cout << "  - max_over_time(inflight_requests[5m]) for max inflight requests" << std::endl;
        std::cout << "  - avg_over_time(inflight_requests[5m]) for avg inflight requests" << std::endl;
        return true;
        
    } catch (const std::exception& e) {
        std::cerr << "Failed to initialize metrics: " << e.what() << std::endl;
        enabled_ = false;
        return false;
    }
}

void Metrics::shutdown() {
    if (enabled_) {
        enabled_ = false;
        exposer_.reset();
        registry_.reset();
        std::cout << "Metrics exposition stopped" << std::endl;
    }
}

void Metrics::recordGameStarted(int scenario_id) {
    if (!enabled_) return;
    
    games_started_family_->Add({{"scenario_id", std::to_string(scenario_id)}}).Increment();
}

void Metrics::recordGameCompleted(int scenario_id) {
    if (!enabled_) return;
    
    games_completed_family_->Add({{"scenario_id", std::to_string(scenario_id)}}).Increment();
}

void Metrics::recordGameFailed(const std::string& error_type) {
    if (!enabled_) return;
    
    games_failed_family_->Add({{"error_type", error_type}}).Increment();
}

void Metrics::setActiveGames(int scenario_id, int count) {
    if (!enabled_) return;
    
    active_games_family_->Add({{"scenario_id", std::to_string(scenario_id)}}).Set(count);
}

void Metrics::recordRequestStarted() {
    if (!enabled_) return;
    
    size_t current = current_inflight_.fetch_add(1) + 1;
    inflight_requests_current_->Set(current);
}

void Metrics::recordRequestCompleted() {
    if (!enabled_) return;
    
    size_t current = current_inflight_.fetch_sub(1) - 1;
    inflight_requests_current_->Set(current);
    requests_total_counter_->Increment();
}

void Metrics::recordRequestLatency(double duration_seconds) {
    if (!enabled_) return;
    
    request_latency_histogram_->Observe(duration_seconds);
}

void Metrics::recordMissedInterval() {
    if (!enabled_) return;
    
    missed_intervals_->Increment();
}

void Metrics::recordScheduledUpdateLatency(double latency_seconds) {
    if (!enabled_) return;
    
    scheduled_update_latency_histogram_->Observe(latency_seconds);
}
