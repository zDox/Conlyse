#include "observation_session.hpp"
#include <iostream>
#include <thread>
#include <chrono>

static const int MAX_RETRIES = 3;
static const int TIME_TILL_RETRY = 10;

json ObservationPackage::to_json() const {
    json j = {
        {"game_id", game_id},
        {"headers", headers},
        {"cookies", cookies},
        {"proxy", proxy},
        {"auth", auth.to_json()},
        {"client_version", client_version},
        {"game_server_address", game_server_address}
    };
    
    // Convert time_stamps map to JSON
    json ts = json::object();
    for (const auto& [key, value] : time_stamps) {
        ts[std::to_string(key)] = value;
    }
    j["time_stamps"] = ts;
    
    // Convert state_ids map to JSON
    json si = json::object();
    for (const auto& [key, value] : state_ids) {
        si[std::to_string(key)] = value;
    }
    j["state_ids"] = si;
    
    return j;
}

ObservationPackage ObservationPackage::from_json(const json& j) {
    ObservationPackage pkg;
    pkg.game_id = j.value("game_id", 0);
    pkg.headers = j.value("headers", json::object());
    pkg.cookies = j.value("cookies", json::object());
    pkg.proxy = j.value("proxy", json::object());
    pkg.client_version = j.value("client_version", 207);
    pkg.game_server_address = j.value("game_server_address", "");
    
    if (j.contains("auth")) {
        pkg.auth = AuthDetails::from_json(j["auth"]);
    }
    
    // Convert time_stamps from JSON to map
    if (j.contains("time_stamps") && j["time_stamps"].is_object()) {
        for (const auto& [key, value] : j["time_stamps"].items()) {
            try {
                int k = std::stoi(key);
                pkg.time_stamps[k] = value.get<int>();
            } catch (...) {}
        }
    }
    
    // Convert state_ids from JSON to map
    if (j.contains("state_ids") && j["state_ids"].is_object()) {
        for (const auto& [key, value] : j["state_ids"].items()) {
            try {
                int k = std::stoi(key);
                pkg.state_ids[k] = value.get<std::string>();
            } catch (...) {}
        }
    }
    
    return pkg;
}

ObservationSession::ObservationSession(int game_id,
                                     std::shared_ptr<Account> account,
                                     std::shared_ptr<StaticMapCache> map_cache,
                                     const std::string& storage_path,
                                     const std::string& metadata_path,
                                     const std::string& long_term_storage_path,
                                     int file_size_threshold)
    : game_id(game_id)
    , account(account)
    , map_cache_(map_cache)
    , storage_path_(storage_path)
    , metadata_path_(metadata_path)
    , long_term_storage_path_(long_term_storage_path)
    , file_size_threshold_(file_size_threshold)
    , storage_(nullptr)
{
    next_update_at = std::chrono::system_clock::now();
}

bool ObservationSession::needs_update(std::chrono::system_clock::time_point now) const {
    return now >= next_update_at;
}

std::unique_ptr<ObservationWorker> ObservationSession::create_worker() {
    return std::make_unique<ObservationWorker>(
        account,
        storage_path_,
        game_id,
        package_,
        map_cache_,
        metadata_path_,
        long_term_storage_path_,
        file_size_threshold_
    );
}

void ObservationSession::update_package(const ObservationPackage& other) {
    package_ = other;
}

void ObservationSession::reset() {
    package_ = ObservationPackage();
    ensure_storage()->update_resume_metadata(json::object());
}

RecordingStorage* ObservationSession::ensure_storage() {
    if (!storage_) {
        storage_ = std::make_unique<RecordingStorage>(
            storage_path_,
            metadata_path_,
            long_term_storage_path_,
            file_size_threshold_
        );
    }
    return storage_.get();
}

ObservationWorker::ObservationWorker(std::shared_ptr<Account> account,
                                   const std::string& storage_path,
                                   int game_id,
                                   const ObservationPackage& package,
                                   std::shared_ptr<StaticMapCache> map_cache,
                                   const std::string& metadata_path,
                                   const std::string& long_term_storage_path,
                                   int file_size_threshold)
    : account_(account)
    , game_id_(game_id)
    , package_(package)
    , map_cache_(map_cache)
{
    storage_ = std::make_unique<RecordingStorage>(
        storage_path,
        metadata_path,
        long_term_storage_path,
        file_size_threshold
    );
    storage_->setup_logging();
}

ObservationWorker::~ObservationWorker() {
    if (storage_) {
        storage_->teardown_logging();
    }
}

void ObservationWorker::on_request_response(const json& response) {
    storage_->update_resume_metadata(package_.to_json());
    storage_->save_response(response);
}

bool ObservationWorker::ensure_observation_package() {
    if (package_.game_id != 0) {
        return true;
    }
    
    json resume_metadata = storage_->get_resume_metadata();
    if (!resume_metadata.empty() && resume_metadata.contains("auth")) {
        std::cout << "Resuming from Storage for game " << game_id_ << std::endl;
        package_ = ObservationPackage::from_json(resume_metadata);
        return true;
    }
    
    std::cout << "Observation package not yet created, building package for game " 
             << game_id_ << std::endl;
    package_ = create_observation_package();
    return package_.game_id != 0;
}

