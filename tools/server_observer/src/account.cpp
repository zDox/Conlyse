#include "account.hpp"
#include <iostream>

Account::Account(const std::string& username, const std::string& password,
                const std::string& email,
                std::shared_ptr<ProxyConfig> proxy_config)
    : username(username)
    , password(password)
    , email(email)
    , proxy_config(proxy_config)
    , hub_interface_(nullptr)
    , games_loaded_(false)
{}

Account::~Account() {
}

bool Account::login_internal() {
    if (!hub_interface_) {
        std::string proxy_url = proxy_config ? proxy_config->to_url() : "";
        hub_interface_ = std::make_shared<HubInterfaceWrapper>(proxy_url, proxy_url);
    }
    
    if (hub_interface_->is_authenticated()) {
        return true;
    }
    
    return hub_interface_->login(username, password);
}

bool Account::login() {
    std::lock_guard<std::mutex> lock(mutex_);
    return login_internal();
}

std::shared_ptr<HubInterfaceWrapper> Account::get_interface() {
    std::lock_guard<std::mutex> lock(mutex_);

    if (!hub_interface_) {
        std::string proxy_url = proxy_config ? proxy_config->to_url() : "";
        hub_interface_ = std::make_shared<HubInterfaceWrapper>(proxy_url, proxy_url);
    }
    
    if (!hub_interface_->is_authenticated()) {
        login_internal();
    }
    
    return hub_interface_;
}

void Account::reset_interface() {
    std::lock_guard<std::mutex> lock(mutex_);
    std::string proxy_url = proxy_config ? proxy_config->to_url() : "";
    hub_interface_ = std::make_shared<HubInterfaceWrapper>(proxy_url, proxy_url);
    games_.clear();
    games_loaded_ = false;
    login_internal();
}

void Account::reset_proxy(std::shared_ptr<ProxyConfig> new_proxy_config) {
    std::lock_guard<std::mutex> lock(mutex_);
    proxy_config = new_proxy_config;
    std::string proxy_url = proxy_config ? proxy_config->to_url() : "";
    hub_interface_ = std::make_shared<HubInterfaceWrapper>(proxy_url, proxy_url);
    games_.clear();
    games_loaded_ = false;
    login_internal();
}

std::vector<HubGameProperties> Account::get_my_games() {
    std::lock_guard<std::mutex> lock(mutex_);
    if (!games_loaded_) {
        ensure_games_loaded_internal();
    }
    return games_;
}

bool Account::has_game(int game_id) {
    std::lock_guard<std::mutex> lock(mutex_);
    ensure_games_loaded_internal();
    for (const auto& game : games_) {
        if (game.game_id == game_id) {
            return true;
        }
    }
    return false;
}

bool Account::has_maximum_games() {
    std::lock_guard<std::mutex> lock(mutex_);
    ensure_games_loaded_internal();
    return games_.size() >= MAXIMUM_NUMBER_OF_GAMES;
}

int Account::open_game_slots() {
    std::lock_guard<std::mutex> lock(mutex_);
    ensure_games_loaded_internal();
    return MAXIMUM_NUMBER_OF_GAMES - games_.size();
}

void Account::ensure_games_loaded_internal() {
    if (games_loaded_) {
        return;
    }
    
    // Ensure hub_interface_ is initialized
    if (!hub_interface_) {
        get_interface();
    }
    
    if (!hub_interface_->is_authenticated()) {
        login_internal();
    }
    
    games_ = hub_interface_->get_my_games();
    games_loaded_ = true;
}

void Account::ensure_games_loaded() {
    std::lock_guard<std::mutex> lock(mutex_);
    ensure_games_loaded_internal();
}

json Account::to_json() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return {
        {"username", username},
        {"password", password},
        {"email", email},
        {"proxy_id", proxy_config ? proxy_config->proxy_id : ""},
        {"proxy_url", proxy_config ? proxy_config->to_url() : ""}
    };
}

std::shared_ptr<Account> Account::from_json(const json& j) {
    std::string proxy_url = j.value("proxy_url", "");
    auto proxy_config = std::make_shared<ProxyConfig>(ProxyConfig::from_url(proxy_url));
    proxy_config->proxy_id = j.value("proxy_id", "");

    return std::make_shared<Account>(
        j.value("username", ""),
        j.value("password", ""),
        j.value("email", ""),
        proxy_config
    );
}
