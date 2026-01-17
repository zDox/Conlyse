#include "hub_interface_wrapper.hpp"
#include <iostream>
#include <stdexcept>
#include <sstream>
#include <mutex>

// Python initialization guard
static bool python_initialized = false;
static std::mutex python_init_mutex;

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
    : hub_interface_(nullptr)
    , python_module_(nullptr)
    , authenticated_(false)
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
        Py_Initialize();
        python_initialized = true;
    }
    
    PyGILState_STATE gstate = PyGILState_Ensure();
    
    try {
        // Add the ConflictInterface path to sys.path
        PyRun_SimpleString("import sys");
        PyRun_SimpleString("sys.path.insert(0, '/home/runner/work/ConflictInterface/ConflictInterface')");
        
        // Import the HubInterface module
        PyObject* module_name = PyUnicode_DecodeFSDefault("conflict_interface.interface.hub_interface");
        python_module_ = PyImport_Import(module_name);
        Py_DECREF(module_name);
        
        if (!python_module_) {
            PyErr_Print();
            throw std::runtime_error("Failed to import HubInterface module");
        }
        
        // Get the HubInterface class
        PyObject* hub_interface_class = PyObject_GetAttrString(python_module_, "HubInterface");
        if (!hub_interface_class) {
            PyErr_Print();
            throw std::runtime_error("Failed to get HubInterface class");
        }
        
        // Create proxy dict
        PyObject* proxy_dict = PyDict_New();
        if (!proxy_http_.empty()) {
            PyDict_SetItemString(proxy_dict, "http", PyUnicode_FromString(proxy_http_.c_str()));
        }
        if (!proxy_https_.empty()) {
            PyDict_SetItemString(proxy_dict, "https", PyUnicode_FromString(proxy_https_.c_str()));
        }
        
        // Create HubInterface instance
        PyObject* args = PyTuple_Pack(1, proxy_dict);
        hub_interface_ = PyObject_CallObject(hub_interface_class, args);
        Py_DECREF(args);
        Py_DECREF(proxy_dict);
        Py_DECREF(hub_interface_class);
        
        if (!hub_interface_) {
            PyErr_Print();
            throw std::runtime_error("Failed to create HubInterface instance");
        }
    } catch (...) {
        PyGILState_Release(gstate);
        throw;
    }
    
    PyGILState_Release(gstate);
}

void HubInterfaceWrapper::cleanup_python() {
    PyGILState_STATE gstate = PyGILState_Ensure();
    
    if (hub_interface_) {
        Py_DECREF(hub_interface_);
        hub_interface_ = nullptr;
    }
    
    if (python_module_) {
        Py_DECREF(python_module_);
        python_module_ = nullptr;
    }
    
    PyGILState_Release(gstate);
}

bool HubInterfaceWrapper::login(const std::string& username, const std::string& password) {
    PyGILState_STATE gstate = PyGILState_Ensure();
    
    try {
        PyObject* args = PyTuple_Pack(2, 
            PyUnicode_FromString(username.c_str()),
            PyUnicode_FromString(password.c_str()));
        
        PyObject* result = call_method("login", args);
        Py_DECREF(args);
        
        if (result) {
            bool success = PyObject_IsTrue(result);
            Py_DECREF(result);
            authenticated_ = success;
            PyGILState_Release(gstate);
            return success;
        }
    } catch (const std::exception& e) {
        std::cerr << "Login failed: " << e.what() << std::endl;
    }
    
    PyGILState_Release(gstate);
    return false;
}

void HubInterfaceWrapper::logout() {
    authenticated_ = false;
}

AuthDetails HubInterfaceWrapper::get_auth_details() const {
    PyGILState_STATE gstate = PyGILState_Ensure();
    
    AuthDetails details;
    
    try {
        // Get the auth attribute from hub_interface
        PyObject* auth_obj = PyObject_GetAttrString(hub_interface_, "auth");
        if (!auth_obj || auth_obj == Py_None) {
            Py_XDECREF(auth_obj);
            PyGILState_Release(gstate);
            return details;
        }
        
        // Extract auth fields
        PyObject* auth_str = PyObject_GetAttrString(auth_obj, "auth");
        PyObject* rights_str = PyObject_GetAttrString(auth_obj, "rights");
        PyObject* user_id_int = PyObject_GetAttrString(auth_obj, "user_id");
        PyObject* auth_tstamp_int = PyObject_GetAttrString(auth_obj, "auth_tstamp");
        
        if (auth_str) {
            const char* auth_cstr = PyUnicode_AsUTF8(auth_str);
            if (auth_cstr) details.auth = auth_cstr;
            Py_DECREF(auth_str);
        }
        
        if (rights_str) {
            const char* rights_cstr = PyUnicode_AsUTF8(rights_str);
            if (rights_cstr) details.rights = rights_cstr;
            Py_DECREF(rights_str);
        }
        
        if (user_id_int) {
            details.user_id = PyLong_AsLong(user_id_int);
            Py_DECREF(user_id_int);
        }
        
        if (auth_tstamp_int) {
            details.auth_tstamp = PyLong_AsLong(auth_tstamp_int);
            Py_DECREF(auth_tstamp_int);
        }
        
        Py_DECREF(auth_obj);
    } catch (const std::exception& e) {
        std::cerr << "Failed to get auth details: " << e.what() << std::endl;
    }
    
    PyGILState_Release(gstate);
    return details;
}

