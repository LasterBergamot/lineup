# The self-hosted web image: the built app served by Caddy, which also proxies /api to the API and an
# allow-list of /auth/v1 paths to Supabase Auth (frontend/docker/Caddyfile). It holds no domain: Auth
# is reached on the page's own origin (VITE_AUTH_SAME_ORIGIN). Build context is frontend/.
FROM node:lts-slim@sha256:e4db4c914bf8ad241bd24804fc25d272d89bad97e68cdc8a1414862790a02c39 AS builder
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
# node:lts no longer ships corepack, so install the pnpm release that package.json pins
# (`"packageManager": "pnpm@x.y.z"`), which keeps that field the only place the version is set.
RUN npm install --global "$(node -p 'require("./package.json").packageManager')"
RUN pnpm install --frozen-lockfile
COPY . .
# Public values only. The anon key is a placeholder: self-hosted Auth has no gateway that checks it.
ENV VITE_AUTH_SAME_ORIGIN=true \
    VITE_SUPABASE_ANON_KEY=self-hosted \
    VITE_COLD_START_NOTICE=false
RUN pnpm build

FROM caddy:2-alpine@sha256:e70b164da81ef698b3ad19af799ea6086ce6d9e48ed4079eb9fe26f6fbf14ee5 AS runtime
COPY docker/Caddyfile /etc/caddy/Caddyfile
COPY --from=builder /app/dist /srv
# `_headers` is Cloudflare Pages syntax; Caddy sets the same headers itself. Caddy keeps its state
# under XDG_*_HOME, so point both at a directory the non-root user owns.
RUN rm -f /srv/_headers && mkdir -p /tmp/caddy && chown -R 1000:1000 /tmp/caddy
ENV XDG_DATA_HOME=/tmp/caddy XDG_CONFIG_HOME=/tmp/caddy
USER 1000:1000
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["wget", "-q", "--spider", "http://127.0.0.1:8080/"]
