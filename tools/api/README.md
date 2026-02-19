# Conlyse API

FastAPI-based service providing authentication, 2FA, device management, RBAC, and download endpoints for the Conlyse ecosystem.

## Overview

The API connects to the existing PostgreSQL (`replays` database) and MinIO (S3-compatible) instances
that are already part of the ConflictInterface Docker Compose stack.

## Endpoints

### Authentication (`/api/v1/auth`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/register` | Register a new user account |
| `POST` | `/auth/login` | Login; returns JWT pair or 2FA pending token if 2FA is enabled |
| `POST` | `/auth/2fa/verify` | Complete 2FA login with TOTP or email code |
| `POST` | `/auth/refresh` | Exchange refresh token for new token pair |
| `POST` | `/auth/logout` | Invalidate refresh token / session |
| `GET`  | `/auth/me` | Get current authenticated user's profile |

#### TOTP 2FA

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/2fa/totp/enroll` | Generate TOTP secret, return QR code provisioning URI |
| `POST` | `/auth/2fa/totp/verify` | Verify TOTP code to complete enrollment |
| `POST` | `/auth/2fa/totp/disable` | Disable TOTP for the current user |

#### Email 2FA

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/2fa/email/send` | Send verification code to user's email |
| `POST` | `/auth/2fa/email/verify` | Verify email 2FA code |

#### Device Management

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/auth/devices` | List all active devices for the current user |
| `DELETE` | `/auth/devices/{device_id}` | Revoke a specific device session |

### Downloads (`/api/v1/downloads`)

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| `GET` | `/downloads/binary/{platform}` | any authenticated | Pre-signed URL for Conlyse binary (`windows`/`macos`/`linux`) |
| `GET` | `/downloads/replay/{game_id}/{player_id}` | `pro`, `admin` | Pre-signed URL for a replay file |
| `GET` | `/downloads/analysis/{game_id}/{player_id}` | `pro`, `admin` | Pre-signed URL for a replay analysis file |
| `GET` | `/downloads/static-map-data/{map_id}` | any authenticated | Pre-signed URL for static map data |

### Admin (`/api/v1/admin`) — Admin role required

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/users` | List all users (paginated) |
| `GET` | `/admin/users/{user_id}` | Get details of a specific user |
| `PATCH` | `/admin/users/{user_id}/role` | Assign or change a user's role |
| `POST` | `/admin/users/{user_id}/ban` | Disable (ban) a user account |
| `POST` | `/admin/users/{user_id}/reset-password` | Reset a user's password |
| `DELETE` | `/admin/users/{user_id}/devices/{device_id}` | Force-logout a user's device |

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
| `MAX_DEVICES_PER_USER` | `2` | Maximum concurrent devices per account |
| `SMTP_HOST` | `localhost` | SMTP server host |
| `SMTP_PORT` | `587` | SMTP server port |
| `SMTP_USER` | `` | SMTP username |
| `SMTP_PASSWORD` | `` | SMTP password |
| `SMTP_FROM` | `noreply@conlyse.com` | From address for 2FA emails |
| `SMTP_TLS` | `true` | Use STARTTLS for SMTP |
| `EMAIL_2FA_CODE_EXPIRE_SECONDS` | `300` | Email 2FA code TTL in seconds |

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

| Role | Description |
|------|-------------|
| `free` | Standard user (default on registration) |
| `pro` | Pro user — can access replay/analysis downloads |
| `admin` | Administrator — full access including admin endpoints |

Roles can be changed via `PATCH /admin/users/{user_id}/role` (admin only).

## Two-Factor Authentication

### TOTP (Authenticator App)

1. `POST /auth/2fa/totp/enroll` — receive `provisioning_uri` and scan QR code in your authenticator app
2. `POST /auth/2fa/totp/verify` with `{"code": "123456"}` — activate TOTP
3. On next login, the response will include `{"two_fa_required": true, "two_fa_pending_token": "..."}` instead of tokens
4. `POST /auth/2fa/verify` with `{"two_fa_pending_token": "...", "code": "123456"}` — receive final JWT pair

### Email 2FA

1. `POST /auth/2fa/email/send` — receive a 6-digit code by email (valid for 5 minutes)
2. `POST /auth/2fa/email/verify` with `{"code": "123456"}` — activate email 2FA

## Device / Session Limits

Each login creates a device record. The maximum number of concurrent devices is controlled by `MAX_DEVICES_PER_USER` (default: 2). When the limit is reached, the oldest device is automatically removed.

Users can view and revoke their own devices via:
- `GET /auth/devices`
- `DELETE /auth/devices/{device_id}`

Admins can force-logout any user's device via:
- `DELETE /admin/users/{user_id}/devices/{device_id}`
