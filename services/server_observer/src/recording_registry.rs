use crate::db::{DbClient, DbClientError};
use std::collections::BTreeMap;
use std::sync::{Arc, Mutex};

#[derive(Clone)]
pub struct RecordingRegistry {
    db: DbClient,
    active: Arc<Mutex<BTreeMap<i32, i32>>>,
}

impl RecordingRegistry {
    pub async fn new(db: DbClient) -> Result<Self, DbClientError> {
        let active_games = db.get_active_games().await?;
        let mut map = BTreeMap::new();
        for (game_id, scenario_id) in active_games {
            map.insert(game_id, scenario_id);
        }

        Ok(Self {
            db,
            active: Arc::new(Mutex::new(map)),
        })
    }

    pub async fn mark_discovered(&self, game_id: i32, scenario_id: i32) -> Result<(), DbClientError> {
        self.db.upsert_discovered_game(game_id, scenario_id).await
    }

    pub async fn mark_recording(&self, game_id: i32, scenario_id: i32) -> Result<(), DbClientError> {
        self.db.mark_game_recording(game_id, scenario_id).await?;
        self.active
            .lock()
            .expect("recording registry mutex poisoned")
            .insert(game_id, scenario_id);
        Ok(())
    }

    pub async fn mark_completed(&self, game_id: i32) -> Result<(), DbClientError> {
        self.db.mark_game_completed(game_id).await?;
        self.active
            .lock()
            .expect("recording registry mutex poisoned")
            .remove(&game_id);
        Ok(())
    }

    pub async fn mark_failed(&self, game_id: i32, reason: Option<&str>) -> Result<(), DbClientError> {
        self.db.mark_game_failed(game_id, reason).await?;
        self.active
            .lock()
            .expect("recording registry mutex poisoned")
            .remove(&game_id);
        Ok(())
    }

    pub fn active(&self) -> BTreeMap<i32, i32> {
        self.active
            .lock()
            .expect("recording registry mutex poisoned")
            .clone()
    }

    pub fn get_scenario_id(&self, game_id: i32) -> Option<i32> {
        self.active
            .lock()
            .expect("recording registry mutex poisoned")
            .get(&game_id)
            .copied()
    }

    pub fn db(&self) -> &DbClient {
        &self.db
    }
}