ObservationPackage ObservationWorker::create_observation_package() {
    auto hub_itf = account_->get_interface();
    if (!hub_itf) {
        return ObservationPackage();
    }
    
    // Get authentication details
    AuthDetails auth = hub_itf->get_auth_details();
    json headers = hub_itf->get_headers();
    json cookies = hub_itf->get_cookies();
    
    // Build proxy dict
    json proxy = json::object();
    if (!hub_itf->get_proxy_http().empty()) {
        proxy["http"] = hub_itf->get_proxy_http();
    }
    if (!hub_itf->get_proxy_https().empty()) {
        proxy["https"] = hub_itf->get_proxy_https();
    }
    
    // For now, we need to call the Python GameApi to get game server address
    // This is a simplified version - in production you'd need to implement
    // the full game loading logic
    ObservationPackage pkg;
    pkg.game_id = game_id_;
    pkg.headers = headers;
    pkg.cookies = cookies;
    pkg.proxy = proxy;
    pkg.auth = auth;
    pkg.client_version = 207;
    
    // Try to determine game server address
    // This would need proper implementation via Python GameApi
    pkg.game_server_address = "";
    
    return pkg;
}

void ObservationWorker::reset_package() {
    account_->reset_interface();
    package_ = create_observation_package();
}

bool ObservationWorker::ensure_static_map_data(ObservationApi& api, int map_id) {
    if (map_cache_->is_cached(map_id)) {
        return true;
    }
    
    try {
        json static_map_data = api.get_static_map_data(map_id);
        map_cache_->save(map_id, static_map_data);
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Failed to get static map data: " << e.what() << std::endl;
        return false;
    }
}

bool ObservationWorker::is_game_ended(const json& response) {
    if (!response.is_object()) {
        return false;
    }
    
    if (!response.contains("result") || !response["result"].is_object()) {
        return false;
    }
    
    const auto& result = response["result"];
    if (!result.contains("states") || !result["states"].is_object()) {
        return false;
    }
    
    const auto& states = result["states"];
    for (const auto& [key, state] : states.items()) {
        if (state.is_object() && state.contains("gameEnded") && 
            state["gameEnded"].is_boolean() && state["gameEnded"].get<bool>()) {
            return true;
        }
    }
    
    return false;
}

bool ObservationWorker::run() {
    int attempt = 1;
    
    while (true) {
        std::cout << "Starting update for game " << game_id_ << std::endl;
        
        if (!ensure_observation_package()) {
            std::cerr << "Failed to create observation package" << std::endl;
            return false;
        }
        
        try {
            // Create observation API
            ObservationApi api(
                package_.headers,
                package_.cookies,
                package_.proxy,
                package_.auth,
                game_id_,
                package_.game_server_address,
                package_.client_version
            );
            
            // Fetch game state
            json game_state = api.request_game_state(package_.state_ids, package_.time_stamps);
            
            // Update package with new auth and connection details
            package_.auth = api.get_auth();
            package_.cookies = api.get_cookies();
            package_.headers = api.get_headers();
            package_.game_server_address = api.get_game_server_address();
            
            // Save response
            on_request_response(game_state);
            
            // Process map data
            try {
                if (game_state.contains("result") && game_state["result"].is_object()) {
                    const auto& result = game_state["result"];
                    if (result.contains("states") && result["states"].is_object()) {
                        const auto& states = result["states"];
                        if (states.contains("3") && states["3"].is_object()) {
                            const auto& state3 = states["3"];
                            if (state3.contains("map") && state3["map"].is_object()) {
                                const auto& map = state3["map"];
                                if (map.contains("mapID")) {
                                    int map_id = map["mapID"].get<int>();
                                    ensure_static_map_data(api, map_id);
                                }
                            }
                        }
                    }
                }
            } catch (const std::exception& e) {
                // Map data not available or invalid
            }
            
            // Check if game ended
            if (is_game_ended(game_state)) {
                return false;
            }
            
            return true;
            
        } catch (const std::runtime_error& e) {
            std::string error = e.what();
            
            // Handle authentication failure
            if (error.find("Authentication failed") != std::string::npos) {
                if (attempt >= MAX_RETRIES) {
                    std::cerr << "Authentication failed after " << MAX_RETRIES 
                             << " retries" << std::endl;
                    return false;
                }
                
                std::cerr << "Authentication failed, resetting package and retrying..." 
                         << std::endl;
                reset_package();
                attempt++;
                continue;
            }
            
            // Handle server errors
            if (error.find("HTTP status: 5") != std::string::npos) {
                std::cerr << "GameServer returned error, retrying in " 
                         << TIME_TILL_RETRY << " seconds..." << std::endl;
                std::this_thread::sleep_for(std::chrono::seconds(TIME_TILL_RETRY));
                continue;
            }
            
            // Handle network errors
            if (error.find("failed") != std::string::npos || 
                error.find("timeout") != std::string::npos) {
                std::cerr << "GameServer is not responding, retrying in " 
                         << TIME_TILL_RETRY << " seconds..." << std::endl;
                std::this_thread::sleep_for(std::chrono::seconds(TIME_TILL_RETRY));
                continue;
            }
            
            // Unknown error
            throw;
        }
    }
}
