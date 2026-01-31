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

### 3. Docker Build (`docker-build.yml`)

Builds and publishes the ServerObserver Docker image to GitHub Container Registry.

- **Trigger**: 
  - Push to `main` branch (when relevant files change)
  - Manual trigger via workflow_dispatch
  
- **Monitored Paths**:
  - `tools/server_observer/**`
  - `conflict_interface/**`
  - `setup.py`
  - `pyproject.toml`

- **Actions**:
  - Builds multi-stage Docker image
  - Pushes to `ghcr.io/zdox/server-observer`
  - Tags: `latest`, `main`, `main-<sha>`
  - Uses layer caching for faster builds

**Note:** The Docker image does NOT contain `config.json` or `account_pool.json`. These files must be mounted at runtime for security and configuration flexibility.

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

See `tools/server_observer/DOCKER.md` for more details.
