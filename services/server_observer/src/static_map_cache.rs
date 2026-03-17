use crate::db::DbClient;
use crate::s3_client::S3Client;
use serde_json::Value as JsonValue;
use std::collections::HashSet;
use std::sync::{Arc, Mutex};
use thiserror::Error;
use zstd::stream::encode_all;

#[derive(Debug, Error)]
pub enum StaticMapError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("DB error: {0}")]
    Db(#[from] crate::db::DbClientError),
    #[error("S3 error: {0}")]
    S3(#[from] crate::s3_client::S3Error),
    #[error("Compression error: {0}")]
    Compression(String),
}

#[derive(Clone)]
pub struct StaticMapCache {
    saved_ids: Arc<Mutex<HashSet<String>>>,
    s3: S3Client,
    db: DbClient,
}

impl StaticMapCache {
    pub async fn new(s3: S3Client, db: DbClient) -> Result<Self, StaticMapError> {
        let mut ids = HashSet::new();
        // Pre-populate the in-memory cache from existing DB entries so
        // we don't re-upload or re-insert maps that are already known.
        for map_id in db.get_all_map_ids().await? {
            ids.insert(map_id);
        }
        Ok(Self {
            saved_ids: Arc::new(Mutex::new(ids)),
            s3,
            db,
        })
    }

    pub fn is_cached(&self, map_id: &str) -> bool {
        let ids = self.saved_ids.lock().unwrap();
        ids.contains(map_id)
    }

    pub async fn save(
        &self,
        map_id: &str,
        static_map_data: &JsonValue,
    ) -> Result<(), StaticMapError> {
        {
            let ids = self.saved_ids.lock().unwrap();
            if ids.contains(map_id) {
                return Ok(());
            }
        }

        let json_str = static_map_data.to_string();
        let compressed = encode_all(json_str.as_bytes(), 3)
            .map_err(|e| StaticMapError::Compression(e.to_string()))?;

        let s3_key = format!("static_maps/map_{}.bin", map_id);
        self.s3.upload_bytes(compressed, &s3_key).await?;

        if !self.db.map_exists(map_id).await? {
            let version = static_map_data
                .get("version")
                .and_then(|v| v.as_str())
                .map(|s| s.to_string());
            self.db
                .insert_map(map_id, &s3_key, version.as_deref())
                .await?;
        }

        let mut ids = self.saved_ids.lock().unwrap();
        ids.insert(map_id.to_string());

        Ok(())
    }
}

