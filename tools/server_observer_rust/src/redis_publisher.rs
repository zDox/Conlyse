use serde::Deserialize;
use std::time::{SystemTime, UNIX_EPOCH};
use thiserror::Error;
use zstd::stream::encode_all;

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

    /// Publish a pre-serialized JSON response to the Redis stream,
    /// matching the existing C++/Python contract:
    /// fields: timestamp (ms), game_id, player_id, response (zstd-compressed JSON bytes).
    pub fn publish_response(
        &self,
        game_id: i64,
        player_id: i64,
        response_json: &str,
    ) -> Result<(), RedisPublisherError> {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default();
        let timestamp_ms = now.as_millis() as i64;

        let compressed = encode_all(response_json.as_bytes(), 3)?;
        self.publish_compressed_response(timestamp_ms, game_id, player_id, &compressed)
    }

    pub fn publish_compressed_response(
        &self,
        timestamp_ms: i64,
        game_id: i64,
        player_id: i64,
        compressed_response: &[u8],
    ) -> Result<(), RedisPublisherError> {
        let mut conn = self.client.get_connection()?;

        let mut cmd = redis::cmd("XADD");
        cmd.arg(&self.cfg.stream_name)
            .arg("*")
            .arg("timestamp")
            .arg(timestamp_ms)
            .arg("game_id")
            .arg(game_id)
            .arg("player_id")
            .arg(player_id)
            .arg("response")
            .arg(compressed_response);

        let _: String = cmd.query(&mut conn)?;
        Ok(())
    }
}

