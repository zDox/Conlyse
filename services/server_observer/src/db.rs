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
    ///
    /// `map_id` is stored as a string (VARCHAR) in the `maps` table and is
    /// treated as an opaque identifier (e.g. "map42"), not a numeric ID.
    pub async fn map_exists(&self, map_id: &str) -> Result<bool, DbClientError> {
        let conn = self.pool.get().await?;
        let row = conn
            .query_opt("SELECT 1 FROM maps WHERE map_id = $1 LIMIT 1", &[&map_id])
            .await?;
        Ok(row.is_some())
    }

    /// Insert a row into maps table; version may be None.
    ///
    /// `map_id` is stored as a string (VARCHAR) in the `maps` table, matching
    /// how other services (e.g. the API and converter) treat map identifiers.
    pub async fn insert_map(
        &self,
        map_id: &str,
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

    /// Return all known map IDs from the `maps` table.
    ///
    /// Each entry is the opaque string identifier stored in the `map_id`
    /// column (e.g. "map42"). This is used to initialize the in-memory
    /// static map cache at startup.
    pub async fn get_all_map_ids(&self) -> Result<Vec<String>, DbClientError> {
        let conn = self.pool.get().await?;
        let rows = conn
            .query("SELECT map_id FROM maps", &[])
            .await?;
        let mut ids = Vec::with_capacity(rows.len());
        for row in rows {
            let id: String = row.get(0);
            ids.push(id);
        }
        Ok(ids)
    }

    pub async fn upsert_discovered_game(
        &self,
        game_id: i32,
        scenario_id: i32,
    ) -> Result<(), DbClientError> {
        let conn = self.pool.get().await?;
        conn.execute(
            "INSERT INTO games (game_id, scenario_id, status, discovered_date, started_date, completed_date, failed_reason, created_at, updated_at) \
             VALUES ($1, $2, 'discovered', NOW(), NULL, NULL, NULL, NOW(), NOW()) \
             ON CONFLICT (game_id) DO UPDATE SET scenario_id = EXCLUDED.scenario_id, updated_at = NOW()",
            &[&game_id, &scenario_id],
        )
        .await?;
        Ok(())
    }

    pub async fn mark_game_recording(
        &self,
        game_id: i32,
        scenario_id: i32,
    ) -> Result<(), DbClientError> {
        let conn = self.pool.get().await?;
        conn.execute(
            "INSERT INTO games (game_id, scenario_id, status, discovered_date, started_date, completed_date, failed_reason, created_at, updated_at) \
             VALUES ($1, $2, 'recording', NOW(), NOW(), NULL, NULL, NOW(), NOW()) \
             ON CONFLICT (game_id) DO UPDATE SET \
               scenario_id = EXCLUDED.scenario_id, \
               status = 'recording', \
               started_date = COALESCE(games.started_date, NOW()), \
               updated_at = NOW()",
            &[&game_id, &scenario_id],
        )
        .await?;
        Ok(())
    }

    pub async fn mark_game_completed(&self, game_id: i32) -> Result<(), DbClientError> {
        let conn = self.pool.get().await?;
        conn.execute(
            "UPDATE games SET status = 'completed', completed_date = NOW(), updated_at = NOW() WHERE game_id = $1",
            &[&game_id],
        )
        .await?;
        conn.execute(
            "INSERT INTO replay_library (user_id, game_id, created_at) \
             SELECT user_id, game_id, NOW() FROM recording_list WHERE game_id = $1 \
             ON CONFLICT (user_id, game_id) DO NOTHING",
            &[&game_id],
        )
        .await?;
        Ok(())
    }

    pub async fn mark_game_failed(
        &self,
        game_id: i32,
        reason: Option<&str>,
    ) -> Result<(), DbClientError> {
        let conn = self.pool.get().await?;
        conn.execute(
            "UPDATE games SET status = 'failed', failed_reason = $2, completed_date = NOW(), updated_at = NOW() WHERE game_id = $1",
            &[&game_id, &reason],
        )
        .await?;
        Ok(())
    }

    pub async fn get_active_games(&self) -> Result<Vec<(i32, i32)>, DbClientError> {
        let conn = self.pool.get().await?;
        let rows = conn
            .query(
                "SELECT game_id, scenario_id FROM games WHERE status = 'recording'",
                &[],
            )
            .await?;
        let mut out = Vec::with_capacity(rows.len());
        for row in rows {
            let game_id: i32 = row.get(0);
            let scenario_id: i32 = row.get(1);
            out.push((game_id, scenario_id));
        }
        Ok(out)
    }

    pub async fn is_on_any_recording_list(&self, game_id: i32) -> Result<bool, DbClientError> {
        let conn = self.pool.get().await?;
        let row = conn
            .query_opt(
                "SELECT 1 FROM recording_list WHERE game_id = $1 LIMIT 1",
                &[&game_id],
            )
            .await?;
        Ok(row.is_some())
    }

    pub async fn get_recording_list_candidates(&self) -> Result<Vec<(i32, i32)>, DbClientError> {
        let conn = self.pool.get().await?;
        let rows = conn
            .query(
                "SELECT DISTINCT g.game_id, g.scenario_id \
                 FROM games g \
                 JOIN recording_list r ON r.game_id = g.game_id \
                 WHERE g.status NOT IN ('recording', 'completed')",
                &[],
            )
            .await?;
        let mut out = Vec::with_capacity(rows.len());
        for row in rows {
            let game_id: i32 = row.get(0);
            let scenario_id: i32 = row.get(1);
            out.push((game_id, scenario_id));
        }
        Ok(out)
    }
}

