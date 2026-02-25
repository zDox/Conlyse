use reqwest::header::{HeaderMap, HeaderValue, AUTHORIZATION};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::fs::File;
use std::io::BufReader;
use std::path::Path;
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

#[derive(Debug, Clone)]
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
        // Very small parser for urls like socks5://user:pass@host:port
        let without_scheme = url.split("://").nth(1)?;
        let mut parts = without_scheme.split('@');
        let creds = parts.next()?;
        let host_port = parts.next()?;

        let mut cred_parts = creds.splitn(2, ':');
        let username = cred_parts.next()?.to_string();
        let password = cred_parts.next().unwrap_or("").to_string();

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
    pub email: String,
    pub proxy_config: ProxyConfig,
}

#[derive(Debug, Deserialize)]
struct AccountFile {
    #[serde(default)]
    WEBSHARE_API_TOKEN: String,
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
    #[error("WebShare token not set")]
    MissingToken,
}

#[derive(Debug)]
pub struct AccountPool {
    pub accounts: Vec<Account>,
    pub proxies: HashMap<String, Proxy>,
    guest_join_counts: HashMap<String, usize>,
    free_account_pointer: usize,
    guest_account_pointer: usize,
    pool_path: String,
    webshare_token: String,
}

impl AccountPool {
    pub async fn load_from_file<P: AsRef<Path>>(
        path: P,
        explicit_token: Option<String>,
    ) -> Result<Self, AccountPoolError> {
        let file = File::open(&path)?;
        let reader = BufReader::new(file);
        let parsed: AccountFile = serde_json::from_reader(reader)?;

        let webshare_token = explicit_token
            .or_else(|| {
                if parsed.WEBSHARE_API_TOKEN.is_empty() {
                    None
                } else {
                    Some(parsed.WEBSHARE_API_TOKEN.clone())
                }
            })
            .ok_or(AccountPoolError::MissingToken)?;

        let proxies = Self::fetch_proxies(&webshare_token).await?;

        // Assign proxies to accounts similar to C++ logic.
        let mut accounts = Vec::new();
        let mut assigned_proxy_ids: HashSet<String> = HashSet::new();
        let mut unassigned_proxy_ids: HashSet<String> = proxies.keys().cloned().collect();
        let mut accounts_missing_proxies: Vec<AccountEntry> = Vec::new();

        for entry in parsed.accounts {
            if !entry.proxy_id.is_empty() && proxies.contains_key(&entry.proxy_id) {
                if !assigned_proxy_ids.insert(entry.proxy_id.clone()) {
                    accounts_missing_proxies.push(entry);
                } else {
                    unassigned_proxy_ids.remove(&entry.proxy_id);
                    let proxy = &proxies[&entry.proxy_id];
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
            free_account_pointer: 0,
            guest_account_pointer: 0,
            pool_path: path.as_ref().to_string_lossy().to_string(),
            webshare_token,
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
                proxy_map.insert(p.id.clone(), p);
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
            self.guest_account_pointer += 1;
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
        }

        None
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
}

