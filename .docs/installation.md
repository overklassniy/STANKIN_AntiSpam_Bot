# Установка

Требования, способы запуска и настройка окружения для СТАНКИН Анти-Спам.

## Требования

| Компонент | Версия | Назначение |
| --- | --- | --- |
| Python | 3.14+ | Backend, бот, ML |
| PostgreSQL | 14+ | Хранение данных |
| Node.js | 22+ | Сборка фронтенда (только для разработки) |
| Docker | 24+ | Контейнерный запуск (рекомендуется) |

## Способ 1: Docker Compose (рекомендуется)

### 1. Подготовка

```bash
git clone https://github.com/overklassniy/STANKIN_AntiSpam_Bot.git
cd STANKIN_AntiSpam_Bot
cp .env.example .env
```

### 2. Настройка переменных окружения

Отредактируйте `.env`, обязательно заполните:

- `BOT_TOKEN` — токен бота от @BotFather
- `DATABASE_URL` — строка подключения к PostgreSQL
- `SECRET_KEY` — секретный ключ для сессий
- `ADMIN_PASSWORD` — пароль администратора (первичная инициализация)
- `NOTIFICATION_CHAT_ID` — ID чата управления

Полный список переменных — в [configuration.md](configuration.md).

### 3. Запуск

```bash
docker compose up -d
```

Используется готовый образ из GitHub Container Registry. Веб-панель доступна по адресу `http://localhost:12523`.

### 4. Получение доступа к панели

Отправьте боту в личные сообщения команду:

```
/start get_password
```

или

```
/get_password
```

Бот проверит, что вы администратор хотя бы в одной группе, и отправит учётные данные для входа.

## Способ 2: Локальный запуск

### 1. Установка Python-зависимостей

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-ml-onnx.txt
```

### 2. Сборка фронтенда

```bash
npm ci
npm run build
```

### 3. Настройка окружения

```bash
cp .env.example .env
# Отредактируйте .env
```

### 4. Подготовка базы данных

Убедитесь, что PostgreSQL запущен и база данных, указанная в `DATABASE_URL`, существует. Таблицы создаются автоматически при первом запуске.

### 5. Запуск

```bash
python run.py
```

Режимы запуска:

```bash
python run.py              # Бот и панель (по умолчанию)
python run.py --bot        # Только бот
python run.py --panel      # Только панель
```

## ML-модели

BERT-модель должна находиться в директории `models/`. По умолчанию используется `finetuned_rubert_tiny2`. Модель можно указать через настройку `BERT_MODEL` в базе данных или переменную окружения `BERT_MODEL`.

Поддерживаемые форматы моделей:

- **ONNX** — файлы `model.onnx` или `model_quantized.onnx` в директории модели
- **PyTorch / safetensors** — стандартный формат transformers

Сжатые модели размещаются в `models/compressed/` и выбираются с префиксом `compressed/` в веб-панели.

## Проверка установки

После запуска проверьте:

1. Бот отвечает на команду `/start` в личных сообщениях
2. Веб-панель доступна по адресу `http://localhost:12523`
3. В логах нет ошибок подключения к базе данных
4. Команда `/get_password` возвращает учётные данные
