"""
Prometheus metrics for the server converter.

This module defines and manages metrics for monitoring server converter performance,
error rates, and resource utilization.
"""
from prometheus_client import Counter, Histogram, Gauge, Summary


# Message processing metrics
messages_processed_total = Counter(
    'server_converter_messages_processed_total',
    'Total number of messages processed from Redis stream',
    ['status']  # status: success, error
)

messages_processing_duration_seconds = Histogram(
    'server_converter_messages_processing_duration_seconds',
    'Time spent processing a batch of messages',
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

# Replay operation metrics
replay_creation_duration_seconds = Histogram(
    'server_converter_replay_creation_duration_seconds',
    'Time spent creating a new replay',
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

replay_append_duration_seconds = Histogram(
    'server_converter_replay_append_duration_seconds',
    'Time spent appending to an existing replay',
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)

replay_operations_total = Counter(
    'server_converter_replay_operations_total',
    'Total number of replay operations',
    ['operation', 'status']  # operation: create, append, complete; status: success, error
)

# Storage metrics
hot_storage_replays = Gauge(
    'server_converter_hot_storage_replays',
    'Number of replays currently in hot storage'
)

cold_storage_uploads_total = Counter(
    'server_converter_cold_storage_uploads_total',
    'Total number of replays uploaded to cold storage',
    ['status']  # status: success, error
)

# Database metrics
database_operations_total = Counter(
    'server_converter_database_operations_total',
    'Total number of database operations',
    ['operation', 'status']  # operation: create, update, query; status: success, error
)

database_operation_duration_seconds = Histogram(
    'server_converter_database_operation_duration_seconds',
    'Time spent on database operations',
    ['operation'],  # operation: create, update, query
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)

# Redis consumer metrics
redis_consumer_lag = Gauge(
    'server_converter_redis_consumer_lag',
    'Number of pending messages in the Redis stream consumer group'
)

redis_read_operations_total = Counter(
    'server_converter_redis_read_operations_total',
    'Total number of Redis read operations',
    ['status']  # status: success, error
)

# Error metrics
errors_total = Counter(
    'server_converter_errors_total',
    'Total number of errors encountered',
    ['error_type']  # error_type: processing, database, storage, redis
)

# Batch processing metrics
batch_size_summary = Summary(
    'server_converter_batch_size',
    'Summary of batch sizes processed'
)

# Response count metrics
responses_per_replay_summary = Summary(
    'server_converter_responses_per_replay',
    'Summary of number of responses added per replay operation'
)
