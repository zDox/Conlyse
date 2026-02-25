mod account_pool;
mod db;
mod metrics;
mod recording_registry;
mod redis_publisher;
mod s3_client;
mod static_map_cache;

use crate::metrics::MetricsServer;
use config::{Config, File};
use tokio::signal;
use tracing_subscriber::FmtSubscriber;

#[derive(Debug, serde::Deserialize)]
struct AppConfig {
    database: Option<db::DbConfig>,
    redis: Option<redis_publisher::RedisConfig>,
    s3: Option<s3_client::S3Config>,
    metrics_port: Option<u16>,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize logging
    let subscriber = FmtSubscriber::builder().finish();
    tracing::subscriber::set_global_default(subscriber)?;

    // Load configuration from ./config.(toml/json/...) using `config` crate defaults.
    let settings = Config::builder()
        .add_source(File::with_name("config").required(false))
        .build()?;
    let config: AppConfig = settings.try_deserialize()?;

    // Initialize core infrastructure clients (DB, Redis, S3, Metrics)
    let db_pool = if let Some(db_cfg) = &config.database {
        Some(db::DbClient::new(db_cfg.clone()).await?)
    } else {
        None
    };

    let redis_client = if let Some(redis_cfg) = &config.redis {
        Some(redis_publisher::RedisPublisher::new(redis_cfg.clone())?)
    } else {
        None
    };

    let s3_client = if let Some(s3_cfg) = &config.s3 {
        Some(s3_client::S3Client::new(s3_cfg.clone()).await?)
    } else {
        None
    };

    let _metrics_server = if let Some(port) = config.metrics_port {
        Some(MetricsServer::run(port).await?)
    } else {
        None
    };

    tracing::info!(
        "Core infrastructure initialized: db={:?}, redis={:?}, s3={:?}",
        db_pool.is_some(),
        redis_client.is_some(),
        s3_client.is_some()
    );

    // TODO: Wire observer orchestration here in later stages.
    tracing::info!("Rust ServerObserver skeleton is running. Press Ctrl+C to exit.");

    // Wait for shutdown signal
    signal::ctrl_c().await?;

    tracing::info!("Shutdown signal received, exiting.");
    Ok(())
}
