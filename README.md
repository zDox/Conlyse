# Conlyse

[![Supported client version](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FzDox%2FConlyse%2Fbadges%2Fsupported-client.json)](libs/conflict_interface/conflict_interface/data_types/newest/version.py)
[![Latest CoN client version](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FzDox%2FConlyse%2Fbadges%2Flatest-client.json)](.github/workflows/conflict_interface-check-new-version.yml)

Conlyse is an unofficial, open-source system for **recording, storing, and replaying Conflict of Nations games**. A headless Rust service captures live game state and publishes it to Redis; a Python daemon converts the stream into a compact, patch-based replay format (`.conrp`); and a PySide6 + OpenGL desktop client lets you time-travel through any moment of a recorded game.

![Conlyse Desktop](apps/docs/static/img/desktop.png)

---

## How it works

```
CoN game servers
      │
      ▼
 ServerObserver  ──(raw game state)──▶  Redis stream
 (Rust)
                                              │
                                             ▼
                                    ServerConverter  ──▶  PostgreSQL  (metadata)
                                    (Python)         ──▶  MinIO       (.conrp files)
                                                               │
                                                               ▼
                                                       Conlyse API  ◀──  Conlyse Desktop
                                                       (FastAPI)         (PySide6 + OpenGL)
```

| Component | What it does |
|---|---|
| **ServerObserver** (Rust) | Discovers live games, manages recording sessions, publishes raw responses to a Redis stream |
| **ServerConverter** (Python) | Consumes the stream, assembles patch-based `.conrp` replay files, writes metadata to PostgreSQL and files to MinIO |
| **Conlyse API** (FastAPI) | Auth (JWT + TOTP/email 2FA), RBAC, and pre-signed download endpoints on top of PostgreSQL + MinIO |
| **Conlyse Desktop** (PySide6 + OpenGL) | Interactive map viewer with timeline scrubbing, dock panels, dark/light theme |
| **conflict-interface** (Python + C++) | Core library: type-safe game-state data structures, replay builder, bidirectional time-travel playback, CoN API wrappers |

---

## Quick start

### Try the desktop client (no backend needed)

Download the pre-built binary from the [Releases page](https://github.com/zdox/Conlyse/releases/latest) — Windows, macOS, and Linux builds are available.

Or run from source (Python 3.12 + OpenGL 3.3+):

```bash
git clone https://github.com/zDox/Conlyse.git
cd Conlyse
pip install -e apps/desktop
python -m conlyse
```

Download the sample replay and static map data from [Releases](https://github.com/zdox/Conlyse/releases/latest) to try it immediately without running the recording pipeline.

### Run the full stack with Docker Compose

```bash
cp .env.example .env        # set passwords, JWT secret, etc.
docker compose -f infra/docker-compose.yml up -d
```

Services once healthy:

| Service | URL |
|---|---|
| Conlyse API | `http://localhost:8000` (OpenAPI at `/docs`) |
| MinIO Console | `http://localhost:9001` |
| PostgreSQL | `localhost:5432` |
| Redis | `localhost:6379` |

See [Deployment](apps/docs/docs/deployment.md) for the full configuration reference.

---

## Repository layout

```
apps/
  desktop/              PySide6 + OpenGL desktop client
  docs/                 Docusaurus documentation site
libs/
  conflict_interface/   Core Python library (C++ extensions via pybind11)
services/
  api/                  FastAPI service (auth, RBAC, downloads)
  server_converter/     Python replay-building daemon
  server_observer/      Rust game recording service
tools/
  recording_converter/  CLI for offline replay conversion
infra/                  Docker Compose configs (dev + prod)
```

Each component has its own README with setup and configuration details.

---

## Documentation

Full documentation lives in [`apps/docs/`](apps/docs/) and covers:

- [Getting started with conflict-interface](apps/docs/docs/conflict-interface/getting-started.md)
- [Desktop client guide](apps/docs/docs/desktop.md)
- [Full stack deployment](apps/docs/docs/deployment.md)
- [Server Observer configuration](apps/docs/docs/server-observer.md)
- [Server Converter configuration](apps/docs/docs/server-converter.md)

---

## Authors

Built by **zDox** and **Niknam3**.
