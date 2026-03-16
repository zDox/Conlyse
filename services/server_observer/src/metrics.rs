use axum::{routing::get, Router};
use once_cell::sync::Lazy;
use prometheus::{
    default_registry, Encoder, Histogram, HistogramOpts, HistogramVec, IntCounter, IntCounterVec,
    IntGauge, IntGaugeVec, Opts, TextEncoder,
};
use std::net::SocketAddr;
use thiserror::Error;
use tokio::net::TcpListener;
use tokio::task::JoinHandle;
use tracing::info;

// Histogram buckets for request latency (seconds), matching the C++ implementation
const LATENCY_BUCKETS: &[f64] = &[
    0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0,
];

// Histogram buckets for response size (bytes), matching the C++ implementation
const RESPONSE_SIZE_BUCKETS: &[f64] = &[
    100.0, 1000.0, 10000.0, 100000.0, 1000000.0, 10000000.0, 100000000.0,
];

// Game lifecycle metrics
static GAMES_STARTED_TOTAL: Lazy<IntCounterVec> = Lazy::new(|| {
    let opts = Opts::new(
        "games_started_total",
        "Total number of games started for recording",
    );
    let vec = IntCounterVec::new(opts, &["scenario_id"]).expect("create games_started_total");
    default_registry()
        .register(Box::new(vec.clone()))
        .expect("register games_started_total");
    vec
});

static GAMES_COMPLETED_TOTAL: Lazy<IntCounterVec> = Lazy::new(|| {
    let opts = Opts::new(
        "games_completed_total",
        "Total number of games completed successfully",
    );
    let vec = IntCounterVec::new(opts, &["scenario_id"]).expect("create games_completed_total");
    default_registry()
        .register(Box::new(vec.clone()))
        .expect("register games_completed_total");
    vec
});

static GAMES_FAILED_TOTAL: Lazy<IntCounterVec> = Lazy::new(|| {
    let opts = Opts::new(
        "games_failed_total",
        "Total number of games that failed during recording",
    );
    let vec = IntCounterVec::new(opts, &["error_type"]).expect("create games_failed_total");
    default_registry()
        .register(Box::new(vec.clone()))
        .expect("register games_failed_total");
    vec
});

static ACTIVE_GAMES: Lazy<IntGaugeVec> = Lazy::new(|| {
    let opts = Opts::new(
        "active_games",
        "Number of currently active game recordings",
    );
    let vec = IntGaugeVec::new(opts, &["scenario_id"]).expect("create active_games");
    default_registry()
        .register(Box::new(vec.clone()))
        .expect("register active_games");
    vec
});

// Update scheduling metrics
static MISSED_UPDATE_INTERVALS_TOTAL: Lazy<IntCounter> = Lazy::new(|| {
    let opts = Opts::new(
        "missed_update_intervals_total",
        "Number of update intervals missed (>10s off schedule)",
    );
    let counter = IntCounter::with_opts(opts).expect("create missed_update_intervals_total");
    default_registry()
        .register(Box::new(counter.clone()))
        .expect("register missed_update_intervals_total");
    counter
});

static SCHEDULED_UPDATE_LATENCY_SECONDS: Lazy<Histogram> = Lazy::new(|| {
    let opts = HistogramOpts::new(
        "scheduled_update_latency_seconds",
        "Latency between scheduled update time and actual execution in seconds",
    )
    .buckets(LATENCY_BUCKETS.to_vec());
    let hist = Histogram::with_opts(opts).expect("create scheduled_update_latency_seconds");
    default_registry()
        .register(Box::new(hist.clone()))
        .expect("register scheduled_update_latency_seconds");
    hist
});

// HTTP metrics
static INFLIGHT_GAME_UPDATES: Lazy<IntGauge> = Lazy::new(|| {
    let opts = Opts::new(
        "inflight_game_updates",
        "Current number of in-flight game update operations",
    );
    let gauge = IntGauge::with_opts(opts).expect("create inflight_game_updates");
    default_registry()
        .register(Box::new(gauge.clone()))
        .expect("register inflight_game_updates");
    gauge
});

