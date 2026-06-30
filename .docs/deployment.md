# Развёртывание

Развёртывание, CI/CD, мониторинг и резервное копирование СТАНКИН Анти-Спам.

## Docker

### Docker-образ

Образ публикуется в GitHub Container Registry:

```
ghcr.io/overklassniy/stankin_antispam_bot:latest
```

Dockerfile использует многостадийную сборку:

1. **frontend-builder** — сборка фронтенда (Node.js 22, TypeScript, SCSS, Tailwind)
2. **deps-builder** — установка Python-зависимостей через uv (Python 3.14)
3. **libgomp-builder** — получение libgomp из Chainguard dev-образа (для ONNX Runtime)
4. **runtime** — минимальный образ на базе Chainguard Python

Runtime-образ не содержит shell, что уменьшает поверхность атаки.

### Docker Compose

Конфигурация `docker-compose.yml`:

```yaml
services:
  app:
    image: ghcr.io/overklassniy/stankin_antispam_bot:latest
    pull_policy: always
    container_name: stankin-antispam
    env_file: .env
    volumes:
      - ./models:/app/models
      - ./logs:/app/logs
      - ./data:/app/data
    ports:
      - "12523:12523"
    restart: unless-stopped
```

Монтируемые директории:

- `models/` — ML-модели (BERT, ONNX)
- `logs/` — файлы логов
- `data/` — данные приложения

### Развёртывание на сервере

1. Установите Docker и Docker Compose на сервер
2. Склонируйте репозиторий или создайте директорию с `docker-compose.yml` и `.env`
3. Заполните `.env` (минимум: `BOT_TOKEN`, `DATABASE_URL`, `SECRET_KEY`, `NOTIFICATION_CHAT_ID`)
4. Убедитесь, что PostgreSQL доступен с сервера
5. Запустите:

```bash
docker compose up -d
```

6. Проверьте логи:

```bash
docker compose logs -f
```

### Обновление

```bash
docker compose pull
docker compose up -d
```

Образ скачивается заново при `pull_policy: always`.

## CI/CD

GitHub Actions workflow (`.github/workflows/docker-publish.yml`) автоматически собирает и публикует Docker-образ при пуше в ветку `master`.

Процесс:

1. Checkout исходного кода
2. Настройка Docker Buildx
3. Авторизация в GHCR через `GITHUB_TOKEN`
4. Сборка образа с кешированием слоёв через GitHub Actions cache
5. Публикация с тегом `latest` (только для ветки `master`)
6. Для pull request — сборка без публикации (проверка)

## Мониторинг

### Sentry

Интеграция с Sentry настраивается через переменные окружения:

- `SENTRY_DSN` — обязательный для включения мониторинга
- `SENTRY_TRACES_SAMPLE_RATE` — процент трейс-сессий
- `SENTRY_ENABLE_LOGS` — отправка логов как structured logs
- `SENTRY_LOGS_LEVEL` — уровень логов для structured logs
- `SENTRY_BREADCRUMBS_LEVEL` — уровень breadcrumbs
- `SENTRY_EVENT_LEVEL` — уровень events

Sentry перехватывает:

- Неперехваченные исключения в обработчиках бота
- Ошибки в FastAPI-приложении
- Контекстные breadcrumbs для диагностики

Версия приложения (`APP_VERSION = '3.0.0'`) передаётся в Sentry как release.

### Логирование

Логи записываются в файлы в директории `logs/` и выводятся в stdout. Уровень логирования зависит от режима:

- Обычный режим — `INFO`
- Тестовый режим (`TESTING=true`) — `DEBUG`

## Резервное копирование

### Автоматические бэкапы

Настраиваются через веб-панель или API:

- `BACKUP_ENABLED` — включение автоматических бэкапов
- `BACKUP_START_TIME` — время начала (формат HH:MM)
- `BACKUP_INTERVAL_HOURS` — интервал в часах

Процесс:

1. Создание дампа БД через `pg_dump`
2. Вычисление SHA-256 хеша файла
3. Отправка файла в Telegram-чат управления в тред `NOTIFICATION_CHAT_BACKUP_THREAD`

### Ручной бэкап

Через API:

```bash
curl -X POST http://localhost:12523/api/v1/backup \
  -H "Cookie: session=..." 
```

Через веб-панель — кнопка создания резервной копии в разделе настроек.

Требуется наличие `pg_dump` в окружении. В Docker-образе `postgresql-client` предустановлен.
