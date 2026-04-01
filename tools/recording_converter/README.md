## Recording Converter CLI

CLI tool to convert local **recorder** output into replay databases or structured JSON dumps using the `conflict-interface` replay system.

This tool operates entirely on on-disk recordings and is the **offline** counterpart to the `server_converter` service, which converts live responses from Redis streams.

---

### Overview

`recording-converter` understands three operating modes, controlled by `--mode`:

- **`rur`** (From **R**esponse using **U**pdate to **R**eplay)
  - Uses JSON responses (and their `ResponseMetadata`) to build a replay via `ReplayBuilder`.
  - Recommended for typical recorder output, and matches how the online `server_converter` service constructs replays.
- **`gmr`** (**G**ame-state **M**ake-bipatch **R**eplay)
  - Uses binary `game_states.bin` and `make_bireplay_patch` between consecutive states to build a replay.
  - Slow when you have full game-state snapshots and want state-to-state patching.
- **`rtj`** (**R**ecording **T**o **J**SON)
  - Dumps the contents of a recording (game states, requests, responses) into human-readable JSON files on disk.
  - Ideal for debugging, external analysis, or building custom pipelines.

Depending on the mode, the converter writes either:

- A single **replay file** (e.g. `my_recording.bin`) usable with `ReplayInterface` and downstream tools, or
- A **directory tree of JSON files** (one per state/request/response).

For live, server-side conversion from Redis streams into replay files and metadata, see the separate [`server_converter` service](../../services/server_converter/README.md).

---

### Requirements

- **Python**: `3.12+`
- **Python packages** (installed automatically when you install this tool):
  - `conflict-interface>=0.1.2`
  - `tqdm`

No external services (PostgreSQL, Redis, MinIO, etc.) are required for `recording-converter` itself. You only need access to **recording directories** produced by the recorder pipeline.

---

### Installation

From the repository root:

```bash
cd /path/to/ConflictInterface

# (Recommended) Create and activate a virtualenv
python -m venv .venv
source .venv/bin/activate

# Install the recording converter CLI
pip install -e tools/recording_converter
```

This installs the `recording-converter` console script into your environment.

Verify installation:

```bash
recording-converter --help
```

---

### Recording Directory Layout

`recording-converter` operates on a **recording directory** produced by the `recorder` tool or a compatible capture pipeline. A typical layout looks like:

- `game_states.bin`
  - Binary file with compressed, pickled game states.
  - Required for **`gmr`** mode.
- `static_map_data.bin` *(optional)*
  - Compressed static map data, used indirectly by replay tooling.
- `requests.jsonl.zst` *(optional)*
  - Zstandard-compressed stream of JSON **requests**, each framed with a timestamp and length.
  - Used by JSON dump mode (`rtj`).
- `responses*.jsonl.zst` *(optional, one or more files)*
  - Zstandard-compressed stream(s) of JSON **responses**, with embedded `ResponseMetadata`.
  - Required for **`rur`** mode and used by JSON dump mode (`rtj`).
- `metadata.json` *(optional but recommended)*
  - Metadata about the recording (e.g. update counts) used to size loops and provide logging.

You pass the path to this directory via `--recording-dir`.

---

### Basic Usage

General pattern:

- **Replay from game states (`gmr`)**

```bash
recording-converter \
  --recording-dir recordings/my_recording \
  --output-replay my_recording.bin \
  --mode gmr \
  --game-id 12345 \
  --player-id 67890
```

- **Replay from JSON responses (`rur`)**

```bash
recording-converter \
  --recording-dir recordings/my_recording \
  --output-replay my_recording.bin \
  --mode rur
```

- **Dump recording to JSON (`rtj`)**

```bash
recording-converter \
  --recording-dir recordings/my_recording \
  --mode rtj \
  --output-dir recordings/my_recording_json
```

Key arguments:

- `--recording-dir`  
  Path to the recording directory. Required for all modes.
- `--mode {gmr,rur,rtj}`  
  Operating mode. Defaults to `gmr` if omitted.
- `--output-replay`  
  Output replay file path. Required for `gmr` and `rur` (non-bulk).
- `--output-dir`  
  Output directory for JSON dumps in `rtj` mode, or output root in bulk mode.
- `--overwrite`  
  Allow overwriting existing output (file or directory).
- `--limit`  
  Limit the number of game states / responses / requests processed (for quicker tests).

---

### Mode-specific Examples

#### Game-state to replay (`gmr`)

Use this when you have complete `game_states.bin` snapshots and want a replay built from state-to-state patches.

```bash
recording-converter \
  --recording-dir recordings/my_recording \
  --output-replay my_recording.bin \
  --mode gmr \
  --game-id 12345 \
  --player-id 67890 \
  --overwrite
```

Notes:

- `--game-id` and `--player-id` are **required** in this mode; they are not inferred from the recording.
- If `my_recording.bin` already exists and `--overwrite` is not set, the converter will abort with an error.

#### JSON responses to replay (`rur`)

Use this when you primarily capture JSON responses (with `ResponseMetadata`) and want the replay built via `ReplayBuilder`.

```bash
recording-converter \
  --recording-dir recordings/my_recording \
  --output-replay my_recording.bin \
  --mode rur \
  --overwrite
```

