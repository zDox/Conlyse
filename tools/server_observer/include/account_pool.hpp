#ifndef ACCOUNT_POOL_HPP
#define ACCOUNT_POOL_HPP

#include <string>
#include <vector>
#include <map>
#include <memory>
#include <functional>
#include "account.hpp"
#include "proxy_config.hpp"
#include <nlohmann/json.hpp>

struct Proxy {
    std::string id;
    std::string username;
    std::string password;
    std::string address;
    int port;
    bool valid;
    std::string country_code;
    
    std::string get_proxy_url() const;
    static Proxy from_json(const json& j);
};

class AccountPool {
public:
    AccountPool(const std::string& path, const std::string& webshare_token = "");
    
    std::vector<std::shared_ptr<Account>> accounts;
    std::map<std::string, Proxy> proxies;
    
    std::shared_ptr<Account> get_any_account();
    std::shared_ptr<Account> next_free_account();
    std::shared_ptr<Account> next_guest_account(int max_guest_games_per_account);
    
    void increment_guest_join(std::shared_ptr<Account> account);
    void decrement_guest_join(std::shared_ptr<Account> account);
    
    bool reset_account_proxy(const std::shared_ptr<Account> &account);

    // Callback to notify when an account's proxy is reset
    using ProxyResetCallback = std::function<void(std::shared_ptr<Account>)>;
    void set_proxy_reset_callback(ProxyResetCallback callback);

    size_t free_account_pointer;
    size_t guest_account_pointer;
    
private:
    std::string pool_path_;
    std::string webshare_token_;
    std::map<std::string, int> guest_join_counts_;
    ProxyResetCallback proxy_reset_callback_;

    void load_token();
    void load_proxies();
    void load_accounts();
    std::map<std::string, Proxy> get_proxies(const std::string& token);
};

#endif // ACCOUNT_POOL_HPP
