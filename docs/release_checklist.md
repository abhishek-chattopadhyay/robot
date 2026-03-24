# ROBOT Release Checklist

Use this checklist before merging `devo` into `main` and creating a stable release.

## 1. Code readiness

- [ ] No known blocker bugs in the authenticated PBPK workflow
- [ ] Draft creation, validation, build, and deposit flow tested manually
- [ ] Draft ownership works correctly
- [ ] Crate ownership works correctly
- [ ] Deposit ownership works correctly
- [ ] No duplicate or stale API routes remain
- [ ] No dead UI files or outdated frontend code remain

## 2. Authentication and security

- [ ] ORCID login works in local testing
- [ ] Redirect URI is documented and configured correctly
- [ ] `.env` is not tracked by Git
- [ ] `.env.example` contains all required variables
- [ ] `PBPK_COOKIE_SECURE=false` is only used for local HTTP development
- [ ] Production deployment plan uses `PBPK_COOKIE_SECURE=true`

## 3. Testing and CI

- [ ] Local pytest suite passes
- [ ] GitHub Actions CI passes on `devo`
- [ ] Critical ownership and access tests are green
- [ ] No failing or skipped critical tests remain unexplained

```bash
PYTHONPATH=packages uv run pytest
```

## 4. Documentation

- [ ] README reflects the current app behavior
- [ ] Architecture documentation is up to date
- [ ] Governance documentation is up to date
- [ ] Roadmap reflects the current state and next priorities
- [ ] Release checklist itself is still accurate

## 5. Repository hygiene

- [ ] `.gitignore` excludes runtime state and secrets
- [ ] `uv.lock` is committed
- [ ] No local runtime files from `var/` are staged
- [ ] No temporary debug files are staged
- [ ] Commit history on `devo` is understandable enough for merge

## 6. Deployment readiness

- [ ] Docker build succeeds
- [ ] App starts successfully from Docker
- [ ] Persistent `var/` mount is documented
- [ ] ORCID environment variables are documented for deployment
- [ ] Zenodo token flow has been tested at least in sandbox

## 7. Manual smoke test before merge

- [ ] Open `/ui` while logged out → landing page is visible
- [ ] Click login → ORCID flow works
- [ ] Open `/ui/pbpk` while logged in → editor works
- [ ] Import or create PBPK metadata draft
- [ ] Validate draft
- [ ] Build RO-Crate
- [ ] See crate in Recent Crates
- [ ] Deposit to Zenodo sandbox successfully
- [ ] See deposit in Recent Deposits
- [ ] Logout works

## 8. Merge and release

- [ ] Merge strategy decided (recommended: squash merge or clean merge)
- [ ] `devo` merged into `main`
- [ ] First stable release tag chosen, e.g. `v0.1.0`
- [ ] Release notes drafted

## Suggested commands for final review

```bash
git status
PYTHONPATH=packages uv run pytest
docker build -t robot:latest .
git log --oneline --decorate --graph -20