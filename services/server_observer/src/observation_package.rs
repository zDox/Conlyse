use crate::account_pool::ProxyConfig;
use crate::hub_interface_wrapper::AuthDetails;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ObservationPackage {
    pub game_id: i32,
    pub headers: HashMap<String, String>,
    pub cookies: HashMap<String, String>,
    pub proxy: ProxyConfig,
    pub auth: AuthDetails,
    pub client_version: i32,
    pub game_server_address: String,
    pub time_stamps: HashMap<String, String>,
    pub state_ids: HashMap<String, String>,
}

impl ObservationPackage {
    pub fn to_json(&self) -> Value {
        serde_json::to_value(self).unwrap_or(Value::Null)
    }

    pub fn from_json(value: Value) -> Self {
        serde_json::from_value(value).unwrap_or_default()
    }
}
