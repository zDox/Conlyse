#include "hub_interface_wrapper.hpp"
#include <iostream>
#include <stdexcept>
#include <sstream>
#include <mutex>

namespace py = pybind11;

// Python initialization guard
static bool python_initialized = false;
static std::mutex python_init_mutex;
static py::scoped_interpreter* interpreter = nullptr;

json AuthDetails::to_json() const {
    return json{
        {"auth", auth},
        {"rights", rights},
        {"user_id", user_id},
        {"auth_tstamp", auth_tstamp}
    };
}

AuthDetails AuthDetails::from_json(const json& j) {
    AuthDetails details;
    details.auth = j.value("auth", "");
    details.rights = j.value("rights", "");
    details.user_id = j.value("user_id", 0);
    details.auth_tstamp = j.value("auth_tstamp", 0);
    return details;
}

HubGameProperties HubGameProperties::from_json(const json& j) {
    HubGameProperties props;
    props.game_id = j.value("game_id", 0);
    props.scenario_id = j.value("scenario_id", 0);
    props.open_slots = j.value("open_slots", 0);
    props.name = j.value("name", "");
    return props;
}

HubInterfaceWrapper::HubInterfaceWrapper(const std::string& proxy_http, const std::string& proxy_https)
    : authenticated_(false)
    , proxy_http_(proxy_http)
    , proxy_https_(proxy_https)
{
    init_python();
}

HubInterfaceWrapper::~HubInterfaceWrapper() {
    cleanup_python();
}
void HubInterfaceWrapper::init_python() {
    std::lock_guard<std::mutex> lock(python_init_mutex);

    if (!python_initialized) {
        // Initialize Python interpreter using pybind11
        interpreter = new py::scoped_interpreter();
        python_initialized = true;
    }

    py::gil_scoped_acquire acquire;

    try {
        // Set up the Python path - INSERT at beginning
        py::module_ sys = py::module_::import("sys");
        py::list path = sys.attr("path");
        
        // Insert our paths at the BEGINNING so they take priority
        path.insert(0, "/home/zdox/PycharmProjects/ConflictInterface");
        path.insert(1, "/home/zdox/PycharmProjects/ConflictInterface/.venv/lib/python3.12/site-packages");

        // Debug: Print sys.path to verify
        py::print("sys.path after setup:", path);

        // Import the HubInterface module
        python_module_ = py::module_::import("conflict_interface.interface.hub_interface");

        // Get the HubInterface class
        py::object hub_interface_class = python_module_.attr("HubInterface");

        // Create proxy dict
        py::dict proxy_dict;
        if (!proxy_http_.empty()) {
            proxy_dict["http"] = proxy_http_;
        }
        if (!proxy_https_.empty()) {
            proxy_dict["https"] = proxy_https_;
        }

        // Create HubInterface instance
        hub_interface_ = hub_interface_class(proxy_dict);

    } catch (const py::error_already_set& e) {
        throw std::runtime_error(std::string("Failed to initialize Python: ") + e.what());
    }
}

void HubInterfaceWrapper::cleanup_python() {
    // pybind11 handles cleanup automatically with RAII
    // No manual reference counting needed
}

bool HubInterfaceWrapper::login(const std::string& username, const std::string& password) {
    py::gil_scoped_acquire acquire;
    
    try {
        py::object result = hub_interface_.attr("login")(username, password);
        
        std::cout << "Logged in successfully: " << username << std::endl;
        bool success = result.cast<bool>();
        authenticated_ = true;
        return success;
    } catch (const py::error_already_set& e) {
        std::cerr << "Login failed: " << e.what() << std::endl;
        return false;
    } catch (const std::exception& e) {
        std::cerr << "Login failed: " << e.what() << std::endl;
        return false;
    }
}

void HubInterfaceWrapper::logout() {
    authenticated_ = false;
}

AuthDetails HubInterfaceWrapper::get_auth_details() const {
    py::gil_scoped_acquire acquire;
    
    AuthDetails details;
    
    try {
        // Get the auth attribute from hub_interface
        py::object auth_obj = hub_interface_.attr("auth");
        
        if (auth_obj.is_none()) {
            return details;
        }
        
        // Extract auth fields
        details.auth = auth_obj.attr("auth").cast<std::string>();
        details.rights = auth_obj.attr("rights").cast<std::string>();
        details.user_id = auth_obj.attr("user_id").cast<int>();
        details.auth_tstamp = auth_obj.attr("auth_tstamp").cast<int>();
        
    } catch (const py::error_already_set& e) {
        std::cerr << "Failed to get auth details: " << e.what() << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "Failed to get auth details: " << e.what() << std::endl;
    }
    
    return details;
}

std::vector<HubGameProperties> HubInterfaceWrapper::get_my_games() {
    py::gil_scoped_acquire acquire;
    std::vector<HubGameProperties> games;
    
    try {
        py::object result = hub_interface_.attr("get_my_games")();
        if (py::isinstance<py::list>(result)) {
            json games_json = py_to_json(result);
            for (const auto& game_json : games_json) {
                games.push_back(HubGameProperties::from_json(game_json));
            }
        }
    } catch (const py::error_already_set& e) {
        std::cerr << "Failed to get my games: " << e.what() << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "Failed to get my games: " << e.what() << std::endl;
    }
    
    return games;
}

