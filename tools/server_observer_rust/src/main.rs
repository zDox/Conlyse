mod account_pool;
mod db;
mod game_finder;
mod hub_interface_wrapper;
mod metrics;
mod observation_api;
mod observation_package;
mod observation_session;
mod recording_registry;
mod recording_storage;
mod redis_publisher;
mod s3_client;
mod scheduler;
mod server_observer;
mod static_map_cache;

use crate::hub_interface_wrapper::HubInterfaceWrapper;
use crate::metrics::MetricsServer;
use crate::server_observer::ServerObserver;
use serde_json::Value;
use std::env;
use std::sync::Arc;
use tokio::signal;
use tracing_subscriber::{EnvFilter, FmtSubscriber};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let filter = EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info"));
    let subscriber = FmtSubscriber::builder().with_env_filter(filter).finish();
    tracing::subscriber::set_global_default(subscriber)?;

    let args: Vec<String> = env::args().collect();
    let config_file = args
        .get(1)
        .cloned()
        .unwrap_or_else(|| "config.json".to_string());
    let account_pool_file = args
        .get(2)
        .cloned()
        .unwrap_or_else(|| "account_pool.json".to_string());

    tracing::info!(
        config_file = %config_file,
        account_pool_file = %account_pool_file,
        "starting server_observer_rust process"
    );

    let config_contents = std::fs::read_to_string(&config_file)?;
    let config_json: Value = serde_json::from_str(&config_contents)?;

    let _metrics_server = if let Some(port) = config_json
        .get("metrics_port")
        .and_then(Value::as_u64)
    {
        let port_u16 = port as u16;
        tracing::info!(metrics_port = port_u16, "metrics server enabled");
        Some(MetricsServer::run(port_u16).await?)
    } else {
        tracing::info!("metrics server disabled");
        None
    };

    let webshare_token = config_json
        .get("WEBSHARE_API_TOKEN")
        .and_then(Value::as_str)
        .map(str::to_string);

    let account_pool =
        account_pool::AccountPool::load_from_file(&account_pool_file, webshare_token).await?;
    let account_pool = Arc::new(tokio::sync::Mutex::new(account_pool));

    let observer = ServerObserver::new(config_json, Arc::clone(&account_pool)).await?;
    let mut run_task = {
        let observer = Arc::clone(&observer);
        tokio::spawn(async move { observer.run().await })
    };

    tokio::select! {
        _ = signal::ctrl_c() => {
            tracing::info!("Shutdown signal received, stopping observer...");
            observer.stop().await;
        }
        result = &mut run_task => {
            match result {
                Ok(success) => {
                    tracing::info!(success = success, "observer loop exited");
                }
                Err(err) => {
                    tracing::error!(?err, "observer task failed");
                }
            }
            HubInterfaceWrapper::shutdown_python();
            return Ok(());
        }
    }

    let _ = run_task.await;

    HubInterfaceWrapper::shutdown_python();
    Ok(())
}
