import logging
import time
from pathlib import Path

import zstandard as zstd

from conflict_interface.logger_config import get_logger, setup_library_logger
from conflict_interface.replay.replay_segment import ReplaySegment
from paths import TEST_DATA

logger = get_logger()


def compress_file(src, dst, level=11):
    t1 = time.perf_counter()
    cctx = zstd.ZstdCompressor(level=level)
    with open(src, 'rb') as f_in, open(dst, 'wb') as f_out:
        compressed = cctx.compress(f_in.read())
        f_out.write(compressed)
    t2 = time.perf_counter()
    logger.debug(f"Compressed {src} to {dst} in {(t2 - t1)*1000} ms")
    return len(compressed), (t2-t1)*1000



def decompress_file(src, dst):
    t1 = time.perf_counter()
    dctx = zstd.ZstdDecompressor()
    with open(src, 'rb') as f_in, open(dst, 'wb') as f_out:
        f_out.write(dctx.decompress(f_in.read()))
    t2 = time.perf_counter()
    logger.debug(f"Decompressed {src} to {dst} in {(t2 - t1)*1000} ms")

class ReplayCompressor:
    def __init__(self, uncompressed_path: Path | None = None, replay: ReplaySegment | None = None, compressed_path: Path | None = None):
        """
        :param uncompressed_path: Path to uncompressed file (compression input / decompression output). If not
            provided, and ``replay`` is given, the path will be taken from ``replay.file_path``.
        :param replay: Optional :class:`Replay` instance. When provided and ``uncompressed_path`` is not given,
            the replay's ``file_path`` is used as the uncompressed input/output path. This is useful when working
            directly with a loaded replay instead of specifying the file path manually.
        :param compressed_path: Path to compressed file (compression output / decompression input)
        """
        self.replay = replay
        self.uncompressed_path = uncompressed_path
        self.compressed_path = compressed_path
        if not self.replay and not self.uncompressed_path:
            logger.warning("No replay or file_path given")

    def compress(self, level = 11):
        if not self.replay and not self.uncompressed_path:
            logger.warning("No replay or file_path given")
            return

        if not self.uncompressed_path:
            assert self.replay

            if self.replay.is_open():
                self.replay.close()

            self.uncompressed_path = self.replay.file_path

        if not self.compressed_path:
            self.compressed_path = self.uncompressed_path

        return compress_file(self.uncompressed_path, self.compressed_path, level = level)

    def decompress(self):
        if not self.compressed_path:
            logger.warning("No file_path given")
            return

        if not self.uncompressed_path:
            self.uncompressed_path = self.compressed_path

        decompress_file(self.compressed_path, self.uncompressed_path)