std::vector<HubGameProperties> HubInterfaceWrapper::get_global_games() {
    py::gil_scoped_acquire acquire;
    std::vector<HubGameProperties> games;
    
    try {
        py::object result = hub_interface_.attr("get_global_games")();
        if (py::isinstance<py::list>(result)) {
            json games_json = py_to_json(result);
            for (const auto& game_json : games_json) {
                games.push_back(HubGameProperties::from_json(game_json));
            }
        }
    } catch (const py::error_already_set& e) {
        std::cerr << "Failed to get global games: " << e.what() << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "Failed to get global games: " << e.what() << std::endl;
    }
    
    return games;
}

HubInterfaceWrapper::GameApiData HubInterfaceWrapper::join_game_as_guest(int game_id) {
    py::gil_scoped_acquire acquire;
    GameApiData data;
    data.client_version = 207;
    data.map_id = 0;
    
    try {
        // Import GameApi
        py::module_ game_api_module = py::module_::import("conflict_interface.game_api");
        py::object game_api_class = game_api_module.attr("GameApi");
        
        // Get hub_interface_.api attributes
        py::object api = hub_interface_.attr("api");
        py::object session = api.attr("session");
        py::object proxy = api.attr("proxy");
        py::object auth_details = api.attr("auth");
        
        // Create GameApi instance: GameApi(session, auth_details, game_id, proxy)
        py::object game_api = game_api_class(session, auth_details, game_id, proxy);
        
        // Call load_game_site()
        game_api.attr("load_game_site")();
        
        // Extract data from game_api
        py::object gs_addr = game_api.attr("game_server_address");
        if (!gs_addr.is_none()) {
            data.game_server_address = gs_addr.cast<std::string>();
        }
        
        py::object client_ver = game_api.attr("client_version");
        if (!client_ver.is_none()) {
            data.client_version = client_ver.cast<int>();
        }
        
        py::object map_id_obj = game_api.attr("map_id");
        if (!map_id_obj.is_none()) {
            if (py::isinstance<py::int_>(map_id_obj)) {
                data.map_id = map_id_obj.cast<int>();
            } else if (py::isinstance<py::str>(map_id_obj)) {
                data.map_id = std::stoi(map_id_obj.cast<std::string>());
            }
        }
        
        // Get updated auth
        py::object auth_obj = game_api.attr("auth");
        if (!auth_obj.is_none()) {
            data.auth.auth = auth_obj.attr("auth").cast<std::string>();
            data.auth.rights = auth_obj.attr("rights").cast<std::string>();
            data.auth.user_id = auth_obj.attr("user_id").cast<int>();
            data.auth.auth_tstamp = auth_obj.attr("auth_tstamp").cast<int>();
        }
        
        // Get session headers and cookies
        py::object ga_session = game_api.attr("session");
        py::object headers_obj = ga_session.attr("headers");
        data.headers = py_to_json(headers_obj);
        
        py::object cookies_obj = ga_session.attr("cookies");
        data.cookies = py_to_json(cookies_obj);
        
    } catch (const py::error_already_set& e) {
        std::cerr << "Failed to join game: " << e.what() << std::endl;
        throw;
    } catch (const std::exception& e) {
        std::cerr << "Failed to join game: " << e.what() << std::endl;
        throw;
    }
    
    return data;
}

json HubInterfaceWrapper::get_cookies() const {
    py::gil_scoped_acquire acquire;
    json cookies;
    
    try {
        // Get api.session.cookies
        py::object api = hub_interface_.attr("api");
        py::object session = api.attr("session");
        py::object cookies_obj = session.attr("cookies");
        cookies = py_to_json(cookies_obj);
    } catch (const py::error_already_set& e) {
        std::cerr << "Failed to get cookies: " << e.what() << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "Failed to get cookies: " << e.what() << std::endl;
    }
    
    return cookies;
}

json HubInterfaceWrapper::get_headers() const {
    py::gil_scoped_acquire acquire;
    json headers;
    
    try {
        // Get api.session.headers
        py::object api = hub_interface_.attr("api");
        py::object session = api.attr("session");
        py::object headers_obj = session.attr("headers");
        headers = py_to_json(headers_obj);
    } catch (const py::error_already_set& e) {
        std::cerr << "Failed to get headers: " << e.what() << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "Failed to get headers: " << e.what() << std::endl;
    }
    
    return headers;
}

json HubInterfaceWrapper::py_to_json(const py::handle& obj) const {
    if (obj.is_none()) {
        return nullptr;
    }
    
    if (py::isinstance<py::bool_>(obj)) {
        return obj.cast<bool>();
    }
    
    if (py::isinstance<py::int_>(obj)) {
        return obj.cast<long>();
    }
    
    if (py::isinstance<py::float_>(obj)) {
        return obj.cast<double>();
    }
    
    if (py::isinstance<py::str>(obj)) {
        return obj.cast<std::string>();
    }
    
    if (py::isinstance<py::list>(obj)) {
        json arr = json::array();
        py::list list = obj.cast<py::list>();
        for (const auto& item : list) {
            arr.push_back(py_to_json(item));
        }
        return arr;
    }
    
    if (py::isinstance<py::dict>(obj)) {
        json dict = json::object();
        py::dict py_dict = obj.cast<py::dict>();
        for (const auto& item : py_dict) {
            std::string key = py::str(item.first).cast<std::string>();
            dict[key] = py_to_json(item.second);
        }
        return dict;
    }
    
    // Try to convert object to dict using __dict__
    if (py::hasattr(obj, "__dict__")) {
        py::object dict = obj.attr("__dict__");
        if (py::isinstance<py::dict>(dict)) {
            return py_to_json(dict);
        }
    }
    
    return nullptr;
}
