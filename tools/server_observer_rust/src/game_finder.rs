use crate::account_pool::AccountPool;
use crate::recording_registry::RecordingRegistry;
use serde::Deserialize;
use std::collections::HashSet;
use std::sync::{Arc, Mutex};
use thiserror::Error;
use tokio::task::JoinHandle;
use tokio::time::{sleep, Duration};

#[derive(Debug, Clone, Deserialize)]
pub struct GameFinderConfig {
    #[serde(default)]
    pub scenario_ids: Vec<i32>,
    #[serde(default = "default_scan_interval")]
    pub scan_interval: f64,
    #[serde(default = "default_enabled_scanning")]
    pub enabled_scanning: bool,
    #[serde(default = "default_max_parallel_recordings")]
    pub max_parallel_recordings: i32,
    #[serde(default = "default_max_guest_games_per_account")]
    pub max_guest_games_per_account: i32,
}

fn default_scan_interval() -> f64 {
    30.0
}
fn default_enabled_scanning() -> bool {
    true
}
fn default_max_parallel_recordings() -> i32 {
    1
}
fn default_max_guest_games_per_account() -> i32 {
    -1
}

#[derive(Debug, Error)]
pub enum GameFinderError {
    #[error("Game finder task failed: {0}")]
    Task(#[from] tokio::task::JoinError),
}

type ObservationStarter = Arc<dyn Fn(i32, i32) + Send + Sync>;
type ActiveSessionCounter = Arc<dyn Fn() -> usize + Send + Sync>;

pub struct GameFinder {
    cfg: GameFinderConfig,
    account_pool: Arc<tokio::sync::Mutex<AccountPool>>,
    registry: RecordingRegistry,
    known_games: Arc<Mutex<HashSet<i32>>>,
    observation_starter: Option<ObservationStarter>,
    active_session_counter: Option<ActiveSessionCounter>,
    scan_handle: Option<JoinHandle<()>>,
}

impl GameFinder {
    pub fn new(
        cfg: GameFinderConfig,
        account_pool: Arc<tokio::sync::Mutex<AccountPool>>,
        registry: RecordingRegistry,
    ) -> Self {
        let known_games = {
            let mut set = HashSet::new();
            for (game_id, _) in registry.active() {
                set.insert(game_id);
            }
            Arc::new(Mutex::new(set))
        };

        Self {
            cfg,
            account_pool,
            registry,
            known_games,
            observation_starter: None,
            active_session_counter: None,
            scan_handle: None,
        }
    }

    pub fn set_observation_starter(&mut self, starter: ObservationStarter) {
        self.observation_starter = Some(starter);
    }

    pub fn set_active_session_counter(&mut self, counter: ActiveSessionCounter) {
        self.active_session_counter = Some(counter);
    }

    pub fn mark_game_known(&self, game_id: i32) {
        let mut set = self.known_games.lock().unwrap();
        set.insert(game_id);
    }

    pub fn refresh_known_games_from_registry(&self) {
        let active = self.registry.active();
        let mut set = self.known_games.lock().unwrap();
        set.clear();
        for (game_id, _) in active {
            set.insert(game_id);
        }
    }

    pub fn set_scan_interval(&mut self, interval: f64) {
        if interval > 0.0 {
            self.cfg.scan_interval = interval;
        }
    }

    pub fn set_scenario_ids(&mut self, scenario_ids: Vec<i32>) {
        self.cfg.scenario_ids = scenario_ids;
    }

    pub fn set_max_parallel_recordings(&mut self, max: i32) {
        if max >= 1 {
            self.cfg.max_parallel_recordings = max;
        }
    }

    pub fn set_max_guest_games_per_account(&mut self, max_guest: i32) {
        if max_guest >= -1 {
            self.cfg.max_guest_games_per_account = max_guest;
        }
    }

    pub fn set_enabled_scanning(&mut self, enabled: bool) {
        self.cfg.enabled_scanning = enabled;
    }

    pub fn start_scanning(&mut self) -> Result<(), GameFinderError> {
        if !self.cfg.enabled_scanning || self.scan_handle.is_some() {
            return Ok(());
        }

        let interval = self.cfg.scan_interval;
        let observation_starter = self.observation_starter.clone();
        let active_session_counter = self.active_session_counter.clone();
        let max_parallel_recordings = self.cfg.max_parallel_recordings;

        // NOTE: This is a skeleton implementation. The actual game discovery,
        // hub interaction, and selection logic needs to be implemented by
        // integrating a HubInterface equivalent.
        let handle = tokio::spawn(async move {
            loop {
                if let (Some(starter), Some(counter)) =
                    (observation_starter.as_ref(), active_session_counter.as_ref())
                {
                    let active = counter();
                    if (active as i32) < max_parallel_recordings {
                        // Placeholder: in a real implementation, call out to the hub,
                        // filter games by scenario_ids, and invoke starter(game_id, scenario_id).
                        tracing::debug!(
                            "GameFinder tick: active_sessions={}, max_parallel_recordings={}",
                            active,
                            max_parallel_recordings
                        );
                    }
                }

                sleep(Duration::from_secs_f64(interval)).await;
            }
        });

        self.scan_handle = Some(handle);
        Ok(())
    }
}

