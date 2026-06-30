# Архитектура

Архитектура системы СТАНКИН Анти-Спам, компоненты и поток данных.

## Обзор

Система состоит из трёх основных компонентов, работающих в едином event loop:

- **Бот** (aiogram) — приём и обработка сообщений Telegram
- **Веб-панель** (FastAPI) — управление и мониторинг
- **Ядро** — общая инфраструктура: БД, конфигурация, логирование

```mermaid
graph TB
    subgraph Entry Point
        RUN[run.py]
    end

    subgraph Bot Module
        DP[Dispatcher]
        HANDLERS[Handlers]
        MOD[ModerationService]
        SPAM[SpamDetection]
        EXT[External APIs]
        DISC[Chat Discovery]
        BACKUP[BackupService]
        NOTIFY[Notifications]
    end

    subgraph Panel Module
        APP[FastAPI App]
        API[REST API]
        AUTH[Auth]
        PAGES[HTML Pages]
    end

    subgraph Core Module
        CFG[Config]
        DB[DB Pool]
        REPOS[Repositories]
        LOG[Logging]
        SENTRY[Sentry]
    end

    subgraph External
        TG[Telegram API]
        PG[(PostgreSQL)]
        MODELS[ML Models]
        CAS[CAS API]
        LOLS[LOLS API]
        OPENAI[OpenAI API]
    end

    RUN --> DP
    RUN --> APP
    DP --> HANDLERS
    HANDLERS --> MOD
    MOD --> SPAM
    MOD --> EXT
    MOD --> REPOS
    SPAM --> MODELS
    EXT --> CAS
    EXT --> LOLS
    SPAM --> OPENAI
    HANDLERS --> NOTIFY
    NOTIFY --> TG
    DP --> DISC
    DP --> BACKUP
    BACKUP --> PG
    APP --> API
    APP --> PAGES
    API --> AUTH
    API --> REPOS
    REPOS --> PG
    CFG --> RUN
    DB --> REPOS
    LOG --> SENTRY
```

## Запуск

Единый entry point — `run.py`. Поддерживает три режима:

- `--all` (по умолчанию) — бот и панель в одном event loop
- `--bot` — только бот
- `--panel` — только панель

При совместном запуске бот и панель разделяют общий пул соединений PostgreSQL. Сигналы SIGINT и SIGTERM обрабатываются для корректного завершения.

## Поток обработки сообщения

```mermaid
sequenceDiagram
    participant TG as Telegram
    participant DP as Dispatcher
    participant MOD as ModerationService
    participant SPAM as SpamDetection
    participant EXT as External APIs
    participant DB as PostgreSQL
    participant NOTIFY as Notifications

    TG->>DP: Входящее сообщение
    DP->>MOD: handle_message()
    MOD->>DB: Проверка чата (наблюдаемый?)
    MOD->>DB: Загрузка настроек чата
    MOD->>TG: Проверка автора (админ?)

    alt Автор не админ
        MOD->>DB: Проверка белого списка
        alt В белом списке
            MOD-->>DP: Пропустить
        else Не в белом списке
            MOD->>SPAM: analyze_message()
            SPAM->>SPAM: BERT-предсказание
            MOD->>EXT: check_cas(), check_lols()
            MOD->>SPAM: check_spam_chatgpt() (опционально)
            MOD->>MOD: determine_spam_status()

            alt Спам
                MOD->>TG: Удалить сообщение
                MOD->>DB: Сохранить запись о спаме
                MOD->>NOTIFY: Отправить уведомление
                NOTIFY->>TG: Алерт в чат управления
            else Не спам
                MOD-->>DP: Пропустить
            end
        end
    else Автор админ
        MOD-->>DP: Пропустить
    end
```

## Слой данных

Доступ к PostgreSQL организован через паттерн Repository. Все репозитории используют общий asyncpg connection pool.

```mermaid
graph LR
    subgraph Repositories
        CHAT[ChatRepository]
        SPAM[SpamRepository]
        MUTED[MutedRepository]
        SETTINGS[SettingsRepository]
        USER[UserRepository]
        WHITELIST[WhitelistRepository]
        COLLECTED[CollectedRepository]
    end

    POOL[asyncpg Pool] --> DB[(PostgreSQL)]
    CHAT --> POOL
    SPAM --> POOL
    MUTED --> POOL
    SETTINGS --> POOL
    USER --> POOL
    WHITELIST --> POOL
    COLLECTED --> POOL
```

| Репозиторий | Назначение |
| --- | --- |
| `ChatRepository` | Управление наблюдаемыми чатами |
| `SpamRepository` | Журнал обнаруженных спам-сообщений |
| `MutedRepository` | Ограниченные пользователи и история ограничений |
| `SettingsRepository` | Глобальные и per-chat настройки |
| `UserRepository` | Пользователи панели и права доступа к чатам |
| `WhitelistRepository` | Белый список пользователей, исключённых из проверки |
| `CollectedRepository` | Собранные сообщения (для анализа и обучения) |

## ML-детекция спама

Сервис `SpamDetection` использует многоуровневый подход:

1. **BERT-классификатор** — основная модель (ruBERT-tiny2), загружаемая через ONNX Runtime или transformers pipeline. Возвращает вероятность спама.

2. **Sklearn-ансамбль** — дополнительная проверка для серой зоны (когда BERT-уверенность между порогом уверенности и порогом спама). Использует TF-IDF и char-level признаки.

3. **ChatGPT** — опциональная проверка через OpenAI API для сообщений из серой зоны, когда BERT и sklearn не дают однозначного ответа.

4. **Внешние API** — проверка отправителя через CAS и LOLS. Если пользователь найден в базе спамеров, сообщение классифицируется как спам независимо от BERT.

Решение принимается в `ModerationService.determine_spam_status()` на основе совокупности всех проверок.

## Резервное копирование

`BackupService` создаёт дамп БД через `pg_dump`, вычисляет SHA-256 хеш и отправляет файл в Telegram-чат управления в указанный тред. Поддерживается как ручной запуск через API, так и автоматический по расписанию.
