use crate::db::DbClient;
use crate::s3_client::S3Client;
use serde_json::Value as JsonValue;
use std::collections::HashSet;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use thiserror::Error;
use tokio::fs;
use tokio::io::AsyncWriteExt;
use zstd::stream::encode_all;

#[derive(Debug, Error)]
pub enum StaticMapError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("DB error: {0}")]
    Db(#[from] crate::db::DbClientError),
    #[error("Compression error: {0}")]
    Compression(String),
}

#[derive(Clone)]
pub struct StaticMapCache {
    cache_dir: PathBuf,
    saved_ids: Arc<Mutex<HashSet<String>>>,
    s3: Option<S3Client>,
    db: Option<DbClient>,
}

impl StaticMapCache {
    pub async fn new<P: AsRef<Path>>(
        cache_dir: P,
        s3: Option<S3Client>,
        db: Option<DbClient>,
    ) -> Result<Self, StaticMapError> {
        let cache_dir = cache_dir.as_ref().to_path_buf();
        fs::create_dir_all(&cache_dir).await?;

        let mut ids = HashSet::new();
        let mut entries = fs::read_dir(&cache_dir).await?;
        while let Some(entry) = entries.next_entry().await? {
            if let Ok(file_type) = entry.file_type().await {
                if file_type.is_file() {
                    if let Some(stem) = entry.path().file_stem().and_then(|s| s.to_str()) {
                        if let Some(rest) = stem.strip_prefix("map_") {
                            ids.insert(rest.to_string());
                        }
                    }
                }
            }
        }

        Ok(Self {
            cache_dir,
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
    ) -> Result<PathBuf, StaticMapError> {
        {
            let ids = self.saved_ids.lock().unwrap();
            if ids.contains(map_id) {
                let path = self.cache_dir.join(format!("map_{}.bin", map_id));
                if path.exists() {
                    return Ok(path);
                }
            }
        }

        let filename = format!("map_{}.bin", map_id);
        let path = self.cache_dir.join(&filename);

        let json_str = static_map_data.to_string();
        let compressed = encode_all(json_str.as_bytes(), 3)
            .map_err(|e| StaticMapError::Compression(e.to_string()))?;

        let mut file = fs::File::create(&path).await?;
        file.write_all(&compressed).await?;
        file.flush().await?;

        {
            let mut ids = self.saved_ids.lock().unwrap();
            ids.insert(map_id.to_string());
        }

        // Upload to S3 if configured
        let mut s3_key = String::new();
        if let Some(s3) = &self.s3 {
            s3_key = format!("static_maps/{}", filename);
            if let Err(err) = s3.upload_file(&path, &s3_key).await {
                // Best-effort: log error, keep local cache.
                tracing::error!(?err, "failed to upload static map to S3");
            }
        }

        // Record in DB if configured
        if let Some(db) = &self.db {
            // `map_id` is an opaque string identifier (e.g. "map42") and is
            // stored as such in the `maps` table. Avoid parsing it as an
            // integer so we don't collapse different map IDs into a single
            // numeric value like 0.
            if !db.map_exists(map_id).await? {
                let version = static_map_data
                    .get("version")
                    .and_then(|v| v.as_str())
                    .map(|s| s.to_string());
                db.insert_map(
                    map_id,
                    &s3_key,
                    version.as_deref(),
                )
                .await?;
            }
        }

        Ok(path)
    }
}

