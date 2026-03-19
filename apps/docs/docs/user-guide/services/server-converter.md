---
id: server-converter
title: Server Converter
description: Overview and operations for the Server Converter service.
---

# Server Converter
The `ServerConverter` service consumes game responses from Redis (published by `server_observer`), converts them into replay files, stores replay artifacts in hot/cold storage, and updates replay metadata in PostgreSQL.

This page expands on `deployment.md` by documenting every configuration setting supported by the converter.

## How it fits in the stack
`server_observer` captures game state and pushes entries to a Redis stream. `server_converter` reads that stream, caches/processes responses, writes local `.conrp` replay files, optionally uploads them to S3-compatible storage, and updates status in PostgreSQL for API consumers.

## Configuration reference (JSON)

Top-level schema:

```json
{
  "redis": { /* RedisConfig */ },
  "storage": { /* StorageConfig */ },
  "database": { /* DatabaseConfig */ },
  "batch_size": 10,
  "check_interval_seconds": 5,
  "metrics_port": 8000
}
```

### Global settings
`batch_size` (integer, optional, default: `10`)
:: Minimum number of cached responses for a `(game_id, player_id)` pair before the converter processes that replay.

`check_interval_seconds` (integer, optional, default: `5`)
:: Idle/poll interval used by the processing loop.
:: Also used as Redis blocking read timeout (`XREADGROUP ... BLOCK`) for the first read in each loop cycle.

`metrics_port` (integer, optional, default: `8000`)
:: Port where Prometheus metrics HTTP server is started.
:: Metrics endpoint: `http://<host>:<metrics_port>/metrics`.

### `redis` object
`host` (string, optional, default: `"localhost"`)
:: Redis host.

`port` (integer, optional, default: `6379`)
:: Redis port.

`db` (integer, optional, default: `0`)
:: Redis logical DB index.

`password` (string or `null`, optional, default: `null`)
:: Redis password; when omitted/`null`, no auth password is used.

`stream_name` (string, optional, default: `"game_responses"`)
:: Redis stream name containing observer responses.

`consumer_group` (string, optional, default: `"server_converter"`)
:: Consumer group name used with `XREADGROUP`.
:: The service attempts to create the group on startup (`mkstream=true`).

`consumer_name` (string, optional, default: `"converter_1"`)
:: Consumer name within the consumer group.
:: For horizontal scaling, keep `stream_name` and `consumer_group` shared, but give each instance a unique `consumer_name`.

#### Redis payload expectations
Each stream entry is expected to include:
- `metadata`: JSON with response metadata fields
- `response`: zstd-compressed response payload

Converter behavior:
- Successfully cached messages are acknowledged (`XACK`).
- Poison/unparseable entries are also acknowledged to avoid infinite retry loops.

### `storage` object
`hot_storage_dir` (string/path, required)
:: Directory for local replay files.
:: Created automatically if missing.

`cold_storage_enabled` (boolean, optional, default: `false`)
:: Enables S3-compatible cold storage behavior.
:: If `true`, you should provide a valid `storage.s3` object.

`always_update_cold_storage` (boolean, optional, default: `true`)
:: If `true`, replay snapshots are uploaded after create/append operations.
:: If `false`, uploads happen on finalization (when replay is marked completed).

`s3` (object, conditionally required)
:: S3-compatible settings block used when `cold_storage_enabled=true`.
:: If missing, cold storage manager is not initialized.

#### Hot storage layout
Given `hot_storage_dir`, the converter uses:
- replay file: `game_<game_id>_player_<player_id>.conrp`
- response cache dir: `.response_cache/`
- response cache file: `.response_cache/game_<game_id>_player_<player_id>.jsonl`

### `storage.s3` object
`endpoint_url` (string, required)
:: S3 endpoint URL, e.g. `http://minio:9000`.

`access_key` (string, required)
:: S3 access key.

`secret_key` (string, required)
:: S3 secret key.

`bucket_name` (string, required)
:: Destination bucket for replay uploads.

`region` (string, optional, default: `"us-east-1"`)
:: Region name used by boto3 client initialization.

#### Bucket and key behavior
- Bucket existence is checked on startup; converter attempts to create it if missing.
- Replay upload key format: `replays/game_<game_id>_player_<player_id>.conrp`.

### `database` object
`host` (string, optional, default: `"localhost"`)
:: PostgreSQL host.

`port` (integer, optional, default: `5432`)
:: PostgreSQL port.

`database` (string, optional, default: `"replays"`)
:: Database name.

`user` (string, optional, default: `"postgres"`)
:: Database user.

`password` (string, optional, default: `""`)
:: Database password.

Converter DB behavior:
- Connects at startup and ensures required tables exist.
- Tracks replay status transitions and response counts.
- Stores hot storage path and S3 key metadata used by downstream services.

## Monitoring
Prometheus metrics endpoint:
- `http://<host>:<metrics_port>/metrics`

Scaling guidance with consumer groups:
- same `redis.stream_name`
- same `redis.consumer_group`
- unique `redis.consumer_name` per converter instance
