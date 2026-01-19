#include "account_pool.hpp"
#include <fstream>
#include <iostream>
#include <httplib.h>

std::string Proxy::get_proxy_url() const {
    return "socks5://" + username + ":" + password + "@" + address + ":" + std::to_string(port);
}

Proxy Proxy::from_json(const json& j) {
    Proxy proxy;
    proxy.id = j.value("id", "");
    proxy.username = j.value("username", "");
    proxy.password = j.value("password", "");
    proxy.address = j.value("proxy_address", "");
    proxy.port = j.value("port", 0);
    proxy.valid = j.value("valid", false);
    proxy.country_code = j.value("country_code", "");
    return proxy;
}

AccountPool::AccountPool(const std::string& path, const std::string& webshare_token)
    : pool_path_(path)
    , webshare_token_(webshare_token)
    , free_account_pointer(0)
    , guest_account_pointer(0)
{
    if (webshare_token_.empty()) {
        load_token();
    }
    load_proxies();
    load_accounts();
}

void AccountPool::load_token() {
    std::ifstream file(pool_path_);
    if (!file.is_open()) {
        throw std::runtime_error("File " + pool_path_ + " does not exist");
    }
    
    json credentials;
    file >> credentials;
    
    if (credentials.contains("WEBSHARE_API_TOKEN")) {
        webshare_token_ = credentials["WEBSHARE_API_TOKEN"].get<std::string>();
    } else {
        throw std::runtime_error("WEBSHARE_API_TOKEN not found in " + pool_path_);
    }
}

void AccountPool::load_proxies() {
    if (webshare_token_.empty()) {
        throw std::runtime_error("WebShare token not set");
    }
    proxies = get_proxies(webshare_token_);
}

std::map<std::string, Proxy> AccountPool::get_proxies(const std::string& token) {
    std::map<std::string, Proxy> proxy_map;
    
    httplib::Client cli("https://proxy.webshare.io");
    cli.set_follow_location(true);
    
    httplib::Headers headers = {
        {"Authorization", "Token " + token}
    };
    
    int page = 1;
    bool last_page = false;
    
    while (!last_page) {
        std::string path = "/api/v2/proxy/list/?mode=direct&page=" + std::to_string(page) + "&page_size=25";
        auto res = cli.Get(path.c_str(), headers);
        
        if (!res || res->status != 200) {
            std::cerr << "Failed to fetch proxies from WebShare API" << std::endl;
            break;
        }
        
        try {
            json response = json::parse(res->body);
            last_page = response["next"].is_null();
            page++;
            
            if (response.contains("results") && response["results"].is_array()) {
                for (const auto& proxy_json : response["results"]) {
                    Proxy proxy = Proxy::from_json(proxy_json);
                    proxy_map[proxy.id] = proxy;
                }
            }
        } catch (const std::exception& e) {
            std::cerr << "Error parsing proxy response: " << e.what() << std::endl;
            break;
        }
    }
    
    return proxy_map;
}

void AccountPool::load_accounts() {
    std::ifstream file(pool_path_);
    if (!file.is_open()) {
        std::cerr << "Warning: Could not open account pool file: " << pool_path_ << std::endl;
        return;
    }
    
    try {
        json accounts_file;
        file >> accounts_file;
        
        if (accounts_file.contains("accounts") && accounts_file["accounts"].is_array()) {
            for (const auto& account_json : accounts_file["accounts"]) {
                auto account = std::make_shared<Account>(Account::from_json(account_json));
                accounts.push_back(account);
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "Warning: Error reading account_pool.json: " << e.what() << std::endl;
        return;
    }
    
    // Validate and reassign proxies if needed
    std::set<std::string> assigned_proxy_ids;
    std::set<std::string> unassigned_proxy_ids;
    
    for (const auto& [id, proxy] : proxies) {
        unassigned_proxy_ids.insert(id);
    }
    
    std::vector<std::shared_ptr<Account>> accounts_missing_proxies;
    
    for (auto& account : accounts) {
        if (proxies.find(account->proxy_id) == proxies.end()) {
            std::cerr << "Warning: Account " << account->username 
                     << " has a proxy ID " << account->proxy_id 
                     << " that does not exist" << std::endl;
            accounts_missing_proxies.push_back(account);
        } else if (assigned_proxy_ids.find(account->proxy_id) != assigned_proxy_ids.end()) {
            accounts_missing_proxies.push_back(account);
        } else {
            assigned_proxy_ids.insert(account->proxy_id);
            unassigned_proxy_ids.erase(account->proxy_id);
        }
    }
    
    if (accounts_missing_proxies.size() > unassigned_proxy_ids.size()) {
        std::cerr << "Warning: Not enough unassigned proxies to assign proxies to accounts" << std::endl;
    }
    
    for (auto& account : accounts_missing_proxies) {
        if (unassigned_proxy_ids.empty()) {
            std::cerr << "Warning: Removing account " << account->username 
                     << " due to lack of available proxies" << std::endl;
            accounts.erase(std::remove(accounts.begin(), accounts.end(), account), accounts.end());
            continue;
        }
        
        auto proxy_id = *unassigned_proxy_ids.begin();
        unassigned_proxy_ids.erase(proxy_id);
        
        Proxy& proxy = proxies[proxy_id];
        account->proxy_id = proxy.id;
        account->proxy_url = proxy.get_proxy_url();
    }
}

std::shared_ptr<Account> AccountPool::get_any_account() {
    if (accounts.empty()) {
        return nullptr;
    }
    return accounts[0];
}

std::shared_ptr<Account> AccountPool::next_free_account() {
    if (free_account_pointer >= accounts.size()) {
        return nullptr;
    }
    
    while (accounts[free_account_pointer]->has_maximum_games()) {
        free_account_pointer++;
        if (free_account_pointer >= accounts.size()) {
            return nullptr;
        }
    }
    
    return accounts[free_account_pointer];
}

std::shared_ptr<Account> AccountPool::next_guest_account(int max_guest_games_per_account) {
    if (accounts.empty()) {
        return nullptr;
    }
    
    size_t total = accounts.size();
    size_t checked = 0;
    
    while (checked < total) {
        auto account = accounts[guest_account_pointer % total];
        checked++;
        
        int current = guest_join_counts_[account->username];
        if (max_guest_games_per_account <= 0 || current < max_guest_games_per_account) {
            return account;
        }
        
        guest_account_pointer++;
    }
    
    return nullptr;
}

void AccountPool::increment_guest_join(std::shared_ptr<Account> account) {
    if (!account) {
        return;
    }
    guest_join_counts_[account->username]++;
}

void AccountPool::decrement_guest_join(std::shared_ptr<Account> account) {
    if (!account) {
        return;
    }
    if (guest_join_counts_.find(account->username) != guest_join_counts_.end()) {
        guest_join_counts_[account->username] = std::max(0, guest_join_counts_[account->username] - 1);
    }
}
