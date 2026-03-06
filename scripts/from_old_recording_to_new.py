
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
from multiprocessing import Pool
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

import orjson
import zstandard as zstd
from tqdm import tqdm

from conflict_interface.replay.response_metadata import ResponseMetadata

try:
    # Reuse existing recorder logger formatting if available.
    from tools.recording_converter.recorder_logger import get_logger
except Exception:  # pragma: no cover - fallback for non-tool environments
    def get_logger() -> logging.Logger:
        logger = logging.getLogger("from_old_recording_to_new")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger


logger = get_logger()


class OldResponsesConverter:
    """
    Convert legacy recordings (responses files without embedded metadata) into
    the new on-disk format expected by `RecordingReader.read_json_response_file`.

    Legacy layout (per frame in responses*.jsonl.zst):
        [8 bytes BE timestamp_ms][4 bytes BE compressed_len][compressed_data]
        compressed_data: zstd(JSON response)

    New layout (inner payload before outer zstd compression):
        [4 bytes BE metadata_len][metadata JSON][4 bytes BE response_len][response JSON]
    """

    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        overwrite: bool = False,
        games_filter: Optional[Sequence[int]] = None,
        verify: bool = False,
        use_tqdm: bool = True,
    ) -> None:
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.overwrite = overwrite
        self.verify = verify
        self.games_filter = set(int(g) for g in games_filter) if games_filter else None

        # Controls whether tqdm progress bars are shown from this converter.
        # In multiprocessing workers we disable tqdm to avoid garbled output.
        self._use_tqdm = use_tqdm

        self._decompressor = zstd.ZstdDecompressor()
        self._compressor = zstd.ZstdCompressor(level=3)

    # ------------------------------------------------------------------ #
    # Legacy reader
    # ------------------------------------------------------------------ #
    def read_legacy_response_file(
        self, file_path: Path
    ) -> List[Tuple[int, dict]]:
        """
        Read a legacy responses*.jsonl.zst file and return a list of
        (timestamp_ms, response_dict) tuples.
        """
        json_responses: List[Tuple[int, dict]] = []

        with open(file_path, "rb") as f:
            while True:
                # Read timestamp (8 bytes)
                timestamp_bytes = f.read(8)
                if not timestamp_bytes:
                    break

                timestamp_ms = int.from_bytes(timestamp_bytes, "big")

                # Read length (4 bytes)
                length_bytes = f.read(4)
                if not length_bytes:
                    break

                length = int.from_bytes(length_bytes, "big")
                if length <= 0:
                    logger.warning(
                        "Non-positive frame length %s at timestamp %s in %s",
                        length,
                        timestamp_ms,
                        file_path,
                    )
                    break

                # Read compressed data
                compressed_data = f.read(length)
                if len(compressed_data) != length:
                    logger.warning(
                        "Incomplete legacy JSON data at timestamp %s in %s",
                        timestamp_ms,
                        file_path,
                    )
                    break

                try:
                    # Decompress and parse JSON
                    decompressed = self._decompressor.decompress(compressed_data)
                    decoded = decompressed.decode("utf-8")
                    json_response = orjson.loads(decoded)
                except Exception as exc:
                    logger.warning(
                        "Failed to decode legacy response at timestamp %s in %s: %s",
                        timestamp_ms,
                        file_path,
                        exc,
                    )
                    continue

                if not isinstance(json_response, dict):
                    logger.warning(
                        "Legacy response at timestamp %s in %s is not a JSON object, skipping",
                        timestamp_ms,
                        file_path,
                    )
                    continue

                json_responses.append((timestamp_ms, json_response))

        logger.info(
            "Read %d legacy responses from %s", len(json_responses), file_path
        )
        return json_responses

    # ------------------------------------------------------------------ #
    # Metadata helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _parse_game_id_from_dir(game_dir: Path) -> Optional[int]:
        name = game_dir.name
        if not name.startswith("game_"):
            logger.warning("Skipping directory without game_ prefix: %s", game_dir)
            return None
        try:
            return int(name.split("_", 1)[1])
        except ValueError:
            logger.warning("Unable to parse game_id from directory name: %s", game_dir)
            return None

    @staticmethod
    def _extract_client_version(response: dict, fallback_game_dir: Path) -> int:
        value = response.get("client_version")
        if value is None:
            return 210
        try:
            return int(value)
        except (TypeError, ValueError):
            # logger.warning(
            #    "Non-integer client_version %r in response for %s, defaulting to 210",
            #    value,
            #    fallback_game_dir,
            #)
            return 210

    @staticmethod
    def _extract_map_id(response: dict, fallback_game_dir: Path) -> str:
        try:
            result = response.get("result") or {}
            states = result.get("states") or {}
            state3 = states.get("3") or {}
            map_obj = state3.get("map") or {}
            map_id = map_obj.get("map_id")
            if map_id is None:
                raise KeyError("map_id missing")
            return str(map_id)
        except Exception:
            # logger.warning(
            #    "Unable to extract map_id from response for %s, defaulting to 5652_28",
            #    fallback_game_dir,
            #)
            return "5652_28"

    # ------------------------------------------------------------------ #
    # Frame conversion
    # ------------------------------------------------------------------ #
    def _encode_frames(
        self,
        game_id: int,
        game_dir: Path,
        responses: Iterable[Tuple[int, dict]],
    ) -> Iterable[bytes]:
        """
        Yield fully-encoded outer frames for the new format.
        """
        for timestamp_ms, response in responses:
            client_version = self._extract_client_version(response, game_dir)
            map_id = self._extract_map_id(response, game_dir)

            metadata = ResponseMetadata(
                timestamp=int(timestamp_ms),
                game_id=int(game_id),
                player_id=0,
                client_version=int(client_version),
                map_id=str(map_id),
            )

            metadata_bytes = metadata.to_string().encode("utf-8")

            try:
                response_bytes = orjson.dumps(response)
            except TypeError:
                # Fallback to stdlib JSON for non-orjson-serializable objects
                response_bytes = json.dumps(response, separators=(",", ":")).encode(
                    "utf-8"
                )

            meta_len_bytes = len(metadata_bytes).to_bytes(4, "big")
            resp_len_bytes = len(response_bytes).to_bytes(4, "big")

            combined = meta_len_bytes + metadata_bytes + resp_len_bytes + response_bytes
            compressed = self._compressor.compress(combined)

            outer = (
                int(timestamp_ms).to_bytes(8, "big")
                + len(compressed).to_bytes(4, "big")
                + compressed
            )
            yield outer

    def convert_response_file(
        self,
        game_id: int,
        game_dir: Path,
        input_file: Path,
        output_file: Path,
    ) -> None:
        """
        Convert a single legacy responses*.jsonl.zst file.
        """
        if output_file.exists() and not self.overwrite:
            logger.info(
                "Destination %s exists and overwrite is disabled, skipping",
                output_file,
            )
            return

        responses = self.read_legacy_response_file(input_file)
        if not responses:
            logger.warning("No responses found in %s, skipping conversion", input_file)
            return
        total_frames = len(responses)

        output_file.parent.mkdir(parents=True, exist_ok=True)
        written = 0

        with open(output_file, "wb") as f:
            for frame in tqdm(
                self._encode_frames(game_id, game_dir, responses),
                total=total_frames,
                desc=f"Converting responses for game {game_id} ({input_file.name})",
                unit="frame",
                leave=False,
                disable=not self._use_tqdm,
            ):
                f.write(frame)
                written += 1

        logger.info(
            "Converted %d responses from %s to new format at %s",
            written,
            input_file,
            output_file,
        )

    # ------------------------------------------------------------------ #
    # Directory traversal and mirroring
    # ------------------------------------------------------------------ #
    def _iter_game_dirs(self) -> Iterable[Tuple[int, Path]]:
        if not self.input_dir.exists():
            logger.error("Input directory does not exist: %s", self.input_dir)
            return

        for entry in self.input_dir.iterdir():
            if not entry.is_dir():
                continue
            game_id = self._parse_game_id_from_dir(entry)
            if game_id is None:
                continue
            if self.games_filter is not None and game_id not in self.games_filter:
                continue
            yield game_id, entry

    @staticmethod
    def _is_response_file(path: Path) -> bool:
        name = path.name
        return name.startswith("responses") and name.endswith(".jsonl.zst")

    def convert_game_dir(self, game_id: int, game_dir: Path) -> None:
        """
        Mirror a single game directory into the output tree, converting all
        responses*.jsonl.zst files into the new format.
        """
        relative = game_dir.relative_to(self.input_dir)
        dest_root = self.output_dir / relative
        dest_root.mkdir(parents=True, exist_ok=True)

        logger.info("Converting game %s at %s -> %s", game_id, game_dir, dest_root)

        # First pass: convert response files; second pass: copy non-response files.
        entries = list(game_dir.iterdir())
        for entry in tqdm(
            entries,
            desc=f"Game {game_id}",
            unit="item",
            leave=False,
            disable=not self._use_tqdm,
        ):
            dest_entry = dest_root / entry.name

            if entry.is_dir():
                # Mirror subdirectories recursively, handling any nested response files.
                self._mirror_subtree(game_id, entry, dest_entry)
                continue

            if self._is_response_file(entry):
                self.convert_response_file(game_id, game_dir, entry, dest_entry)
            else:
                # Plain file: copy as-is.
                if dest_entry.exists() and not self.overwrite:
                    logger.info(
                        "File %s already exists and overwrite is disabled, skipping copy",
                        dest_entry,
                    )
                else:
                    dest_entry.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(entry, dest_entry)

        if self.verify:
            self._verify_converted_game(dest_root)

    def _mirror_subtree(self, game_id: int, src: Path, dst: Path) -> None:
        """
        Recursively mirror a subtree, converting any responses*.jsonl.zst files.
        """
        for root, dirs, files in os.walk(src):
            root_path = Path(root)
            relative = root_path.relative_to(src)
            dest_root = dst / relative
            dest_root.mkdir(parents=True, exist_ok=True)

            for d in dirs:
                (dest_root / d).mkdir(parents=True, exist_ok=True)

            for filename in tqdm(
                files,
                desc=f"Mirroring {root_path}",
                unit="file",
                leave=False,
                disable=not self._use_tqdm,
            ):
                src_file = root_path / filename
                dest_file = dest_root / filename

                if self._is_response_file(src_file):
                    self.convert_response_file(game_id, src, src_file, dest_file)
                else:
                    if dest_file.exists() and not self.overwrite:
                        logger.info(
                            "File %s already exists and overwrite is disabled, skipping copy",
                            dest_file,
                        )
                    else:
                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_file, dest_file)

    # ------------------------------------------------------------------ #
    # Optional verification
    # ------------------------------------------------------------------ #
    def _verify_converted_game(self, dest_game_dir: Path) -> None:
        """
        Optionally verify that converted responses can be read by RecordingReader.
        """
        try:
            from tools.recording_converter.recording_reader import RecordingReader
        except Exception as exc:
            logger.warning(
                "Verification requested but RecordingReader import failed: %s",
                exc,
            )
            return

        try:
            reader = RecordingReader(dest_game_dir)
            # Just try reading a subset; if any exception is raised, log it.
            responses = reader.read_json_responses(limit=10)
            logger.info(
                "Verification succeeded for %s, read %d responses",
                dest_game_dir,
                len(responses),
            )
        except Exception as exc:
            logger.error(
                "Verification failed for %s: %s",
                dest_game_dir,
                exc,
            )

    # ------------------------------------------------------------------ #
    # Public entrypoint
    # ------------------------------------------------------------------ #
    def run(self, processes: Optional[int] = None) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        game_dirs = list(self._iter_game_dirs())

        if not game_dirs:
            logger.warning(
                "No matching game_* directories found under %s", self.input_dir
            )
            return

        # Normalize process count: None or values < 1 fall back to sequential processing.
        if processes is not None and processes < 1:
            processes = 1

        if processes is None or processes == 1 or len(game_dirs) == 1:
            for game_id, game_dir in tqdm(
                game_dirs,
                desc="Games",
                unit="game",
                disable=not self._use_tqdm,
            ):
                self.convert_game_dir(game_id, game_dir)
        else:
            logger.info("Converting games using %d worker processes", processes)
            jobs: List[Tuple[Path, Path, bool, bool, int, Path]] = [
                (
                    self.input_dir,
                    self.output_dir,
                    self.overwrite,
                    self.verify,
                    game_id,
                    game_dir,
                )
                for game_id, game_dir in game_dirs
            ]

            with Pool(processes=processes) as pool:
                for _ in tqdm(
                    pool.imap_unordered(_convert_single_game_worker, jobs),
                    total=len(jobs),
                    desc="Games",
                    unit="game",
                    disable=not self._use_tqdm,
                ):
                    pass

        logger.info("Finished converting legacy recordings under %s", self.input_dir)


