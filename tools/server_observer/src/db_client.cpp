#include "db_client.hpp"
#include <cstdlib>
#include <sstream>

static std::string getenv_or_empty(const char* key) {
    const char* v = std::getenv(key);
    return v ? std::string(v) : std::string();
}

std::string DbClient::build_conninfo_from_env() {
    std::ostringstream ss;
    auto host = getenv_or_empty("PGHOST");
    auto port = getenv_or_empty("PGPORT");
    auto db   = getenv_or_empty("PGDATABASE");
    auto user = getenv_or_empty("PGUSER");
    auto pass = getenv_or_empty("PGPASSWORD");

    if (!host.empty()) ss << " host=" << host;
    if (!port.empty()) ss << " port=" << port;
    if (!db.empty())   ss << " dbname=" << db;
    if (!user.empty()) ss << " user=" << user;
    if (!pass.empty()) ss << " password=" << pass;
    return ss.str();
}

DbClient::DbClient() : conn_(nullptr) {
    std::string conninfo = build_conninfo_from_env();
    conn_ = PQconnectdb(conninfo.c_str());
}

DbClient::~DbClient() {
    if (conn_) {
        PQfinish(conn_);
        conn_ = nullptr;
    }
}

bool DbClient::is_connected() const {
    return conn_ && PQstatus(conn_) == CONNECTION_OK;
}

bool DbClient::map_exists(const std::string& map_id) {
    if (!is_connected()) return false;

    const char* paramValues[1];
    paramValues[0] = map_id.c_str();

    PGresult* res = PQexecParams(
        conn_,
        "SELECT 1 FROM maps WHERE map_id = $1 LIMIT 1",
        1,
        nullptr,
        paramValues,
        nullptr,
        nullptr,
        0
    );

    if (PQresultStatus(res) != PGRES_TUPLES_OK) {
        PQclear(res);
        return false;
    }

    int rows = PQntuples(res);
    PQclear(res);
    return rows > 0;
}

bool DbClient::insert_map(const std::string& map_id, const std::string& s3_key, const std::optional<std::string>& version) {
    if (!is_connected()) return false;

    const char* paramValues[3];
    int nParams = 0;

    paramValues[nParams++] = map_id.c_str();
    const char* version_c = version.has_value() ? version->c_str() : nullptr;
    paramValues[nParams++] = version_c;
    paramValues[nParams++] = s3_key.c_str();

    PGresult* res = PQexecParams(
        conn_,
        "INSERT INTO maps (map_id, version, s3_key, created_at, updated_at) VALUES ($1, $2, $3, NOW(), NOW())",
        nParams,
        nullptr,
        paramValues,
        nullptr,
        nullptr,
        0
    );

    bool ok = PQresultStatus(res) == PGRES_COMMAND_OK;
    PQclear(res);
    return ok;
}
