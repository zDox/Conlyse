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
    metadata_file: PathBuf,
    recorder_log_file: PathBuf,
    state: Mutex<StorageState>,
}

impl RecordingStorage {
    pub fn new(
        output_path: impl AsRef<Path>,
        metadata_path: Option<impl AsRef<Path>>,
    ) -> Result<Self, RecordingStorageError> {
        let output_path = output_path.as_ref().to_path_buf();
        let metadata_path = metadata_path
            .as_ref()
            .map(|p| p.as_ref().to_path_buf())
            .unwrap_or_else(|| output_path.clone());

        fs::create_dir_all(&output_path)?;
        fs::create_dir_all(&metadata_path)?;

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

    pub fn update_resume_metadata(&self, resume: Value) {
        let mut state = self.state.lock().expect("recording storage mutex poisoned");
        state.metadata_cache["resume"] = resume.clone();
        state.resume_metadata = resume;

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
                "timestamp": now_epoch_seconds(),
                "datetime": now_epoch_seconds().to_string()
            }));
        }

        state.updates_since_last_flush += 1;
        if state.updates_since_last_flush >= METADATA_FLUSH_INTERVAL {
            state.updates_since_last_flush = 0;
            let metadata_snapshot = state.metadata_cache.clone();
            drop(state);
            let _ = save_metadata_file(&self.metadata_file, &metadata_snapshot);
        }
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

fn now_epoch_seconds() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or_default()
}
