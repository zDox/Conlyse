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

    pub fn publish_compressed_response(
        &self,
        timestamp_ms: i64,
        game_id: i64,
        player_id: i64,
        client_version: i64,
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
            .arg("client_version")
            .arg(client_version)
            .arg("response")
            .arg(compressed_response);

        let _: String = cmd.query(&mut conn)?;
        Ok(())
    }
}

