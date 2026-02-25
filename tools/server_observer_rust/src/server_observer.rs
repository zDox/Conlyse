use crate::account_pool::AccountPool;
use crate::db::{DbClient, DbConfig};
use crate::game_finder::{GameFinder, GameFinderConfig};
use crate::observation_session::{ObservationError, ObservationResult, ObservationSession};
use crate::recording_registry::RecordingRegistry;
use crate::redis_publisher::{RedisConfig, RedisPublisher};
use crate::s3_client::{S3Client, S3Config};
use crate::scheduler::Scheduler;
use crate::static_map_cache::{StaticMapCache, StaticMapError};
use serde_json::Value;
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
        config: Value,
        account_pool: Arc<tokio::sync::Mutex<AccountPool>>,
    ) -> Result<Arc<Self>, ServerObserverError> {
        let max_parallel_recordings = i64_at(&config, "max_parallel_recordings", 1) as i32;
        let max_parallel_updates = i64_at(&config, "max_parallel_updates", 1) as i32;
        let max_parallel_first_updates = i64_at(&config, "max_parallel_first_updates", 1) as i32;
        let update_interval = f64_at(&config, "update_interval", 60.0);

        let output_dir = str_at(&config, "output_dir")
            .unwrap_or("./recordings")
            .to_string();
        let output_metadata_dir = str_at(&config, "output_metadata_dir")
            .unwrap_or_default()
            .to_string();
        let long_term_storage_path = str_at(&config, "long_term_storage_path")
            .unwrap_or_default()
            .to_string();
        let file_size_threshold = i64_at(&config, "file_size_threshold", 0);

        let registry_default_dir = if output_metadata_dir.is_empty() {
            output_dir.clone()
        } else {
            output_metadata_dir.clone()
        };
        let registry_path = str_at(&config, "registry_path")
            .map(str::to_string)
            .unwrap_or_else(|| format!("{registry_default_dir}/server_observer_registry.json"));
        let registry = RecordingRegistry::new(registry_path);

        let db_client = if let Some(database_cfg) = config.get("database").and_then(Value::as_object) {
            let maybe_cfg = parse_db_config(database_cfg);
            if let Some(cfg) = maybe_cfg {
                match DbClient::new(cfg).await {
                    Ok(client) if client.is_connected().await => Some(client),
                    Ok(_) => {
                        tracing::warn!("database configured but connection test failed; disabling DB features");
                        None
                    }
                    Err(err) => {
                        tracing::warn!(?err, "failed to initialize database client; disabling DB features");
                        None
                    }
                }
            } else {
                None
            }
        } else {
            None
        };

        let static_maps_dir = config
            .pointer("/storage/static_maps_dir")
            .and_then(Value::as_str)
            .map(str::to_string)
            .unwrap_or_else(|| format!("{output_dir}/static_maps"));

        let s3_client = if let Some(s3_cfg) = config.pointer("/storage/s3").and_then(Value::as_object)
        {
            if let Some(parsed) = parse_s3_config(s3_cfg) {
                Some(S3Client::new(parsed).await?)
            } else {
                None
            }
        } else {
            None
        };

        let map_cache = StaticMapCache::new(static_maps_dir, s3_client, db_client.clone()).await?;

        let redis_publisher = if let Some(redis_cfg) = config.get("redis").and_then(Value::as_object) {
            let cfg = RedisConfig {
                host: redis_cfg
                    .get("host")
                    .and_then(Value::as_str)
                    .unwrap_or("localhost")
                    .to_string(),
                port: redis_cfg
                    .get("port")
                    .and_then(Value::as_u64)
                    .unwrap_or(6379) as u16,
                stream_name: redis_cfg
                    .get("stream_name")
                    .and_then(Value::as_str)
                    .unwrap_or("game_responses")
                    .to_string(),
                password: redis_cfg
                    .get("password")
                    .and_then(Value::as_str)
                    .map(str::to_string),
            };
            match RedisPublisher::new(cfg) {
                Ok(redis) => Some(redis),
                Err(err) => {
                    tracing::warn!(?err, "failed to initialize redis publisher; disabling redis");
                    None
                }
            }
        } else {
            None
        };

        let scheduler = Arc::new(Scheduler::new(
            max_parallel_updates.max(1),
            max_parallel_first_updates.max(1),
            update_interval,
        ));

        let game_finder_cfg = serde_json::from_value::<GameFinderConfig>(config.clone())
            .unwrap_or(GameFinderConfig {
                scenario_ids: Vec::new(),
                scan_interval: 30.0,
                enabled_scanning: true,
                max_parallel_recordings,
                max_guest_games_per_account: -1,
                listing_account: None,
            });
        let game_finder = GameFinder::new(game_finder_cfg, Arc::clone(&account_pool), registry.clone());

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

        observer.install_game_finder_callbacks();
        Ok(observer)
    }

    pub async fn run(self: Arc<Self>) -> bool {
        self.stop_flag.store(false, Ordering::SeqCst);

        self.resume_active().await;
        {
            let mut guard = self.game_finder.lock().expect("game finder mutex poisoned");
            if let Some(game_finder) = guard.as_mut() {
                game_finder.refresh_known_games_from_registry();
                if let Err(err) = game_finder.start_scanning() {
                    tracing::warn!(?err, "failed to start game finder scanning");
                }
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

        true
    }

    pub async fn stop(&self) {
        self.stop_flag.store(true, Ordering::SeqCst);
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
    }

    async fn resume_active(&self) {
        let active = self.registry.active();
        for (game_id, meta) in active {
            let scenario_id = meta
                .get("scenario_id")
                .and_then(Value::as_i64)
                .unwrap_or(-1) as i32;
            if scenario_id < 0 {
                continue;
            }

            let already_exists = self
                .observer_sessions
                .lock()
                .expect("observer sessions mutex poisoned")
                .contains_key(&game_id);
            if already_exists {
                continue;
            }

            if self
                .observer_sessions
                .lock()
                .expect("observer sessions mutex poisoned")
                .len()
                >= self.max_parallel_recordings.load(Ordering::SeqCst) as usize
            {
                break;
            }
            self.start_observation_session(game_id, scenario_id).await;
        }
    }

    async fn start_due_updates(self: &Arc<Self>) {
        let due_sessions = self.scheduler.get_due_updates();
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
            self.scheduler.decrement_active_coroutines();
            return;
        };

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
        self.scheduler.decrement_active_coroutines();
    }

    async fn handle_game_ended(
        &self,
        game_id: i32,
        session_arc: &Arc<tokio::sync::Mutex<ObservationSession>>,
    ) {
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
                if immediate {
                    self.scheduler.schedule_immediate_update(&mut session);
                } else {
                    self.scheduler.schedule_next_update(&mut session, false);
                }
            }
        }

        if needs_proxy_reset {
            let new_proxy = {
                let mut pool = self.account_pool.lock().await;
                if pool.reset_account_proxy(&username).await {
                    pool.get_account_proxy(&username)
                } else {
                    None
                }
            };
            if let Some(proxy) = new_proxy {
                self.reset_sessions_for_account(&username, proxy).await;
            }
        }

        if drop_session {
            self.registry.mark_failed(game_id, Some(&result.error_message));
            {
                let mut pool = self.account_pool.lock().await;
                pool.decrement_guest_join(&username);
            }
            self.observer_sessions
                .lock()
                .expect("observer sessions mutex poisoned")
                .remove(&game_id);
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
    }
}

