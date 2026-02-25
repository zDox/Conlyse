use crate::account_pool::AccountPool;
use crate::hub_interface_wrapper::{HubGameProperties, HubInterfaceWrapper};
use crate::recording_registry::RecordingRegistry;
use serde::Deserialize;
use std::collections::{HashSet, HashSet as Set};
use std::fs::OpenOptions;
use std::io::Write;
use std::sync::atomic::{AtomicBool, Ordering};
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
    #[serde(default)]
    pub listing_account: Option<ListingAccountConfig>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct ListingAccountConfig {
    #[serde(default)]
    pub username: String,
    #[serde(default)]
    pub password: String,
    #[serde(default)]
    pub proxy_url: String,
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
    cfg: Arc<Mutex<GameFinderConfig>>,
    account_pool: Arc<tokio::sync::Mutex<AccountPool>>,
    registry: RecordingRegistry,
    known_games: Arc<Mutex<HashSet<i32>>>,
    observation_starter: Option<ObservationStarter>,
    active_session_counter: Option<ActiveSessionCounter>,
    scan_handle: Option<JoinHandle<()>>,
    stop_flag: Arc<AtomicBool>,
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
            cfg: Arc::new(Mutex::new(cfg)),
            account_pool,
            registry,
            known_games,
            observation_starter: None,
            active_session_counter: None,
            scan_handle: None,
            stop_flag: Arc::new(AtomicBool::new(false)),
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
            self.cfg.lock().unwrap().scan_interval = interval;
        }
    }

    pub fn set_scenario_ids(&mut self, scenario_ids: Vec<i32>) {
        self.cfg.lock().unwrap().scenario_ids = scenario_ids;
    }

    pub fn set_max_parallel_recordings(&mut self, max: i32) {
        if max >= 1 {
            self.cfg.lock().unwrap().max_parallel_recordings = max;
        }
    }

    pub fn set_max_guest_games_per_account(&mut self, max_guest: i32) {
        if max_guest >= -1 {
            self.cfg.lock().unwrap().max_guest_games_per_account = max_guest;
        }
    }

    pub fn set_enabled_scanning(&mut self, enabled: bool) {
        self.cfg.lock().unwrap().enabled_scanning = enabled;
        if enabled && self.scan_handle.is_none() {
            if let Err(err) = self.start_scanning() {
                tracing::warn!(?err, "failed to start scanning while enabling GameFinder");
            }
        }
    }

    pub fn is_scanning_enabled(&self) -> bool {
        self.cfg.lock().unwrap().enabled_scanning
    }

    pub fn start_scanning(&mut self) -> Result<(), GameFinderError> {
        let enabled = self.cfg.lock().unwrap().enabled_scanning;
        if !enabled {
            return Ok(());
        }
        if self.scan_handle.is_some() {
            return Ok(());
        }

        self.stop_flag.store(false, Ordering::SeqCst);
        let cfg = Arc::clone(&self.cfg);
        let stop_flag = Arc::clone(&self.stop_flag);
        let known_games = Arc::clone(&self.known_games);
        let account_pool = Arc::clone(&self.account_pool);
        let observation_starter = self.observation_starter.clone();
        let active_session_counter = self.active_session_counter.clone();
        let handle = tokio::spawn(async move {
            while !stop_flag.load(Ordering::SeqCst) {
                let cfg_snapshot = cfg.lock().unwrap().clone();
                if cfg_snapshot.enabled_scanning {
                    if let (Some(starter), Some(counter), Some(listing)) = (
                        observation_starter.as_ref(),
                        active_session_counter.as_ref(),
                        cfg_snapshot.listing_account.as_ref(),
                    ) {
                        let mut active_sessions = counter();
                        let selected_games = select_games(
                            listing,
                            &cfg_snapshot.scenario_ids,
                            &known_games,
                        );
                        for (scenario_id, game) in selected_games {
                            if active_sessions >= cfg_snapshot.max_parallel_recordings as usize {
                                break;
                            }
                            let has_available_account = {
                                let mut pool = account_pool.lock().await;
                                pool.next_guest_account_owned(cfg_snapshot.max_guest_games_per_account)
                                    .is_some()
                            };
                            if !has_available_account {
                                tracing::warn!(
                                    "no account available for guest limit {}, ending scan batch",
                                    cfg_snapshot.max_guest_games_per_account
                                );
                                break;
                            }
                            starter(game.game_id, scenario_id);
                            active_sessions += 1;
                            known_games.lock().unwrap().insert(game.game_id);
                        }
                    } else {
                        tracing::warn!("game finder scanning configured without callbacks/listing account");
                    }
                }

                let interval = cfg_snapshot.scan_interval.max(0.1);
                let sleep_end = std::time::Instant::now() + Duration::from_secs_f64(interval);
                while !stop_flag.load(Ordering::SeqCst) && std::time::Instant::now() < sleep_end {
                    sleep(Duration::from_millis(100)).await;
                }
            }
        });

        self.scan_handle = Some(handle);
        Ok(())
    }

    pub async fn stop_scanning(&mut self) {
        self.stop_flag.store(true, Ordering::SeqCst);
        if let Some(handle) = self.scan_handle.take() {
            let _ = handle.await;
        }
    }
}

fn select_games(
    listing: &ListingAccountConfig,
    scenario_ids: &[i32],
    known_games: &Arc<Mutex<HashSet<i32>>>,
) -> Vec<(i32, HubGameProperties)> {
    let mut selected = Vec::new();
    let mut seen_games: Set<i32> = Set::new();

    let interface = match HubInterfaceWrapper::new(listing.proxy_url.clone(), listing.proxy_url.clone()) {
        Ok(i) => i,
        Err(err) => {
            tracing::warn!(?err, "failed creating listing interface");
            // #region agent log
            if let Ok(mut file) = OpenOptions::new()
                .create(true)
                .append(true)
                .open("/home/zdox/PycharmProjects/ConflictInterface/.cursor/debug-ef93be.log")
            {
                let error_str = format!("{err:?}").replace('"', "\\\"");
                let timestamp = std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .map(|d| d.as_millis())
                    .unwrap_or(0);
                let payload = format!(
                    "{{\"sessionId\":\"ef93be\",\"runId\":\"pre-fix\",\"hypothesisId\":\"H1\",\"location\":\"game_finder.rs:238-245\",\"message\":\"failed creating listing interface\",\"data\":{{\"error\":\"{error_str}\"}},\"timestamp\":{timestamp}}}"
                );
                let _ = writeln!(file, "{}", payload);
            }
            // #endregion agent log
            return selected;
        }
    };
    let mut interface = interface;

    if interface
        .login(&listing.username, &listing.password)
        .ok()
        != Some(true)
    {
        tracing::warn!(
            account = listing.username,
            "listing account login failed; skipping scan iteration"
        );
        return selected;
    }

    let games = match interface.get_global_games() {
        Ok(g) => g,
        Err(err) => {
            tracing::warn!(?err, "failed to fetch global games");
            return selected;
        }
    };

    for scenario_id in scenario_ids {
        let new_candidates: Vec<HubGameProperties> = {
            let known = known_games.lock().unwrap();
            games
                .iter()
                .filter(|game| game.scenario_id == *scenario_id && !known.contains(&game.game_id))
                .cloned()
                .collect()
        };

        let joinable = new_candidates
            .into_iter()
            .filter(|game| game.open_slots >= 1)
            .collect::<Vec<_>>();

        for game in joinable {
            if seen_games.insert(game.game_id) {
                selected.push((*scenario_id, game));
            }
        }
    }

    selected
}

