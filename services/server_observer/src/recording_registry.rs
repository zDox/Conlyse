use serde::{Deserialize, Serialize};
use serde_json::{json, Value as JsonValue};
use std::collections::BTreeMap;
use std::fs;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};

#[derive(Debug, Clone, Serialize, Deserialize)]
struct RegistryState {
    #[serde(default)]
    recording: BTreeMap<String, JsonValue>,
    #[serde(default)]
    completed: BTreeMap<String, JsonValue>,
    #[serde(default)]
    failed: BTreeMap<String, JsonValue>,
}

#[derive(Clone)]
pub struct RecordingRegistry {
    path: PathBuf,
    state: Arc<Mutex<RegistryState>>,
}

impl RecordingRegistry {
    pub fn new<P: Into<PathBuf>>(path: P) -> Self {
        let path = path.into();
        let parent = path.parent().map(PathBuf::from);
        if let Some(parent) = parent {
            let _ = fs::create_dir_all(parent);
        }

        let state = if let Ok(contents) = fs::read_to_string(&path) {
            serde_json::from_str(&contents).unwrap_or_else(|_| RegistryState {
                recording: BTreeMap::new(),
                completed: BTreeMap::new(),
                failed: BTreeMap::new(),
            })
        } else {
            RegistryState {
                recording: BTreeMap::new(),
                completed: BTreeMap::new(),
                failed: BTreeMap::new(),
            }
        };

        Self {
            path,
            state: Arc::new(Mutex::new(state)),
        }
    }

    fn save(&self) {
        if let Ok(state) = self.state.lock() {
            if let Ok(serialized) = serde_json::to_string_pretty(&*state) {
                let _ = fs::write(&self.path, serialized);
            }
        }
    }

    pub fn mark_recording(&self, game_id: i32, scenario_id: i32, replay_path: Option<&str>) {
        let mut state = self.state.lock().unwrap();
        let key = game_id.to_string();
        let mut meta = json!({ "scenario_id": scenario_id });
        if let Some(path) = replay_path {
            meta["replay_path"] = json!(path);
        }
        state.recording.insert(key, meta);
        drop(state);
        self.save();
    }

    pub fn mark_completed(&self, game_id: i32) {
        let mut state = self.state.lock().unwrap();
        let key = game_id.to_string();
        let meta = state.recording.remove(&key).unwrap_or_else(|| json!({}));
        state.completed.insert(key, meta);
        drop(state);
        self.save();
    }

    pub fn mark_failed(&self, game_id: i32, reason: Option<&str>) {
        let mut state = self.state.lock().unwrap();
        let key = game_id.to_string();
        let mut meta = state.recording.remove(&key).unwrap_or_else(|| json!({}));
        if let Some(reason) = reason {
            meta["reason"] = json!(reason);
        }
        state.failed.insert(key, meta);
        drop(state);
        self.save();
    }

    pub fn active(&self) -> BTreeMap<i32, JsonValue> {
        let state = self.state.lock().unwrap();
        let mut result = BTreeMap::new();
        for (k, v) in &state.recording {
            if let Ok(id) = k.parse::<i32>() {
                result.insert(id, v.clone());
            }
        }
        result
    }

    pub fn get_scenario_id(&self, game_id: i32) -> Option<i32> {
        let state = self.state.lock().unwrap();
        let key = game_id.to_string();
        state
            .recording
            .get(&key)
            .and_then(|meta| meta.get("scenario_id"))
            .and_then(|v| v.as_i64())
            .map(|v| v as i32)
    }
}