static HTTP_REQUESTS_TOTAL: Lazy<IntCounter> = Lazy::new(|| {
    let opts = Opts::new(
        "http_requests_total",
        "Total number of HTTP requests completed",
    );
    let counter = IntCounter::with_opts(opts).expect("create http_requests_total");
    default_registry()
        .register(Box::new(counter.clone()))
        .expect("register http_requests_total");
    counter
});

static HTTP_REQUEST_DURATION_SECONDS: Lazy<HistogramVec> = Lazy::new(|| {
    let opts = HistogramOpts::new(
        "http_request_duration_seconds",
        "HTTP request latency in seconds",
    )
    .buckets(LATENCY_BUCKETS.to_vec());
    let vec = HistogramVec::new(opts, &["client"]).expect("create http_request_duration_seconds");
    default_registry()
        .register(Box::new(vec.clone()))
        .expect("register http_request_duration_seconds");
    vec
});

static HTTP_RESPONSE_SIZE_BYTES: Lazy<HistogramVec> = Lazy::new(|| {
    let opts = HistogramOpts::new(
        "http_response_size_bytes",
        "HTTP response size in bytes (compressed)",
    )
    .buckets(RESPONSE_SIZE_BUCKETS.to_vec());
    let vec =
        HistogramVec::new(opts, &["compression"]).expect("create http_response_size_bytes");
    default_registry()
        .register(Box::new(vec.clone()))
        .expect("register http_response_size_bytes");
    vec
});

// Public helpers used by the rest of the crate
pub fn record_game_started(scenario_id: i32) {
    GAMES_STARTED_TOTAL
        .with_label_values(&[&scenario_id.to_string()])
        .inc();
}

pub fn record_game_completed(scenario_id: i32) {
    GAMES_COMPLETED_TOTAL
        .with_label_values(&[&scenario_id.to_string()])
        .inc();
}

pub fn record_game_failed(error_type: &str) {
    GAMES_FAILED_TOTAL
        .with_label_values(&[error_type])
        .inc();
}

pub fn set_active_games(scenario_id: i32, count: i64) {
    ACTIVE_GAMES
        .with_label_values(&[&scenario_id.to_string()])
        .set(count);
}

pub fn record_game_update_started() {
    INFLIGHT_GAME_UPDATES.inc();
}

pub fn record_game_update_completed() {
    INFLIGHT_GAME_UPDATES.dec();
}

pub fn record_request_completed() {
    HTTP_REQUESTS_TOTAL.inc();
}

pub fn record_request_latency(duration_seconds: f64) {
    HTTP_REQUEST_DURATION_SECONDS
        .with_label_values(&["httpclient"])
        .observe(duration_seconds);
}

pub fn record_missed_interval() {
    MISSED_UPDATE_INTERVALS_TOTAL.inc();
}

pub fn record_scheduled_update_latency(latency_seconds: f64) {
    SCHEDULED_UPDATE_LATENCY_SECONDS.observe(latency_seconds);
}

pub fn record_response_size(bytes: usize) {
    HTTP_RESPONSE_SIZE_BYTES
        .with_label_values(&["true"])
        .observe(bytes as f64);
}

pub struct MetricsServer {
    handle: JoinHandle<()>,
}

impl Drop for MetricsServer {
    fn drop(&mut self) {
        self.handle.abort();
    }
}

impl MetricsServer {
    pub async fn run(port: u16) -> Result<Self, MetricsError> {
        let app = Router::new().route(
            "/metrics",
            get(|| async {
                let encoder = TextEncoder::new();
                let metric_families = prometheus::gather();
                let mut buffer = Vec::new();
                if encoder.encode(&metric_families, &mut buffer).is_err() {
                    return Err(axum::http::StatusCode::INTERNAL_SERVER_ERROR);
                }
                let body = String::from_utf8(buffer)
                    .map_err(|_| axum::http::StatusCode::INTERNAL_SERVER_ERROR)?;
                Ok::<String, axum::http::StatusCode>(body)
            }),
        );

        let addr = SocketAddr::from(([0, 0, 0, 0], port));
        info!("Starting metrics server on {}", addr);

        let listener = TcpListener::bind(addr).await?;

        let handle = tokio::spawn(async move {
            if let Err(err) = axum::serve(listener, app).await {
                tracing::error!(?err, "metrics server error");
            }
        });

        Ok(Self { handle })
    }
}

#[derive(Debug, Error)]
pub enum MetricsError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
}

