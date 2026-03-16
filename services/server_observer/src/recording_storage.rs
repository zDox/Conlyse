use serde_json::{json, Value};
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};
use thiserror::Error;

const METADATA_FLUSH_INTERVAL: i32 = 10;

#[derive(Debug, Error)]
pub enum RecordingStorageError {
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("json error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("invalid configuration: {0}")]
    InvalidConfig(String),
}

#[derive(Debug, Clone)]
struct StorageState {
    metadata_cache: Value,
    resume_metadata: Value,
    file_sequence: i32,
    updates_since_last_flush: i32,
}

pub struct RecordingStorage {
    output_path: PathBuf,
    metadata_path: PathBuf,
    long_term_storage_path: Option<PathBuf>,
    file_size_threshold: u64,
    responses_file: PathBuf,
    metadata_file: PathBuf,
    recorder_log_file: PathBuf,
    state: Mutex<StorageState>,
}

impl RecordingStorage {
    pub fn new(
        output_path: impl AsRef<Path>,
        metadata_path: Option<impl AsRef<Path>>,
        long_term_storage_path: Option<impl AsRef<Path>>,
        file_size_threshold: i64,
    ) -> Result<Self, RecordingStorageError> {
        let output_path = output_path.as_ref().to_path_buf();
        let metadata_path = metadata_path
            .as_ref()
            .map(|p| p.as_ref().to_path_buf())
            .unwrap_or_else(|| output_path.clone());
        let long_term_storage_path = long_term_storage_path.map(|p| p.as_ref().to_path_buf());

        let has_long_term = long_term_storage_path.is_some();
        let has_threshold = file_size_threshold > 0;
        if has_long_term != has_threshold {
            return Err(RecordingStorageError::InvalidConfig(
                "long_term_storage_path and file_size_threshold must be set together".to_string(),
            ));
        }
        if file_size_threshold < 0 {
            return Err(RecordingStorageError::InvalidConfig(
                "file_size_threshold must be >= 0".to_string(),
            ));
        }

        fs::create_dir_all(&output_path)?;
        fs::create_dir_all(&metadata_path)?;

        let responses_file = output_path.join("responses.jsonl.zst");
        let metadata_file = metadata_path.join("metadata.json");
        let recorder_log_file = metadata_path.join("recording.log");

        if !metadata_file.exists() {
            let metadata = json!({
                "version": "1.0",
                "created_at": now_epoch_seconds(),
                "updates": []
            });
            save_metadata_file(&metadata_file, &metadata)?;
        }

        let metadata_cache = load_metadata_file(&metadata_file)?;
        let resume_metadata = metadata_cache
            .get("resume")
            .cloned()
            .unwrap_or_else(|| Value::Null);
        let file_sequence = metadata_cache
            .get("file_sequence")
            .and_then(Value::as_i64)
            .unwrap_or(0) as i32;

        Ok(Self {
            output_path,
            metadata_path,
            long_term_storage_path,
            file_size_threshold: file_size_threshold as u64,
            responses_file,
            metadata_file,
            recorder_log_file,
            state: Mutex::new(StorageState {
                metadata_cache,
                resume_metadata,
                file_sequence,
                updates_since_last_flush: 0,
            }),
        })
    }

    /// Append a single zstd-compressed response frame to the on-disk log.
    ///
    /// The caller is responsible for the contents of `compressed_data`. For
    /// game server recordings, each frame currently has the inner layout:
    ///
    ///   [4 bytes BE metadata_len][metadata JSON bytes]
    ///   [4 bytes BE response_len][raw response JSON bytes]
    ///
    /// This entire blob is then zstd-compressed and stored here together with
    /// an outer timestamp/length envelope:
    ///
    ///   [8 bytes BE timestamp][4 bytes BE compressed_len][compressed_data...]
    pub fn save_response(&self, compressed_data: Vec<u8>) -> Result<(), RecordingStorageError> {
        let mut state = self.state.lock().expect("recording storage mutex poisoned");

        if self.should_rotate_file()? {
            self.rotate_to_long_term_storage(&mut state)?;
        }

        let timestamp = now_epoch_seconds() as u64;
        append_bytes_to_file(&self.responses_file, timestamp, &compressed_data)?;

        if !state
            .metadata_cache
            .get("updates")
            .is_some_and(Value::is_array)
        {
            state.metadata_cache["updates"] = Value::Array(Vec::new());
        }
        if let Some(updates) = state.metadata_cache.get_mut("updates").and_then(Value::as_array_mut)
        {
            updates.push(json!({
                "timestamp": timestamp,
                "datetime": now_epoch_seconds().to_string()
            }));
        }

        state.updates_since_last_flush += 1;
        if state.updates_since_last_flush >= METADATA_FLUSH_INTERVAL {
            state.updates_since_last_flush = 0;
            let metadata_snapshot = state.metadata_cache.clone();
            drop(state);
            save_metadata_file(&self.metadata_file, &metadata_snapshot)?;
        }

        Ok(())
    }

