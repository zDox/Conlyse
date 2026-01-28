#include <iostream>
#include <fstream>
#include <csignal>
#include "server_observer.hpp"
#include "account_pool.hpp"
#include "hub_interface_wrapper.hpp"

static std::unique_ptr<ServerObserver> g_observer;

void signal_handler(int signal) {
    if (g_observer) {
        g_observer->stop();
    }
    // Don't call exit() - let the program exit normally so destructors run properly
}

int main(int argc, char* argv[]) {
    // Register signal handlers
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    
    std::cout << "ServerObserver C++ version starting..." << std::endl;
    
    // Parse command line arguments
    std::string config_file = "config.json";
    std::string account_pool_file = "account_pool.json";
    
    if (argc > 1) {
        config_file = argv[1];
    }
    if (argc > 2) {
        account_pool_file = argv[2];
    }
    
    // Load configuration
    json config;
    try {
        std::ifstream config_stream(config_file);
        if (!config_stream.is_open()) {
            std::cerr << "Error: Could not open config file: " << config_file << std::endl;
            return 1;
        }
        config_stream >> config;
    } catch (const std::exception& e) {
        std::cerr << "Error loading config: " << e.what() << std::endl;
        return 1;
    }
    
    // Create account pool
    std::shared_ptr<AccountPool> account_pool;
    try {
        std::string webshare_token = "";
        if (config.contains("WEBSHARE_API_TOKEN")) {
            webshare_token = config["WEBSHARE_API_TOKEN"].get<std::string>();
        }
        
        account_pool = std::make_shared<AccountPool>(account_pool_file, webshare_token);
        std::cout << "Loaded " << account_pool->accounts.size() << " accounts" << std::endl;
        std::cout << "Loaded " << account_pool->proxies.size() << " proxies" << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "Error loading account pool: " << e.what() << std::endl;
        return 1;
    }
    
    // Create and run server observer
    int exit_code = 0;
    try {
        g_observer = std::make_unique<ServerObserver>(config, account_pool);
        
        std::cout << "Starting server observer..." << std::endl;
        bool success = g_observer->run();
        
        if (success) {
            std::cout << "ServerObserver completed successfully" << std::endl;
            exit_code = 0;
        } else {
            std::cerr << "ServerObserver failed" << std::endl;
            exit_code = 1;
        }
    } catch (const std::exception& e) {
        std::cerr << "Error running server observer: " << e.what() << std::endl;
        exit_code = 1;
    }

    // Explicitly destroy the observer to ensure Python cleanup happens before interpreter shutdown
    std::cout << "Cleaning up observer..." << std::endl;
    g_observer.reset();
    std::cout << "Observer cleanup complete" << std::endl;

    // Explicitly shutdown the Python interpreter to ensure proper cleanup order
    HubInterfaceWrapper::shutdown_python();

    return exit_code;
}
