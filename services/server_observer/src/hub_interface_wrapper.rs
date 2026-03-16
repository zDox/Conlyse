use pyo3::prelude::*;
use pyo3::types::PyDict;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::Path;
use std::sync::Once;
use thiserror::Error;

static PY_INIT: Once = Once::new();

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct AuthDetails {
    pub auth: String,
    pub rights: String,
    pub user_id: i64,
    pub auth_tstamp: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct HubGameProperties {
    pub game_id: i32,
    pub scenario_id: i32,
    pub open_slots: i32,
    pub name: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct GameApiData {
    pub game_server_address: String,
    pub client_version: i32,
    pub map_id: String,
    pub auth: AuthDetails,
    pub headers: HashMap<String, String>,
    pub cookies: HashMap<String, String>,
}

#[derive(Debug, Error)]
pub enum HubInterfaceError {
    #[error("python error: {0}")]
    Python(#[from] PyErr),
}

pub struct HubInterfaceWrapper {
    hub_interface: Py<PyAny>,
    authenticated: bool,
}

impl HubInterfaceWrapper {
    pub fn new(proxy_http: impl Into<String>, proxy_https: impl Into<String>) -> Result<Self, HubInterfaceError> {
        let proxy_http = proxy_http.into();
        let proxy_https = proxy_https.into();

        PY_INIT.call_once(Python::initialize);

        let hub_interface = Python::attach(|py| -> Result<Py<PyAny>, HubInterfaceError> {
            ensure_python_path(py)?;

            let module = py.import("conflict_interface.interface.hub_interface")?;
            let class = module.getattr("HubInterface")?;

            let proxy_dict = PyDict::new(py);
            if !proxy_http.is_empty() {
                proxy_dict.set_item("http", proxy_http)?;
            }
            if !proxy_https.is_empty() {
                proxy_dict.set_item("https", proxy_https)?;
            }

            let instance = class.call1((proxy_dict,))?;
            Ok(instance.unbind())
        })?;

        Ok(Self {
            hub_interface,
            authenticated: false,
        })
    }

    pub fn login(&mut self, username: &str, password: &str) -> Result<bool, HubInterfaceError> {
        Python::attach(|py| -> Result<bool, HubInterfaceError> {
            let hub = self.hub_interface.bind(py);
            hub.call_method1("login", (username, password))?;
            Ok(true)
        })?;
        self.authenticated = true;
        Ok(true)
    }

    #[allow(dead_code)]
    pub fn logout(&mut self) {
        self.authenticated = false;
    }

    pub fn is_authenticated(&self) -> bool {
        self.authenticated
    }

    #[allow(dead_code)]
    pub fn get_auth_details(&self) -> Result<AuthDetails, HubInterfaceError> {
        Python::attach(|py| -> Result<AuthDetails, HubInterfaceError> {
            let hub = self.hub_interface.bind(py);
            let auth_obj = hub.getattr("auth")?;
            if auth_obj.is_none() {
                return Ok(AuthDetails::default());
            }

            Ok(AuthDetails {
                auth: extract_attr_string(&auth_obj, "auth"),
                rights: extract_attr_string(&auth_obj, "rights"),
                user_id: extract_attr_i64(&auth_obj, "user_id"),
                auth_tstamp: extract_attr_i64_or_string(&auth_obj, "auth_tstamp"),
            })
        })
    }

    #[allow(dead_code)]
    pub fn get_my_games(&self) -> Result<Vec<HubGameProperties>, HubInterfaceError> {
        Python::attach(|py| -> Result<Vec<HubGameProperties>, HubInterfaceError> {
            let hub = self.hub_interface.bind(py);
            let value = hub.call_method0("get_my_games")?;
            parse_game_list(&value)
        })
    }

    pub fn get_global_games(&self) -> Result<Vec<HubGameProperties>, HubInterfaceError> {
        Python::attach(|py| -> Result<Vec<HubGameProperties>, HubInterfaceError> {
            let hub = self.hub_interface.bind(py);
            let value = hub.call_method0("get_global_games")?;
            parse_game_list(&value)
        })
    }

    pub fn join_game_as_guest(&self, game_id: i32) -> Result<GameApiData, HubInterfaceError> {
        Python::attach(|py| -> Result<GameApiData, HubInterfaceError> {
            let hub = self.hub_interface.bind(py);
            let game_api_module = py.import("conflict_interface.api.game_api")?;
            let game_api_class = game_api_module.getattr("GameApi")?;

            let api = hub.getattr("api")?;
            let session = api.getattr("session")?;
            let proxy = api.getattr("proxy")?;
            let auth_details = api.getattr("auth")?;

            let game_api = game_api_class.call1((session, auth_details, game_id, proxy))?;
            game_api.call_method0("load_game_site")?;

            let game_server_address = extract_attr_string(&game_api, "game_server_address");
            let client_version = extract_attr_i64(&game_api, "client_version") as i32;
            let map_id = extract_attr_string(&game_api, "map_id");

            let auth_obj = game_api.getattr("auth")?;
            let auth = if auth_obj.is_none() {
                AuthDetails::default()
            } else {
                AuthDetails {
                    auth: extract_attr_string(&auth_obj, "auth"),
                    rights: extract_attr_string(&auth_obj, "rights"),
                    user_id: extract_attr_i64(&auth_obj, "user_id"),
                    auth_tstamp: extract_attr_i64_or_string(&auth_obj, "auth_tstamp"),
                }
            };

            let ga_session = game_api.getattr("session")?;
            let headers = py_to_string_map(&ga_session.getattr("headers")?)?;
            let cookies = py_to_string_map(&ga_session.getattr("cookies")?)?;

            Ok(GameApiData {
                game_server_address,
                client_version: if client_version > 0 { client_version } else { 207 },
                map_id,
                auth,
                headers,
                cookies,
            })
        })
    }

    pub fn shutdown_python() {}
}

fn ensure_python_path(py: Python<'_>) -> Result<(), HubInterfaceError> {
    let sys = py.import("sys")?;
    let path = sys.getattr("path")?;

    let workspace_root_path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(|p| p.parent());

    let workspace_root = workspace_root_path
        .and_then(|p| p.to_str())
        .unwrap_or("/workspace")
        .to_string();

    let libs_conflict_interface = workspace_root_path
        .map(|p| p.join("libs").join("conflict_interface"));

    let libs_conflict_interface_str = libs_conflict_interface
        .as_ref()
        .and_then(|p| p.to_str())
        .unwrap_or("")
        .to_string();

    let contains_workspace = path
        .call_method1("__contains__", (workspace_root.clone(),))?
        .extract::<bool>()?;
    if !contains_workspace {
        path.call_method1("insert", (0usize, workspace_root))?;
    }

    if !libs_conflict_interface_str.is_empty() {
        let contains_libs = path
            .call_method1("__contains__", (libs_conflict_interface_str.clone(),))?
            .extract::<bool>()?;
        if !contains_libs {
            path.call_method1("insert", (0usize, libs_conflict_interface_str))?;
        }
    }

    Ok(())
}

fn parse_game_list(value: &Bound<'_, PyAny>) -> Result<Vec<HubGameProperties>, HubInterfaceError> {
    let mut games = Vec::new();
    for item in value.try_iter()? {
        let item = item?;
        games.push(HubGameProperties {
            game_id: extract_attr_i64(&item, "game_id") as i32,
            scenario_id: extract_attr_i64(&item, "scenario_id") as i32,
            open_slots: extract_attr_i64(&item, "open_slots") as i32,
            name: extract_attr_string(&item, "name"),
        });
    }
    Ok(games)
}

fn py_to_string_map(value: &Bound<'_, PyAny>) -> Result<HashMap<String, String>, HubInterfaceError> {
    if let Ok(dict) = value.cast::<PyDict>() {
        return dict_to_string_map(&dict);
    }

    if value.hasattr("get_dict")? {
        let cookie_dict = value.call_method0("get_dict")?;
        if let Ok(dict) = cookie_dict.cast::<PyDict>() {
            return dict_to_string_map(&dict);
        }
    }

    if value.hasattr("items")? {
        let items = value.call_method0("items")?;
        let mut out = HashMap::new();
        for pair in items.try_iter()? {
            let pair = pair?;
            let key = pair.get_item(0)?.extract::<String>()?;
            let val = py_value_to_string(&pair.get_item(1)?);
            out.insert(key, val);
        }
        return Ok(out);
    }

    Ok(HashMap::new())
}

fn dict_to_string_map(dict: &Bound<'_, PyDict>) -> Result<HashMap<String, String>, HubInterfaceError> {
    let mut out = HashMap::new();
    for (k, v) in dict.iter() {
        let key = k.extract::<String>()?;
        let value = py_value_to_string(&v);
        out.insert(key, value);
    }
    Ok(out)
}

fn py_value_to_string(v: &Bound<'_, PyAny>) -> String {
    if let Ok(s) = v.extract::<String>() {
        return s;
    }
    if let Ok(i) = v.extract::<i64>() {
        return i.to_string();
    }
    if let Ok(f) = v.extract::<f64>() {
        return f.to_string();
    }
    if let Ok(b) = v.extract::<bool>() {
        return b.to_string();
    }
    String::new()
}

fn extract_attr_string(obj: &Bound<'_, PyAny>, attr: &str) -> String {
    obj.getattr(attr)
        .ok()
        .and_then(|v| v.extract::<String>().ok())
        .unwrap_or_default()
}

fn extract_attr_i64(obj: &Bound<'_, PyAny>, attr: &str) -> i64 {
    obj.getattr(attr)
        .ok()
        .and_then(|v| v.extract::<i64>().ok())
        .unwrap_or_default()
}

fn extract_attr_i64_or_string(obj: &Bound<'_, PyAny>, attr: &str) -> i64 {
    if let Ok(v) = obj.getattr(attr) {
        if let Ok(num) = v.extract::<i64>() {
            return num;
        }
        if let Ok(s) = v.extract::<String>() {
            if let Ok(num) = s.parse::<i64>() {
                return num;
            }
        }
    }
    0
}
