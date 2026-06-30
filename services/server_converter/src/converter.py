"""
Main server converter logic for processing game responses.
"""
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any

from conflict_interface.replay.replay_builder import ReplayBuilder
from conflict_interface.replay.response_metadata import ResponseMetadata
from conflict_interface.utils.exceptions import UnsupportedDatatypeVersionError
from conflict_interface.versions import LATEST_VERSION
from server_converter.config import ServerConverterConfig
from server_converter.database import ReplayDatabase, ReplayStatus
from server_converter.redis_consumer import RedisStreamConsumer
from server_converter.cold_storage import ColdStorageManager
from server_converter.hot_storage import HotStorageManager
from server_converter.response_cache import ResponseCache
from server_converter import metrics

logger = logging.getLogger(__name__)

_VERSION_PENDING_WARN_INTERVAL = 3600


class ServerConverter:
    """
    Converts game responses from Redis stream to replay files.

    Caches responses on disk until a game accumulates enough for processing,
    then creates/appends to replay files in hot storage,
    and moves completed replays to cold storage.
    """

    def __init__(self, config: ServerConverterConfig):
        self.config = config

        db_config = {
            'host': config.database.host,
            'port': config.database.port,
            'database': config.database.database,
            'user': config.database.user,
            'password': config.database.password
        }

        self.db = ReplayDatabase(db_config)
        self.db.connect()

        self.redis_consumer = RedisStreamConsumer(config.redis)
        self.hot_storage = HotStorageManager(config.storage.hot_storage_dir)

        cache_dir = config.storage.hot_storage_dir / ".response_cache"
        self.response_cache = ResponseCache(cache_dir, config.batch_size)

        self.cold_storage: Optional[ColdStorageManager] = None
        if config.storage.cold_storage_enabled and config.storage.s3_config:
            self.cold_storage = ColdStorageManager(config.storage.s3_config)

        self._last_version_pending_warn = 0.0

        logger.info("Server converter initialized with disk-based response caching")

    def process_batch(self) -> int:
        """
        Process messages from Redis stream and cache them on disk.

        Returns:
            Number of messages processed
        """
        start_time = time.time()

        try:
            total_cached = 0
            first_read = True
            next_ready_check_at = start_time + self.config.check_interval_seconds
            processed_ready_during_drain = False
            while True:

                messages = self.redis_consumer.read_messages(
                    count=None,
                    block=(self.config.check_interval_seconds * 1000) if first_read else 0,
                )
                first_read = False

                if not messages:
                    break

                logger.debug("Caching %d messages to disk", len(messages))

                cached_message_ids = []
                poison_message_ids = []
                for message_id, message_data in messages:
                    try:
                        meta_dict = message_data["metadata"]
                        response = message_data["response"]

                        metadata = ResponseMetadata.from_dict(meta_dict)

                        self.response_cache.add_response(metadata, response)
                        cached_message_ids.append(message_id)
                        total_cached += 1

                    except Exception as e:
                        logger.warning(
                            "Poison message %s: %s; acking to avoid retry",
                            message_id, e,
                            extra={
                                "game_id": message_data.get("game_id"),
                                "player_id": message_data.get("player_id"),
                            },
                        )
                        metrics.errors_total.labels(error_type='caching').inc()
                        metrics.poison_messages_total.inc()
                        poison_message_ids.append(message_id)

                if cached_message_ids:
                    self.redis_consumer.acknowledge_messages(cached_message_ids)
                    logger.debug("Cached and acknowledged %d messages", len(cached_message_ids))
                if poison_message_ids:
                    self.redis_consumer.acknowledge_messages(poison_message_ids)
                    logger.info("Acked %d poison message(s) to avoid retry", len(poison_message_ids))

                now = time.time()
                if now >= next_ready_check_at:
                    self._process_ready_games()
                    processed_ready_during_drain = True
                    next_ready_check_at = now + self.config.check_interval_seconds

            if total_cached == 0:
                self._process_ready_games()
                logger.debug("No new messages to cache")
                return 0

            if not processed_ready_during_drain:
                self._process_ready_games()

            return total_cached

        finally:
            duration = time.time() - start_time
            metrics.messages_processing_duration_seconds.observe(duration)

    def _process_ready_games(self):
        """
        Process games that have accumulated enough responses in the cache.
        """
        games_with_responses = self.response_cache.list_games_with_responses()
        if not games_with_responses:
            logger.debug("No games with responses found in cache")
            return

        batch_ready_games = self.response_cache.list_games_ready_to_process()
        observer_completed = set(self.db.get_observer_completed_pairs(games_with_responses))

        ready_games = set(batch_ready_games) | observer_completed
        logger.debug(
            "Ready games: %s (%d by batch, %d observer-completed)",
            ready_games, len(batch_ready_games), len(observer_completed),
        )
        if not ready_games:
            return

        logger.info(
            "Found %d games ready to process (%d by batch, %d observer-completed)",
            len(ready_games), len(batch_ready_games), len(observer_completed),
        )

        version_pending_games = []

        for game_id, player_id in sorted(ready_games):
            ctx = {"game_id": game_id, "player_id": player_id}
            try:
                if self.db.is_conversion_failed(game_id, player_id):
                    logger.debug("Skipping: marked as conversion-failed", extra=ctx)
                    continue

                if self.db.is_version_pending(game_id, player_id):
                    pending_version = self.db.get_pending_datatype_version(game_id, player_id)
                    if pending_version is not None and pending_version > LATEST_VERSION:
                        logger.debug("Skipping: waiting for version update", extra=ctx)
                        version_pending_games.append((game_id, player_id))
                        continue
                    logger.info(
                        "Retrying previously version_pending game (pending_version=%s, LATEST_VERSION=%d)",
                        pending_version, LATEST_VERSION, extra=ctx,
                    )
                    self.db.clear_version_pending(game_id, player_id)

                cached_responses = self.response_cache.get_cached_responses(game_id, player_id)

                is_observer_completed = (game_id, player_id) in observer_completed
                if is_observer_completed:
                    if len(cached_responses) == 0:
                        continue
                    logger.info(
                        "Observer marked completed; flushing %d cached responses",
                        len(cached_responses),
                        extra=ctx,
                    )
                else:
                    if len(cached_responses) < self.config.batch_size:
                        logger.debug(
                            "Skipping: only %d responses available (race condition)",
                            len(cached_responses),
                            extra=ctx,
                        )
                        continue

                logger.info(
                    "Processing %d cached responses",
                    len(cached_responses),
                    extra=ctx,
                )

                success = self._process_game_responses(game_id, player_id, cached_responses)

                if success:
                    self.response_cache.clear_cache(game_id, player_id)
                    metrics.messages_processed_total.labels(status='success').inc(len(cached_responses))
                    logger.info("Successfully processed and cleared cache", extra=ctx)

                    if is_observer_completed:
                        try:
                            self.mark_replay_completed(game_id, player_id)
                        except Exception as e:
                            logger.error(
                                "Failed to mark replay completed: %s", e,
                                exc_info=True, extra=ctx,
                            )
                            metrics.errors_total.labels(error_type='processing').inc()
                else:
                    metrics.messages_processed_total.labels(status='error').inc(len(cached_responses))
                    reason = "conversion failed (inconsistent or unrecoverable state)"
                    self.db.record_conversion_failure(game_id, player_id, reason=reason)
                    logger.warning("Failed to process; recorded as conversion-failed", extra=ctx)

            except UnsupportedDatatypeVersionError as e:
                ctx = {"game_id": game_id, "player_id": player_id}
                if e.version > LATEST_VERSION:
                    logger.warning(
                        "%s — cached responses retained; reboot after updating conflict_interface",
                        e, extra=ctx,
                    )
                    self.db.record_version_pending(game_id, player_id, e.version)
                    version_pending_games.append((game_id, player_id))
                    metrics.errors_total.labels(error_type='unsupported_version').inc()
                else:
                    logger.error(
                        "%s — version not newer than latest (%d); marking as failed",
                        e, LATEST_VERSION, extra=ctx,
                    )
                    self.db.record_conversion_failure(game_id, player_id, reason=str(e)[:500])
                    metrics.errors_total.labels(error_type='processing').inc()
            except Exception as e:
                logger.error("Error processing ready game: %s", e, exc_info=True,
                             extra={"game_id": game_id, "player_id": player_id})
                metrics.errors_total.labels(error_type='processing').inc()
                self.db.record_conversion_failure(game_id, player_id, reason=str(e)[:500])

        now = time.time()
        if version_pending_games and (now - self._last_version_pending_warn) > _VERSION_PENDING_WARN_INTERVAL:
            logger.warning(
                "%d game(s) stuck waiting for conflict_interface update: %s",
                len(version_pending_games), version_pending_games,
            )
            metrics.errors_total.labels(error_type='version_pending').inc()
            self._last_version_pending_warn = now

    def _process_game_responses(self, game_id: int, player_id: int,
                                json_responses: List[Tuple[ResponseMetadata, dict]]) -> bool:
        ctx = {"game_id": game_id, "player_id": player_id}
        logger.debug("Processing %d responses", len(json_responses), extra=ctx)

        replay_exists = self.hot_storage.replay_exists(game_id, player_id)
        replay_entry = self.db.get_replay_by_game_and_player(game_id, player_id)
        converter_started = replay_entry and replay_entry.get("status_converter") is not None

        if not replay_exists and not converter_started:
            return self._create_new_replay(game_id, player_id, json_responses)
        elif replay_exists and replay_entry:
            return self._append_to_replay(game_id, player_id, json_responses, replay_entry)
        else:
            logger.error(
                "Inconsistent state: replay_exists=%s, replay_entry=%s",
                replay_exists, replay_entry is not None,
                extra=ctx,
            )
            return False

    def _create_new_replay(self, game_id: int, player_id: int,
                          json_responses: List[Tuple[ResponseMetadata, dict]]) -> bool:
        ctx = {"game_id": game_id, "player_id": player_id}
        logger.info("Creating new replay", extra=ctx)

        start_time = time.time()

        try:
            replay_path = self.hot_storage.add_replay(game_id, player_id)

            builder = ReplayBuilder(replay_path, game_id, player_id)
            initial_index = builder.create_replay(json_responses)
            remaining_responses = json_responses[initial_index + 1:] if initial_index + 1 < len(json_responses) else []
            builder.append_json_responses(remaining_responses)

            first_meta = json_responses[0][0]
            recording_start_time = datetime.fromtimestamp(first_meta.timestamp / 1000.0)
            replay_name = f"game_{game_id}_player_{player_id}"

            self.db.create_replay_entry(
                game_id=game_id,
                player_id=player_id,
                replay_name=replay_name,
                hot_storage_path=str(replay_path),
                recording_start_time=recording_start_time
            )

            replay_entry = self.db.get_replay_by_game_and_player(game_id, player_id)
            self.db.increment_response_count(replay_entry['id'], len(json_responses))

            if self.cold_storage and self.config.storage.always_update_cold_storage:
                logger.debug("Uploading new replay snapshot to cold storage", extra=ctx)
                try:
                    s3_key = self.cold_storage.upload_replay(replay_path, game_id, player_id)
                    if s3_key:
                        self.db.update_replay_status(
                            replay_entry["id"], ReplayStatus.RECORDING, s3_key=s3_key,
                        )
                        metrics.cold_storage_uploads_total.labels(status='success').inc()
                    else:
                        metrics.cold_storage_uploads_total.labels(status='error').inc()
                        metrics.errors_total.labels(error_type='storage').inc()
                except Exception as e:
                    logger.error("Failed to upload new replay snapshot to cold storage: %s", e,
                                 exc_info=True, extra=ctx)
                    metrics.cold_storage_uploads_total.labels(status='error').inc()
                    metrics.errors_total.labels(error_type='storage').inc()

            metrics.responses_per_replay_summary.observe(len(json_responses))
            metrics.replay_operations_total.labels(operation='create', status='success').inc()
            metrics.hot_storage_replays.inc()

            logger.info("Created replay at %s with %d responses", replay_path, len(json_responses), extra=ctx)
            return True

        except UnsupportedDatatypeVersionError:
            raise
        except Exception as e:
            logger.error("Failed to create replay: %s", e, exc_info=True, extra=ctx)
            metrics.replay_operations_total.labels(operation='create', status='error').inc()
            metrics.errors_total.labels(error_type='storage').inc()
            return False

        finally:
            duration = time.time() - start_time
            metrics.replay_creation_duration_seconds.observe(duration)

    def _append_to_replay(self, game_id: int, player_id: int,
                         json_responses: List[Tuple[ResponseMetadata, dict]],
                         replay_entry: Dict[str, Any]) -> bool:
        ctx = {"game_id": game_id, "player_id": player_id}
        logger.debug("Appending %d responses to existing replay", len(json_responses), extra=ctx)

        start_time = time.time()

        try:
            replay_path = self.hot_storage.get_replay_path(game_id, player_id)
            builder = ReplayBuilder(replay_path, game_id, player_id)
            builder.append_json_responses(json_responses)

            self.db.increment_response_count(replay_entry['id'], len(json_responses))

            if self.cold_storage and self.config.storage.always_update_cold_storage:
                logger.debug("Uploading updated replay snapshot to cold storage", extra=ctx)
                try:
                    s3_key = self.cold_storage.upload_replay(replay_path, game_id, player_id)
                    if s3_key:
                        self.db.update_replay_status(
                            replay_entry["id"], ReplayStatus.RECORDING, s3_key=s3_key,
                        )
                        metrics.cold_storage_uploads_total.labels(status='success').inc()
                    else:
                        metrics.cold_storage_uploads_total.labels(status='error').inc()
                        metrics.errors_total.labels(error_type='storage').inc()
                except Exception as e:
                    logger.error("Failed to upload updated replay snapshot to cold storage: %s", e,
                                 exc_info=True, extra=ctx)
                    metrics.cold_storage_uploads_total.labels(status='error').inc()
                    metrics.errors_total.labels(error_type='storage').inc()

            metrics.responses_per_replay_summary.observe(len(json_responses))
            metrics.replay_operations_total.labels(operation='append', status='success').inc()

            logger.info("Appended %d responses to %s", len(json_responses), replay_path, extra=ctx)
            return True

        except UnsupportedDatatypeVersionError:
            raise
        except Exception as e:
            logger.error("Failed to append to replay: %s", e, exc_info=True, extra=ctx)
            metrics.replay_operations_total.labels(operation='append', status='error').inc()
            metrics.errors_total.labels(error_type='storage').inc()
            return False

        finally:
            duration = time.time() - start_time
            metrics.replay_append_duration_seconds.observe(duration)

    def mark_replay_completed(self, game_id: int, player_id: int) -> bool:
        ctx = {"game_id": game_id, "player_id": player_id}

        replay_entry = self.db.get_replay_by_game_and_player(game_id, player_id)
        if not replay_entry:
            logger.error("No replay entry found", extra=ctx)
            metrics.replay_operations_total.labels(operation='complete', status='error').inc()
            return False

        status_converter = replay_entry.get("status_converter")
        if status_converter in (ReplayStatus.COMPLETED.value, ReplayStatus.ARCHIVED.value):
            logger.debug("Replay already finalized (status_converter=%s)", status_converter, extra=ctx)
            return True

        replay_path = self.hot_storage.get_replay_path(game_id, player_id)
        if not replay_path.exists():
            logger.error("Replay file not found: %s", replay_path, extra=ctx)
            metrics.replay_operations_total.labels(operation='complete', status='error').inc()
            return False

        recording_end_time = datetime.now()

        s3_key = None
        if self.cold_storage:
            logger.info("Moving replay to cold storage", extra=ctx)
            try:
                s3_key = self.cold_storage.upload_replay(replay_path, game_id, player_id)

                if s3_key:
                    self.hot_storage.delete_replay(game_id, player_id)
                    metrics.hot_storage_replays.dec()
                    metrics.cold_storage_uploads_total.labels(status="success").inc()
                else:
                    metrics.cold_storage_uploads_total.labels(status="error").inc()
                    metrics.errors_total.labels(error_type="storage").inc()

            except Exception as e:
                logger.error("Failed to upload to cold storage: %s", e, exc_info=True, extra=ctx)
                metrics.cold_storage_uploads_total.labels(status='error').inc()
                metrics.errors_total.labels(error_type='storage').inc()

        status = ReplayStatus.ARCHIVED if s3_key else ReplayStatus.COMPLETED
        self.db.update_replay_status(
            replay_entry["id"],
            status,
            recording_end_time=recording_end_time,
            s3_key=s3_key,
        )

        try:
            self.db.remove_game_from_recording_lists(game_id)
        except Exception as e:
            logger.warning("Failed to remove game from recording lists: %s", e,
                           exc_info=True, extra=ctx)

        metrics.replay_operations_total.labels(operation='complete', status='success').inc()
        logger.info("Marked replay as %s", status.value, extra=ctx)
        return True

    def run(self):
        logger.info("Starting server converter main loop")
        consecutive_failures = 0
        MAX_CONSECUTIVE = 10
        try:
            while True:
                self._update_hot_storage_metric()
                try:
                    self.process_batch()
                    consecutive_failures = 0
                except Exception as e:
                    consecutive_failures += 1
                    metrics.errors_total.labels(error_type='run_loop').inc()
                    logger.error(
                        "Unhandled exception in process_batch (consecutive=%d): %s",
                        consecutive_failures, e, exc_info=True,
                    )
                    if consecutive_failures >= MAX_CONSECUTIVE:
                        logger.critical(
                            "Reached %d consecutive failures; exiting for supervisor restart",
                            MAX_CONSECUTIVE,
                        )
                        raise
                    time.sleep(min(5 * consecutive_failures, 60))

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
        finally:
            self.shutdown()

    def _update_hot_storage_metric(self):
        try:
            replay_count = self.hot_storage.count_replays()
            metrics.hot_storage_replays.set(replay_count)
        except Exception as e:
            logger.warning("Failed to update hot storage metric: %s", e)

    def shutdown(self):
        logger.info("Shutting down server converter")

        if self.redis_consumer:
            self.redis_consumer.close()

        if self.db:
            self.db.close()
