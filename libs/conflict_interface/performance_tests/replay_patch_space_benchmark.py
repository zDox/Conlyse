
from conflict_interface.replay.replay_segment import ReplaySegment
from conflict_interface.replay.replay_patch import ReplayPatch
import time

class ReplaySpaceBenchmark:
    def __init__(self, replay_file: str):
        self.replay_file = replay_file

    def run_space_test(self):
        replay = ReplaySegment(self.replay_file, "r")
        replay.open()

        replay.load_patches_from_disk_into_cache()
        patches = replay.cache._patches.values()

        total_binary_space = 0
        total_string_space = 0
        patch_count = 0
        max_ops = 0

        for patch in patches:
            if len(patch.operations) > max_ops:
                max_ops = len(patch.operations)
            assert isinstance(patch, ReplayPatch)

            # Serialize
            string_format = patch.to_string()
            byte_format = patch.to_bytes()

            # Deserialize and verify correctness
            reconstructed_from_string = ReplayPatch.from_string(string_format)
            reconstructed_from_bytes = ReplayPatch.from_bytes(byte_format)
            assert patch == reconstructed_from_string, "String deserialization failed!"
            assert patch == reconstructed_from_bytes, "Binary deserialization failed!"

            # Measure sizes
            string_format_size = len(string_format.encode('utf-8'))
            byte_format_size = len(byte_format)

            total_string_space += string_format_size
            total_binary_space += byte_format_size
            patch_count += 1

            # print progress in percent
            if patch_count % max(1, len(patches) // 10) == 0:
                print(f"Processed {patch_count}/{len(patches)} patches ({(patch_count / len(patches)) * 100:.1f}%)")

        # Compute stats
        avg_string_size = total_string_space / patch_count if patch_count else 0
        avg_binary_size = total_binary_space / patch_count if patch_count else 0
        compression_ratio = (total_string_space / total_binary_space) if total_binary_space else 0

        # Print benchmark results
        print(f"Total patches: {patch_count}")
        print(f"Total string size: {total_string_space / 1024:.2f} KB")
        print(f"Total binary size: {total_binary_space / 1024:.2f} KB")
        print(f"Average string size per patch: {avg_string_size:.2f} bytes")
        print(f"Average binary size per patch: {avg_binary_size:.2f} bytes")
        print(f"Compression ratio (string/binary): {compression_ratio:.2f}x")

        print(f"Max operations in a single patch: {max_ops}")

    def run_time_benchmark(self):
        replay = ReplaySegment(self.replay_file, "r")
        replay.open()
        replay.load_patches_from_disk_into_cache()
        patches = list(replay.cache._patches.values())

        total_patches = len(patches)
        print(f"Benchmarking {total_patches} patches...")

        # -------------------------
        # PATCH -> STRING (serialization)
        # -------------------------
        start = time.time()
        for patch in patches:
            _ = patch.to_string()
        string_serialize_time = time.time() - start
        print(f"Patch -> String 1/4 took: {string_serialize_time:.4f} s")

        # -------------------------
        # PATCH -> BYTES (serialization)
        # -------------------------
        start = time.time()
        for patch in patches:
            _ = patch.to_bytes()
        bytes_serialize_time = time.time() - start
        print(f"Patch -> Bytes 2/4 took: {bytes_serialize_time:.4f} s")

        # -------------------------
        # STRING -> PATCH (deserialization)
        # -------------------------
        string_formats = [patch.to_string() for patch in patches]
        start = time.time()
        for s in string_formats:
            _ = ReplayPatch.from_string(s)
        string_deserialize_time = time.time() - start
        print(f"String -> Patch 3/4 took: {string_deserialize_time:.4f} s")

        # -------------------------
        # BYTES -> PATCH (deserialization)
        # -------------------------
        bytes_formats = [patch.to_bytes() for patch in patches]
        start = time.time()
        for b in bytes_formats:
            _ = ReplayPatch.from_bytes(b)
        bytes_deserialize_time = time.time() - start
        print(f"Bytes -> Patch 4/4 took: {bytes_deserialize_time:.4f} s")

        # -------------------------
        # Print results
        # -------------------------
        print("Serialization time (patch -> format):")
        print(f"  String JSON: {string_serialize_time:.4f} s")
        print(f"  Binary MsgPack+ZSTD: {bytes_serialize_time:.4f} s")

        print("Deserialization time (format -> patch):")
        print(f"  String JSON: {string_deserialize_time:.4f} s")
        print(f"  Binary MsgPack+ZSTD: {bytes_deserialize_time:.4f} s")

        print("\nRatios (string_time / binary_time):")
        print(f"  Serialization speed ratio: {string_serialize_time / bytes_serialize_time:.2f}x")
        print(f"  Deserialization speed ratio: {string_deserialize_time / bytes_deserialize_time:.2f}x")


if __name__ == "__main__":
    benchmark = ReplaySpaceBenchmark("../examples/replay.conrp")
    benchmark.run_space_test()
    benchmark.run_time_benchmark()




