use crate::account_pool::AccountPool;
use crate::db::{DbClient, DbConfig};
use crate::game_finder::{GameFinder, GameFinderConfig};
use crate::metrics::{
    record_game_completed, record_game_failed, record_game_started, record_missed_interval,
    record_scheduled_update_latency, record_game_update_completed, record_game_update_started,
    set_active_games,
};
use crate::observation_session::{ObservationError, ObservationResult, ObservationSession};
use crate::recording_registry::RecordingRegistry;
use crate::redis_publisher::{RedisConfig, RedisPublisher};
use crate::s3_client::{S3Client, S3Config};
use crate::scheduler::Scheduler;
use crate::static_map_cache::{StaticMapCache, StaticMapError};
use config::Config as AppConfig;
use std::collections::HashMap;
use std::sync::atomic::{AtomicBool, AtomicI32, Ordering};
use std::sync::{Arc, Mutex};
use std::time::SystemTime;
use thiserror::Error;

const MAX_UPDATE_RETRIES: i32 = 3;

#[derive(Debug, Error)]
pub enum ServerObserverError {
    #[error("map cache error: {0}")]
    StaticMap(#[from] StaticMapError),
    #[error("database error: {0}")]
    Database(#[from] crate::db::DbClientError),
    #[error("s3 error: {0}")]
    S3(#[from] crate::s3_client::S3Error),
    #[error("redis error: {0}")]
    Redis(#[from] crate::redis_publisher::RedisPublisherError),
}

pub struct ServerObserver {
    account_pool: Arc<tokio::sync::Mutex<AccountPool>>,
    scheduler: Arc<Scheduler>,
    max_parallel_recordings: AtomicI32,
    update_interval: Mutex<f64>,
    output_dir: String,
    output_metadata_dir: String,
    long_term_storage_path: String,
    file_size_threshold: i64,
    observer_sessions: Mutex<HashMap<i32, Arc<tokio::sync::Mutex<ObservationSession>>>>,
    registry: RecordingRegistry,
    game_finder: Mutex<Option<GameFinder>>,
    stop_flag: AtomicBool,
    map_cache: StaticMapCache,
    redis_publisher: Option<RedisPublisher>,
}

impl ServerObserver {
    pub async fn new(
        settings: &AppConfig,
        account_pool: Arc<tokio::sync::Mutex<AccountPool>>,
    ) -> Result<Arc<Self>, ServerObserverError> {
        let max_parallel_recordings = settings
            .get::<i64>("max_parallel_recordings")
            .unwrap_or(1) as i32;
        let max_parallel_updates = settings
            .get::<i64>("max_parallel_updates")
            .unwrap_or(1) as i32;
        let max_parallel_first_updates = settings
            .get::<i64>("max_parallel_first_updates")
            .unwrap_or(1) as i32;
        let update_interval = settings
            .get::<f64>("update_interval")
            .unwrap_or(60.0);

        let output_dir = settings
            .get::<String>("output_dir")
            .unwrap_or_else(|_| "./recordings".to_string());
        let output_metadata_dir = settings
            .get::<String>("output_metadata_dir")
            .unwrap_or_default();
        let long_term_storage_path = settings
            .get::<String>("long_term_storage_path")
            .unwrap_or_default();
        let file_size_threshold = settings
            .get::<i64>("file_size_threshold")
            .unwrap_or(0);

        let registry_default_dir = if output_metadata_dir.is_empty() {
            output_dir.clone()
        } else {
            output_metadata_dir.clone()
        };
        let registry_path = settings
            .get::<String>("registry_path")
            .unwrap_or_else(|_| format!("{registry_default_dir}/server_observer_registry.json"));
        let registry = RecordingRegistry::new(registry_path);

        let db_client = match settings.get::<DbConfig>("database") {
            Ok(cfg) => match DbClient::new(cfg).await {
                Ok(client) if client.is_connected().await => Some(client),
                Ok(_) => {
                    tracing::warn!(
                        "database configured but connection test failed; disabling DB features"
                    );
                    None
                }
                Err(err) => {
                    tracing::warn!(
                        ?err,
                        "failed to initialize database client; disabling DB features"
                    );
                    None
                }
            },
            Err(_) => None,
        };

        let static_maps_dir = settings
            .get::<String>("storage.static_maps_dir")
            .unwrap_or_else(|_| format!("{output_dir}/static_maps"));

        let s3_client = match settings.get::<S3Config>("storage.s3") {
            Ok(parsed) => Some(S3Client::new(parsed).await?),
            Err(_) => None,
        };

        let s3_enabled = s3_client.is_some();

        let map_cache = StaticMapCache::new(static_maps_dir, s3_client, db_client.clone()).await?;

        let redis_publisher = match settings.get::<RedisConfig>("redis") {
            Ok(cfg) => match RedisPublisher::new(cfg) {
                Ok(redis) => Some(redis),
                Err(err) => {
                    tracing::warn!(
                        ?err,
                        "failed to initialize redis publisher; disabling redis"
                    );
                    None
                }
            },
            Err(_) => None,
        };

        let db_enabled = db_client.is_some();
        let redis_enabled = redis_publisher.is_some();

        let scheduler = Arc::new(Scheduler::new(
            max_parallel_updates.max(1),
            max_parallel_first_updates.max(1),
            update_interval,
        ));
        scheduler.set_update_interval(update_interval);
        scheduler.set_max_parallel_updates(max_parallel_updates.max(1));
        scheduler.set_max_parallel_first_updates(max_parallel_first_updates.max(1));

        let enabled_scanning = settings
            .get::<bool>("game_finder.enabled")
            .unwrap_or(false);

        let scan_interval = settings
            .get::<f64>("game_finder.scan_interval_seconds")
            .unwrap_or(300.0);

        let max_parallel_recordings_cfg = settings
            .get::<i64>("game_finder.max_games_per_scan")
            .unwrap_or(max_parallel_recordings as i64) as i32;

        let scenario_ids = settings
            .get::<Vec<i32>>("game_finder.scenario_ids")
            .unwrap_or_else(|_| Vec::new());

        let max_guest_games_per_account = settings
            .get::<i64>("game_finder.max_guest_games_per_account")
            .unwrap_or(-1) as i32;

        let game_finder_cfg = GameFinderConfig {
            scenario_ids,
            scan_interval,
            enabled_scanning,
            max_parallel_recordings: max_parallel_recordings_cfg,
            max_guest_games_per_account,
        };
        let mut game_finder =
            GameFinder::new(game_finder_cfg.clone(), Arc::clone(&account_pool), registry.clone());
        game_finder.set_scan_interval(game_finder_cfg.scan_interval);
        game_finder.set_scenario_ids(game_finder_cfg.scenario_ids.clone());
        game_finder.set_max_parallel_recordings(game_finder_cfg.max_parallel_recordings);
        game_finder.set_max_guest_games_per_account(game_finder_cfg.max_guest_games_per_account);

        let observer = Arc::new(Self {
            account_pool,
            scheduler,
            max_parallel_recordings: AtomicI32::new(max_parallel_recordings.max(1)),
            update_interval: Mutex::new(update_interval),
            output_dir,
            output_metadata_dir,
            long_term_storage_path,
            file_size_threshold,
            observer_sessions: Mutex::new(HashMap::new()),
            registry,
            game_finder: Mutex::new(Some(game_finder)),
            stop_flag: AtomicBool::new(false),
            map_cache,
            redis_publisher,
        });

        tracing::info!(
            max_parallel_recordings,
            max_parallel_updates,
            max_parallel_first_updates,
            update_interval,
            db_enabled,
            s3_enabled,
            redis_enabled,
            output_dir = %observer.output_dir,
            output_metadata_dir = %observer.output_metadata_dir,
            long_term_storage_path = %observer.long_term_storage_path,
            file_size_threshold = observer.file_size_threshold,
            "initialized ServerObserver configuration"
        );

        observer.install_game_finder_callbacks();
        observer.install_account_pool_callbacks().await;
        Ok(observer)
    }

    pub async fn run(self: Arc<Self>) -> bool {
        self.stop_flag.store(false, Ordering::SeqCst);

        let current_max_parallel = self.max_parallel_recordings.load(Ordering::SeqCst);
        let current_update_interval = *self
            .update_interval
            .lock()
            .expect("update interval mutex poisoned");
        tracing::info!(
            max_parallel_recordings = current_max_parallel,
            update_interval = current_update_interval,
            "server observer run loop started"
        );

        self.resume_active().await;
        {
            let mut guard = self.game_finder.lock().expect("game finder mutex poisoned");
            if let Some(game_finder) = guard.as_mut() {
                game_finder.refresh_known_games_from_registry();
                let enabled = game_finder.is_scanning_enabled();
                game_finder.set_enabled_scanning(enabled);
            }
        }

        while !self.stop_flag.load(Ordering::SeqCst) {
            let pending = self.scheduler.get_pending_new_sessions();
            for (game_id, scenario_id) in pending {
                let can_start = {
                    let sessions = self
                        .observer_sessions
                        .lock()
                        .expect("observer sessions mutex poisoned");
                    sessions.len() < self.max_parallel_recordings.load(Ordering::SeqCst) as usize
                };
                if can_start {
                    self.start_observation_session(game_id, scenario_id).await;
                }
            }

            self.start_due_updates().await;
        }

        tracing::info!("server observer run loop stopping");

        true
    }

    pub async fn stop(&self) {
        self.stop_flag.store(true, Ordering::SeqCst);
        tracing::info!("stop requested; shutting down scheduler and game finder");
        self.scheduler.stop();

        let mut game_finder = {
            let mut guard = self.game_finder.lock().expect("game finder mutex poisoned");
            guard.take()
        };
        if let Some(ref mut finder) = game_finder {
            finder.stop_scanning().await;
        }

        self.observer_sessions
            .lock()
            .expect("observer sessions mutex poisoned")
            .clear();
    }

    async fn start_observation_session(&self, game_id: i32, scenario_id: i32) {
        let account = {
            let mut pool = self.account_pool.lock().await;
            pool.next_guest_account_owned(-1)
        };
        let Some(account) = account else {
            tracing::warn!("no free account available for new observation");
            return;
        };

        tracing::info!(
            game_id,
            scenario_id,
            account = %account.username,
            "starting new observation session"
        );

        let metadata_path = if self.output_metadata_dir.is_empty() {
            String::new()
        } else {
            format!("{}/game_{}", self.output_metadata_dir, game_id)
        };

        let mut session = ObservationSession::new(
            game_id,
            account.clone(),
            Some(self.map_cache.clone()),
            format!("{}/game_{}", self.output_dir, game_id),
            metadata_path,
            self.long_term_storage_path.clone(),
            self.file_size_threshold,
            self.redis_publisher.clone(),
        );

        self.registry.mark_recording(game_id, scenario_id, Some(""));
        self.scheduler.initialize_session_schedule(&mut session);
        self.scheduler.mark_first_update(game_id);
        self.scheduler.schedule_update(&session);

        {
            let mut sessions = self
                .observer_sessions
                .lock()
                .expect("observer sessions mutex poisoned");
            sessions.insert(game_id, Arc::new(tokio::sync::Mutex::new(session)));
        }

        {
            let mut pool = self.account_pool.lock().await;
            pool.increment_guest_join(&account.username);
        }

        {
            let mut game_finder = self.game_finder.lock().expect("game finder mutex poisoned");
            if let Some(finder) = game_finder.as_mut() {
                finder.mark_game_known(game_id);
            }
        }

        // Record game started metric and update active games gauge
        record_game_started(scenario_id);
        self.update_active_games_metrics().await;
    }

    async fn resume_active(&self) {
        let active = self.registry.active();
        tracing::info!(active_count = active.len(), "resuming active recordings from registry");
        let mut resumed = 0usize;
        for (game_id, meta) in active {
            let scenario_id = meta
                .get("scenario_id")
                .and_then(serde_json::Value::as_i64)
                .unwrap_or(-1) as i32;
            if scenario_id < 0 {
                tracing::warn!(game_id, "skipping registry entry with missing scenario_id");
                continue;
            }

            let already_exists = self
                .observer_sessions
                .lock()
                .expect("observer sessions mutex poisoned")
                .contains_key(&game_id);
            if already_exists {
                tracing::debug!(game_id, "skipping resume for game already in observer_sessions");
                continue;
            }

            if self
                .observer_sessions
                .lock()
                .expect("observer sessions mutex poisoned")
                .len()
                >= self.max_parallel_recordings.load(Ordering::SeqCst) as usize
            {
                tracing::warn!(
                    "reached max_parallel_recordings while resuming; remaining sessions will be picked up later"
                );
                break;
            }
            self.start_observation_session(game_id, scenario_id).await;
            resumed += 1;
        }
        tracing::info!(resumed, "finished resuming active recordings");
    }

    async fn start_due_updates(self: &Arc<Self>) {
        let due_sessions = self.scheduler.get_due_updates();
        if !due_sessions.is_empty() {
            tracing::debug!(due_count = due_sessions.len(), "starting due updates");
        }
        for game_id in due_sessions {
            self.scheduler.increment_active_coroutines();
            let observer = Arc::clone(self);
            tokio::spawn(async move {
                observer.run_single_update_async(game_id).await;
            });
        }
        self.scheduler.process_due_updates().await;
    }

    async fn run_single_update_async(self: Arc<Self>, game_id: i32) {
        let session_arc = {
            self.observer_sessions
                .lock()
                .expect("observer sessions mutex poisoned")
                .get(&game_id)
                .cloned()
        };
        let Some(session_arc) = session_arc else {
            tracing::debug!(game_id, "due update skipped; session no longer exists");
            self.scheduler.decrement_active_coroutines();
            return;
        };

        // Record game update started and scheduled latency metrics
        let scheduled_latency_secs = {
            let session_opt = {
                self.observer_sessions
                    .lock()
                    .expect("observer sessions mutex poisoned")
                    .get(&game_id)
                    .cloned()
            };
            if let Some(session_arc) = session_opt {
                let session = session_arc.lock().await;
                let now = SystemTime::now();
                if now > session.next_update_at {
                    now.duration_since(session.next_update_at)
                        .map(|d| d.as_secs_f64())
                        .ok()
                } else {
                    None
                }
            } else {
                None
            }
        };

        record_game_update_started();
        if let Some(latency) = scheduled_latency_secs {
            record_scheduled_update_latency(latency);
            if latency > 10.0 {
                record_missed_interval();
            }
        }

        let result = {
            let mut session = session_arc.lock().await;
            session.run_update_async().await
        };

        if result.game_ended {
            self.handle_game_ended(game_id, &session_arc).await;
        } else if result.error_code == ObservationError::Success {
            self.handle_successful_update(&session_arc).await;
        } else {
            self.handle_failed_update(game_id, &session_arc, result).await;
        }

        self.scheduler.cleanup_first_update_tracking(game_id);
        record_game_update_completed();
        self.scheduler.decrement_active_coroutines();
    }

    async fn handle_game_ended(
        &self,
        game_id: i32,
        session_arc: &Arc<tokio::sync::Mutex<ObservationSession>>,
    ) {
        let scenario_id = self.registry.get_scenario_id(game_id);
        tracing::info!(game_id, ?scenario_id, "game ended, completing recording");
        self.registry.mark_completed(game_id);
        let username = session_arc.lock().await.account.username.clone();
        {
            let mut pool = self.account_pool.lock().await;
            pool.decrement_guest_join(&username);
        }
        self.observer_sessions
            .lock()
            .expect("observer sessions mutex poisoned")
            .remove(&game_id);

        if let Some(scenario_id) = scenario_id {
            record_game_completed(scenario_id);
        }

        self.update_active_games_metrics().await;
    }

    async fn handle_successful_update(&self, session_arc: &Arc<tokio::sync::Mutex<ObservationSession>>) {
        let mut session = session_arc.lock().await;
        let now = SystemTime::now();
        let latency_secs = now
            .duration_since(session.next_update_at)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0);
        let update_interval = *self.update_interval.lock().expect("update interval mutex poisoned");
        let missed_update = latency_secs > update_interval;

        tracing::info!(
            game_id = session.game_id,
            latency_secs,
            missed_update,
            "successful update completed"
        );

        self.scheduler
            .schedule_next_update(&mut session, missed_update);
        session.reset_attempt();
    }

    async fn handle_failed_update(
        &self,
        game_id: i32,
        session_arc: &Arc<tokio::sync::Mutex<ObservationSession>>,
        result: ObservationResult,
    ) {
        let mut drop_session = false;
        let username: String;
        let mut needs_proxy_reset = false;

        {
            let mut session = session_arc.lock().await;
            username = session.account.username.clone();
            if session.get_attempt() >= MAX_UPDATE_RETRIES {
                drop_session = true;
            } else {
                session.increment_attempt();
                needs_proxy_reset = result.error_code == ObservationError::NetworkError;
                let immediate = self.should_retry_immediately(result.error_code);
                tracing::warn!(
                    game_id,
                    attempt = session.get_attempt(),
                    ?result.error_code,
                    immediate_retry = immediate,
                    "update failed; scheduling retry"
                );
                if immediate {
                    self.scheduler.schedule_immediate_update(&mut session);
                } else {
                    self.scheduler.schedule_next_update(&mut session, false);
                }
            }
        }

        if needs_proxy_reset {
            let mut pool = self.account_pool.lock().await;
            if !pool.reset_account_proxy(&username).await {
                tracing::warn!(account = username, "failed to reset proxy after network error");
            }
        }

        if drop_session {
            tracing::error!(
                game_id,
                account = username,
                error_message = %result.error_message,
                "dropping observation session after exceeding max retries"
            );
            self.registry.mark_failed(game_id, Some(&result.error_message));
            {
                let mut pool = self.account_pool.lock().await;
                pool.decrement_guest_join(&username);
            }
            self.observer_sessions
                .lock()
                .expect("observer sessions mutex poisoned")
                .remove(&game_id);
            let error_type = match result.error_code {
                ObservationError::AuthFailed => "auth_failed",
                ObservationError::ServerError => "server_error",
                ObservationError::NetworkError => "network_error",
                ObservationError::PackageCreationFailed => "package_creation_failed",
                ObservationError::UnknownError => "unknown_error",
                ObservationError::Success | ObservationError::GameEnded => "unknown_error",
            };
            record_game_failed(error_type);

            self.update_active_games_metrics().await;
        }
    }

    async fn update_active_games_metrics(&self) {
        let mut active_by_scenario = std::collections::HashMap::<i32, i64>::new();
        {
            let sessions = self
                .observer_sessions
                .lock()
                .expect("observer sessions mutex poisoned");
            for (&game_id, _) in sessions.iter() {
                if let Some(scenario_id) = self.registry.get_scenario_id(game_id) {
                    *active_by_scenario.entry(scenario_id).or_insert(0) += 1;
                }
            }
        }

        for (scenario_id, count) in active_by_scenario {
            set_active_games(scenario_id, count);
        }
    }

    fn should_retry_immediately(&self, error_code: ObservationError) -> bool {
        error_code == ObservationError::AuthFailed || error_code == ObservationError::ServerError
    }

    async fn reset_sessions_for_account(
        &self,
        username: &str,
        new_proxy: crate::account_pool::ProxyConfig,
    ) {
        let session_arcs = {
            self.observer_sessions
                .lock()
                .expect("observer sessions mutex poisoned")
                .values()
                .cloned()
                .collect::<Vec<_>>()
        };

        for session_arc in session_arcs {
            let mut session = session_arc.lock().await;
            if session.account.username == username {
                session.set_proxy(new_proxy.clone());
            }
        }
    }

    fn install_game_finder_callbacks(self: &Arc<Self>) {
        let weak = Arc::downgrade(self);
        let active_weak = Arc::downgrade(self);
        let mut guard = self.game_finder.lock().expect("game finder mutex poisoned");
        let Some(game_finder) = guard.as_mut() else {
            return;
        };

        game_finder.set_observation_starter(Arc::new(move |game_id, scenario_id| {
            if let Some(observer) = weak.upgrade() {
                observer.scheduler.queue_new_session(game_id, scenario_id);
            }
        }));

        game_finder.set_active_session_counter(Arc::new(move || {
            active_weak
                .upgrade()
                .map(|observer| {
                    observer
                        .observer_sessions
                        .lock()
                        .expect("observer sessions mutex poisoned")
                        .len()
                })
                .unwrap_or(0)
        }));

        tracing::info!("installed GameFinder callbacks");
    }

    async fn install_account_pool_callbacks(self: &Arc<Self>) {
        let weak = Arc::downgrade(self);
        let callback = Arc::new(move |username: String| {
            let Some(observer) = weak.upgrade() else {
                return;
            };
            tokio::spawn(async move {
                let new_proxy = {
                    let pool = observer.account_pool.lock().await;
                    pool.get_account_proxy(&username)
                };
                if let Some(proxy) = new_proxy {
                    observer.reset_sessions_for_account(&username, proxy).await;
                }
            });
        });

        let mut pool = self.account_pool.lock().await;
        pool.set_proxy_reset_callback(callback);
        tracing::info!("installed AccountPool proxy reset callback");
    }
}

