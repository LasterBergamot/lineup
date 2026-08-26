FROM python:3.13-slim

# LibreOffice converts the .docx to PDF. The template is authored in Calibri / Calibri Light
# (proprietary, absent here), so we also install the libre metric-compatible substitutes:
# Carlito (Calibri), Caladea (Cambria) and Liberation (Arial/Times/Courier). Without them
# LibreOffice falls back to a font with different metrics and the layout drifts.
# --no-install-recommends is kept for a lean image, so the font packages are listed explicitly.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libreoffice \
        fonts-crosextra-carlito \
        fonts-crosextra-caladea \
        fonts-liberation2 \
    && rm -rf /var/lib/apt/lists/*

# Force Calibri / Calibri Light -> Carlito so the docx renders with Calibri's metrics.
COPY docker/fontconfig/99-calibri-carlito.conf /etc/fonts/conf.d/99-calibri-carlito.conf
RUN fc-cache -f

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
