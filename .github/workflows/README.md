# GitHub Actions Workflows

This directory contains CI/CD workflows for the ConflictInterface repository.

## Workflows

### 1. Tests (`tests.yml`)

Runs Python tests on every push and pull request.

- **Trigger**: Push, Pull Request, Manual (workflow_dispatch)
- **Actions**: 
  - Sets up Python 3.12
  - Installs dependencies
  - Downloads test data
  - Runs test suite

### 2. Documentation (`documentation.yml`)

Builds and deploys Sphinx documentation to GitHub Pages.

- **Trigger**: Currently disabled (empty trigger list)
- **Actions**: 
  - Builds Sphinx documentation
  - Deploys to gh-pages branch on push to main

### 3. Docker Build (`server-observer-docker.yml`)

Builds and publishes the ServerObserver Docker image to GitHub Container Registry.

- **Trigger**: 
  - Push to `main` branch (when relevant files change)
  - Manual trigger via workflow_dispatch
  
- **Monitored Paths**:
  - `services/server_observer/**`
  - `libs/conflict_interface/**`
  - `setup.py`
  - `pyproject.toml`

- **Actions**:
  - Builds multi-stage Docker image
  - Pushes to `ghcr.io/zdox/server-observer`
  - Tags: `latest`, `main`, `main-<sha>`
  - Uses layer caching for faster builds

**Note:** The Docker image does NOT contain configuration or account pool files. These must be mounted at runtime for security and configuration flexibility.

### 4. Client version tracking (`conflict_interface-check-new-version.yml`)

Detects the client version Conflict of Nations currently ships and keeps the README badges honest.

- **Trigger**: Daily at 05:00 UTC, on a push to `main` that changes `data_types/newest/version.py`, and manually
- **Actions**:
  - Runs `scripts/check_new_version.py` — hub-logs-in, guest-joins a live game and reads its `clientVersion`
  - Runs `scripts/write_version_badges.py` to regenerate `supported-client.json` and `latest-client.json`
    (shields.io endpoint format, rendered as badges in the root README), then force-pushes them to the
    `badges` branch — but only when a number actually changed. `main` is pull-request-only, so the badges
    live on that content-only orphan branch instead and the README reads them from
    `raw.githubusercontent.com/zDox/Conlyse/badges/`
  - Dispatches `conflict_interface-create-version-data.yml` when ConflictData has no data for the detected version yet

The "latest CoN client" badge turns orange whenever the live version is ahead of
`libs/conflict_interface/conflict_interface/data_types/newest/version.py`, i.e. Conlyse needs a datatype bump.

### 5. Version data capture (`conflict_interface-create-version-data.yml`)

- **Trigger**: `workflow_dispatch` with a `version` input (normally dispatched by the workflow above)
- **Actions**: records game responses and static map data, downloads and beautifies the live client JS bundle, then
  opens a PR against `zDox/ConflictData` adding `v{version}/`

## Secrets

The following secrets are used by the workflows:

- `TEST_ACCOUNT_USERNAME` - Test account username (tests.yml)
- `TEST_ACCOUNT_PASSWORD` - Test account password (tests.yml)
- `TEST_ACCOUNT_EMAIL` - Test account email (tests.yml)
- `TEST_PROXY_URL` - Test proxy URL (tests.yml)
- `GITHUB_TOKEN` - Automatically provided by GitHub (docker-build.yml, documentation.yml)

## Permissions

- **tests.yml**: `contents: write`
- **documentation.yml**: `contents: write`
- **docker-build.yml**: `contents: read, packages: write`

## Using Pre-built Docker Images

Images built by the workflow are available at:

```bash
docker pull ghcr.io/zdox/server-observer:latest

# Run with config files mounted (REQUIRED)
docker run -v $(pwd)/config:/app ghcr.io/zdox/server-observer:latest
```

**Important:** You must provide `config.json` and `account_pool.json` via volume mount. These files are NOT included in the image for security reasons.

See `services/server_observer/README.md` for more details.
