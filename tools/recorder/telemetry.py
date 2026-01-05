"""
Lightweight optional telemetry helpers using OpenTelemetry if available.

Telemetry is enabled only when the OpenTelemetry SDK is installed and
OTEL_EXPORTER_OTLP_ENDPOINT is configured; otherwise methods are no-ops.
"""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Optional

try:
    from opentelemetry import metrics
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
    from opentelemetry.sdk._logs.export import BatchLogProcessor
    _OTEL_AVAILABLE = True
except Exception:
    _OTEL_AVAILABLE = False


_active_recordings = 0
_active_lock = threading.Lock()
_account_usage = (0, 0)


def _maybe_setup_meter():
    if not _OTEL_AVAILABLE:
        return None
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return None
    exporter = OTLPMetricExporter(endpoint=endpoint)
    reader = PeriodicExportingMetricReader(exporter)
    provider = MeterProvider(metric_readers=[reader])
    metrics.set_meter_provider(provider)
    return metrics.get_meter(__name__)


def _maybe_setup_logger():
    if not _OTEL_AVAILABLE:
        return None, None
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return None, None
    provider = LoggerProvider()
    exporter = OTLPLogExporter(endpoint=endpoint)
    provider.add_log_processor(BatchLogProcessor(exporter))
    handler = LoggingHandler(logger_provider=provider)
    return provider, handler


@dataclass
class Telemetry:
    enabled: bool
    update_latency_hist: Optional[object] = None
    bytes_written_hist: Optional[object] = None
    anomalies_counter: Optional[object] = None
    accounts_gauge: Optional[object] = None
    logger_handler: Optional[object] = None
    logger_provider: Optional[object] = None


def telemetry_enabled() -> bool:
    return _OTEL_AVAILABLE and bool(os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"))


class TelemetryRecorder:
    def __init__(self):
        self.telemetry = self._setup()

    def _setup(self) -> Telemetry:
        if not telemetry_enabled():
            return Telemetry(False)

        meter = _maybe_setup_meter()
        logger_provider, logger_handler = _maybe_setup_logger()
        if meter is None:
            return Telemetry(False)

        update_latency_hist = meter.create_histogram(
            name="recorder.replay_update_latency_ms",
            description="Latency of replay/game updates in milliseconds",
            unit="ms",
        )
        bytes_written_hist = meter.create_histogram(
            name="recorder.bytes_written_per_update",
            description="Bytes written per update",
            unit="By",
        )
        anomalies_counter = meter.create_counter(
            name="recorder.anomalies",
            description="Anomalies during recording",
        )

        meter.create_observable_gauge(
            name="recorder.active_recordings",
            description="Number of active recordings",
            callbacks=[lambda opts: [_active_recordings]],
        )

        meter.create_observable_gauge(
            name="recorder.accounts_in_use",
            description="Accounts in use",
            callbacks=[lambda opts: [_account_usage[0]]],
        )

        meter.create_observable_gauge(
            name="recorder.account_pool_size",
            description="Total accounts in pool",
            callbacks=[lambda opts: [_account_usage[1]]],
        )

        return Telemetry(
            enabled=True,
            update_latency_hist=update_latency_hist,
            bytes_written_hist=bytes_written_hist,
            anomalies_counter=anomalies_counter,
            logger_handler=logger_handler,
            logger_provider=logger_provider,
        )

    def on_start(self):
        if not self.telemetry.enabled:
            return
        global _active_recordings
        with _active_lock:
            _active_recordings += 1

    def on_stop(self):
        if not self.telemetry.enabled:
            return
        global _active_recordings
        with _active_lock:
            _active_recordings = max(0, _active_recordings - 1)

    def record_update(self, latency_ms: float, bytes_written: int = 0):
        if not self.telemetry.enabled:
            return
        if self.telemetry.update_latency_hist:
            self.telemetry.update_latency_hist.record(latency_ms)
        if bytes_written and self.telemetry.bytes_written_hist:
            self.telemetry.bytes_written_hist.record(bytes_written)

    def log_anomaly(self, message: str):
        if not self.telemetry.enabled:
            return
        if self.telemetry.anomalies_counter:
            self.telemetry.anomalies_counter.add(1)
        if self.telemetry.logger_handler:
            import logging

            logger = logging.getLogger("recorder.telemetry")
            logger.setLevel(logging.WARNING)
            if self.telemetry.logger_handler not in logger.handlers:
                logger.addHandler(self.telemetry.logger_handler)
            logger.warning(message)

    def on_failure(self, message: str):
        self.log_anomaly(message)
        self.on_stop()

    def update_account_usage(self, in_use: int, total: int):
        if not self.telemetry.enabled:
            return
        global _account_usage
        _account_usage = (in_use, total)
