#ifndef ACCOUNT_HPP
#define ACCOUNT_HPP

#include <string>
#include <memory>
#include <vector>
#include <mutex>
#include "hub_interface_wrapper.hpp"
#include "proxy_config.hpp"

class Account {
public:
    std::string username;
    std::string password;
    std::string email;
    std::shared_ptr<ProxyConfig> proxy_config;

    Account(const std::string& username, const std::string& password,
            const std::string& email,
            std::shared_ptr<ProxyConfig> proxy_config);

    ~Account();
    
    bool login();
    std::shared_ptr<HubInterfaceWrapper> get_interface();
    void reset_interface();
    void reset_proxy(std::shared_ptr<ProxyConfig> new_proxy_config);

    std::vector<HubGameProperties> get_my_games();
    bool has_game(int game_id);
    bool has_maximum_games();
    int open_game_slots();
    
    json to_json() const;
    static std::shared_ptr<Account> from_json(const json& j);

private:
    std::shared_ptr<HubInterfaceWrapper> hub_interface_;
    std::vector<HubGameProperties> games_;
    bool games_loaded_;
    mutable std::mutex mutex_;

    // Internal methods that assume mutex is already locked
    bool login_internal();
    void ensure_games_loaded();
    void ensure_games_loaded_internal();

    static const int MAXIMUM_NUMBER_OF_GAMES = 10;
};

#endif // ACCOUNT_HPP
