#include "metrics.hpp"
#include <iostream>
#include <algorithm>

// Histogram buckets for request latency (in seconds)
// Covers 10ms to 60s with exponential buckets
static const std::vector<double> LATENCY_BUCKETS = {
    0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0
};

// Time window for rolling metrics (300 seconds = 5 minutes)
static const auto ROLLING_WINDOW_DURATION = std::chrono::seconds(300);

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
    , inflight_requests_family_(nullptr)
    , inflight_requests_current_(nullptr)
    , inflight_requests_min_(nullptr)
    , inflight_requests_max_(nullptr)
    , inflight_requests_avg_(nullptr)
    , requests_per_second_family_(nullptr)
    , requests_per_second_current_(nullptr)
    , requests_per_second_min_(nullptr)
    , requests_per_second_max_(nullptr)
    , requests_per_second_avg_(nullptr)
    , request_latency_family_(nullptr)
    , request_latency_histogram_(nullptr)
    , scheduled_update_latency_family_(nullptr)
    , scheduled_update_latency_histogram_(nullptr)
    , total_requests_completed_(0)
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
        
        // Inflight requests metrics
        inflight_requests_family_ = &prometheus::BuildGauge()
            .Name("inflight_requests")
            .Help("Number of in-flight HTTP requests")
            .Register(*registry_);
        
        inflight_requests_current_ = &inflight_requests_family_->Add({{"stat", "current"}});
        inflight_requests_min_ = &inflight_requests_family_->Add({{"stat", "min_300s"}});
        inflight_requests_max_ = &inflight_requests_family_->Add({{"stat", "max_300s"}});
        inflight_requests_avg_ = &inflight_requests_family_->Add({{"stat", "avg_300s"}});
        
        // Requests per second metrics
        requests_per_second_family_ = &prometheus::BuildGauge()
            .Name("requests_per_second")
            .Help("HTTP requests per second statistics")
            .Register(*registry_);
        
        requests_per_second_current_ = &requests_per_second_family_->Add({{"stat", "current"}});
        requests_per_second_min_ = &requests_per_second_family_->Add({{"stat", "min_300s"}});
        requests_per_second_max_ = &requests_per_second_family_->Add({{"stat", "max_300s"}});
        requests_per_second_avg_ = &requests_per_second_family_->Add({{"stat", "avg_300s"}});
        
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
    
    current_inflight_++;
    
    // Record snapshot for rolling window
    std::lock_guard<std::mutex> lock(rolling_window_mutex_);
    inflight_snapshots_.push_back({
        std::chrono::system_clock::now(),
        current_inflight_.load()
    });
}

void Metrics::recordRequestCompleted() {
    if (!enabled_) return;
    
    current_inflight_--;
    total_requests_completed_++;
    
    // Record snapshot for RPS calculation
    std::lock_guard<std::mutex> lock(rolling_window_mutex_);
    rps_snapshots_.push_back({
        std::chrono::system_clock::now(),
        total_requests_completed_.load()
    });
}

void Metrics::recordRequestLatency(double duration_seconds) {
    if (!enabled_) return;
    
    request_latency_histogram_->Observe(duration_seconds);
}

void Metrics::recordMissedInterval() {
    if (!enabled_) return;
    
    missed_intervals_counter_->Add({}).Increment();
}

void Metrics::recordScheduledUpdateLatency(double latency_seconds) {
    if (!enabled_) return;
    
    scheduled_update_latency_histogram_->Observe(latency_seconds);
}

void Metrics::updateRequestMetrics() {
    if (!enabled_) return;
    
    std::lock_guard<std::mutex> lock(rolling_window_mutex_);
    
    auto now = std::chrono::system_clock::now();
    auto cutoff_time = now - ROLLING_WINDOW_DURATION;
    
    // Remove old snapshots
    while (!inflight_snapshots_.empty() && 
           inflight_snapshots_.front().timestamp < cutoff_time) {
        inflight_snapshots_.pop_front();
    }
    
    while (!rps_snapshots_.empty() && 
           rps_snapshots_.front().timestamp < cutoff_time) {
        rps_snapshots_.pop_front();
    }
    
    // Update inflight metrics
    updateInflightMetrics();
    
    // Update RPS metrics
    updateRpsMetrics();
}

void Metrics::updateInflightMetrics() {
    // Assumes lock is already held
    
    if (inflight_snapshots_.empty()) {
        inflight_requests_current_->Set(0);
        inflight_requests_min_->Set(0);
        inflight_requests_max_->Set(0);
        inflight_requests_avg_->Set(0);
        return;
    }
    
    size_t current = current_inflight_.load();
    size_t min_val = current;
    size_t max_val = current;
    size_t sum = 0;
    
    for (const auto& snapshot : inflight_snapshots_) {
        min_val = std::min(min_val, snapshot.inflight_count);
        max_val = std::max(max_val, snapshot.inflight_count);
        sum += snapshot.inflight_count;
    }
    
    double avg = static_cast<double>(sum) / inflight_snapshots_.size();
    
    inflight_requests_current_->Set(current);
    inflight_requests_min_->Set(min_val);
    inflight_requests_max_->Set(max_val);
    inflight_requests_avg_->Set(avg);
}

void Metrics::updateRpsMetrics() {
    // Assumes lock is already held
    
    if (rps_snapshots_.size() < 2) {
        requests_per_second_current_->Set(0);
        requests_per_second_min_->Set(0);
        requests_per_second_max_->Set(0);
        requests_per_second_avg_->Set(0);
        return;
    }
    
    // Calculate RPS over 1-second windows
    std::vector<double> rps_values;
    
    for (size_t i = 1; i < rps_snapshots_.size(); ++i) {
        auto& prev = rps_snapshots_[i - 1];
        auto& curr = rps_snapshots_[i];
        
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(
            curr.timestamp - prev.timestamp
        ).count() / 1000.0;
        
        if (duration > 0) {
            double rps = static_cast<double>(curr.completed_count - prev.completed_count) / duration;
            rps_values.push_back(rps);
        }
    }
    
    if (rps_values.empty()) {
        requests_per_second_current_->Set(0);
        requests_per_second_min_->Set(0);
        requests_per_second_max_->Set(0);
        requests_per_second_avg_->Set(0);
        return;
    }
    
    double current_rps = rps_values.back();
    double min_rps = *std::min_element(rps_values.begin(), rps_values.end());
    double max_rps = *std::max_element(rps_values.begin(), rps_values.end());
    double avg_rps = std::accumulate(rps_values.begin(), rps_values.end(), 0.0) / rps_values.size();
    
    requests_per_second_current_->Set(current_rps);
    requests_per_second_min_->Set(min_rps);
    requests_per_second_max_->Set(max_rps);
    requests_per_second_avg_->Set(avg_rps);
}
