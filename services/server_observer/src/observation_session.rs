use crate::account_pool::{Account, ProxyConfig};
use crate::hub_interface_wrapper::HubInterfaceWrapper;
use crate::observation_api::{GameServerError, GameServerResult, ObservationApi, ObservationApiError};
use crate::observation_package::ObservationPackage;
use crate::recording_storage::{RecordingStorage, RecordingStorageError};
use crate::redis_publisher::RedisPublisher;
use crate::response_metadata::ResponseMetadata;
use crate::static_map_cache::{StaticMapCache, StaticMapError};
use serde_json;
use std::io;
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use thiserror::Error;
use zstd::stream::encode_all;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ObservationError {
    Success = 0,
    GameEnded,
    AuthFailed,
    ServerError,
    NetworkError,
    PackageCreationFailed,
    UnknownError,
}

#[derive(Debug, Clone)]
pub struct ObservationResult {
    pub error_code: ObservationError,
    pub error_message: String,
    pub game_ended: bool,
}

impl ObservationResult {
    pub fn make_success(game_ended: bool) -> Self {
        Self {
            error_code: ObservationError::Success,
            error_message: String::new(),
            game_ended,
        }
    }

    pub fn make_game_ended() -> Self {
        Self {
            error_code: ObservationError::GameEnded,
            error_message: "Game has ended".to_string(),
            game_ended: true,
        }
    }

    pub fn make_auth_failed(game_ended: bool, msg: impl Into<String>) -> Self {
        Self {
            error_code: ObservationError::AuthFailed,
            error_message: msg.into(),
            game_ended,
        }
    }

    pub fn make_server_error(msg: impl Into<String>) -> Self {
        Self {
            error_code: ObservationError::ServerError,
            error_message: msg.into(),
            game_ended: false,
        }
    }

    pub fn make_network_error(game_ended: bool, msg: impl Into<String>) -> Self {
        Self {
            error_code: ObservationError::NetworkError,
            error_message: msg.into(),
            game_ended,
        }
    }

    pub fn make_package_failed(msg: impl Into<String>) -> Self {
        Self {
            error_code: ObservationError::PackageCreationFailed,
            error_message: msg.into(),
            game_ended: false,
        }
    }

    pub fn make_unknown_error(msg: impl Into<String>) -> Self {
        Self {
            error_code: ObservationError::UnknownError,
            error_message: msg.into(),
            game_ended: false,
        }
    }
}

