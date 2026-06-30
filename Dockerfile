# Dockerfile — главный образ (только ONNX Runtime, без Torch)

# Стадия 1: сборка фронтенда
FROM node:22-slim AS frontend-builder

WORKDIR /build

COPY package.json package-lock.json ./
RUN npm ci

COPY postcss.config.js ./
COPY panel/src/ ./panel/src/
COPY panel/templates/ ./panel/templates/

RUN npm run build

# Стадия 2: установка Python-зависимостей
FROM python:3.14-slim AS deps-builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN uv venv /opt/venv --no-seed
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build

COPY requirements-prod.txt ./
RUN uv pip install --no-cache -r requirements-prod.txt && \
    uv pip uninstall -y pip setuptools hf-xet 2>/dev/null; true

# Очистка кеша и тестовых файлов в установленных пакетах
RUN find /opt/venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; true && \
    find /opt/venv -type d -name "tests" -exec rm -rf {} + 2>/dev/null; true && \
    find /opt/venv -type d -name "test" -exec rm -rf {} + 2>/dev/null; true && \
    find /opt/venv -name "*.pyc" -delete 2>/dev/null; true

# Исправляем symlink python в venv на путь Chainguard runtime
RUN ln -sf /usr/bin/python /opt/venv/bin/python && \
    ln -sf /usr/bin/python3 /opt/venv/bin/python3 && \
    ln -sf /usr/bin/python3.14 /opt/venv/bin/python3.14

# Стадия 3: установка системных пакетов из dev-образа
FROM cgr.dev/chainguard/python:latest-dev AS pkg-builder
USER root
RUN apk add --no-cache libgomp libstdc++-dev postgresql-client libpq liblz4-1

# Копируем pg_dump и рекурсивно собираем все разделяемые библиотеки через readelf
RUN <<'EOF'
set -e
mkdir -p /rootfs/usr/bin /rootfs/usr/lib
cp /usr/bin/pg_dump /rootfs/usr/bin/pg_dump
cp /usr/lib/libgomp.so.1 /rootfs/usr/lib/libgomp.so.1
cp /usr/lib/libstdc++.so* /rootfs/usr/lib/ 2>/dev/null
cp /usr/lib/libgcc_s.so* /rootfs/usr/lib/ 2>/dev/null

queue="/usr/bin/pg_dump"
processed=""
while [ -n "$queue" ]; do
    current="${queue%% *}"
    rest="${queue#* }"
    [ "$rest" = "$current" ] && rest=""
    queue="$rest"
    case "$processed" in
        *"$current"*) continue ;;
    esac
    processed="$processed $current"
    for lib in $(readelf -d "$current" 2>/dev/null | grep NEEDED | sed 's/.*\[\(.*\)\]/\1/'); do
        found=$(find /usr/lib -name "$lib" 2>/dev/null | head -1)
        if [ -n "$found" ]; then
            cp -L "$found" /rootfs/usr/lib/ 2>/dev/null
            queue="${queue:+$queue }$found"
        fi
    done
done
EOF

# Стадия 4: runtime на Chainguard
FROM cgr.dev/chainguard/python:latest AS runtime

ENTRYPOINT []
COPY --from=pkg-builder /rootfs/usr/lib/ /usr/lib/
COPY --from=pkg-builder /rootfs/usr/bin/pg_dump /usr/bin/pg_dump
COPY --from=deps-builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:/usr/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY core/ ./core/
COPY bot/ ./bot/
COPY panel/ ./panel/
COPY run.py ./

COPY --from=frontend-builder /build/panel/static/js/ ./panel/static/js/
COPY --from=frontend-builder /build/panel/static/styles/ ./panel/static/styles/

EXPOSE 12523

CMD ["/opt/venv/bin/python", "run.py"]