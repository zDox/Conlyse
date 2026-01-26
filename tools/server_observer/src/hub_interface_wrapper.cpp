#include "hub_interface_wrapper.hpp"
#include <iostream>
#include <stdexcept>
#include <sstream>
#include <mutex>
#include <Python.h>

namespace py = pybind11;

// Python initialization guard
static bool python_initialized = false;
static std::mutex python_init_mutex;
static std::unique_ptr<py::scoped_interpreter> interpreter;

// Static shutdown function to be called before program exit
// This ensures Python cleanup happens before static destruction
void HubInterfaceWrapper::shutdown_python() {
    std::lock_guard<std::mutex> lock(python_init_mutex);

    if (python_initialized && Py_IsInitialized()) {
        std::cout << "Shutting down Python interpreter..." << std::endl;

        // Re-acquire the GIL to properly finalize
        py::gil_scoped_acquire acquire;

        // Destroy the interpreter explicitly
        interpreter.reset();
        python_initialized = false;

        std::cout << "Python interpreter shut down successfully" << std::endl;
    }
}

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
        // Note: py::scoped_interpreter automatically acquires the GIL
        interpreter = std::make_unique<py::scoped_interpreter>();
        python_initialized = true;
        // Release the GIL immediately to allow multi-threading
        // Without this, other threads cannot acquire the GIL
        PyEval_SaveThread();
    }

    // Acquire GIL for this thread to perform initialization
    py::gil_scoped_acquire acquire;

    try {
        // Set up the Python path
        // Use environment PYTHONPATH or current working directory
        py::module_ sys = py::module_::import("sys");
        py::list path = sys.attr("path");
        
        // Try to add the repository root to path if not already present
        // This allows imports to work from the repository structure
        const char* pythonpath_env = std::getenv("PYTHONPATH");
        if (pythonpath_env) {
            py::str pythonpath(pythonpath_env);
            if (!path.contains(pythonpath)) {
                path.insert(0, pythonpath);
            }
        }

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
    // GIL is automatically released when 'acquire' goes out of scope
}

void HubInterfaceWrapper::cleanup_python() {
    // Clean up Python objects while holding the GIL

    // First check if Python is still initialized
    if (!Py_IsInitialized()) {
        // Python is already shut down, nothing we can safely do
        return;
    }

    if (!python_initialized) {
        return;
    }

    // Acquire GIL for cleanup - this should work now that we're not using PyEval_SaveThread
    try {
        py::gil_scoped_acquire acquire;

        // Explicitly reset/clear Python objects to decrement their reference counts
        hub_interface_ = py::object();  // Reset to empty object
        python_module_ = py::module_();  // Reset to empty module

    } catch (const std::exception& e) {
        std::cerr << "Warning: Exception during Python cleanup: " << e.what() << std::endl;
    } catch (...) {
        std::cerr << "Warning: Unknown exception during Python cleanup" << std::endl;
    }
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
        details.user_id = auth_obj.attr("user_id").cast<long>();
        details.auth_tstamp = auth_obj.attr("auth_tstamp").cast<long>();
        
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
    GameApiData data;
    data.client_version = 207;
    data.map_id = "";
    
    try {
        py::gil_scoped_acquire acquire;

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
            if (py::isinstance<py::str>(map_id_obj)) {
                data.map_id = map_id_obj.cast<std::string>();
            }
        }
        
        // Get updated auth
        py::object auth_obj = game_api.attr("auth");
        if (!auth_obj.is_none()) {
            data.auth.auth = auth_obj.attr("auth").cast<std::string>();
            if (!auth_obj.attr("rights").is_none() ) {
                data.auth.rights = auth_obj.attr("rights").cast<std::string>();
            }
            if (!auth_obj.attr("user_id").is_none()) {
                data.auth.user_id = auth_obj.attr("user_id").cast<long>();
            }
            if (!auth_obj.attr("auth_tstamp").is_none()) {
                data.auth.auth_tstamp = std::stol(auth_obj.attr("auth_tstamp").cast<std::string>());
            }
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
        // Iterate directly over obj to avoid creating a copy
        for (const auto& item : obj) {
            arr.push_back(py_to_json(item));
        }
        return arr;
    }
    
    if (py::isinstance<py::dict>(obj)) {
        json dict = json::object();
        // For dict, we need to cast to access key-value pairs properly
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