#[derive(Debug, Error)]
pub enum ObservationSessionError {
    #[error("hub interface error: {0}")]
    Hub(#[from] crate::hub_interface_wrapper::HubInterfaceError),
    #[error("observation api error: {0}")]
    Api(#[from] ObservationApiError),
    #[error("recording storage error: {0}")]
    Storage(#[from] RecordingStorageError),
    #[error("static map error: {0}")]
    StaticMap(#[from] StaticMapError),
    #[error("compression error: {0}")]
    Compression(#[from] io::Error),
    #[error("json error: {0}")]
    Json(#[from] serde_json::Error),
}

pub struct ObservationSession {
    pub game_id: i32,
    pub account: Account,
    pub next_update_at: SystemTime,
    pub update_sequence_number: i64,

    map_cache: Option<StaticMapCache>,
    api: Option<ObservationApi>,
    storage_path: String,
    metadata_path: String,
    long_term_storage_path: String,
    file_size_threshold: i64,
    package: ObservationPackage,
    storage: Option<RecordingStorage>,
    attempt: i32,
    redis_publisher: Option<RedisPublisher>,
    hub_interface: Option<HubInterfaceWrapper>,
}

impl ObservationSession {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        game_id: i32,
        account: Account,
        map_cache: Option<StaticMapCache>,
        storage_path: String,
        metadata_path: String,
        long_term_storage_path: String,
        file_size_threshold: i64,
        redis_publisher: Option<RedisPublisher>,
    ) -> Self {
        Self {
            game_id,
            account,
            next_update_at: SystemTime::now(),
            update_sequence_number: 0,
            map_cache,
            api: None,
            storage_path,
            metadata_path,
            long_term_storage_path,
            file_size_threshold,
            package: ObservationPackage::default(),
            storage: None,
            attempt: 1,
            redis_publisher,
            hub_interface: None,
        }
    }

    pub fn set_proxy(&mut self, proxy_config: ProxyConfig) {
        self.account.proxy_config = proxy_config.clone();
        self.package.proxy = proxy_config.clone();
        if let Some(api) = &mut self.api {
            if let Err(err) = api.set_proxy(proxy_config) {
                tracing::warn!(?err, game_id = self.game_id, "failed to apply new proxy to api");
            }
        }
    }

    pub fn increment_attempt(&mut self) {
        self.attempt += 1;
    }

    pub fn reset_attempt(&mut self) {
        self.attempt = 1;
    }

    pub fn get_attempt(&self) -> i32 {
        self.attempt
    }

    fn ensure_storage(&mut self) -> Result<&mut RecordingStorage, ObservationSessionError> {
        if self.storage.is_none() {
            let metadata = if self.metadata_path.is_empty() {
                None
            } else {
                Some(self.metadata_path.as_str())
            };
            let long_term = if self.long_term_storage_path.is_empty() {
                None
            } else {
                Some(self.long_term_storage_path.as_str())
            };
            self.storage = Some(RecordingStorage::new(
                self.storage_path.as_str(),
                metadata,
                long_term,
                self.file_size_threshold,
            )?);
        }
        Ok(self.storage.as_mut().expect("storage must be initialized"))
    }

    fn ensure_observation_package(&mut self) -> bool {
        if self.package.game_id != 0 {
            return true;
        }

        let resume_metadata = match self.ensure_storage() {
            Ok(storage) if storage.has_resume_metadata() => storage.get_resume_metadata(),
            Ok(_) => serde_json::Value::Null,
            Err(err) => {
                tracing::warn!(?err, game_id = self.game_id, "failed to load resume metadata");
                serde_json::Value::Null
            }
        };
        if resume_metadata.is_object() {
            self.package = ObservationPackage::from_json(resume_metadata);
            match ObservationApi::new(
                self.package.headers.clone(),
                self.package.cookies.clone(),
                self.account.proxy_config.clone(),
                self.package.auth.clone(),
                self.game_id,
                self.package.game_server_address.clone(),
                self.package.client_version,
            ) {
                Ok(api) => {
                    self.api = Some(api);
                    return true;
                }
                Err(err) => {
                    tracing::warn!(
                        ?err,
                        game_id = self.game_id,
                        "failed restoring api from resume metadata"
                    );
                }
            }
        }

        self.package = self.create_observation_package();
        self.package.game_id != 0
    }

    fn create_observation_package(&mut self) -> ObservationPackage {
        let proxy_url = if self.account.proxy_config.enabled {
            self.account.proxy_config.to_url()
        } else {
            String::new()
        };

        if self.hub_interface.is_none() {
            match HubInterfaceWrapper::new(proxy_url.clone(), proxy_url) {
                Ok(wrapper) => self.hub_interface = Some(wrapper),
                Err(err) => {
                    tracing::error!(?err, game_id = self.game_id, "failed creating HubInterfaceWrapper");
                    return ObservationPackage::default();
                }
            }
        }

        let Some(hub_itf) = &mut self.hub_interface else {
            return ObservationPackage::default();
        };

        if !hub_itf.is_authenticated() {
            match hub_itf.login(&self.account.username, &self.account.password) {
                Ok(true) => {}
                Ok(false) => {
                    tracing::error!(
                        game_id = self.game_id,
                        account = self.account.username,
                        "hub login returned false"
                    );
                    return ObservationPackage::default();
                }
                Err(err) => {
                    tracing::error!(?err, game_id = self.game_id, "hub login failed");
                    return ObservationPackage::default();
                }
            }
        }

        let game_data = match hub_itf.join_game_as_guest(self.game_id) {
            Ok(data) => data,
            Err(err) => {
                tracing::error!(?err, game_id = self.game_id, "failed to join game as guest");
                return ObservationPackage::default();
            }
        };

        let pkg = ObservationPackage {
            game_id: self.game_id,
            headers: game_data.headers,
            cookies: game_data.cookies,
            proxy: self.account.proxy_config.clone(),
            auth: game_data.auth,
            client_version: game_data.client_version,
            game_server_address: game_data.game_server_address,
            time_stamps: Default::default(),
            state_ids: Default::default(),
        };

        match ObservationApi::new(
            pkg.headers.clone(),
            pkg.cookies.clone(),
            self.account.proxy_config.clone(),
            pkg.auth.clone(),
            self.game_id,
            pkg.game_server_address.clone(),
            pkg.client_version,
        ) {
            Ok(api) => {
                self.api = Some(api);
                pkg
            }
            Err(err) => {
                tracing::error!(?err, game_id = self.game_id, "failed creating ObservationApi");
                ObservationPackage::default()
            }
        }
    }

    pub fn reset_package(&mut self) {
        if let Ok(storage) = self.ensure_storage() {
            let _ = storage.flush_metadata();
        }
        self.hub_interface = None;
        self.package = self.create_observation_package();
    }

    async fn ensure_static_map_data(&mut self, map_id: &str) -> bool {
        let Some(map_cache) = &self.map_cache else {
            return false;
        };
        if map_cache.is_cached(map_id) {
            return true;
        }

        let Some(api) = &self.api else {
            return false;
        };
        match api.get_static_map_data(map_id).await {
            Ok(static_map_data) => map_cache.save(map_id, &static_map_data).await.is_ok(),
            Err(err) => {
                tracing::warn!(?err, game_id = self.game_id, map_id = map_id, "failed static map fetch");
                false
            }
        }
    }

    fn handle_game_server_error(&mut self, result: &GameServerResult) -> ObservationResult {
        match result.error_code {
            GameServerError::AuthError => {
                self.reset_package();
                ObservationResult::make_auth_failed(false, result.error_message.clone())
            }
            GameServerError::HttpError => {
                self.reset_package();
                ObservationResult::make_server_error(result.error_message.clone())
            }
            GameServerError::NetworkError => {
                self.reset_package();
                ObservationResult::make_network_error(false, result.error_message.clone())
            }
            GameServerError::ClientVersionMismatch
            | GameServerError::ServerSwitch
            | GameServerError::ParseError => {
                ObservationResult::make_unknown_error(result.error_message.clone())
            }
            GameServerError::UnknownError | GameServerError::Success => {
                self.reset_package();
                ObservationResult::make_unknown_error(result.error_message.clone())
            }
        }
    }

    fn process_successful_response(
        &mut self,
        result: &GameServerResult,
    ) -> Result<(), ObservationSessionError> {
        if let Some(api) = &self.api {
            api.update_package(&mut self.package);
        }

        let compressed_response = encode_all(result.raw_response.as_bytes(), 3)?;
        let timestamp_ms = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or(Duration::from_secs(0))
            .as_millis() as i64;

        let metadata = ResponseMetadata {
            timestamp: timestamp_ms,
            game_id: self.game_id as i64,
            // Guest observer sessions currently use player_id = 0; this is kept for
            // compatibility while allowing future expansion.
            player_id: 0,
            client_version: self.package.client_version as i64,
            map_id: result.map_id.clone(),
        };

        if let Some(redis) = &self.redis_publisher {
            if let Err(err) = redis.publish_compressed_response(
                &metadata,
                &compressed_response,
            ) {
                tracing::warn!(?err, game_id = self.game_id, "failed redis publish");
            }
        }

        // For on-disk recording, store metadata and raw JSON response together in a
        // single zstd-compressed frame with the following layout:
        //   [4 bytes BE metadata_len][metadata JSON bytes]
        //   [4 bytes BE response_len][raw response JSON bytes]
        let metadata_json = serde_json::to_vec(&metadata)?;
        let response_bytes = result.raw_response.as_bytes();

        let meta_len = metadata_json.len() as u32;
        let resp_len = response_bytes.len() as u32;

        let mut combined = Vec::with_capacity(
            4 + metadata_json.len() + 4 + response_bytes.len(),
        );
        combined.extend_from_slice(&meta_len.to_be_bytes());
        combined.extend_from_slice(&metadata_json);
        combined.extend_from_slice(&resp_len.to_be_bytes());
        combined.extend_from_slice(response_bytes);

        let compressed_recording = encode_all(&combined[..], 3)?;

        let pkg_json = self.package.to_json();
        let storage = self.ensure_storage()?;
        storage.update_resume_metadata(pkg_json);
        storage.save_response(compressed_recording)?;
        Ok(())
    }

    pub async fn run_update_async(&mut self) -> ObservationResult {
        tracing::info!(game_id = self.game_id, attempt = self.attempt, "starting update");

        if let Ok(storage) = self.ensure_storage() {
            let _ = storage.setup_logging();
        }

        let outcome = async {
            if !self.ensure_observation_package() {
                return ObservationResult::make_package_failed("Failed to create observation package");
            }

            let Some(api) = &mut self.api else {
                return ObservationResult::make_package_failed("Observation API not initialized");
            };

            let response = api
                .request_game_state_async(&mut self.package.state_ids, &mut self.package.time_stamps)
                .await;
            let result = api.parse_and_validate_response(
                response,
                &mut self.package.state_ids,
                &mut self.package.time_stamps,
            );

            if !result.success() {
                return self.handle_game_server_error(&result);
            }

            if !result.map_id.is_empty() {
                let _ = self.ensure_static_map_data(&result.map_id).await;
            }

            if let Err(err) = self.process_successful_response(&result) {
                return ObservationResult::make_unknown_error(err.to_string());
            }

            if result.game_ended {
                ObservationResult::make_game_ended()
            } else {
                ObservationResult::make_success(false)
            }
        }
        .await;

        if let Ok(storage) = self.ensure_storage() {
            let _ = storage.teardown_logging();
        }

        outcome
    }
}

impl Drop for ObservationSession {
    fn drop(&mut self) {
        if let Some(storage) = &self.storage {
            let _ = storage.flush_metadata();
            let _ = storage.teardown_logging();
        }
    }
}
