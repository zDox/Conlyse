use crate::connectivity_check;
use crate::metrics::{record_proxy_replacement};
use reqwest::header::{HeaderMap, HeaderValue, AUTHORIZATION};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::fs::File;
use std::io::BufReader;
use std::path::Path;
use std::sync::Arc;
use thiserror::Error;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Proxy {
    pub id: String,
    pub username: String,
    pub password: String,
    #[serde(rename = "proxy_address")]
    pub address: String,
    pub port: u16,
    pub valid: bool,
    pub country_code: String,
}

impl Proxy {
    pub fn proxy_url(&self) -> String {
        format!(
            "socks5://{}:{}@{}:{}",
            self.username, self.password, self.address, self.port
        )
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ProxyConfig {
    pub proxy_id: String,
    pub enabled: bool,
    pub host: String,
    pub port: u16,
    pub username: String,
    pub password: String,
}

impl ProxyConfig {
    pub fn from_url(url: &str, id: String) -> Option<Self> {
        let without_scheme = url.split("://").nth(1)?;
        let (username, password, host_port) = if let Some((creds, hp)) = without_scheme.split_once('@')
        {
            let (u, p) = creds.split_once(':').unwrap_or((creds, ""));
            (u.to_string(), p.to_string(), hp)
        } else {
            (String::new(), String::new(), without_scheme)
        };

        let mut hp_parts = host_port.splitn(2, ':');
        let host = hp_parts.next()?.to_string();
        let port: u16 = hp_parts
            .next()
            .and_then(|p| p.parse().ok())
            .unwrap_or(0);

        Some(Self {
            proxy_id: id,
            enabled: true,
            host,
            port,
            username,
            password,
        })
    }

    pub fn to_url(&self) -> String {
        if self.username.is_empty() && self.password.is_empty() {
            format!("socks5://{}:{}", self.host, self.port)
        } else {
            format!(
                "socks5://{}:{}@{}:{}",
                self.username, self.password, self.host, self.port
            )
        }
    }
}

#[derive(Debug, Clone)]
pub struct Account {
    pub username: String,
    pub password: String,
    #[allow(dead_code)]
    pub email: String,
    pub proxy_config: ProxyConfig,
}

#[derive(Debug, Deserialize)]
struct AccountFile {
    #[serde(default)]
    accounts: Vec<AccountEntry>,
}

#[derive(Debug, Deserialize)]
struct AccountEntry {
    username: String,
    password: String,
    email: String,
    #[serde(default)]
    proxy_id: String,
    #[serde(default)]
    proxy_url: String,
}

#[derive(Debug, Error)]
pub enum AccountPoolError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("HTTP error: {0}")]
    Http(#[from] reqwest::Error),
}

pub type ProxyResetCallback = Arc<dyn Fn(String) + Send + Sync>;

pub struct AccountPool {
    pub accounts: Vec<Account>,
    pub proxies: HashMap<String, Proxy>,
    guest_join_counts: HashMap<String, usize>,
    guest_account_pointer: usize,
    pool_path: String,
    webshare_token: String,
    proxy_reset_callback: Option<ProxyResetCallback>,
}

impl AccountPool {
    pub async fn load_from_file<P: AsRef<Path>>(
        path: P,
        webshare_token: String,
    ) -> Result<Self, AccountPoolError> {
        let file = File::open(&path)?;
        let reader = BufReader::new(file);
        let parsed: AccountFile = serde_json::from_reader(reader)?;


        let proxies = Self::fetch_proxies(&webshare_token).await?;

        // Assign proxies to accounts similar to C++ logic.
        let mut accounts = Vec::new();
        let mut assigned_proxy_ids: HashSet<String> = HashSet::new();
        let mut unassigned_proxy_ids: HashSet<String> = proxies.keys().cloned().collect();
        let mut accounts_missing_proxies: Vec<AccountEntry> = Vec::new();

        for entry in parsed.accounts {
            let mut requested_proxy_id = entry.proxy_id.clone();
            if requested_proxy_id.is_empty() && !entry.proxy_url.is_empty() {
                requested_proxy_id = proxies
                    .iter()
                    .find_map(|(id, proxy)| (proxy.proxy_url() == entry.proxy_url).then_some(id.clone()))
                    .unwrap_or_default();
            }

            if !requested_proxy_id.is_empty() && proxies.contains_key(&requested_proxy_id) {
                if !assigned_proxy_ids.insert(requested_proxy_id.clone()) {
                    accounts_missing_proxies.push(entry);
                } else {
                    unassigned_proxy_ids.remove(&requested_proxy_id);
                    let proxy = &proxies[&requested_proxy_id];
                    let cfg =
                        ProxyConfig::from_url(&proxy.proxy_url(), proxy.id.clone()).unwrap_or(
                            ProxyConfig {
                                proxy_id: proxy.id.clone(),
                                enabled: false,
                                host: proxy.address.clone(),
                                port: proxy.port,
                                username: proxy.username.clone(),
                                password: proxy.password.clone(),
                            },
                        );
                    accounts.push(Account {
                        username: entry.username,
                        password: entry.password,
                        email: entry.email,
                        proxy_config: cfg,
                    });
                }
            } else {
                accounts_missing_proxies.push(entry);
            }
        }

        for entry in accounts_missing_proxies {
            let proxy_id = match unassigned_proxy_ids.iter().next().cloned() {
                Some(id) => id,
                None => {
                    // No proxy available; skip this account.
                    continue;
                }
            };
            unassigned_proxy_ids.remove(&proxy_id);
            let proxy = &proxies[&proxy_id];
            let cfg =
                ProxyConfig::from_url(&proxy.proxy_url(), proxy.id.clone()).unwrap_or(
                    ProxyConfig {
                        proxy_id: proxy.id.clone(),
                        enabled: false,
                        host: proxy.address.clone(),
                        port: proxy.port,
                        username: proxy.username.clone(),
                        password: proxy.password.clone(),
                    },
                );
            accounts.push(Account {
                username: entry.username,
                password: entry.password,
                email: entry.email,
                proxy_config: cfg,
            });
        }

        Ok(Self {
            accounts,
            proxies,
            guest_join_counts: HashMap::new(),
            guest_account_pointer: 0,
            pool_path: path.as_ref().to_string_lossy().to_string(),
            webshare_token,
            proxy_reset_callback: None,
        })
    }

