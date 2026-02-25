#include "db_client.hpp"
#include <cstdlib>
#include <sstream>

std::string DbClient::build_conninfo(const std::string& host, int port,
                                      const std::string& dbname,
                                      const std::string& user,
                                      const std::string& password) {
    std::ostringstream ss;
    if (!host.empty()) ss << " host=" << host;
    if (port > 0) ss << " port=" << port;
    if (!dbname.empty()) ss << " dbname=" << dbname;
    if (!user.empty()) ss << " user=" << user;
    if (!password.empty()) ss << " password=" << password;
    return ss.str();
}

DbClient::DbClient(const std::string& host, int port, const std::string& dbname,
                   const std::string& user, const std::string& password)
    : conn_(nullptr) {
    std::string conninfo = build_conninfo(host, port, dbname, user, password);
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
