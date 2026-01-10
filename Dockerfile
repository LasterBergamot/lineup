# -----------------------------------------------------------------------------
# Stage 1: Base image with Python and Poetry
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    # Poetry configuration
    POETRY_VERSION=1.7.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    # Application directory
    APP_HOME="/app"

# Add poetry to PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
        libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Set working directory
WORKDIR $APP_HOME

# Copy dependency files first (leverages Docker cache)
COPY pyproject.toml poetry.lock* ./

# -----------------------------------------------------------------------------
# Stage 2: Development image
# -----------------------------------------------------------------------------
FROM base AS development

# Install all dependencies including dev
RUN poetry install --no-root

# Copy application code
COPY . .

# Install the project itself
RUN poetry install

# Expose port
EXPOSE 5000

# Development server with hot-reload
# Note: For development, use docker-compose which mounts volumes for hot-reload
CMD ["python", "run.py"]

# -----------------------------------------------------------------------------
# Stage 3: Production dependencies
# -----------------------------------------------------------------------------
FROM base AS production-deps

# Install only production dependencies
RUN poetry install --no-root --only main

# Install gunicorn for production WSGI server
RUN pip install gunicorn==21.2.0

# -----------------------------------------------------------------------------
# Stage 4: Production image (minimal)
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    APP_HOME="/app" \
    # Production Flask configuration
    FLASK_ENV=production

# Install only runtime dependencies (libpq for PostgreSQL)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Set working directory
WORKDIR $APP_HOME

# Copy installed packages from production-deps stage
COPY --from=production-deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=production-deps /usr/local/bin/gunicorn /usr/local/bin/gunicorn

# Copy application code
COPY --chown=appuser:appgroup . .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:5000/api/v1/health || exit 1

# Production server using gunicorn
# - Workers: 2*CPU+1 is a good default (configured via env var or default to 4)
# - Bind to 0.0.0.0 to accept connections from outside container
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--access-logfile", "-", "--error-logfile", "-", "run:app"]
