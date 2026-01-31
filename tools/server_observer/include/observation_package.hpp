#ifndef OBSERVATION_PACKAGE_HPP
#define OBSERVATION_PACKAGE_HPP

#include <string>
#include <map>
#include <nlohmann/json.hpp>
#include "proxy_config.hpp"
#include "account.hpp"

using json = nlohmann::json;

struct ObservationPackage {
    int game_id = 0;
    std::map<std::string, std::string> headers;
    std::map<std::string, std::string> cookies;
    ProxyConfig proxy;
    AuthDetails auth;
    int client_version = 0;
    std::string game_server_address;
    std::map<std::string, std::string> time_stamps;
    std::map<std::string, std::string> state_ids;

    json to_json() const;

    static ObservationPackage from_json(const json &j);
};

#endif // OBSERVATION_PACKAGE_HPP
