use crate::account_pool::ProxyConfig;
use crate::hub_interface_wrapper::AuthDetails;
use crate::observation_package::ObservationPackage;
use regex::Regex;
use reqwest::header::{COOKIE, HeaderName, HeaderValue};
use reqwest::{Client, Proxy};
use serde_json::{json, Value};
use sha1::{Digest, Sha1};
use std::collections::HashMap;
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use thiserror::Error;

#[derive(Debug, Clone)]
pub struct HttpResponse {
    pub timeout: bool,
    pub status_code: u16,
    pub data: String,
    pub error_message: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GameServerError {
    Success,
    HttpError,
    ParseError,
    AuthError,
    ServerSwitch,
    ClientVersionMismatch,
    NetworkError,
    UnknownError,
}

#[derive(Debug, Clone)]
pub struct GameServerResult {
    pub error_code: GameServerError,
    pub error_message: String,
    pub raw_response: String,
    pub game_ended: bool,
    pub map_id: String,
}

impl GameServerResult {
    pub fn success(&self) -> bool {
        self.error_code == GameServerError::Success
    }
}

#[derive(Debug, Error)]
pub enum ObservationApiError {
    #[error("http client error: {0}")]
    HttpClient(String),
    #[error("request error: {0}")]
    Request(#[from] reqwest::Error),
    #[error("json parse error: {0}")]
    Json(#[from] serde_json::Error),
}

pub struct ObservationApi {
    game_id: i32,
    player_id: i32,
    auth: AuthDetails,
    request_id: i32,
    client_version: i32,
    game_server_address: String,
    headers: HashMap<String, String>,
    cookies: HashMap<String, String>,
    proxy: ProxyConfig,
    client: Client,
}

impl ObservationApi {
    pub fn new(
        headers: HashMap<String, String>,
        cookies: HashMap<String, String>,
        proxy: ProxyConfig,
        auth_details: AuthDetails,
        game_id: i32,
        game_server_address: String,
        client_version: i32,
    ) -> Result<Self, ObservationApiError> {
        let client = build_http_client(&proxy)?;
        Ok(Self {
            game_id,
            player_id: 0,
            auth: auth_details,
            request_id: 0,
            client_version,
            game_server_address,
            headers,
            cookies,
            proxy,
            client,
        })
    }

    pub async fn request_game_state_async(
        &mut self,
        state_ids: &mut HashMap<String, String>,
        time_stamps: &mut HashMap<String, String>,
    ) -> HttpResponse {
        let include_state_meta = !state_ids.is_empty() && !time_stamps.is_empty();

        let mut action = json!({
            "@c": "ultshared.action.UltUpdateGameStateAction",
            "stateType": 0,
            "stateID": "0",
            "addStateIDsOnSent": include_state_meta,
            "actions": ["java.util.LinkedList", []]
        });

        if include_state_meta {
            action["stateIDs"] = json!(state_ids);
            action["stateIDs"]["@c"] = json!("java.util.HashMap");
            action["tstamps"] = json!(time_stamps);
            action["tstamps"]["@c"] = json!("java.util.HashMap");
        }

        let hash_input = format!("undefined{}", current_time_ms());
        let mut hasher = Sha1::new();
        hasher.update(hash_input.as_bytes());
        let hash_hex = format!("{:x}", hasher.finalize());

        let mut payload = json!({
            "requestID": self.request_id,
            "language": "en",
            "version": self.client_version,
            "tstamp": self.auth.auth_tstamp.to_string(),
            "client": "con-client",
            "hash": hash_hex,
            "sessionTstamp": 0,
            "gameID": self.game_id.to_string(),
            "playerID": self.player_id,
            "siteUserID": self.auth.user_id.to_string(),
            "adminLevel": Value::Null,
            "rights": self.auth.rights,
            "userAuth": self.auth.auth,
            "lastCallDuration": 0
        });
        self.request_id += 1;

        if let Some(map) = action.as_object() {
            for (k, v) in map {
                payload[k] = v.clone();
            }
        }

        let mut req = self
            .client
            .post(&self.game_server_address)
            .header("Accept", "text/plain, */*; q=0.01")
            .header("Accept-Encoding", "gzip, deflate, br")
            .header("Content-Type", "application/json");

        for (k, v) in &self.headers {
            if let (Ok(name), Ok(value)) = (
                HeaderName::from_bytes(k.as_bytes()),
                HeaderValue::from_str(v),
            ) {
                req = req.header(name, value);
            }
        }

        if !self.cookies.is_empty() {
            let cookie_header = self
                .cookies
                .iter()
                .map(|(k, v)| format!("{k}={v}"))
                .collect::<Vec<_>>()
                .join("; ");
            req = req.header(COOKIE, cookie_header);
        }

        let response = req.body(payload.to_string()).send().await;
        let response = match response {
            Ok(resp) => resp,
            Err(err) => {
                return HttpResponse {
                    timeout: err.is_timeout(),
                    status_code: 0,
                    data: String::new(),
                    error_message: err.to_string(),
                };
            }
        };

        let status = response.status().as_u16();
        match response.text().await {
            Ok(data) => HttpResponse {
                timeout: false,
                status_code: status,
                data,
                error_message: String::new(),
            },
            Err(err) => HttpResponse {
                timeout: err.is_timeout(),
                status_code: status,
                data: String::new(),
                error_message: err.to_string(),
            },
        }
    }

    pub fn parse_and_validate_response(
        &mut self,
        response: HttpResponse,
        state_ids: &mut HashMap<String, String>,
        time_stamps: &mut HashMap<String, String>,
    ) -> GameServerResult {
        if response.timeout {
            return GameServerResult {
                error_code: GameServerError::NetworkError,
                error_message: if response.error_message.is_empty() {
                    "Request timed out".to_string()
                } else {
                    response.error_message
                },
                raw_response: String::new(),
                game_ended: false,
                map_id: String::new(),
            };
        }

        if response.status_code != 200 {
            let mut message = format!("HTTP status: {}", response.status_code);
            if !response.error_message.is_empty() {
                message.push_str(" - ");
                message.push_str(&response.error_message);
            }
            return GameServerResult {
                error_code: GameServerError::HttpError,
                error_message: message,
                raw_response: String::new(),
                game_ended: false,
                map_id: String::new(),
            };
        }

        let raw = response.data;
        let game_state: Value = match serde_json::from_str(&raw) {
            Ok(v) => v,
            Err(err) => {
                return GameServerResult {
                    error_code: GameServerError::ParseError,
                    error_message: format!("JSON parse error: {err}"),
                    raw_response: raw,
                    game_ended: false,
                    map_id: String::new(),
                };
            }
        };

        let Some(result_obj) = game_state.get("result").and_then(Value::as_object) else {
            return GameServerResult {
                error_code: GameServerError::UnknownError,
                error_message: "No result object in response".to_string(),
                raw_response: raw,
                game_ended: false,
                map_id: String::new(),
            };
        };

        let Some(result_class) = result_obj.get("@c").and_then(Value::as_str) else {
            return GameServerResult {
                error_code: GameServerError::UnknownError,
                error_message: "No @c field in result".to_string(),
                raw_response: raw,
                game_ended: false,
                map_id: String::new(),
            };
        };

        if result_class == "ultshared.UltAuthentificationException" {
            let mut error_message = format!("Authentication failed: {result_class}");
            if let Some(msg) = result_obj.get("message").and_then(Value::as_str) {
                error_message.push_str(" - ");
                error_message.push_str(msg);
            }
            return GameServerResult {
                error_code: GameServerError::AuthError,
                error_message,
                raw_response: raw,
                game_ended: false,
                map_id: String::new(),
            };
        }

        if result_class == "ultshared.rpc.UltSwitchServerException" {
            let mut error_message = "Server switch required".to_string();
            if let Some(new_server) = result_obj.get("newHostName").and_then(Value::as_str) {
                error_message.push_str(": ");
                error_message.push_str(new_server);
                self.update_server_address(format!("https://{new_server}"));
                if let Ok(client) = build_http_client(&self.proxy) {
                    self.client = client;
                }
            }

            return GameServerResult {
                error_code: GameServerError::ServerSwitch,
                error_message,
                raw_response: raw,
                game_ended: false,
                map_id: String::new(),
            };
        }

        if result_class == "ultshared.UltClientVersionMismatchException" {
            let mut error_message = "Client version mismatch".to_string();
            if let Some(message) = result_obj.get("detailMessage").and_then(Value::as_str) {
                let old_re = Regex::new(r"con-client: #(\d+)").ok();
                let new_re = Regex::new(r"con-client_live\.txt: #(\d+)").ok();

                let old_version = old_re
                    .as_ref()
                    .and_then(|re| re.captures(message))
                    .and_then(|c| c.get(1))
                    .and_then(|m| m.as_str().parse::<i32>().ok());
                let new_version = new_re
                    .as_ref()
                    .and_then(|re| re.captures(message))
                    .and_then(|c| c.get(1))
                    .and_then(|m| m.as_str().parse::<i32>().ok());

                if let (Some(old), Some(new)) = (old_version, new_version) {
                    error_message = format!(
                        "Client version mismatch: old version {old}, new version {new}"
                    );
                    self.client_version = new;
                } else {
                    error_message = format!("Client version mismatch: {message}");
                }
            }

            return GameServerResult {
                error_code: GameServerError::ClientVersionMismatch,
                error_message,
                raw_response: raw,
                game_ended: false,
                map_id: String::new(),
            };
        }

        if result_class != "ultshared.UltAutoGameState" && result_class != "ultshared.UltGameState" {
            let mut message = format!("Unknown error class: {result_class}");
            if let Some(m) = result_obj.get("message").and_then(Value::as_str) {
                message.push_str(" - ");
                message.push_str(m);
            }
            return GameServerResult {
                error_code: GameServerError::UnknownError,
                error_message: message,
                raw_response: raw,
                game_ended: false,
                map_id: String::new(),
            };
        }

        let Some(states) = result_obj.get("states").and_then(Value::as_object) else {
            return GameServerResult {
                error_code: GameServerError::UnknownError,
                error_message: "Game state extraction failed".to_string(),
                raw_response: raw,
                game_ended: false,
                map_id: String::new(),
            };
        };

        let mut game_ended = false;
        let mut map_id = String::new();

        for (key, state_value) in states {
            let Some(state) = state_value.as_object() else {
                continue;
            };

            if let Some(state_id) = state.get("stateID").and_then(value_to_string) {
                state_ids.insert(key.clone(), state_id);
            }
            if let Some(ts) = state.get("timeStamp").and_then(value_to_string) {
                time_stamps.insert(key.clone(), ts);
            }

            if key == "3" {
                if let Some(id) = state
                    .get("map")
                    .and_then(Value::as_object)
                    .and_then(|m| m.get("mapID"))
                    .and_then(value_to_string)
                {
                    map_id = id;
                }
            } else if key == "12" {
                if state
                    .get("gameEnded")
                    .and_then(Value::as_bool)
                    .unwrap_or(false)
                {
                    game_ended = true;
                }
            }
        }

        if state_ids.is_empty() || time_stamps.is_empty() {
            return GameServerResult {
                error_code: GameServerError::UnknownError,
                error_message: "Game state extraction failed".to_string(),
                raw_response: raw,
                game_ended: false,
                map_id: String::new(),
            };
        }

        GameServerResult {
            error_code: GameServerError::Success,
            error_message: String::new(),
            raw_response: raw,
            game_ended,
            map_id,
        }
    }

    pub async fn get_static_map_data(&self, map_id: &str) -> Result<Value, ObservationApiError> {
        let url = format!("https://static1.bytro.com/fileadmin/mapjson/live/{map_id}.json");
        let mut req = self
            .client
            .get(url)
            .header("Accept", "application/json, text/javascript, */*; q=0.01");

        if !self.cookies.is_empty() {
            let cookie_header = self
                .cookies
                .iter()
                .map(|(k, v)| format!("{k}={v}"))
                .collect::<Vec<_>>()
                .join("; ");
            req = req.header(COOKIE, cookie_header);
        }

        let response = req.send().await?;
        if !response.status().is_success() {
            return Err(ObservationApiError::HttpClient(format!(
                "failed static map fetch: status {}",
                response.status()
            )));
        }

        Ok(response.json::<Value>().await?)
    }

    pub fn update_package(&self, pkg: &mut ObservationPackage) {
        pkg.client_version = self.client_version;
        pkg.game_server_address = self.game_server_address.clone();
        pkg.headers = self.headers.clone();
        pkg.cookies = self.cookies.clone();
        pkg.auth = self.auth.clone();
    }

    pub fn update_server_address(&mut self, url: String) {
        self.game_server_address = url;
    }

    pub fn set_proxy(&mut self, proxy: ProxyConfig) -> Result<(), ObservationApiError> {
        self.proxy = proxy;
        self.client = build_http_client(&self.proxy)?;
        Ok(())
    }
}

fn build_http_client(proxy: &ProxyConfig) -> Result<Client, ObservationApiError> {
    let mut builder = Client::builder().timeout(Duration::from_secs(60));
    if proxy.enabled && !proxy.host.is_empty() && proxy.port > 0 {
        let proxy_url = proxy.to_url();
        let req_proxy = Proxy::all(proxy_url)
            .map_err(|err| ObservationApiError::HttpClient(err.to_string()))?;
        builder = builder.proxy(req_proxy);
    }
    builder
        .build()
        .map_err(|err| ObservationApiError::HttpClient(err.to_string()))
}

fn current_time_ms() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis() as i64)
        .unwrap_or_default()
}

fn value_to_string(value: &Value) -> Option<String> {
    match value {
        Value::String(s) => Some(s.clone()),
        Value::Number(n) => Some(n.to_string()),
        Value::Bool(b) => Some(b.to_string()),
        _ => None,
    }
}
