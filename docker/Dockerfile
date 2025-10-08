# syntax=docker/dockerfile:1.4

FROM python:3.11-slim AS build

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/opt/venv/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        python3-dev \
        libffi-dev \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv

WORKDIR /opt/app

COPY docker/requirements.prod.txt ./requirements.txt
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:${PATH}" \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=production \
    PORT=8080 \
    EPHEMERIS_BACKEND=swieph \
    PYTHONPATH=/opt/app

# Install runtime dependencies including curl for health checks
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libcairo2 \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libpangocairo-1.0-0 \
        libharfbuzz0b \
        libfreetype6 \
        libjpeg62-turbo \
        libpng16-16 \
        libtiff6 \
        libgdk-pixbuf-2.0-0 \
        libopenjp2-7 \
        shared-mime-info \
        fonts-dejavu \
        tzdata \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -r -s /bin/false -u 1001 ephemeris

WORKDIR /opt/app

COPY --from=build /opt/venv /opt/venv

COPY --chown=ephemeris:ephemeris api ./api
COPY --chown=ephemeris:ephemeris data ./data

# Create ephemeris directory with proper permissions
RUN mkdir -p /opt/app/data/ephemeris \
    && chown -R ephemeris:ephemeris /opt/app

ENV EPHEMERIS_DIR=/opt/app/data/ephemeris \
    USE_WEASY=true

# Switch to non-root user
USER ephemeris

EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
