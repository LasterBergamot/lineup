---
name: setup-project
description: Set up the lineup project from a fresh clone — install prerequisites, dependencies, build the container, run migrations, and verify everything works. Use when the repo has just been cloned and nothing is installed yet, or when helping someone get a working dev environment.
---

Set up this repo as if it had just been cloned and nothing were installed. Work through the
steps below in order, checking as you go rather than assuming success. Treat `README.md` as
the source of truth if anything here looks out of date — reread it before starting.

## 1. Check required tools

Verify each is installed; if missing, point the user to its install link from `README.md`
("Prerequisites" section) rather than guessing an install command yourself, since it's
OS-dependent:

- Python 3.13+ (`python3 --version`)
- `uv` (`uv --version`)
- `task` (`task --version`)
- Docker Engine + Docker Compose (`docker --version`, `docker compose version`) — required
  for PDF conversion (LibreOffice only runs inside the container)

Optional tools (`gh`, `yamllint`, `actionlint`, `lazydocker`) are not required for setup —
skip unless the user is specifically working on CI workflows or wants container monitoring.

## 2. Install dependencies

```bash
task install
```

This runs `uv sync` and creates the virtualenv. Confirm it completes without errors.

## 3. Run the test suite

```bash
task test
```

Should pass at 100% coverage. If it doesn't, something is wrong with the environment (not
the code) — stop and investigate before continuing (e.g. wrong Python version, stale lock
file).

## 4. Build and start the container

```bash
task build
task up
```

`task build` builds the `lineup` image (LibreOffice + metric-compatible fonts baked in);
`task up` starts it via `compose.yml`. The API should now be reachable at
`http://127.0.0.1:8000`, docs at `http://127.0.0.1:8000/docs`.

Verify with:

```bash
curl -sf http://127.0.0.1:8000/docs -o /dev/null && echo "API is up"
```

## 5. Run database migrations

The app auto-creates tables on startup outside of `ENV=production`, but for a setup that
matches how the container behaves, apply migrations explicitly:

```bash
task migrate
```

## 6. Run the e2e fidelity test (optional but recommended)

With the container running:

```bash
task test-e2e
```

Builds the image fresh, starts the container, runs the real PDF-conversion fidelity check
against `tests/resources/expected-rajtlista.pdf`, then tears down. This is the strongest
signal that LibreOffice/fonts are working correctly end to end.

## 7. Report status

Summarize what's installed, what's running, and flag anything that failed or was skipped
(e.g. Docker unavailable, a test failure) rather than declaring success by default.
