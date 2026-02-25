#ifndef DB_CLIENT_HPP
#define DB_CLIENT_HPP

#include <string>
#include <optional>
#include <libpq-fe.h>

class DbClient {
public:
    // Constructor with explicit parameters (loaded from config.json)
    DbClient(const std::string& host, int port, const std::string& dbname,
             const std::string& user, const std::string& password);
    ~DbClient();

    bool is_connected() const;

    // Returns true if a row exists in maps table for given map_id (TEXT)
    bool map_exists(const std::string& map_id);

    // Inserts a row into maps table; version may be empty
    bool insert_map(const std::string& map_id, const std::string& s3_key, const std::optional<std::string>& version = std::nullopt);

private:
    PGconn* conn_;

    // Builds a connection string from explicit parameters
    static std::string build_conninfo(const std::string& host, int port,
                                      const std::string& dbname,
                                      const std::string& user,
                                      const std::string& password);
};

#endif // DB_CLIENT_HPP
