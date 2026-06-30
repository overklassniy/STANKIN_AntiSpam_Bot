# Разработка

Настройка окружения разработки, сборка фронтенда и локальный запуск СТАНКИН Анти-Спам.

## Требования для разработки

| Инструмент | Версия | Назначение |
| --- | --- | --- |
| Python | 3.14+ | Backend |
| Node.js | 22+ | Сборка фронтенда |
| PostgreSQL | 14+ | База данных |
| git | — | Контроль версий |

## Настройка окружения

### 1. Клонирование

```bash
git clone https://github.com/overklassniy/STANKIN_AntiSpam_Bot.git
cd STANKIN_AntiSpam_Bot
```

### 2. Python-окружение

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-ml-onnx.txt
```

### 3. Node.js-окружение

```bash
npm ci
```

### 4. Переменные окружения

```bash
cp .env.example .env
```

Заполните обязательные переменные. Для локальной разработки используйте тестовый режим:

```
TESTING=true
TEST_BOT_TOKEN=your_test_bot_token
```

### 5. База данных

Создайте базу данных PostgreSQL и укажите строку подключения в `DATABASE_URL`. Таблицы создаются автоматически при первом запуске.

## Сборка фронтенда

### Однократная сборка

```bash
npm run build
```

Команда выполняет последовательно:

1. `build:tailwind` — компиляция Tailwind CSS через PostCSS
2. `build:scss` — компиляция SCSS в сжатый CSS
3. `build:ts` — компиляция TypeScript в JavaScript

Результаты помещаются в `panel/static/styles/` и `panel/static/js/`.

### Режим наблюдения

Для автоматической пересборки при изменениях:

```bash
npm run watch
```

Запускает параллельно:

- `watch:tailwind` — отслеживание изменений Tailwind CSS
- `watch:scss` — отслеживание изменений SCSS
- `watch:ts` — отслеживание изменений TypeScript

## Запуск

### Полный запуск (бот + панель)

```bash
python run.py
```

### Только бот

```bash
python run.py --bot
```

### Только панель

```bash
python run.py --panel
```

Веб-панель доступна по адресу `http://localhost:12523`.

## Структура фронтенда

### TypeScript (`panel/src/ts/`)

| Файл | Назначение |
| --- | --- |
| `api.ts` | API-клиент для REST-эндпоинтов |
| `settings.ts` | Логика страницы настроек |
| `pagination.ts` | Клиентская пагинация таблиц |
| `hamburger.ts` | Мобильное меню |
| `theme-toggle.ts` | Переключение тёмной/светлой темы |
| `toast.ts` | Уведомления (toast-сообщения) |
| `main.ts` | Логика главной страницы |
| `login.ts` | Логика страницы входа |
| `loginFaq.ts` | FAQ на странице входа |
| `settings-page.ts` | Инициализация страницы настроек |

### SCSS (`panel/src/scss/`)

| Файл | Назначение |
| --- | --- |
| `main.scss` | Entry point, импорт всех partials |
| `_variables.scss` | CSS-переменные, цвета, размеры |
| `_mixins.scss` | SCSS-миксины |
| `_base.scss` | Базовые стили, сброс, типографика |
| `_layout.scss` | Layout: сетка, контейнеры, шапка, подвал |
| `_components.scss` | Переиспользуемые компоненты |
| `_settings.scss` | Стили страницы настроек |
| `_login.scss` | Стили страницы входа |
| `_exception.scss` | Стили страниц ошибок |

## ML-модели для разработки

Для локальной разработки поместите BERT-модель в директорию `models/`. Модель должна содержать файл `config.json`. Поддерживаемые форматы:

- ONNX: файлы `model.onnx` или `model_quantized.onnx`
- PyTorch / safetensors: стандартный формат transformers

Модель выбирается через настройку `BERT_MODEL` в базе данных или переменную окружения.

## Отладка

### Тестовый режим

Включается переменной `TESTING=true`. В этом режиме:

- Используется `TEST_BOT_TOKEN` вместо `BOT_TOKEN`
- Проверяются все сообщения, включая от администраторов
- Уровень логирования повышается до `DEBUG`
- Веб-панель работает в debug-режиме uvicorn

### Логирование

Логи выводятся в stdout и записываются в файлы в директории `logs/`. Формат логов включает временная метку, уровень, модуль и сообщение.

### Sentry в разработке

Для локальной разработки Sentry можно отключить, не указывая `SENTRY_DSN`. Если нужно протестировать интеграцию, используйте отдельный проект Sentry с низким `SENTRY_TRACES_SAMPLE_RATE`.
