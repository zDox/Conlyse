use crate::response_metadata::ResponseMetadata;
use serde::Deserialize;
use serde_json;
use thiserror::Error;

#[derive(Debug, Clone, Deserialize)]
pub struct RedisConfig {
    pub host: String,
    pub port: u16,
    #[serde(default = "default_stream_name")]
    pub stream_name: String,
    #[serde(default)]
    pub password: Option<String>,
}

fn default_stream_name() -> String {
    "game_responses".to_string()
}

#[derive(Debug, Error)]
pub enum RedisPublisherError {
    #[error("Redis error: {0}")]
    Redis(#[from] redis::RedisError),
    #[error("Compression error: {0}")]
    Compression(#[from] std::io::Error),
    #[error("Metadata serialization error: {0}")]
    Json(String),
}

#[derive(Clone)]
pub struct RedisPublisher {
    cfg: RedisConfig,
    client: redis::Client,
}

impl RedisPublisher {
    pub fn new(cfg: RedisConfig) -> Result<Self, RedisPublisherError> {
        let url = if let Some(password) = &cfg.password {
            format!("redis://:{}@{}:{}/", password, cfg.host, cfg.port)
        } else {
            format!("redis://{}:{}/", cfg.host, cfg.port)
        };

        let client = redis::Client::open(url)?;
        Ok(Self { cfg, client })
    }

    /// Publish a compressed game server response and its associated metadata to Redis.
    ///
    /// Wire format (Redis stream entry fields):
    /// - `metadata`: JSON string of `ResponseMetadata`
    /// - `response`: zstd-compressed response body bytes
    pub fn publish_compressed_response(
        &self,
        metadata: &ResponseMetadata,
        compressed_response: &[u8],
    ) -> Result<(), RedisPublisherError> {
        let mut conn = self.client.get_connection()?;

        let meta_json =
            serde_json::to_string(metadata).map_err(|e| RedisPublisherError::Json(e.to_string()))?;

        let mut cmd = redis::cmd("XADD");
        cmd.arg(&self.cfg.stream_name)
            .arg("*")
            .arg("metadata")
            .arg(meta_json)
            .arg("response")
            .arg(compressed_response);

        let _: String = cmd.query(&mut conn)?;
        Ok(())
    }
}

