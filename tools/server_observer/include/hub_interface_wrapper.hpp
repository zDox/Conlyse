#ifndef HUB_INTERFACE_WRAPPER_HPP
#define HUB_INTERFACE_WRAPPER_HPP

#include <string>
#include <memory>
#include <pybind11/pybind11.h>
#include <pybind11/embed.h>
#include <nlohmann/json.hpp>

namespace py = pybind11;
using json = nlohmann::json;

/**
 * AuthDetails structure to hold authentication information
 */
struct AuthDetails {
    std::string auth;
    std::string rights;
    long user_id;
    long auth_tstamp;
    
    json to_json() const;
    static AuthDetails from_json(const json& j);
};

/**
 * HubGameProperties structure to hold game properties
 */
struct HubGameProperties {
    int game_id;
    int scenario_id;
    int open_slots;
    std::string name;
    
    static HubGameProperties from_json(const json& j);
};

/**
 * Wrapper around Python HubInterface to handle authentication
 * This is the ONLY way to login and retrieve authentication data
 */
class HubInterfaceWrapper {
public:
    HubInterfaceWrapper(const std::string& proxy_http = "", const std::string& proxy_https = "");
    ~HubInterfaceWrapper();
    
    // Authentication
    bool login(const std::string& username, const std::string& password);
    void logout();
    bool is_authenticated() const { return authenticated_; }
    
    // Get authentication details
    AuthDetails get_auth_details() const;
    
    // Get games
    std::vector<HubGameProperties> get_my_games();
    std::vector<HubGameProperties> get_global_games();
    
    // Game join - creates GameApi and loads game site to get server address and updated auth
    struct GameApiData {
        std::string game_server_address;
        int client_version;
        std::string map_id;
        AuthDetails auth;
        json headers;
        json cookies;
    };
    GameApiData join_game_as_guest(int game_id);
    
    // Session and proxy info
    json get_cookies() const;
    json get_headers() const;
    std::string get_proxy_http() const { return proxy_http_; }
    std::string get_proxy_https() const { return proxy_https_; }
    
private:
    py::object hub_interface_;
    py::module_ python_module_;
    bool authenticated_;
    std::string proxy_http_;
    std::string proxy_https_;
    
    void init_python();
    void cleanup_python();
    json py_to_json(const py::handle& obj) const;
};

#endif // HUB_INTERFACE_WRAPPER_HPP
