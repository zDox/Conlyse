use serde::{Deserialize, Serialize};

/// Metadata attached to each game server response published to Redis.
///
/// Wire contract with server_converter (Python):
///   Redis stream entry fields:
///     - `metadata`: JSON string of this struct
///     - `response`: zstd-compressed response body bytes
///
/// The Python consumer parses `metadata` back into a dict with the same
/// field names and integer semantics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResponseMetadata {
    /// Unix timestamp in milliseconds when the response was recorded.
    pub timestamp: i64,
    /// Game identifier.
    pub game_id: i64,
    /// Player identifier (currently 0 for guest observer sessions).
    pub player_id: i64,
    /// Game client version used to communicate with the server.
    pub client_version: i64,
    /// Static map identifier associated with this response, if any.
    ///
    /// This is a string field to match the map IDs used by the game
    /// servers. It is optional on the wire; older payloads may omit it.
    #[serde(default)]
    pub map_id: String,
}