    async fn fetch_proxies(token: &str) -> Result<HashMap<String, Proxy>, AccountPoolError> {
        let client = reqwest::Client::new();
        let mut headers = HeaderMap::new();
        headers.insert(
            AUTHORIZATION,
            HeaderValue::from_str(&format!("Token {}", token)).unwrap(),
        );

        let mut page = 1;
        let mut proxy_map = HashMap::new();

        loop {
            let url = format!(
                "https://proxy.webshare.io/api/v2/proxy/list/?mode=direct&page={}&page_size=25",
                page
            );
            let resp = client.get(&url).headers(headers.clone()).send().await?;

            if !resp.status().is_success() {
                break;
            }

            #[derive(Deserialize)]
            struct ProxyResponse {
                next: Option<String>,
                results: Vec<Proxy>,
            }

            let parsed: ProxyResponse = resp.json().await?;
            for p in parsed.results {
                if p.valid {
                    proxy_map.insert(p.id.clone(), p);
                }
            }

            if parsed.next.is_none() {
                break;
            }
            page += 1;
        }

        Ok(proxy_map)
    }

    pub fn next_guest_account(
        &mut self,
        max_guest_games_per_account: i32,
    ) -> Option<&Account> {
        if self.accounts.is_empty() {
            return None;
        }

        let total = self.accounts.len();
        let mut checked = 0usize;

        while checked < total {
            let idx = self.guest_account_pointer % total;
            checked += 1;

            let account = &self.accounts[idx];
            let current = *self
                .guest_join_counts
                .get(&account.username)
                .unwrap_or(&0);

            if max_guest_games_per_account <= 0
                || current < max_guest_games_per_account as usize
            {
                return Some(account);
            }

            self.guest_account_pointer += 1;
        }

        None
    }

    pub fn next_guest_account_owned(&mut self, max_guest_games_per_account: i32) -> Option<Account> {
        self.next_guest_account(max_guest_games_per_account).cloned()
    }

    pub fn increment_guest_join(&mut self, username: &str) {
        let counter = self.guest_join_counts.entry(username.to_string()).or_insert(0);
        *counter += 1;
    }

    pub fn decrement_guest_join(&mut self, username: &str) {
        if let Some(counter) = self.guest_join_counts.get_mut(username) {
            if *counter > 0 {
                *counter -= 1;
            }
        }
    }

    pub fn set_proxy_reset_callback(&mut self, callback: ProxyResetCallback) {
        self.proxy_reset_callback = Some(callback);
    }

    pub fn get_account_proxy(&self, username: &str) -> Option<ProxyConfig> {
        self.accounts
            .iter()
            .find(|a| a.username == username)
            .map(|a| a.proxy_config.clone())
    }