def _convert_single_game_worker(
    args: Tuple[Path, Path, bool, bool, int, Path]
) -> int:
    """
    Worker function to convert a single game directory in a separate process.
    """
    (
        input_dir,
        output_dir,
        overwrite,
        verify,
        game_id,
        game_dir,
    ) = args

    converter = OldResponsesConverter(
        input_dir=input_dir,
        output_dir=output_dir,
        overwrite=overwrite,
        games_filter=None,
        verify=verify,
        use_tqdm=False,
    )
    converter.convert_game_dir(game_id, game_dir)
    return game_id


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert legacy ConflictInterface recordings (old responses format) "
            "into the new metadata+response frame format."
        )
    )
    parser.add_argument(
        "-i",
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing legacy game_* recordings.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        required=True,
        help="Directory where converted recordings will be written.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing responses*.jsonl.zst files in the output directory.",
    )
    parser.add_argument(
        "--games",
        type=str,
        default="",
        help=(
            "Optional comma-separated list of game IDs to convert. "
            "If omitted, all game_* folders under input-dir are processed."
        ),
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help=(
            "After conversion, attempt to read a subset of responses using "
            "RecordingReader to verify the new format."
        ),
    )
    parser.add_argument(
        "-p",
        "--processes",
        type=int,
        default=os.cpu_count() or 1,
        help=(
            "Number of worker processes to use for converting games. "
            "Defaults to the number of available CPU cores."
        ),
    )
    return parser.parse_args(argv)


def _parse_games_filter(games_arg: str) -> Optional[List[int]]:
    if not games_arg:
        return None
    game_ids: List[int] = []
    for part in games_arg.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            game_ids.append(int(part))
        except ValueError:
            logger.warning("Ignoring invalid game id value in --games: %r", part)
    return game_ids or None


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)

    games_filter = _parse_games_filter(args.games)

    converter = OldResponsesConverter(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        overwrite=args.overwrite,
        games_filter=games_filter,
        verify=args.verify,
    )
    converter.run(processes=args.processes)


if __name__ == "__main__":
    main()
