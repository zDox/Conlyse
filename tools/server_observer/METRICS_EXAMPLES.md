# Example Configuration for Prometheus Metrics

## config.json Example

```json
{
  "max_parallel_recordings": 24000,
  "max_parallel_updates": 100,
  "max_parallel_first_updates": 50,
  "update_interval": 60.0,
  "update_worker_threads": 8,
  "request_manager_threads": 4,
  "max_in_flight_requests": 200,
  "output_dir": "./recordings",
  "output_metadata_dir": "./metadata",
  "long_term_storage_path": "/mnt/storage/recordings",
  "file_size_threshold": 10485760,
  "registry_path": "./metadata/server_observer_registry.json",
  "metrics_port": 9090,
  "scenario_ids": [1, 2, 3, 4, 5],
  "game_finder": {
    "scan_interval": 30,
    "max_games_per_scan": 100
  }
}
```

## Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'game-recording'
    environment: 'production'

scrape_configs:
  - job_name: 'server_observer'
    static_configs:
      - targets: ['server-observer:9090']
        labels:
          service: 'game-recorder'
          instance: 'observer-01'
```

## Example Grafana Dashboard JSON

```json
{
  "dashboard": {
    "title": "Game Recording Server",
    "panels": [
      {
        "title": "Active Games by Scenario",
        "targets": [
          {
            "expr": "active_games",
            "legendFormat": "Scenario {{scenario_id}}"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Games Started/Completed (Last Hour)",
        "targets": [
          {
            "expr": "increase(games_started_total[1h])",
            "legendFormat": "Started - Scenario {{scenario_id}}"
          },
          {
            "expr": "increase(games_completed_total[1h])",
            "legendFormat": "Completed - Scenario {{scenario_id}}"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Failed Games by Error Type",
        "targets": [
          {
            "expr": "sum by(error_type) (increase(games_failed_total[1h]))",
            "legendFormat": "{{error_type}}"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Requests Per Second",
        "targets": [
          {
            "expr": "rate(http_requests_total[1m])",
            "legendFormat": "RPS"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Inflight Requests (5min window)",
        "targets": [
          {
            "expr": "inflight_requests",
            "legendFormat": "Current"
          },
          {
            "expr": "min_over_time(inflight_requests[5m])",
            "legendFormat": "Min (5m)"
          },
          {
            "expr": "max_over_time(inflight_requests[5m])",
            "legendFormat": "Max (5m)"
          },
          {
            "expr": "avg_over_time(inflight_requests[5m])",
            "legendFormat": "Avg (5m)"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Request Latency Percentiles",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "p50"
          },
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "p95"
          },
          {
            "expr": "histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "p99"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Missed Update Intervals (Last Hour)",
        "targets": [
          {
            "expr": "increase(missed_update_intervals_total[1h])",
            "legendFormat": "Missed Intervals"
          }
        ],
        "type": "singlestat"
      }
    ]
  }
}
```

## Prometheus Alerting Rules

```yaml
# alerts.yml
groups:
  - name: game_recording_alerts
    interval: 30s
    rules:
      - alert: HighFailureRate
        expr: rate(games_failed_total[5m]) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High game failure rate"
          description: "Game failure rate is {{ $value }} failures/sec over the last 5 minutes"
      
      - alert: NoGamesStarting
        expr: rate(games_started_total[5m]) == 0
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "No new games being started"
          description: "No games have been started in the last 10 minutes"
      
      - alert: HighRequestLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High request latency"
          description: "95th percentile request latency is {{ $value }}s"
      
      - alert: TooManyMissedIntervals
        expr: rate(missed_update_intervals_total[5m]) > 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Too many missed update intervals"
          description: "Missed {{ $value }} intervals/sec over the last 5 minutes"
      
      - alert: MaxInflightRequestsReached
        expr: inflight_requests >= 190
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Approaching max inflight requests limit"
          description: "Inflight requests ({{ $value }}) approaching limit of 200"
```

## Testing the Metrics Endpoint

```bash
# Start the server with metrics enabled
./server_observer config.json account_pool.json

# Check if metrics endpoint is accessible
curl http://localhost:9090/metrics

# Expected output (sample):
# HELP games_started_total Total number of games started for recording
# TYPE games_started_total counter
# games_started_total{scenario_id="1"} 523
# games_started_total{scenario_id="2"} 891
# 
# HELP games_completed_total Total number of games completed successfully
# TYPE games_completed_total counter
# games_completed_total{scenario_id="1"} 498
# games_completed_total{scenario_id="2"} 856
# 
# HELP active_games Number of currently active game recordings
# TYPE active_games gauge
# active_games{scenario_id="1"} 25
# active_games{scenario_id="2"} 35
# 
# HELP http_requests_total Total number of HTTP requests completed
# TYPE http_requests_total counter
# http_requests_total 15234
# 
# HELP inflight_requests Current number of in-flight HTTP requests
# TYPE inflight_requests gauge
# inflight_requests 42
```

## Docker Compose Example

```yaml
version: '3.8'

services:
  server_observer:
    build: .
    volumes:
      - ./config.json:/app/config.json
      - ./account_pool.json:/app/account_pool.json
      - ./recordings:/app/recordings
      - ./metadata:/app/metadata
    ports:
      - "9090:9090"  # Metrics port
    networks:
      - monitoring
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - ./alerts.yml:/etc/prometheus/alerts.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
    ports:
      - "9091:9090"
    networks:
      - monitoring
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    ports:
      - "3000:3000"
    networks:
      - monitoring
    restart: unless-stopped
    depends_on:
      - prometheus

networks:
  monitoring:
    driver: bridge

volumes:
  prometheus_data:
  grafana_data:
```

## Quick Start

1. **Configure the server:**
   - Add `"metrics_port": 9090` to your `config.json`

2. **Start the server:**
   ```bash
   ./server_observer config.json account_pool.json
   ```

3. **Verify metrics are exposed:**
   ```bash
   curl http://localhost:9090/metrics | head -50
   ```

4. **Configure Prometheus to scrape:**
   - Add the scrape config shown above to `prometheus.yml`
   - Restart Prometheus

5. **Import Grafana dashboard:**
   - Open Grafana at http://localhost:3000
   - Add Prometheus as a data source
   - Import the dashboard JSON provided above
   - Customize panels as needed

6. **Set up alerts:**
   - Add the alerting rules to your Prometheus config
   - Configure notification channels in Alertmanager
