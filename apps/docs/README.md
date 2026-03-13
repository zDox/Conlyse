# Conlyse Documentation

This app is a documentation site for **Conlyse**, built with [Docusaurus](https://docusaurus.io/).

All commands below are meant to be run from this directory:

```bash
cd apps/docs
```

## Installation

Install dependencies with npm (a `package-lock.json` is checked in):

```bash
npm install
```

## Local development

Start the local dev server:

```bash
npm run start
```

This starts a local development server and opens a browser window. Most edits are hot‑reloaded without restarting the server.

## Build

Create a production build:

```bash
npm run build
```

This generates static content into the `build` directory, which can be served by any static hosting service.

## Deployment

If you use GitHub Pages (via Docusaurus’ default workflow), you can build and deploy with:

```bash
npm run deploy
```

Depending on your configuration, you may optionally need:

```bash
USE_SSH=true npm run deploy
# or
GIT_USER=<your-github-username> npm run deploy
```

See the main project docs or `docusaurus.config.ts` for details on the current deployment setup.
