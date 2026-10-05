# Both stages are pinned by digest so a rebuild can't silently pick up a different base
# image; the Dependabot docker ecosystem (.github/dependabot.yml) bumps tag and digest together.

# --- builder: resolve and install the Python dependencies -------------------------------
FROM python:3.13-slim@sha256:3dd7cc108ec1493442514f5c2a871af6af0ec31d768ff6e378a93340c3b3db5f AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.18 /uv /usr/local/bin/uv

# Byte-compile at build time (faster first start) and copy instead of hard-linking, since the
# venv is moved to another stage. The uv cache would only bloat the layer.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# .dockerignore keeps secrets (.env), local databases and dev-only files out of this layer.
COPY . .

# --- runtime: LibreOffice + the app, running as an unprivileged user --------------------
FROM python:3.13-slim@sha256:3dd7cc108ec1493442514f5c2a871af6af0ec31d768ff6e378a93340c3b3db5f AS runtime

# LibreOffice converts the .docx to PDF. The template is authored in Calibri / Calibri Light
# (proprietary, absent here), so we also install the libre metric-compatible substitutes:
# Carlito (Calibri), Caladea (Cambria) and Liberation (Arial/Times/Courier). Without them
# LibreOffice falls back to a font with different metrics and the layout drifts.
# --no-install-recommends is kept for a lean image, so the font packages are listed explicitly.
# tini is PID 1: it reaps the soffice.bin children LibreOffice leaves behind and forwards
# signals, so `docker stop` is immediate.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libreoffice-writer-nogui \
        tini \
        fonts-crosextra-carlito \
        fonts-crosextra-caladea \
        fonts-liberation2 \
    && rm -rf /var/lib/apt/lists/*

# Force Calibri / Calibri Light -> Carlito so the docx renders with Calibri's metrics.
COPY docker/fontconfig/99-calibri-carlito.conf /etc/fonts/conf.d/99-calibri-carlito.conf
RUN fc-cache -f

# A fixed uid/gid so bind mounts and orchestrators see a stable, non-root identity. HOME is
# writable because LibreOffice and fontconfig expect one even though conversions use a
# private profile under /tmp. /app is created here (not by WORKDIR, which would make it
# root-owned) because the default SQLite database (./lineup.db) is written there.
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --create-home --home-dir /home/app \
        --shell /usr/sbin/nologin app \
    && mkdir /app \
    && chown app:app /app

ENV HOME=/home/app \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=builder --chown=app:app /app /app

USER app

EXPOSE 8000

# Liveness only (no ?db=1): a database outage must not make the orchestrator restart a
# healthy API. curl isn't installed, so use the interpreter we already have.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"]

ENTRYPOINT ["tini", "--"]
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
