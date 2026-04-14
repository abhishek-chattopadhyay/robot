
# ROBOT Deployment Guide

This document describes how to deploy and update ROBOT in local development and production.

## 1\. Deployment modes

ROBOT should be run in two different modes depending on the environment.

### Local development

Use:

-   ORCID sandbox
-   local callback URL
-   non-secure cookies
-   local Docker or local FastAPI run

Typical local callback:

```
http://127.0.0.1:8000/v1/auth/orcid/callback
```

### Production

Use:

-   ORCID production
-   real HTTPS domain
-   secure cookies
-   Docker deployment on the server

Typical production callback:

```
https://robot.vhp4safety.nl/v1/auth/orcid/callback
```

## 2\. Local development setup

### Environment

Create a local `.env` file from `.env.example` and use sandbox values.

Example:

```
ORCID_CLIENT_ID=YOUR_SANDBOX_CLIENT_ID
ORCID_CLIENT_SECRET=YOUR_SANDBOX_CLIENT_SECRET
ORCID_REDIRECT_URI=http://127.0.0.1:8000/v1/auth/orcid/callback
ORCID_BASE_URL=https://sandbox.orcid.org
ORCID_USE_SANDBOX=true
ORCID_SCOPE=/authenticate

ROBOT_ENFORCE_AUTH=true
PBPK_SESSION_COOKIE=pbpk_session
PBPK_COOKIE_SECURE=false
PBPK_COOKIE_SAMESITE=lax
```

### Run locally

```
set -a
source .env
set +a
PYTHONPATH=packages uv run uvicorn pbpk_backend.app:app --reload
```

Open:

-   `http://127.0.0.1:8000/ui`
-   `http://127.0.0.1:8000/ui/pbpk`

## 3\. Production deployment setup

### Production requirements

Before deploying production auth, make sure:

-   the public domain is served over HTTPS
-   the ORCID production callback is registered exactly
-   Docker is installed on the server
-   runtime data is persistent

### ORCID production callback

The callback must exactly match:

```
https://robot.vhp4safety.nl/v1/auth/orcid/callback
```

### Server-side secret file

On the server, keep a file such as `robot.env` with real secrets.

Example:

```
ORCID_CLIENT_ID=YOUR_PRODUCTION_CLIENT_ID
ORCID_CLIENT_SECRET=YOUR_PRODUCTION_CLIENT_SECRET
ORCID_REDIRECT_URI=https://robot.vhp4safety.nl/v1/auth/orcid/callback
ORCID_BASE_URL=https://orcid.org
ORCID_USE_SANDBOX=false
ORCID_SCOPE=/authenticate

ROBOT_ENFORCE_AUTH=true
PBPK_SESSION_COOKIE=pbpk_session
PBPK_COOKIE_SECURE=true
PBPK_COOKIE_SAMESITE=lax
```

Optional only if needed:

```
PBPK_COOKIE_DOMAIN=robot.vhp4safety.nl
```

Do not commit `robot.env` to Git.

## 4\. Production Docker Compose pattern

The Git-tracked `docker-compose.yml` should contain variable placeholders.

Example:

```
services:
  robot:
    build: .
    container_name: robot-app
    ports:
      - "8000:8000"
    environment:
      PYTHONPATH: /app/packages
      PBPK_DATA_ROOT: /app/var
      PBPK_DB_PATH: /app/var/pbpk.db
      ROBOT_ENFORCE_AUTH: "${ROBOT_ENFORCE_AUTH}"
      PBPK_SESSION_COOKIE: "${PBPK_SESSION_COOKIE}"
      ORCID_CLIENT_ID: "${ORCID_CLIENT_ID}"
      ORCID_CLIENT_SECRET: "${ORCID_CLIENT_SECRET}"
      ORCID_REDIRECT_URI: "${ORCID_REDIRECT_URI}"
      ORCID_BASE_URL: "${ORCID_BASE_URL}"
      ORCID_USE_SANDBOX: "${ORCID_USE_SANDBOX}"
      ORCID_SCOPE: "${ORCID_SCOPE}"
      PBPK_COOKIE_SECURE: "${PBPK_COOKIE_SECURE}"
      PBPK_COOKIE_SAMESITE: "${PBPK_COOKIE_SAMESITE}"
      PBPK_COOKIE_DOMAIN: "${PBPK_COOKIE_DOMAIN}"
    volumes:
      - robot_data:/app/var
    restart: unless-stopped

volumes:
  robot_data:
```

## 5\. First-time production deployment

On the server:

### Clone the repository

```
git clone <your-repo-url>
cd robot
```

### Create the secret env file

```
cp robot.env.example robot.env
```

Edit `robot.env` and insert the real values.

### Start the container

```
docker compose --env-file robot.env up -d --build
```

## 6\. Updating production after a new release

When a new version is pushed to GitHub:

```
git pull origin main
docker compose --env-file robot.env up -d --build
```

This will rebuild and restart ROBOT with the updated code.

## 7\. Runtime persistence

ROBOT stores runtime data under `/app/var` inside the container.

This includes:

-   uploads
-   drafts
-   crates
-   SQLite auth/session database
-   audit files
-   temporary zip outputs

This data must remain persistent across restarts.

Do not delete the volume unless you intentionally want to wipe the runtime state.

## 8\. Health and config checks

### Auth config

```
curl -s https://robot.vhp4safety.nl/v1/auth/config
```

Expected values in production:

-   `orcid_use_sandbox: false`
-   `orcid_base_url: https://orcid.org`
-   `redirect_uri: https://robot.vhp4safety.nl/v1/auth/orcid/callback`
-   `cookie_secure: true`

### Logs

```
docker logs robot-app --tail 100
```

## 9\. Manual production smoke test

After each significant update, test:

1.  open `https://robot.vhp4safety.nl/ui`
2.  click **Login with ORCID**
3.  log in with a real ORCID account
4.  return to ROBOT dashboard
5.  open PBPK editor
6.  create or import draft
7.  validate draft
8.  build RO-Crate
9.  confirm crate appears in Recent Crates
10.  deposit to Zenodo sandbox if needed for verification
11.  confirm deposit appears in Recent Deposits
12.  logout

## 10\. Security notes

-   never commit real ORCID secrets
-   never commit `robot.env`
-   use HTTPS in production
-   use `PBPK_COOKIE_SECURE=true` in production
-   prefer sandbox for local development and testing
-   use ORCID production only on the deployed HTTPS domain

## 11\. Environment strategy summary

### Local

-   ORCID sandbox
-   localhost callback
-   insecure cookie allowed

### Production

-   ORCID production
-   HTTPS real domain callback
-   secure cookie required

**Simple rule:**  
sandbox + localhost for development, production + real domain for deployment.

## 12\. Recovery / rollback

If a deployment fails:

1.  inspect container logs
2.  verify `robot.env`
3.  verify `/v1/auth/config`
4.  rebuild the previous working commit if needed

Example rollback:

```
git checkout <previous-working-commit>
docker compose --env-file robot.env up -d --build
```

## 13\. Future improvements

Possible future deployment improvements include:

-   automatic `.env` loading for local development
-   health endpoint for container orchestration
-   staged deployment workflow
-   backup automation for runtime data
-   image registry-based release deployment