std::vector<HubGameProperties> HubInterfaceWrapper::get_my_games() {
    PyGILState_STATE gstate = PyGILState_Ensure();
    std::vector<HubGameProperties> games;
    
    try {
        PyObject* result = call_method("get_my_games");
        if (result && PyList_Check(result)) {
            json games_json = py_to_json(result);
            for (const auto& game_json : games_json) {
                games.push_back(HubGameProperties::from_json(game_json));
            }
            Py_DECREF(result);
        }
    } catch (const std::exception& e) {
        std::cerr << "Failed to get my games: " << e.what() << std::endl;
    }
    
    PyGILState_Release(gstate);
    return games;
}

std::vector<HubGameProperties> HubInterfaceWrapper::get_global_games() {
    PyGILState_STATE gstate = PyGILState_Ensure();
    std::vector<HubGameProperties> games;
    
    try {
        PyObject* result = call_method("get_global_games");
        if (result && PyList_Check(result)) {
            json games_json = py_to_json(result);
            for (const auto& game_json : games_json) {
                games.push_back(HubGameProperties::from_json(game_json));
            }
            Py_DECREF(result);
        }
    } catch (const std::exception& e) {
        std::cerr << "Failed to get global games: " << e.what() << std::endl;
    }
    
    PyGILState_Release(gstate);
    return games;
}

json HubInterfaceWrapper::get_cookies() const {
    PyGILState_STATE gstate = PyGILState_Ensure();
    json cookies;
    
    try {
        // Get api.session.cookies
        PyObject* api = PyObject_GetAttrString(hub_interface_, "api");
        if (api) {
            PyObject* session = PyObject_GetAttrString(api, "session");
            if (session) {
                PyObject* cookies_obj = PyObject_GetAttrString(session, "cookies");
                if (cookies_obj) {
                    cookies = py_to_json(cookies_obj);
                    Py_DECREF(cookies_obj);
                }
                Py_DECREF(session);
            }
            Py_DECREF(api);
        }
    } catch (const std::exception& e) {
        std::cerr << "Failed to get cookies: " << e.what() << std::endl;
    }
    
    PyGILState_Release(gstate);
    return cookies;
}

json HubInterfaceWrapper::get_headers() const {
    PyGILState_STATE gstate = PyGILState_Ensure();
    json headers;
    
    try {
        // Get api.session.headers
        PyObject* api = PyObject_GetAttrString(hub_interface_, "api");
        if (api) {
            PyObject* session = PyObject_GetAttrString(api, "session");
            if (session) {
                PyObject* headers_obj = PyObject_GetAttrString(session, "headers");
                if (headers_obj) {
                    headers = py_to_json(headers_obj);
                    Py_DECREF(headers_obj);
                }
                Py_DECREF(session);
            }
            Py_DECREF(api);
        }
    } catch (const std::exception& e) {
        std::cerr << "Failed to get headers: " << e.what() << std::endl;
    }
    
    PyGILState_Release(gstate);
    return headers;
}

PyObject* HubInterfaceWrapper::call_method(const char* method_name, PyObject* args) {
    if (!hub_interface_) {
        throw std::runtime_error("HubInterface not initialized");
    }
    
    PyObject* method = PyObject_GetAttrString(hub_interface_, method_name);
    if (!method) {
        PyErr_Print();
        throw std::runtime_error(std::string("Method not found: ") + method_name);
    }
    
    PyObject* result;
    if (args) {
        result = PyObject_CallObject(method, args);
    } else {
        result = PyObject_CallObject(method, nullptr);
    }
    
    Py_DECREF(method);
    
    if (!result) {
        PyErr_Print();
        throw std::runtime_error(std::string("Method call failed: ") + method_name);
    }
    
    return result;
}

json HubInterfaceWrapper::py_to_json(PyObject* obj) const {
    if (!obj || obj == Py_None) {
        return nullptr;
    }
    
    if (PyBool_Check(obj)) {
        return obj == Py_True;
    }
    
    if (PyLong_Check(obj)) {
        return PyLong_AsLong(obj);
    }
    
    if (PyFloat_Check(obj)) {
        return PyFloat_AsDouble(obj);
    }
    
    if (PyUnicode_Check(obj)) {
        const char* str = PyUnicode_AsUTF8(obj);
        return str ? std::string(str) : "";
    }
    
    if (PyList_Check(obj)) {
        json arr = json::array();
        Py_ssize_t size = PyList_Size(obj);
        for (Py_ssize_t i = 0; i < size; i++) {
            PyObject* item = PyList_GetItem(obj, i);
            arr.push_back(py_to_json(item));
        }
        return arr;
    }
    
    if (PyDict_Check(obj)) {
        json dict = json::object();
        PyObject *key, *value;
        Py_ssize_t pos = 0;
        
        while (PyDict_Next(obj, &pos, &key, &value)) {
            const char* key_str = PyUnicode_AsUTF8(key);
            if (key_str) {
                dict[key_str] = py_to_json(value);
            }
        }
        return dict;
    }
    
    // Try to convert object to dict using __dict__
    if (PyObject_HasAttrString(obj, "__dict__")) {
        PyObject* dict = PyObject_GetAttrString(obj, "__dict__");
        if (dict && PyDict_Check(dict)) {
            json result = py_to_json(dict);
            Py_DECREF(dict);
            return result;
        }
        Py_XDECREF(dict);
    }
    
    return nullptr;
}