    /// Persists current runtime proxy assignments back to the account_pool.json on disk.
    /// Only `proxy_id` and `proxy_url` fields are updated; all other fields are preserved.
    pub fn save_to_file(&self) -> Result<(), Box<dyn std::error::Error>> {
        let file = File::open(&self.pool_path)?;
        let reader = BufReader::new(file);
        let mut json: serde_json::Value = serde_json::from_reader(reader)?;

        if let Some(entries) = json["accounts"].as_array_mut() {
            for entry in entries.iter_mut() {
                let uname = entry["username"].as_str().unwrap_or("");
                if let Some(account) = self.accounts.iter().find(|a| a.username == uname) {
                    entry["proxy_id"] =
                        serde_json::Value::String(account.proxy_config.proxy_id.clone());
                    entry["proxy_url"] =
                        serde_json::Value::String(account.proxy_config.to_url());
                }
            }
        }

        let tmp_path = format!("{}.tmp", self.pool_path);
        let tmp_file = File::create(&tmp_path)?;
        serde_json::to_writer_pretty(tmp_file, &json)?;
        std::fs::rename(&tmp_path, &self.pool_path)?;
        Ok(())
    }

    /// Calls the WebShare replace API to swap out the broken proxy for `username` with a
    /// freshly provisioned one, verifies it, assigns it, and persists to disk.
    /// Falls back to pool rotation if the API call fails or the new proxy fails verification.
    pub async fn replace_proxy(&mut self, username: &str, game_server_url: &str) -> bool {
        let old_proxy = self
            .accounts
            .iter()
            .find(|a| a.username == username)
            .map(|a| (a.proxy_config.proxy_id.clone(), a.proxy_config.host.clone()));
        let (old_proxy_id, old_address) = old_proxy.unwrap_or_default();

        // Try WebShare replace API first.
        if !old_proxy_id.is_empty() && !old_address.is_empty() {
            if let Some(new_proxy) = self
                .request_webshare_replacement(&old_proxy_id, &old_address)
                .await
            {
                let new_url = new_proxy.proxy_url();
                tracing::info!(
                    account = username,
                    old_proxy_id = %old_proxy_id,
                    new_proxy_id = %new_proxy.id,
                    "received replacement proxy from WebShare; verifying"
                );
                if connectivity_check::proxy_passes_checks(&new_url, game_server_url).await {
                    let new_cfg = ProxyConfig::from_url(&new_url, new_proxy.id.clone())
                        .unwrap_or(ProxyConfig {
                            proxy_id: new_proxy.id.clone(),
                            enabled: true,
                            host: new_proxy.address.clone(),
                            port: new_proxy.port,
                            username: new_proxy.username.clone(),
                            password: new_proxy.password.clone(),
                        });
                    self.proxies.insert(new_proxy.id.clone(), new_proxy);
                    if let Some(account) = self.accounts.iter_mut().find(|a| a.username == username) {
                        account.proxy_config = new_cfg;
                    }
                    if let Err(err) = self.save_to_file() {
                        tracing::warn!(?err, "failed to persist proxy assignment to disk");
                    }
                    if let Some(cb) = &self.proxy_reset_callback {
                        cb(username.to_string());
                    }
                    record_proxy_replacement("webshare_api");
                    tracing::info!(
                        account = username,
                        old_proxy_id = %old_proxy_id,
                        "proxy successfully replaced and verified via WebShare"
                    );
                    return true;
                } else {
                    tracing::warn!(
                        account = username,
                        "WebShare replacement proxy failed connectivity checks; falling back to pool rotation"
                    );
                }
            }
        }

        // Fallback: rotate within the existing pool.
        let ok = self.reset_account_proxy(username).await;
        if !ok {
            record_proxy_replacement("failed");
        }
        ok
    }

    /// Replaces a single broken proxy via the WebShare v3 replacement API. That API is
    /// asynchronous: the POST only creates a replacement job, which is polled by id until it
    /// reaches a terminal state. WebShare doesn't hand back the new proxy directly, so once the
    /// job completes we re-fetch the proxy list and diff it against what we knew before to find
    /// the newly added proxy.
    async fn request_webshare_replacement(&self, proxy_id: &str, old_address: &str) -> Option<Proxy> {
        let client = reqwest::Client::new();
        let mut headers = HeaderMap::new();
        headers.insert(
            AUTHORIZATION,
            HeaderValue::from_str(&format!("Token {}", self.webshare_token)).unwrap(),
        );

        #[derive(Serialize)]
        struct ToReplace<'a> {
            #[serde(rename = "type")]
            kind: &'a str,
            ip_addresses: [&'a str; 1],
        }

        #[derive(Serialize)]
        struct ReplaceWith<'a> {
            #[serde(rename = "type")]
            kind: &'a str,
            count: u32,
        }

        #[derive(Serialize)]
        struct ReplaceRequest<'a> {
            to_replace: ToReplace<'a>,
            replace_with: [ReplaceWith<'a>; 1],
            dry_run: bool,
        }

        #[derive(Deserialize)]
        struct ReplaceJob {
            id: u64,
            state: String,
            proxies_added: Option<u32>,
        }

