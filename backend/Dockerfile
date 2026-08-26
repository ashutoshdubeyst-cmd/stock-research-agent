# syntax=docker/dockerfile:1

FROM python:3.13-slim AS runtime

# Avoid bytecode files, flush logs immediately, and keep pip caches out.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000

WORKDIR /app

# Run the API as an unprivileged user.
RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup --home /app appuser

# Keep dependency installation cacheable when only source code changes.
COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install --requirement requirements.txt

COPY --chown=appuser:appgroup app ./app

USER appuser

EXPOSE 8000

# Use Python's standard library so curl/wget is unnecessary.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