Notes:

- If `--game-id` / `--player-id` are **not** provided, the converter infers them from the response metadata stream.
- If IDs cannot be inferred consistently, the converter logs an error and aborts.

#### Recording to JSON (`rtj`)

Use this for debugging or external analysis, where you want plain JSON files per state/request/response.

```bash
# Explicit output directory
recording-converter \
  --recording-dir recordings/my_recording \
  --mode rtj \
  --output-dir recordings/my_recording_json \
  --overwrite
```

If `--output-dir` is omitted in `rtj` mode, the converter will error at the CLI level. Internally, `FromRecordingToJson` defaults to `<recording-dir>/json_dumps`, so a common pattern is:

```bash
recording-converter \
  --recording-dir recordings/my_recording \
  --mode rtj \
  --output-dir recordings/my_recording/json_dumps \
  --overwrite
```

The resulting directory contains:

- `game_states/` – one JSON file per game state
- `json_requests/` – one JSON file per request (if `requests.jsonl.zst` exists)
- `json_responses/` – one JSON file per response (if `responses*.jsonl.zst` exist)

---

### Bulk Conversion

Bulk mode lets you convert **many recordings at once**. In bulk mode, `--recording-dir` is treated as a **root directory** whose immediate subdirectories are individual recordings.

Bulk conversion is available for:

- `gmr`
- `rur`

Bulk is **not supported** for `rtj`.

#### Example: bulk `gmr` conversion

```bash
recording-converter \
  --recording-dir /data/recordings_root \
  --output-dir /data/replays \
  --mode gmr \
  --bulk \
  --bulk-game-limit 100 \
  -p 8 \
  --game-id 12345 \
  --player-id 67890 \
  --overwrite
```

Behavior:

- Each subdirectory `/data/recordings_root/<name>` that contains `game_states.bin` becomes a job.
- For each job, a replay file `/data/replays/<name>.bin` is created.
- You can cap how many jobs run via `--bulk-game-limit N` (applied after optional name filtering).
- Existing output files are overwritten only if `--overwrite` is provided.

#### Example: bulk `rur` conversion with filters

```bash
recording-converter \
  --recording-dir /data/recordings_root \
  --output-dir /data/replays \
  --mode rur \
  --bulk \
  --recording-name game_12345 \
  --recording-name game_67890 \
  -p 4 \
  --overwrite
```

Behavior:

- Only subdirectories whose names match `--recording-name` values are processed.
- In `rur` mode, a subdirectory is considered valid if it contains at least one `responses*.jsonl.zst` file.
- Game and player IDs are inferred from `ResponseMetadata` unless explicitly provided.

---

### Logging & Progress

`recording-converter` exposes basic logging and progress options:

- `-v`, `--verbose`  
  Enable verbose logging (`DEBUG` level).
- `-q`, `--quiet`  
  Quiet mode (only `ERROR` level).
- `--no-progress`  
  Disable `tqdm` progress bars (useful for non-interactive or log-only environments, especially in bulk mode).

If neither `-v` nor `-q` is given, the default log level is `INFO`.

---

### Troubleshooting

- **“Recording directory not found”**  
  Ensure `--recording-dir` points to an existing directory containing your recording.

- **“Game state file not found: game_states.bin” in `gmr` mode**  
  The selected mode requires `game_states.bin`. Either:
  - Switch to `--mode rur` if you only have JSON responses, or
  - Regenerate the recording with game-state capturing enabled.

- **“No JSON responses found in recording” in `rur` mode**  
  The converter could not find any `responses*.jsonl.zst` files or they were empty. Verify that your recorder pipeline produces responses for this recording.

- **Output file already exists**  
  For `gmr` / `rur`, if the target replay file already exists and you did not pass `--overwrite`, the converter aborts. Rerun with `--overwrite` if you are sure you want to replace the file.

- **Output directory already exists in `rtj` mode**  
  JSON dump mode refuses to reuse an existing directory unless you pass `--overwrite`, in which case the directory is removed and recreated.

- **Cannot determine `game_id` / `player_id`**  
  - In `gmr` mode, you must provide both via `--game-id` and `--player-id`.  
  - In `rur` mode, they are inferred from `ResponseMetadata`. If inference fails (e.g. inconsistent IDs in the stream), provide them explicitly.

- **Bulk mode reports “No suitable recording directories found”**  
  Check that:
  - Your `--recording-dir` root actually contains per-recording subdirectories.
  - Those subdirectories contain the required files for the chosen mode (`game_states.bin` for `gmr`, `responses*.jsonl.zst` for `rur`).
  - Any `--recording-name` filters you provided actually match directory names.

---

### See Also

- [`services/server_converter/README.md`](../../services/server_converter/README.md) – online converter service that consumes responses from Redis and writes replays + metadata.
- [`tools/replay_debug/README.md`](../replay_debug/README.md) – interactive replay inspection and debugging tool.
- [`README.md` at the repo root](../../README.md) – overall architecture, CLI overview, and Docker deployment.
- `libs/conflict_interface/examples/replay_roundtrip.py` – validation tool comparing replay reconstruction vs. JSON responses.
- `libs/conflict_interface/examples/replay_province_changed.py` – example of consuming replay files for province-change analysis.

