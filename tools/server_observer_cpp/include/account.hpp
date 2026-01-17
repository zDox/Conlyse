#ifndef ACCOUNT_HPP
#define ACCOUNT_HPP

#include <string>
#include <memory>
#include <vector>
#include "hub_interface_wrapper.hpp"

class Account {
public:
    std::string username;
    std::string password;
    std::string email;
    std::string proxy_id;
    std::string proxy_url;
    
    Account(const std::string& username, const std::string& password,
            const std::string& email, const std::string& proxy_id,
            const std::string& proxy_url);
    
    ~Account();
    
    bool login();
    std::shared_ptr<HubInterfaceWrapper> get_interface();
    void reset_interface();
    
    std::vector<HubGameProperties> get_my_games();
    bool has_game(int game_id);
    bool has_maximum_games();
    int open_game_slots();
    
    json to_json() const;
    static Account from_json(const json& j);
    
private:
    std::shared_ptr<HubInterfaceWrapper> hub_interface_;
    std::vector<HubGameProperties> games_;
    bool games_loaded_;
    
    void ensure_games_loaded();
    
    static const int MAXIMUM_NUMBER_OF_GAMES = 10;
};

#endif // ACCOUNT_HPP
