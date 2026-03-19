---
id: server-observer
title: Server Observer
description: Overview and operations for the Server Observer service.
---

# Server Observer
The `ServerObserver` is the component that continuously discovers and records live Conflict games. It coordinates observation sessions, periodically updates them, persists state to PostgreSQL, stores per-game artifacts locally, and publishes the responses obtained from the CoN servers into a Redis stream for `Server Converter` to process.

## How it works

At a high level, `ServerObserver` runs an always-on loop:

1. Loads your TOML configuration and an `account_pool.json` file.
2. Initializes connections to:
   - PostgreSQL (game/replay metadata and recording state)
   - Redis (publishing to a stream)
   - S3-compatible storage (ensures the bucket exists, used for static map assets)
3. Keeps a scheduler that:
   - limits how many sessions run in parallel
   - runs per-session updates on a target cadence (`update_interval`)
   - limits concurrency for the first update of new sessions (`max_parallel_first_updates`)
4. Optionally runs `GameFinder`:
   - scans for new games matching configured `scenario_ids`
   - marks discovered games in the database
   - starts new observation sessions when capacity and account limits allow
5. For each observation session:
   - joins a game using an observer account from the account pool (and an assigned proxy)
   - on each update, requests game state, compresses the result with zstd, and publishes it to Redis
   - writes local recording logs and resume metadata, so a session can continue after restarts

When a game is detected as ended, the session is finalized and the database recording state is updated.


## Configuration reference (TOML)

The configuration file is TOML. The Rust code reads the following settings.

**Operational note:** Keep the number of concurrent recordings low and the `update_interval` high. If you poll too aggressively, you may overload the game servers, trigger rate-limiting or risk IP-ban.

### Top-level keys

`webshare_api_token` (required)
: Webshare API token used to fetch proxy information for the account pool.

`metrics_port` (optional)
: Port number for the Prometheus metrics HTTP server. If this key is missing or cannot be parsed as a `u16`, the metrics server is disabled.

`max_parallel_recordings` (optional, default: `1`)
: Maximum total number of concurrent observation sessions.

`max_parallel_normal_recordings` (optional, default: same as `max_parallel_recordings`)
: Maximum number of "normal" (non-priority) sessions running at once. Priority sessions can still run up to the total cap defined by `max_parallel_recordings`.

`max_parallel_updates` (optional, default: `1`)
: Maximum number of concurrent session updates the scheduler can start at once.

`max_parallel_first_updates` (optional, default: `1`)
: Maximum number of concurrent "first updates" across sessions. A session's first update is limited separately from the normal update cap.

`update_interval` (optional, default: `300.0`)
: Target interval in seconds between successful updates for each active session. The scheduler uses this cadence and spreads load by applying an offset derived from `game_id`.

`output_dir` (optional, default: `./recordings`)
: Base directory where each game session writes its local artifacts (logs, resume metadata cache, etc.).

`output_metadata_dir` (optional, default: empty)
: If empty or omitted, per-game metadata is stored alongside the per-game output directory. If set, per-game metadata is stored under this directory (with a `game_<id>` subdirectory).

### `[database]` (required)

These values are used to connect to PostgreSQL and validate connectivity at startup.

`host` (required)
: Database host name.

`port` (required)
: Database port (as an integer).

`database` (required)
: PostgreSQL database name.

`user` (required)
: Database user.

`password` (required)
: Database password.

### `[redis]` (required)

This section configures the Redis publisher that writes observation results to a Redis stream.

`host` (required)
: Redis host name.

`port` (required)
: Redis port (as an integer).

`stream_name` (optional, default: `game_responses`)
: Redis stream name used for publishing entries.

`password` (optional)
: If set, Redis connections use this password. If omitted, no password is used.

Publishing format
: Each stream entry includes fields:
: - `metadata`: JSON-serialized `ResponseMetadata`
: - `response`: zstd-compressed response bytes

### `[storage.s3]` (required)

This section configures S3-compatible storage for static map assets.

`endpoint_url` (required)
: S3 endpoint URL (for example `http://minio:9000`).

`access_key` (required)
: S3 access key.

`secret_key` (required)
: S3 secret key.

`bucket_name` (required)
: Bucket where objects are stored.

`region` (required, but may be empty)
: Region string used when creating the bucket.

If `region` is an empty string, the Rust code will not send a region override when creating the bucket.

Bucket creation behavior
: On startup, the service verifies the bucket exists and attempts to create it if missing.

### `[game_finder]` (optional section)

If present in your TOML, `ServerObserver` can automatically discover games to record and start new sessions.

`enabled` (optional, default: `false`)
: Enables/disables scanning for new games.

`scan_interval_seconds` (optional, default: `300.0`)
: Time between scan iterations (while enabled).

`scenario_ids` (optional, default: empty list)
: Scenario IDs that are eligible for observation during scanning.

`max_games_per_scan` (optional, default: derived from `max_parallel_recordings`)
: Maximum number of discovered games the observer will try to start during a scanning iteration.

`max_guest_games_per_account` (optional, default: `-1`): Per-account cap for how many guest games can be active at the same time.

Behavior note for values `<= 0`: If this value is `0` or negative, it is treated as "no per-account cap" (unlimited) by the account pool logic.

## `account_pool.json` reference

`ServerObserver` loads an account pool JSON file that describes the accounts it can use to join and observe games, and (optionally) request proxy assignments.

Expected top-level structure:

```json
{
  "accounts": [
    {
      "username": "...",
      "password": "...",
      "email": "...",
      "proxy_id": "",
      "proxy_url": ""
    }
  ]
}
```

### `accounts[]` fields

`username` (required)
: Account login name used to join games.

`password` (required)
: Account password.

`email` (required in the example; used as an identifier in the pool)
: Account email.

`proxy_id` (optional, default: empty string)
: If set (non-empty), this should be the proxy ID as returned by Webshare (the IDs are fetched from the Webshare API at startup).

`proxy_url` (optional, default: empty string)
: Alternative to `proxy_id`. If `proxy_id` is empty but `proxy_url` is set, the service tries to find a matching Webshare proxy entry by comparing the Webshare `proxy_url()` with your provided `proxy_url`.

### Proxy assignment rules (high level)

At startup, `ServerObserver` fetches the available proxies from Webshare using `webshare_api_token`, then assigns proxies to accounts:

- If `proxy_id` points to a proxy that exists in the fetched proxy list, that proxy is used.
- If `proxy_id` is empty and `proxy_url` is set, the service attempts to map your `proxy_url` to a fetched Webshare proxy entry.
- If an account cannot be assigned a requested proxy, the service assigns an unassigned proxy from the fetched pool (if available).
- If there are no proxies available, accounts may be skipped.

If network errors are detected during updates, the service may reset an account's proxy by re-fetching proxies from Webshare and re-assigning a different unassigned proxy.

## Metrics and logging

### Prometheus metrics

If `metrics_port` is set, the service exposes Prometheus metrics via:

`http://<host>:<metrics_port>/metrics`

### Logging

The service uses Rust `tracing`. You can control log verbosity using `RUST_LOG`.

Example:

```bash
export RUST_LOG=info
```

If `RUST_LOG` is not set, the service defaults to `info`.