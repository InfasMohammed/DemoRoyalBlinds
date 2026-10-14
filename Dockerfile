FROM python:3.12-slim AS builder
WORKDIR /app
RUN --mount=type=secret,id=build_ca,target=/tmp/build-ca.pem \
    if [ -f /tmp/build-ca.pem ]; then export PIP_CERT=/tmp/build-ca.pem; fi; \
    pip install --no-cache-dir uv==0.12.23
COPY backend/pyproject.toml backend/uv.lock ./
RUN --mount=type=secret,id=build_ca,target=/tmp/build-ca.pem \
    if [ -f /tmp/build-ca.pem ]; then export SSL_CERT_FILE=/tmp/build-ca.pem; fi; \
    uv sync --locked --no-dev --no-cache

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    APP_ENV=production \
    AUTH_REQUIRED=true \
    BUSINESS_DATA_SOURCE=supabase \
    DATA_MODE=demo \
    POST_APPROVAL_WORKER_ENABLED=false \
    DEMO_STORE_PATH=/tmp/rbdemo/reports.json
WORKDIR /app
RUN groupadd --gid 10001 appuser && useradd --uid 10001 --gid 10001 --no-create-home appuser
COPY --from=builder /app/.venv /app/.venv
COPY --chown=10001:10001 backend/app /app/app
COPY --chown=10001:10001 deploy/start.sh /app/start.sh
USER 10001:10001
EXPOSE 8080
CMD ["sh", "/app/start.sh"]
