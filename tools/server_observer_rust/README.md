## Rust Server Observer

This crate is a Rust rewrite of the existing C++ `ServerObserver` in `tools/server_observer`. It is intended to be behaviourally compatible with the current pipeline:

- C++/Rust **observer** discovers games, records responses, caches static maps, and publishes compressed responses into Redis.
- Python **converter** (`tools/server_converter`) consumes Redis messages and builds replays, using Postgres and S3/MinIO for metadata and storage.

### Building

From `tools/server_observer_rust`:

```bash
cargo build
```

The crate uses Tokio, reqwest, Redis, Postgres (`tokio-postgres` + `bb8`), S3/MinIO (`aws-sdk-s3`), zstd, and Prometheus/axum for metrics.

### Configuration

Configuration is loaded from a `config.toml` file in the working directory using the [`config`](https://crates.io/crates/config) crate. The TOML structure mirrors the configuration used by the existing C++ observer:

- `database`: Postgres connection parameters (host, port, database, user, password).
- `redis`: Redis stream configuration (host, port, stream_name, optional password).
- `storage.static_maps_dir`: Local directory for static map cache.
- `storage.s3`: S3/MinIO settings (endpoint_url, access_key, secret_key, bucket_name, region).
- `metrics_port`: Port on which to expose Prometheus metrics (optional).

See `config.example.toml` for a complete example; copy it to `config.toml` and adjust values for your environment.

Account and proxy information are loaded from `account_pool.json`, matching the current JSON format (`WEBSHARE_API_TOKEN`, `accounts` array, proxy metadata).

### Status

- **Implemented**:
  - Async Postgres client (`DbClient`) mirroring the `maps` table contract.
  - Redis publisher that zstd‑compresses JSON responses and publishes to a Redis stream compatible with the Python `RedisStreamConsumer`.
  - S3/MinIO client using `aws-sdk-s3` for static map uploads.
  - Static map cache that compresses JSON with zstd, caches locally, uploads to S3, and records metadata in Postgres.
  - Account pool and WebShare proxy fetching, including guest account rotation.
  - Recording registry (JSON on disk) compatible with the existing registry semantics.
  - Prometheus `/metrics` endpoint using the `prometheus` crate and `axum`.
  - Skeleton `GameFinder` for future integration with a Rust or Python hub interface.

- **Planned / to be wired**:
  - Full observer orchestration (game discovery, scheduling, per‑game observation loop).
  - Direct integration with the existing Python hub interface / game API (or a pure‑Rust hub client).
  - End‑to‑end contract tests against the Python `ServerConverter` (see `COMPATIBILITY.md`).

### Cutover

For a big‑bang cutover from C++ to Rust:

1. Deploy the Rust observer alongside the existing C++ observer in a staging environment.
2. Follow the checklist in `COMPATIBILITY.md` to validate Redis, Postgres, S3/MinIO, and metrics compatibility.
3. When satisfied, stop the C++ observer, start the Rust observer with the same configuration, and monitor:
   - Redis stream consumption by the Python converter.
   - Prometheus metrics and logs for errors, retries, and throughput.
4. Keep a rollback path by retaining the C++ observer deployment until the Rust observer has been stable for an agreed period.

