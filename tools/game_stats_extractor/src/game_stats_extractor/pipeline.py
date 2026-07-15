"""
Orchestrates extraction and aggregation across many replay files.

Extraction runs in parallel (ProcessPoolExecutor) if workers > 1.
Aggregation is single-threaded after all games are collected.
"""
import logging
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

from tqdm import tqdm

from .aggregators.building_aggregator import BuildingAggregator
from .aggregators.country_aggregator import CountryAggregator
from .aggregators.global_aggregator import GlobalAggregator
from .aggregators.nation_similarity_aggregator import NationSimilarityAggregator
from .aggregators.province_aggregator import ProvinceAggregator
from .aggregators.timeseries_aggregator import TimeSeriesAggregator
from .extractors.replay_extractor import ReplayExtractor
from .models.intermediate import GameData
from .output import write_output

logger = logging.getLogger(__name__)


# Module-level worker function — must be importable by multiprocessing
def _extract_worker(args: tuple[Path, Optional[Path]]) -> Optional[GameData]:
    file_path, map_data_dir = args
    extractor = ReplayExtractor(map_data_dir=map_data_dir)
    return extractor.extract_safe(file_path)


class Pipeline:
    def __init__(
        self,
        replays_dir: Path,
        output_dir: Path,
        workers: int = os.cpu_count() or 1,
        map_data_dir: Optional[Path] = None,
        min_province_appearances: int = 3,
        min_timeseries_games: int = 3,
    ):
        self.replays_dir = replays_dir
        self.output_dir = output_dir
        self.workers = workers
        self.map_data_dir = map_data_dir
        self.min_province_appearances = min_province_appearances
        self.min_timeseries_games = min_timeseries_games

    def run(self) -> None:
        replay_files = sorted(self.replays_dir.glob("game_*.conrp"))
        if not replay_files:
            logger.error("No game_*.conrp files found in %s", self.replays_dir)
            return

        logger.info("Found %d replay files in %s", len(replay_files), self.replays_dir)

        games: list[GameData] = []
        failed = 0

        if self.workers > 1:
            games, failed = self._extract_parallel(replay_files)
        else:
            games, failed = self._extract_sequential(replay_files)

        # All extracted games are ended — non-ended replays are rejected early in extract()
        logger.info(
            "Extracted %d ended game(s) successfully, %d skipped/failed "
            "(not ended or corrupted)",
            len(games),
            failed,
        )

        if not games:
            logger.error("No games extracted — aborting aggregation")
            return

        logger.info("Aggregating global statistics...")
        global_agg = GlobalAggregator().aggregate(games)

        logger.info("Aggregating country statistics...")
        country_aggs = CountryAggregator().aggregate(games)

        logger.info("Aggregating province statistics (min appearances=%d)...", self.min_province_appearances)
        province_aggs = ProvinceAggregator(min_appearances=self.min_province_appearances).aggregate(games)

        logger.info("Aggregating time series...")
        timeseries_agg = TimeSeriesAggregator(min_games=self.min_timeseries_games).aggregate(games)

        logger.info("Aggregating building statistics...")
        building_aggs = BuildingAggregator().aggregate(games)

        logger.info("Aggregating nation build-similarity clusters...")
        nation_similarity_aggs, cluster_info = NationSimilarityAggregator().aggregate(country_aggs)

        logger.info(
            "Writing output: %d countries, %d provinces, %d building types, %d clustered nations",
            len(country_aggs),
            len(province_aggs),
            len(building_aggs),
            len(nation_similarity_aggs),
        )
        write_output(
            self.output_dir,
            global_agg,
            country_aggs,
            province_aggs,
            timeseries_agg,
            building_aggs,
            nation_similarity_aggs,
            cluster_info,
            games,
            self.replays_dir,
            failed,
        )
        logger.info("Done. Output written to %s", self.output_dir)

    def _extract_sequential(
        self, replay_files: list[Path]
    ) -> tuple[list[GameData], int]:
        extractor = ReplayExtractor(map_data_dir=self.map_data_dir)
        games: list[GameData] = []
        failed = 0
        for f in tqdm(replay_files, desc="Extracting replays"):
            result = extractor.extract_safe(f)
            if result is not None:
                games.append(result)
            else:
                failed += 1
        return games, failed

    def _extract_parallel(
        self, replay_files: list[Path]
    ) -> tuple[list[GameData], int]:
        games: list[GameData] = []
        failed = 0
        args = [(f, self.map_data_dir) for f in replay_files]
        with ProcessPoolExecutor(max_workers=self.workers) as executor:
            futures = {executor.submit(_extract_worker, a): a[0] for a in args}
            for future in tqdm(
                as_completed(futures), total=len(futures), desc="Extracting replays"
            ):
                result = future.result()
                if result is not None:
                    games.append(result)
                else:
                    failed += 1
        return games, failed
