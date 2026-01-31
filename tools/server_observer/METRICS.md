# Prometheus Metrics for Server Observer

## Overview

The server observer now exposes Prometheus metrics for monitoring game recording sessions. These metrics can be visualized using Grafana dashboards.

## Configuration

Add the following to your `config.json` to enable metrics exposition:

```json
{
  "metrics_port": 9090,
  ...other config...
}
```

If `metrics_port` is not specified or is `null`, metrics exposition will be disabled.

## Accessing Metrics

Once the server is running with metrics enabled, you can access the metrics endpoint at:

```
http://<server-ip>:<metrics_port>/metrics
```

For example, if running locally on port 9090:
```
http://localhost:9090/metrics
```

## Available Metrics

### Game Lifecycle Metrics

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `games_started_total` | Counter | `scenario_id` | Total number of games started for recording |
| `games_completed_total` | Counter | `scenario_id` | Total number of games completed successfully |
| `games_failed_total` | Counter | `error_type` | Total number of games that failed during recording |
| `active_games` | Gauge | `scenario_id` | Current number of active game recordings |

**Error Types:**
- `auth_failed` - Authentication failures
- `server_error` - Game server errors
- `network_error` - Network connectivity issues
- `package_creation_failed` - Failed to create observation package
- `unknown_error` - Other errors

### HTTP Request Metrics

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `http_requests_total` | Counter | - | Total number of HTTP requests completed |
| `inflight_requests` | Gauge | - | Current number of in-flight HTTP requests |
| `http_request_duration_seconds` | Histogram | `client=httpclient` | HTTP request latency distribution |

**Histogram Buckets:** 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0 seconds

### Update Scheduling Metrics

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `missed_update_intervals_total` | Counter | - | Number of update intervals missed (>10s off schedule) |
| `scheduled_update_latency_seconds` | Histogram | - | Latency between scheduled update time and actual execution |
