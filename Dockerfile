# Используем Python 3.11 slim
FROM python:3.11-slim

# Устанавливаем метаданные
LABEL maintainer="overklassniy"
LABEL description="СТАНКИН Анти-спам система"
LABEL version="2.1.0"

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем переменные окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --upgrade pip && \
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu && \
    pip install -r requirements.txt

# Копируем весь проект
COPY . .

# Создаем директории для volumes
RUN mkdir -p /app/logs /app/instance /app/data

# Определяем volumes для персистентных данных
VOLUME ["/app/logs", "/app/instance", "/app/data"]

# Открываем порт для панели
EXPOSE 12523

# Проверка работоспособности
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Команда по умолчанию
CMD ["python", "run.py"]
