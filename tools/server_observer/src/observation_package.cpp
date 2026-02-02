#include "observation_package.hpp"

json ObservationPackage::to_json() const {
    // Convert headers map to JSON
    json headers_json = json::object();
    for (const auto &[key, value]: headers) {
        headers_json[key] = value;
    }

    // Convert cookies map to JSON
    json cookies_json = json::object();
    for (const auto &[key, value]: cookies) {
        cookies_json[key] = value;
    }

    // Convert ProxyConfig to JSON
    json proxy_json = json::object();
    if (proxy.enabled) {
        proxy_json["host"] = proxy.host;
        proxy_json["port"] = proxy.port;
        if (!proxy.username.empty()) {
            proxy_json["username"] = proxy.username;
        }
        if (!proxy.password.empty()) {
            proxy_json["password"] = proxy.password;
        }
    }

    json j = {
        {"game_id", game_id},
        {"headers", headers_json},
        {"cookies", cookies_json},
        {"proxy", proxy_json},
        {"auth", auth.to_json()},
        {"client_version", client_version},
        {"game_server_address", game_server_address}
    };

    // Convert time_stamps map to JSON
    json ts = json::object();
    for (const auto &[key, value]: time_stamps) {
        ts[key] = value;
    }
    j["time_stamps"] = ts;

    // Convert state_ids map to JSON
    json si = json::object();
    for (const auto &[key, value]: state_ids) {
        si[key] = value;
    }
    j["state_ids"] = si;

    return j;
}

ObservationPackage ObservationPackage::from_json(const json &j) {
    ObservationPackage pkg;
    pkg.game_id = j.value("game_id", 0);
    pkg.client_version = j.value("client_version", 207);
    pkg.game_server_address = j.value("game_server_address", "");

    // Convert headers from JSON to map
    if (j.contains("headers") && j["headers"].is_object()) {
        for (const auto &[key, value]: j["headers"].items()) {
            try {
                pkg.headers[key] = value.get<std::string>();
            } catch (...) {
            }
        }
    }

    // Convert cookies from JSON to map
    if (j.contains("cookies") && j["cookies"].is_object()) {
        for (const auto &[key, value]: j["cookies"].items()) {
            try {
                pkg.cookies[key] = value.get<std::string>();
            } catch (...) {
            }
        }
    }

    // Convert proxy from JSON to ProxyConfig
    if (j.contains("proxy") && j["proxy"].is_object()) {
        const auto &proxy_json = j["proxy"];
        if (proxy_json.contains("host") && proxy_json.contains("port")) {
            pkg.proxy.enabled = true;
            pkg.proxy.host = proxy_json["host"].get<std::string>();
            pkg.proxy.port = proxy_json["port"].get<int>();
            if (proxy_json.contains("username")) {
                pkg.proxy.username = proxy_json["username"].get<std::string>();
            }
            if (proxy_json.contains("password")) {
                pkg.proxy.password = proxy_json["password"].get<std::string>();
            }
        }
    }

    if (j.contains("auth")) {
        pkg.auth = AuthDetails::from_json(j["auth"]);
    }

    // Convert time_stamps from JSON to map
    if (j.contains("time_stamps") && j["time_stamps"].is_object()) {
        for (const auto &[key, value]: j["time_stamps"].items()) {
            try {
                pkg.time_stamps[key] = value.get<std::string>();
            } catch (...) {
            }
        }
    }

    // Convert state_ids from JSON to map
    if (j.contains("state_ids") && j["state_ids"].is_object()) {
        for (const auto &[key, value]: j["state_ids"].items()) {
            try {
                pkg.state_ids[key] = value.get<std::string>();
            } catch (...) {
            }
        }
    }

    return pkg;
}