    pub fn update_resume_metadata(&self, resume: Value) {
        let mut state = self.state.lock().expect("recording storage mutex poisoned");
        state.metadata_cache["resume"] = resume.clone();
        state.resume_metadata = resume;
    }

    pub fn get_resume_metadata(&self) -> Value {
        self.state
            .lock()
            .expect("recording storage mutex poisoned")
            .resume_metadata
            .clone()
    }

    pub fn has_resume_metadata(&self) -> bool {
        self.state
            .lock()
            .expect("recording storage mutex poisoned")
            .resume_metadata
            .get("auth")
            .is_some()
    }

    pub fn flush_metadata(&self) -> Result<(), RecordingStorageError> {
        let metadata = self
            .state
            .lock()
            .expect("recording storage mutex poisoned")
            .metadata_cache
            .clone();
        save_metadata_file(&self.metadata_file, &metadata)
    }

    pub fn setup_logging(&self) -> Result<(), RecordingStorageError> {
        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.recorder_log_file)?;
        writeln!(file, "=== Logging started at {} ===", now_epoch_seconds())?;
        Ok(())
    }

    pub fn teardown_logging(&self) -> Result<(), RecordingStorageError> {
        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.recorder_log_file)?;
        writeln!(file, "=== Logging ended at {} ===", now_epoch_seconds())?;
        Ok(())
    }

    fn should_rotate_file(&self) -> Result<bool, RecordingStorageError> {
        if self.long_term_storage_path.is_none() || self.file_size_threshold == 0 {
            return Ok(false);
        }
        if !self.responses_file.exists() {
            return Ok(false);
        }
        let size = fs::metadata(&self.responses_file)?.len();
        Ok(size >= self.file_size_threshold)
    }

    fn rotate_to_long_term_storage(
        &self,
        state: &mut StorageState,
    ) -> Result<(), RecordingStorageError> {
        let Some(long_term_base) = &self.long_term_storage_path else {
            return Ok(());
        };
        if !self.responses_file.exists() {
            return Ok(());
        }

        let file_size = fs::metadata(&self.responses_file)?.len();
        let game_dir_name = self
            .output_path
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("game");
        let lts_game_dir = long_term_base.join(game_dir_name);
        fs::create_dir_all(&lts_game_dir)?;

        state.file_sequence += 1;
        state.metadata_cache["file_sequence"] = json!(state.file_sequence);

        let destination = lts_game_dir.join(format!("responses_{:04}.jsonl.zst", state.file_sequence));
        match fs::rename(&self.responses_file, &destination) {
            Ok(_) => {}
            Err(_) => {
                fs::copy(&self.responses_file, &destination)?;
                fs::remove_file(&self.responses_file)?;
            }
        }

        if !state
            .metadata_cache
            .get("rotations")
            .is_some_and(Value::is_array)
        {
            state.metadata_cache["rotations"] = Value::Array(Vec::new());
        }

        if let Some(rotations) = state
            .metadata_cache
            .get_mut("rotations")
            .and_then(Value::as_array_mut)
        {
            rotations.push(json!({
                "sequence": state.file_sequence,
                "timestamp": now_epoch_seconds(),
                "datetime": now_epoch_seconds().to_string(),
                "destination": destination.to_string_lossy().to_string(),
                "size_bytes": file_size
            }));
        }

        Ok(())
    }

    #[allow(dead_code)]
    pub fn metadata_path(&self) -> &Path {
        &self.metadata_path
    }
}

fn load_metadata_file(path: &Path) -> Result<Value, RecordingStorageError> {
    if !path.exists() {
        return Ok(json!({
            "version": "1.0",
            "updates": []
        }));
    }

    let mut contents = String::new();
    File::open(path)?.read_to_string(&mut contents)?;
    if contents.trim().is_empty() {
        return Ok(json!({
            "version": "1.0",
            "updates": []
        }));
    }

    Ok(serde_json::from_str(&contents)?)
}

fn save_metadata_file(path: &Path, value: &Value) -> Result<(), RecordingStorageError> {
    let mut file = File::create(path)?;
    file.write_all(serde_json::to_string_pretty(value)?.as_bytes())?;
    file.flush()?;
    Ok(())
}

fn append_bytes_to_file(
    path: &Path,
    timestamp: u64,
    data: &[u8],
) -> Result<(), RecordingStorageError> {
    let mut file = OpenOptions::new().create(true).append(true).open(path)?;

    let ts = timestamp.to_be_bytes();
    file.write_all(&ts)?;

    let length = (data.len() as u32).to_be_bytes();
    file.write_all(&length)?;

    file.write_all(data)?;
    file.flush()?;
    Ok(())
}

fn now_epoch_seconds() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or_default()
}