        let resp = client
            .post("https://proxy.webshare.io/api/v3/proxy/replace/")
            .headers(headers.clone())
            .json(&ReplaceRequest {
                to_replace: ToReplace {
                    kind: "ip_address",
                    ip_addresses: [old_address],
                },
                replace_with: [ReplaceWith {
                    kind: "any",
                    count: 1,
                }],
                dry_run: false,
            })
            .send()
            .await
            .ok()?;

        if !resp.status().is_success() {
            tracing::warn!(
                proxy_id,
                status = %resp.status(),
                "WebShare replace API returned non-success status"
            );
            return None;
        }

        let job: ReplaceJob = resp.json().await.ok()?;

        let mut job = job;
        const MAX_POLLS: u32 = 10;
        for _ in 0..MAX_POLLS {
            if job.state == "completed" || job.state == "failed" {
                break;
            }
            tokio::time::sleep(std::time::Duration::from_secs(1)).await;
            let poll_resp = client
                .get(format!(
                    "https://proxy.webshare.io/api/v3/proxy/replace/{}/",
                    job.id
                ))
                .headers(headers.clone())
                .send()
                .await
                .ok()?;
            if !poll_resp.status().is_success() {
                return None;
            }
            job = poll_resp.json().await.ok()?;
        }

        if job.state != "completed" || job.proxies_added.unwrap_or(0) == 0 {
            tracing::warn!(proxy_id, state = %job.state, "WebShare replacement job did not complete successfully");
            return None;
        }

        let refreshed = Self::fetch_proxies(&self.webshare_token).await.ok()?;
        refreshed
            .into_iter()
            .find(|(id, _)| !self.proxies.contains_key(id))
            .map(|(_, proxy)| proxy)
    }

    pub async fn reset_account_proxy(&mut self, username: &str) -> bool {
        let old_proxy_id = self
            .accounts
            .iter()
            .find(|a| a.username == username)
            .map(|a| a.proxy_config.proxy_id.clone())
            .unwrap_or_default();

        let updated_proxies = match Self::fetch_proxies(&self.webshare_token).await {
            Ok(map) if !map.is_empty() => map,
            Ok(_) => {
                tracing::error!("no proxies available from WebShare");
                return false;
            }
            Err(err) => {
                tracing::error!(?err, "failed refreshing proxies from WebShare");
                return false;
            }
        };
        self.proxies = updated_proxies;

        let assigned_ids: HashSet<String> = self
            .accounts
            .iter()
            .map(|acc| acc.proxy_config.proxy_id.clone())
            .filter(|id| self.proxies.contains_key(id))
            .collect();

        // Try to find an unassigned proxy first; fall back to least-shared when pool is exhausted.
        let (new_proxy_id, shared) = if let Some(id) = self
            .proxies
            .keys()
            .find(|id| !assigned_ids.contains(*id))
            .cloned()
        {
            (id, false)
        } else {
            tracing::warn!(
                account = username,
                "no unassigned proxy available; sharing least-used proxy"
            );
            let best = self
                .proxies
                .keys()
                .min_by_key(|pid| {
                    self.accounts
                        .iter()
                        .filter(|a| &a.proxy_config.proxy_id == *pid)
                        .count()
                })
                .cloned();
            let Some(id) = best else {
                tracing::error!("proxy pool is empty; cannot assign any proxy");
                return false;
            };
            (id, true)
        };

        let Some(proxy) = self.proxies.get(&new_proxy_id) else {
            return false;
        };
        let new_cfg = ProxyConfig::from_url(&proxy.proxy_url(), proxy.id.clone()).unwrap_or(
            ProxyConfig {
                proxy_id: proxy.id.clone(),
                enabled: false,
                host: proxy.address.clone(),
                port: proxy.port,
                username: proxy.username.clone(),
                password: proxy.password.clone(),
            },
        );

        let share_count = if shared {
            self.accounts
                .iter()
                .filter(|a| a.proxy_config.proxy_id == new_proxy_id)
                .count()
                + 1
        } else {
            1
        };

        let Some(account) = self.accounts.iter_mut().find(|a| a.username == username) else {
            return false;
        };
        account.proxy_config = new_cfg;

        if shared {
            tracing::info!(
                account = username,
                old_proxy_id = old_proxy_id,
                new_proxy_id = new_proxy_id,
                share_count,
                "reset account proxy (sharing)"
            );
            record_proxy_replacement("pool_sharing");
        } else {
            tracing::info!(
                account = username,
                old_proxy_id = old_proxy_id,
                new_proxy_id = new_proxy_id,
                "successfully reset account proxy"
            );
            record_proxy_replacement("pool_rotation");
        }

        if let Err(err) = self.save_to_file() {
            tracing::warn!(?err, "failed to persist proxy assignment to disk after rotation");
        }

        if let Some(callback) = &self.proxy_reset_callback {
            callback(username.to_string());
        }

        true
    }
}