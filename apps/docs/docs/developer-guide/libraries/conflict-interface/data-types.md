---
id: data-types
title: Data Types
---

The data types in ConflictInterface model the GameObjects that Conflict of Nations uses.
They are the bridge between Python objects and the JSON payloads we get from the game/client.

## Versioning

The game changes its JSON schema over time. To keep replays, parsing, and tooling working across client updates, ConflictInterface supports **multiple datatype versions**.

- **Where versions live**: `libs/conflict_interface/conflict_interface/data_types/`
  - **Versioned snapshots**: `v210/`, `v211/`, ...
  - **Current development head**: `newest/`
- **What “latest” means**:
  - The canonical latest version number is `conflict_interface.versions.LATEST_VERSION`, which is re-exported from `conflict_interface/data_types/newest/version.py`.
  - Supported versions are the ones that are registered with the `JsonParser` (see `libs/conflict_interface/conflict_interface/versions.py`).

## Retention policy

ConflictInterface intentionally keeps only a rolling window of datatype snapshots:

- **We keep at most the latest 4 `v###` directories** under `conflict_interface/data_types/`.
- `newest/` is the **current latest**; the `v###/` directories are the legacy snapshots.
- When a new client version lands and we add support:
  - we add a new snapshot directory for the previous latest (see workflow below)
  - and we **delete the oldest** snapshot directory if that would take us above 4 legacy versions

This keeps maintenance overhead and repository size under control while still giving us enough history to:
- parse a reasonable span of older replays/test data

## Updating data types to a new client version

This is the workflow we use when the game/client bumps its schema version.

### 1) Get the new “full test data” JSON

ConflictInterface’s conversion tests are driven by a captured gamestate JSON named:
`full_test_data_1_v<VERSION>.json`.

In CI, the tests download this file from the `zDox/ConflictData` repo (see `.github/workflows/conflict_interface-tests.yml`), using the current `LATEST_VERSION`.

Locally you can do the same (replace `<VERSION>`):

```bash
cd libs/conflict_interface
mkdir -p tests/test_data
wget -O "tests/test_data/full_test_data_1_v<VERSION>.json" \
  "https://raw.githubusercontent.com/zDox/ConflictData/refs/heads/main/FullTestData/full_test_data_1_v<VERSION>.json"
```

If you maintain the test-data capture pipeline, there is also a scheduled workflow that detects version changes and opens a PR to `ConflictData` (see `.github/workflows/conflict_interface-update-testdata.yml`).

### 2) Snapshot the previous latest into a `v###/` package

Before you start changing `newest/`, snapshot the current state so older versions remain supported.

- **Create a new directory**: `libs/conflict_interface/conflict_interface/data_types/v<OLD_LATEST>/`
- **Copy the current `newest/` contents** into it.

Example (illustrative):
- if `newest/version.py` currently says `212`, you snapshot into `v212/` before moving `newest/` forward.

Why: `conflict_interface/data_types/__init__.py` auto-imports version packages like `v210`, `v211`, ... so the parser registry keeps knowledge of those versions.

### 3) Bump `newest/` to the new version number

Update:
- `libs/conflict_interface/conflict_interface/data_types/newest/version.py` (`VERSION = ...`)

This is what flows through:
- `conflict_interface.versions.LATEST_VERSION`
- CI selecting which `full_test_data_1_v<VERSION>.json` to download
- the conversion test selecting which test file to load (see below)

### 4) Update the dataclasses/parsers in `newest/` until conversion passes

Now edit the types under:
- `libs/conflict_interface/conflict_interface/data_types/newest/`

Goal: parsing and dumping the new gamestate JSON should round-trip cleanly (or at least within the comparison constraints).

### 5) Enforce the “newest + 4 legacy versions” rule

If adding the new snapshot makes you exceed 4 legacy `v###/` directories:
- delete the oldest `v###/` directory (the smallest version number)

## Using the `game_object` conversion test to see what changed

The fastest way to learn “what broke” after a client update is to run the conversion test and read its diff output.

### What the test does

`libs/conflict_interface/tests/test_gameobject_conversion.py`:

- loads `tests/test_data/full_test_data_1_v{VERSION}.json` where `VERSION` comes from `data_types/newest/version.py`
- parses the JSON into `GameState` (and each individual `*State`)
- dumps the parsed objects back to JSON
- compares original vs dumped using `tests/helper_functions.compare_dicts`, printing **paths** for any missing keys, changed values, or type mismatches

Those printed paths are your “what changed” map.

### How to run it locally

```bash
cd libs/conflict_interface
python -m unittest -v tests.test_gameobject_conversion
```

Output looks like:

```text
Type at path ultshared.UltMod/upgrades/4117/ut/c/30 is different:
  Original: float
  Processed: int
Type at path ultshared.UltMod/upgrades/4117/ut/rnf is different:
  Original: float
  Processed: int
```

### How to interpret the output

- **“Type at path … is different”**: the dump produced a different JSON type than the input (e.g. `int` vs `float`).
- **The path is your breadcrumb trail**:
  - the prefix (e.g. `ultshared.UltMod`) typically identifies which top-level state/object you’re in
  - following segments (`upgrades/4117/...`) lead you to the exact nested field that mismatched
- **What to do next**:
  - find the corresponding type in `libs/conflict_interface/conflict_interface/data_types/newest/` for that state/object
  - adjust the field type logic so the round-trip preserves the expected JSON shape for the new client version