fn str_at<'a>(config: &'a Value, key: &str) -> Option<&'a str> {
    config.get(key).and_then(Value::as_str)
}

fn i64_at(config: &Value, key: &str, default: i64) -> i64 {
    config.get(key).and_then(Value::as_i64).unwrap_or(default)
}

fn f64_at(config: &Value, key: &str, default: f64) -> f64 {
    config.get(key).and_then(Value::as_f64).unwrap_or(default)
}

fn parse_db_config(map: &serde_json::Map<String, Value>) -> Option<DbConfig> {
    Some(DbConfig {
        host: map.get("host")?.as_str()?.to_string(),
        port: map.get("port").and_then(Value::as_u64).unwrap_or(5432) as u16,
        database: map.get("database")?.as_str()?.to_string(),
        user: map.get("user")?.as_str()?.to_string(),
        password: map.get("password")?.as_str()?.to_string(),
    })
}

fn parse_s3_config(map: &serde_json::Map<String, Value>) -> Option<S3Config> {
    Some(S3Config {
        endpoint_url: map.get("endpoint_url")?.as_str()?.to_string(),
        access_key: map.get("access_key")?.as_str()?.to_string(),
        secret_key: map.get("secret_key")?.as_str()?.to_string(),
        bucket_name: map.get("bucket_name")?.as_str()?.to_string(),
        region: map
            .get("region")
            .and_then(Value::as_str)
            .unwrap_or("us-east-1")
            .to_string(),
    })
}
