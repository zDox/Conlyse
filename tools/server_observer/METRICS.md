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

## Prometheus Queries

### Completed Games in the Last Hour by Scenario ID
```promql
increase(games_completed_total[1h])
```

### Failed Games in the Last Hour
```promql
sum(increase(games_failed_total[1h])) by (error_type)
```

### Started Games in the Last Hour by Scenario ID
```promql
increase(games_started_total[1h])
```

### Active Recording Games by Scenario ID
```promql
active_games
```

### Min/Max/Average Inflight Requests over the Last 300s
```promql
# Minimum inflight requests
min_over_time(inflight_requests[5m])

# Maximum inflight requests
max_over_time(inflight_requests[5m])

# Average inflight requests
avg_over_time(inflight_requests[5m])
```

### Min/Max/Average Requests Per Second over the Last 300s
```promql
# Current rate (requests per second)
rate(http_requests_total[1m])

# Minimum RPS over 5 minutes
min_over_time(rate(http_requests_total[1m])[5m:])

# Maximum RPS over 5 minutes
max_over_time(rate(http_requests_total[1m])[5m:])

# Average RPS over 5 minutes
avg_over_time(rate(http_requests_total[1m])[5m:])
```

### Missed Update Intervals in the Last Hour
```promql
increase(missed_update_intervals_total[1h])
```

### Request Latency Percentiles
```promql
# 50th percentile (median)
histogram_quantile(0.5, rate(http_request_duration_seconds_bucket[5m]))

# 95th percentile
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# 99th percentile
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```

## Grafana Dashboard Examples

### Panel: Active Games by Scenario
- **Query:** `active_games`
- **Visualization:** Graph or Gauge
- **Legend:** `{{scenario_id}}`

### Panel: Games Started/Completed/Failed (Last Hour)
- **Query 1:** `increase(games_started_total[1h])`
- **Query 2:** `increase(games_completed_total[1h])`
- **Query 3:** `sum(increase(games_failed_total[1h]))`
- **Visualization:** Bar chart or Time series

### Panel: Request Latency Heatmap
- **Query:** `rate(http_request_duration_seconds_bucket[5m])`
- **Visualization:** Heatmap

### Panel: Requests Per Second
- **Query:** `rate(http_requests_total[1m])`
- **Visualization:** Graph

### Panel: Inflight Requests
- **Query:** `inflight_requests`
- **Visualization:** Graph with min/max/avg annotations

## Integration with Prometheus

Add the following to your Prometheus `prometheus.yml` configuration:

```yaml
scrape_configs:
  - job_name: 'server_observer'
    static_configs:
      - targets: ['<server-ip>:<metrics_port>']
        labels:
          instance: 'server_observer'
          environment: 'production'
    scrape_interval: 15s
```

Replace `<server-ip>` and `<metrics_port>` with your actual values.

## Notes

- All time-based aggregations (min/max/avg over time windows) are handled by Prometheus queries, not by the application itself
- Histogram metrics automatically provide `_count`, `_sum`, and `_bucket` metrics for flexible aggregation
- Counter metrics are monotonically increasing and should be used with `rate()` or `increase()` functions
- Gauge metrics represent instantaneous values and can go up or down

## Troubleshooting

### Metrics endpoint not accessible
- Ensure `metrics_port` is configured in `config.json`
- Check firewall rules allow access to the metrics port
- Verify the server started successfully with `"Metrics exposition started on 0.0.0.0:<port>"` in the logs

### No data in Prometheus
- Verify Prometheus is scraping the endpoint (check Prometheus targets page)
- Ensure the scrape interval matches your expected data freshness
- Check for network connectivity between Prometheus and the server observer

### Missing scenario_id labels
- This can happen if games are started before the registry is fully initialized
- Scenario ID will be `-1` or missing for such cases
