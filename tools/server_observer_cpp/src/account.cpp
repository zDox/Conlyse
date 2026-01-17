#include "account.hpp"
#include <iostream>

Account::Account(const std::string& username, const std::string& password,
                const std::string& email, const std::string& proxy_id,
                const std::string& proxy_url)
    : username(username)
    , password(password)
    , email(email)
    , proxy_id(proxy_id)
    , proxy_url(proxy_url)
    , hub_interface_(nullptr)
    , games_loaded_(false)
{
    // Create HubInterface with proxy
    hub_interface_ = std::make_shared<HubInterfaceWrapper>(proxy_url, proxy_url);
}

Account::~Account() {
}

bool Account::login() {
    if (!hub_interface_) {
        return false;
    }
    
    if (hub_interface_->is_authenticated()) {
        return true;
    }
    
    return hub_interface_->login(username, password);
}

std::shared_ptr<HubInterfaceWrapper> Account::get_interface() {
    if (!hub_interface_) {
        hub_interface_ = std::make_shared<HubInterfaceWrapper>(proxy_url, proxy_url);
    }
    
    if (!hub_interface_->is_authenticated()) {
        login();
    }
    
    return hub_interface_;
}

void Account::reset_interface() {
    hub_interface_ = std::make_shared<HubInterfaceWrapper>(proxy_url, proxy_url);
    games_.clear();
    games_loaded_ = false;
    login();
}

std::vector<HubGameProperties> Account::get_my_games() {
    if (!games_loaded_) {
        ensure_games_loaded();
    }
    return games_;
}

bool Account::has_game(int game_id) {
    ensure_games_loaded();
    for (const auto& game : games_) {
        if (game.game_id == game_id) {
            return true;
        }
    }
    return false;
}

bool Account::has_maximum_games() {
    ensure_games_loaded();
    return games_.size() >= MAXIMUM_NUMBER_OF_GAMES;
}

int Account::open_game_slots() {
    ensure_games_loaded();
    return MAXIMUM_NUMBER_OF_GAMES - games_.size();
}

void Account::ensure_games_loaded() {
    if (games_loaded_) {
        return;
    }
    
    if (!hub_interface_->is_authenticated()) {
        login();
    }
    
    games_ = hub_interface_->get_my_games();
    games_loaded_ = true;
}

json Account::to_json() const {
    return {
        {"username", username},
        {"password", password},
        {"email", email},
        {"proxy_id", proxy_id},
        {"proxy_url", proxy_url}
    };
}

Account Account::from_json(const json& j) {
    return Account(
        j.value("username", ""),
        j.value("password", ""),
        j.value("email", ""),
        j.value("proxy_id", ""),
        j.value("proxy_url", "")
    );
}
