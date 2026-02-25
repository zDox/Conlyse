use axum::{routing::get, Router};
use prometheus::{Encoder, Registry, TextEncoder};
use std::net::SocketAddr;
use std::sync::Arc;
use thiserror::Error;
use tokio::net::TcpListener;
use tokio::task::JoinHandle;
use tracing::info;

#[derive(Clone)]
pub struct Metrics {
    pub registry: Arc<Registry>,
}

impl Metrics {
    pub fn new() -> Self {
        Self {
            registry: Arc::new(Registry::new()),
        }
    }
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
        let metrics = Metrics::new();
        let registry = metrics.registry.clone();

        let app = Router::new().route(
            "/metrics",
            get(move || {
                let registry = registry.clone();
                async move {
                    let encoder = TextEncoder::new();
                    let metric_families = registry.gather();
                    let mut buffer = Vec::new();
                    if encoder.encode(&metric_families, &mut buffer).is_err() {
                        return Err(axum::http::StatusCode::INTERNAL_SERVER_ERROR);
                    }
                    let body = String::from_utf8(buffer)
                        .map_err(|_| axum::http::StatusCode::INTERNAL_SERVER_ERROR)?;
                    Ok::<String, axum::http::StatusCode>(body)
                }
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

