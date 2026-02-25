use bb8::{Pool, RunError};
use bb8_postgres::PostgresConnectionManager;
use serde::Deserialize;
use thiserror::Error;
use tokio_postgres::{tls::NoTls, Error as PgError};

#[derive(Debug, Clone, Deserialize)]
pub struct DbConfig {
    pub host: String,
    pub port: u16,
    pub database: String,
    pub user: String,
    pub password: String,
}

#[derive(Debug, Error)]
pub enum DbClientError {
    #[error("Postgres error: {0}")]
    Postgres(#[from] PgError),
    #[error("Pool error: {0}")]
    Pool(#[from] RunError<PgError>),
}

#[derive(Clone)]
pub struct DbClient {
    pool: Pool<PostgresConnectionManager<NoTls>>,
}

impl DbClient {
    pub async fn new(config: DbConfig) -> Result<Self, DbClientError> {
        let mut cfg = tokio_postgres::Config::new();
        cfg.host(&config.host)
            .port(config.port)
            .dbname(&config.database)
            .user(&config.user)
            .password(&config.password);

        let mgr = PostgresConnectionManager::new(cfg, NoTls);
        let pool = Pool::builder().build(mgr).await?;

        Ok(Self { pool })
    }

    pub async fn is_connected(&self) -> bool {
        self.pool.get().await.is_ok()
    }

    /// Check if a row exists in maps table for given map_id.
    pub async fn map_exists(&self, map_id: i64) -> Result<bool, DbClientError> {
        let conn = self.pool.get().await?;
        let row = conn
            .query_opt("SELECT 1 FROM maps WHERE map_id = $1 LIMIT 1", &[&map_id])
            .await?;
        Ok(row.is_some())
    }

    /// Insert a row into maps table; version may be None.
    pub async fn insert_map(
        &self,
        map_id: i64,
        s3_key: &str,
        version: Option<&str>,
    ) -> Result<(), DbClientError> {
        let conn = self.pool.get().await?;
        conn.execute(
            "INSERT INTO maps (map_id, version, s3_key, created_at, updated_at) \
             VALUES ($1, $2, $3, NOW(), NOW())",
            &[&map_id, &version, &s3_key],
        )
        .await?;
        Ok(())
    }
}

