# References

Where to read more about everything this project is built on: the libraries and tools we run,
the services we deploy to, the specs we follow and the regulations we have to respect. New to
the project? Read [[Newcomer Guide]] first, then come here when you want the official docs for
something it mentions.

**How this page is kept up to date.** The *Libraries, images and actions* section is
**generated** from the files that declare them (`backend/pyproject.toml`,
`frontend/package.json`, `backend/Dockerfile`, `.github/workflows/`) by
`scripts/docs_references.py`. Run `task docs:references` after changing a dependency; CI
(`task docs:check`) fails if you forget. Version numbers are left out on purpose (Dependabot bumps
them weekly); look them up in `uv.lock` / `package-lock` / the `Dockerfile`. Every other section is handwritten: when you adopt a
new service, tool, spec or regulation, add a row in the matching table in the same PR.

## Core technologies

| Name | What it is here | Link |
|---|---|---|
| Python | Backend language (3.13) | [docs.python.org](https://docs.python.org/3/) |
| FastAPI | Web framework; generates the OpenAPI docs at `/docs` | [fastapi.tiangolo.com](https://fastapi.tiangolo.com/) |
| Pydantic | Request/response validation (`schemas.py`, `models.py`) | [docs.pydantic.dev](https://docs.pydantic.dev/) |
| Uvicorn | ASGI server that runs the FastAPI app | [uvicorn.org](https://www.uvicorn.org/) |
| SQLAlchemy (async) | ORM and database access | [docs.sqlalchemy.org](https://docs.sqlalchemy.org/) |
| Alembic | Database migrations | [alembic.sqlalchemy.org](https://alembic.sqlalchemy.org/) |
| python-docx | Fills the `.docx` lineup template | [python-docx.readthedocs.io](https://python-docx.readthedocs.io/) |
| LibreOffice (headless) | Converts the `.docx` to PDF inside the container | [libreoffice.org](https://www.libreoffice.org/) |
| SQLite | Local/test database | [sqlite.org](https://www.sqlite.org/docs.html) |
| PostgreSQL | Hosted database (via Supabase); row-level security | [postgresql.org/docs](https://www.postgresql.org/docs/current/) · [RLS](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) |

## Frontend (planned, see [[Roadmap: Frontend]])

| Name | What it is for | Link |
|---|---|---|
| React + TypeScript | UI framework and language | [react.dev](https://react.dev/) · [typescriptlang.org](https://www.typescriptlang.org/docs/) |
| Vite | Dev server and bundler | [vite.dev](https://vite.dev/) |
| Tailwind CSS | Styling | [tailwindcss.com](https://tailwindcss.com/) |
| shadcn/ui | Component library (Polaris theme, see `frontend/DESIGN.md`) | [ui.shadcn.com](https://ui.shadcn.com/) |
| TanStack Query | Data fetching, caching, retries (cold-start handling) | [tanstack.com/query](https://tanstack.com/query) |
| pdf.js | In-page PDF previews | [mozilla.github.io/pdf.js](https://mozilla.github.io/pdf.js/) |
| Vitest / Playwright | Unit and browser tests | [vitest.dev](https://vitest.dev/) · [playwright.dev](https://playwright.dev/) |

## Developer tooling

| Name | What it is for | Link |
|---|---|---|
| uv | Python dependency and environment manager (`uv.lock`) | [docs.astral.sh/uv](https://docs.astral.sh/uv/) |
| Task (`Taskfile.yml`) | Command runner behind every `task …` command | [taskfile.dev](https://taskfile.dev/) |
| Ruff | Linter and formatter (including the flake8-bandit `S` security rules) | [docs.astral.sh/ruff](https://docs.astral.sh/ruff/) |
| pytest, pytest-cov | Test runner and coverage (100% required) | [docs.pytest.org](https://docs.pytest.org/) · [pytest-cov](https://pytest-cov.readthedocs.io/) |
| tini | Minimal init process (PID 1) that reaps LibreOffice's child processes | [github.com/krallin/tini](https://github.com/krallin/tini) |
| Docker, Docker Compose | Container image and local run | [docs.docker.com](https://docs.docker.com/) · [Compose](https://docs.docker.com/compose/) |
| Mermaid | Diagrams in these wiki pages | [mermaid.js.org](https://mermaid.js.org/) |
| Claude Code | AI assistant used on this repo (`CLAUDE.md`, `.claude/skills/`) | [docs.claude.com/claude-code](https://docs.claude.com/en/docs/claude-code/overview) |

## CI/CD and security tooling

| Name | What it is for | Link |
|---|---|---|
| GitHub Actions | CI (`ci.yml`, `docs-check.yml`) and wiki sync (`wiki-sync.yml`) | [docs.github.com/actions](https://docs.github.com/actions) |
| Dependabot | Weekly dependency update PRs and security alerts | [docs.github.com/code-security/dependabot](https://docs.github.com/code-security/dependabot) |
| GitHub secret scanning + push protection | Blocks committed credentials | [docs.github.com/code-security/secret-scanning](https://docs.github.com/code-security/secret-scanning) |
| Trivy | Container image vulnerability scan in CI (report-only) | [trivy.dev](https://trivy.dev/) |

## Hosted services

| Service | Role | Link |
|---|---|---|
| Supabase | Postgres database and Auth (Google sign-in) | [supabase.com/docs](https://supabase.com/docs) · [signing keys](https://supabase.com/docs/guides/auth/signing-keys) · [API keys](https://supabase.com/docs/guides/api/api-keys) |
| Fly.io | API hosting (planned, scale to zero) | [fly.io/docs](https://fly.io/docs/) |
| Cloudflare Pages | Frontend hosting (planned) | [developers.cloudflare.com/pages](https://developers.cloudflare.com/pages/) |
| Sentry | Error monitoring (errors only, opt-in via `SENTRY_DSN`) | [docs.sentry.io](https://docs.sentry.io/) · [sensitive data](https://docs.sentry.io/platforms/python/data-management/sensitive-data/) |
| Google Identity (OAuth 2.0) | Sign-in provider behind Supabase Auth | [developers.google.com/identity](https://developers.google.com/identity/protocols/oauth2) |

## Specs and standards

| Spec | Why it matters here | Link |
|---|---|---|
| RFC 6266 (Content-Disposition) | The `filename*=UTF-8''…` download header, so `ő`/`ű` in file names work | [rfc-editor.org/rfc/rfc6266](https://www.rfc-editor.org/rfc/rfc6266) |
| OpenAPI | The API description FastAPI publishes at `/openapi.json`; the frontend client is generated from it | [spec.openapis.org](https://spec.openapis.org/oas/latest.html) |
| OAuth 2.0 (RFC 6749) | What "Sign in with Google" is built on | [rfc-editor.org/rfc/rfc6749](https://www.rfc-editor.org/rfc/rfc6749) |
| JWT (RFC 7519) and JWKS (RFC 7517) | The API validates the Supabase access token against the project's public keys | [RFC 7519](https://www.rfc-editor.org/rfc/rfc7519) · [RFC 7517](https://www.rfc-editor.org/rfc/rfc7517) |
| HTTP semantics (RFC 9110) | Status codes used by the API (404, 409, 422, 503, 504, …) | [rfc-editor.org/rfc/rfc9110](https://www.rfc-editor.org/rfc/rfc9110) |

## Regulations and security baselines

Not legal advice. The checkable requirements derived from these (IDs G1–G14, S1–S15, H1–H4) live
in `.claude/skills/compliance-audit/requirements.md`, tracked by epic #92.

| Source | What it covers | Link |
|---|---|---|
| GDPR (Regulation (EU) 2016/679) | Personal-data rules for players, staff and user accounts; clubs are controllers, we are their processor | [eur-lex.europa.eu](https://eur-lex.europa.eu/eli/reg/2016/679/oj) |
| EDPB guidelines | Legitimate interest, DPIA, ePrivacy storage access | [edpb.europa.eu](https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-22023-technical-scope-art-53-eprivacy-directive_en) |
| NAIH (Hungarian data-protection authority) | Supervisory authority, breach reporting, recommendations | [naih.hu](https://naih.hu/) · [breach reporting](https://naih.hu/adatvedelmi-incidensbejelento-rendszer) |
| Infotv. (Act CXII of 2011) | Hungarian data-protection act | [naih.hu](https://naih.hu/) |
| OWASP Top 10 | Baseline list of web application risks | [owasp.org/Top10](https://owasp.org/Top10/) |
| OWASP ASVS | Verification standard the security requirements map to | [owasp.org/ASVS](https://owasp.org/www-project-application-security-verification-standard/) |
| OWASP API Security Top 10 | API-specific risks (object-level authorization, resource limits) | [owasp.org/API-Security](https://owasp.org/API-Security/) |

## Libraries, images and actions (generated)

<!-- BEGIN GENERATED: dependencies (edit via `task docs:references`, not by hand) -->

### Python packages

Direct dependencies from `backend/pyproject.toml`. Exact versions are pinned in `backend/uv.lock`.

| Package | Group | Link |
|---|---|---|
| `aiosqlite` | runtime | [PyPI](https://pypi.org/project/aiosqlite/) |
| `alembic` | runtime | [PyPI](https://pypi.org/project/alembic/) |
| `asyncpg` | runtime | [PyPI](https://pypi.org/project/asyncpg/) |
| `fastapi` | runtime | [PyPI](https://pypi.org/project/fastapi/) |
| `httpx` | runtime | [PyPI](https://pypi.org/project/httpx/) |
| `pdfplumber` | dev | [PyPI](https://pypi.org/project/pdfplumber/) |
| `pyjwt` | runtime | [PyPI](https://pypi.org/project/pyjwt/) |
| `pytest` | dev | [PyPI](https://pypi.org/project/pytest/) |
| `pytest-asyncio` | dev | [PyPI](https://pypi.org/project/pytest-asyncio/) |
| `pytest-cov` | dev | [PyPI](https://pypi.org/project/pytest-cov/) |
| `python-docx` | runtime | [PyPI](https://pypi.org/project/python-docx/) |
| `ruff` | dev | [PyPI](https://pypi.org/project/ruff/) |
| `sentry-sdk` | runtime | [PyPI](https://pypi.org/project/sentry-sdk/) |
| `sqlalchemy` | runtime | [PyPI](https://pypi.org/project/sqlalchemy/) |
| `uvicorn` | runtime | [PyPI](https://pypi.org/project/uvicorn/) |

### Container image

From `backend/Dockerfile` (tags and digests are in the file).

| Image | Link |
|---|---|
| `ghcr.io/astral-sh/uv` | [github.com/astral-sh/uv](https://github.com/astral-sh/uv) |
| `python` | [hub.docker.com/_/python](https://hub.docker.com/_/python) |

| Debian package (`apt`) | Link |
|---|---|
| `fonts-crosextra-caladea` | [packages.debian.org](https://packages.debian.org/search?keywords=fonts-crosextra-caladea&searchon=names) |
| `fonts-crosextra-carlito` | [packages.debian.org](https://packages.debian.org/search?keywords=fonts-crosextra-carlito&searchon=names) |
| `fonts-liberation2` | [packages.debian.org](https://packages.debian.org/search?keywords=fonts-liberation2&searchon=names) |
| `libreoffice-writer-nogui` | [packages.debian.org](https://packages.debian.org/search?keywords=libreoffice-writer-nogui&searchon=names) |
| `tini` | [packages.debian.org](https://packages.debian.org/search?keywords=tini&searchon=names) |

### GitHub Actions

Third-party actions used in `.github/workflows/`.

| Action | Link |
|---|---|
| `actions/checkout` | [GitHub](https://github.com/actions/checkout) |
| `aquasecurity/trivy-action` | [GitHub](https://github.com/aquasecurity/trivy-action) |
| `arduino/setup-task` | [GitHub](https://github.com/arduino/setup-task) |
| `astral-sh/setup-uv` | [GitHub](https://github.com/astral-sh/setup-uv) |
| `github/codeql-action` | [GitHub](https://github.com/github/codeql-action) |

<!-- END GENERATED: dependencies -->
