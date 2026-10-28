---
paths:
  - "backend/Dockerfile"
  - "backend/.dockerignore"
  - "backend/docker/**"
  - "compose.yml"
---

# Container, fonts and Compose

The template is authored in Calibri/Calibri Light (proprietary). The container ships the libre metric-compatible substitutes (Carlito etc.) so the PDF layout matches the source `.docx`; without them LibreOffice substitutes a differently-sized font and the tab-stop/table layout drifts.

## Image and Compose

- `backend/Dockerfile`: two stages, both `python:3.13-slim` **pinned by digest** (Dependabot's docker ecosystem bumps tag + digest). *builder* installs the deps with the pinned `uv` image (`uv sync --frozen --no-dev`, bytecode-compiled); *runtime* adds `libreoffice-writer-nogui` (no GUI stack; fidelity verified by the e2e suite), `tini` as PID 1 (`ENTRYPOINT ["tini", "--"]`, reaps `soffice.bin` children, instant `docker stop`) and the fonts, then copies the venv in. uv is not in the final image. Runs as the non-root `app` user (uid 10001, owns `/app` so the default SQLite file can be written; `HOME=/home/app`). `HEALTHCHECK` polls `GET /health` (liveness only, so a DB outage doesn't restart the container) with the interpreter, since curl isn't installed. `PYTHONUNBUFFERED=1`. Image size went from ~1.16 GB to ~870 MB
- Fonts: `--no-install-recommends` is kept, so the metric-compatible font packages are installed explicitly — `fonts-crosextra-carlito` (Calibri/Calibri Light), `fonts-crosextra-caladea` (Cambria), `fonts-liberation2` (Arial/Times/Courier). `backend/docker/fontconfig/99-calibri-carlito.conf` (copied to `/etc/fonts/conf.d/`) forces Calibri → Carlito, and `fc-cache -f` refreshes the cache. These are what make the PDF match the source `.docx`.
- The Docker build context is `backend/` (`docker build -t lineup backend` in the Taskfile), so repo-root items (`.github/`, `.claude/`, `documentation/`, `frontend/`, `compose.yml`, `Taskfile.yml`) can never enter the image. `backend/.dockerignore` is a security control: the Dockerfile does `COPY . .`, so it must exclude `.env`/`.env.*` (`backend/.env` holds the Supabase credentials and now sits *inside* the context) and `*.db`, alongside tests, `*.md`, caches, `.git`. Add any new secret/local-state file to it. Because `tests/` is excluded the image ships without tests — that's why the e2e suite runs from the host against the running container, not inside the image.
- `CMD` runs `uvicorn` straight from `/app/.venv/bin` (on `PATH`): no `uv` at runtime, so no writable cache/`HOME` needed for it.
- `compose.yml` (repo root): single `api` service using the pre-built `lineup` image (not `build:`), with `cap_drop: [ALL]` and `no-new-privileges` (LibreOffice needs neither); the image's `HEALTHCHECK` is inherited, and `task test-e2e` starts it with `docker compose up -d --wait`. It gets its settings from `env_file: backend/.env` with `required: false` (Compose >= 2.24) — compose's own `.env` interpolation only looks next to `compose.yml`, so it would silently stop seeing `backend/.env`. With no `backend/.env` the container falls back to its in-container SQLite default.
- `task build` / `task rebuild` builds the image; `task up` / `task down` starts/stops it; containers can be monitored using `lazydocker`
- CI's `e2e` job scans the built `lineup:latest` image with `aquasecurity/trivy-action` (severity `CRITICAL,HIGH`) after `task test-e2e` runs — report-only (`exit-code: "0"`, never fails the build), since the LibreOffice + apt package surface has more CVEs than can realistically be kept at zero. Results go to the job log (table format) and the repo's Security → Code scanning tab (SARIF upload via `github/codeql-action/upload-sarif`).

## Day to day

- `compose.yml` uses `image: lineup`, not `build:` — so `task build`/`task rebuild` is always needed before `task up`
- To fully reset: `task down` → `docker rmi lineup` → `docker image prune` → `task rebuild` → `task up`
