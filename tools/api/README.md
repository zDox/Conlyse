# Conlyse API

FastAPI-based service providing authentication and download endpoints for the Conlyse ecosystem.

## Overview

The API connects to the existing PostgreSQL (`replays` database) and MinIO (S3-compatible) instances
that are already part of the ConflictInterface Docker Compose stack.

## Endpoints

### Authentication (`/api/v1/auth`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/register` | Register a new user account |
| `POST` | `/auth/login` | Login, returns JWT access + refresh tokens |
| `POST` | `/auth/refresh` | Exchange refresh token for new token pair |
| `POST` | `/auth/logout` | Invalidate refresh token / session |
| `GET`  | `/auth/me` | Get current authenticated user's profile |

### Downloads (`/api/v1/downloads`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/downloads/binary/{platform}` | Pre-signed URL for Conlyse binary (`windows`/`macos`/`linux`) |
| `GET` | `/downloads/replay/{game_id}/{player_id}` | Pre-signed URL for a replay file |
| `GET` | `/downloads/analysis/{game_id}/{player_id}` | Pre-signed URL for a replay analysis file |
| `GET` | `/downloads/static-map-data/{map_id}` | Pre-signed URL for static map data |

### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness probe |

## Auto-generated Docs

OpenAPI interactive docs are available at **`/docs`** (Swagger UI) and **`/redoc`** (ReDoc).

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `postgres` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DB` | `replays` | PostgreSQL database name |
| `POSTGRES_USER` | `converter` | PostgreSQL user |
| `POSTGRES_PASSWORD` | `changeme` | PostgreSQL password |
| `MINIO_ENDPOINT` | `http://minio:9000` | MinIO/S3 endpoint URL |
| `MINIO_ACCESS_KEY` | `minioadmin` | MinIO access key |
| `MINIO_SECRET_KEY` | `minioadmin` | MinIO secret key |
| `MINIO_BUCKET_REPLAYS` | `replays` | Bucket for replay/analysis files |
| `MINIO_BUCKET_BINARIES` | `binaries` | Bucket for Conlyse binaries |
| `MINIO_BUCKET_MAPS` | `maps` | Bucket for static map data |
| `MINIO_PRESIGN_EXPIRY` | `3600` | Pre-signed URL expiry in seconds |
| `JWT_SECRET_KEY` | `change-me-in-production` | Secret used to sign JWTs |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |

## Running Locally (Docker Compose)

```bash
# From the repo root
cp .env.example .env        # customise as needed
docker-compose up -d api
```

The API will be available at `http://localhost:8000`.

## Database Migrations

Alembic is used for schema management.  Migrations run inside the container:

```bash
docker-compose exec api alembic upgrade head
```

Or during local development (with dependencies installed):

```bash
cd tools/api
alembic upgrade head
```

## Roles

Users are assigned a role at registration:

| Role | Description |
|------|-------------|
| `user` | Standard user (default) |
| `admin` | Administrator |

Admin accounts must be promoted directly in the database for now (future phase will add an admin API).
