# Анти-спам система

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/e422b6595c0f4261bf30e844bbf70283)](https://app.codacy.com/gh/overklassniy/STANKIN_AntiSpam_Bot?utm_source=github.com&utm_medium=referral&utm_content=overklassniy/STANKIN_AntiSpam_Bot&utm_campaign=Badge_Grade)

Данный проект представляет собой комплексное решение для борьбы со спамом. Он включает в себя сбор и анализ данных, обучение различных моделей для обнаружения спама, интеграцию с Telegram через бота и разработку веб-панели для управления и мониторинга системы. Проект объединяет в себе возможности машинного обучения, автоматизации и веб-разработки, что позволяет эффективно выявлять спамовые сообщения и оперативно реагировать на них.

---

## Оглавление

- [Принципы работы системы](#принципы-работы-системы)
- [Установка и настройка](#установка-и-настройка)
  - [Клонирование репозитория и установка зависимостей](#клонирование-репозитория-и-установка-зависимостей)
  - [Настройка переменных окружения](#настройка-переменных-окружения)
  - [Настройка конфигурационного файла](#настройка-конфигурационного-файла)
  - [Подготовка моделей](#подготовка-моделей)
  - [Инициализация базы данных](#инициализация-базы-данных)
- [Используемые данные](#используемые-данные)
- [Скрипты и утилиты](#скрипты-и-утилиты)
- [Запуск компонентов проекта](#запуск-компонентов-проекта)
  - [Обучение и анализ моделей](#обучение-и-анализ-моделей)
  - [Telegram бот](#telegram-бот)
  - [Веб-панель управления](#веб-панель-управления)
  - [Основной скрипт](#основной-скрипт)
- [Структура проекта](#структура-проекта)
- [Поддержка](#поддержка)
- [Технологии](#технологии)

---

## Принципы работы системы

### Машинное обучение
- **Анализ данных и предобработка:**  
  Исходные данные собираются из различных источников и хранятся в каталоге `data/`. Для их очистки и приведения к единому формату используется блокнот `ipynb/1. Подготовка данных.ipynb` и скрипты из `utils/preprocessing.py`.
  
- **Обучение моделей:**  
  Для классификации спама используются несколько моделей, включая RuBERT и модели на основе логистической регрессии, наивного байеса и случайного леса. Ноутбуки в каталоге `ipynb/` демонстрируют процесс обучения, дообучения и оценки эффективности моделей. Результаты сохраняются в каталоге `models/`.

### Telegram бот
- **Интеграция с мессенджером:**  
  Бот, реализованный в проекте, подключается к Telegram через API, используя токены, указанные в файле `.env`. Он осуществляет мониторинг входящих сообщений и отправляет уведомления администраторам. Запуск бота осуществляется командой `python run_bot.py`.

### Веб-панель управления
- **Административный интерфейс:**  
  Веб-панель предоставляет возможность отслеживания статистики работы системы, управления моделями и просмотра логов. Панель разработана с использованием современных веб-технологий и запускается через файл `run_panel.py`. Интерфейс построен с разделением на шаблоны (HTML), стили (CSS) и скрипты (JavaScript).

---

## Установка и настройка

### Клонирование репозитория и установка зависимостей

1. **Клонирование репозитория:**

   ```bash
   git clone https://github.com/overklassniy/STANKIN_AntiSpam_Bot.git
   cd STANKIN_AntiSpam_Bot
   ```

2. **Создание виртуального окружения и установка зависимостей:**

   ```bash
   python -m venv venv
   source venv/bin/activate  # для Linux/macOS
   venv\Scripts\activate     # для Windows

   pip install --upgrade pip
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
   pip install -r requirements.txt
   ```

### Настройка переменных окружения

Создайте файл `.env` в корне проекта и задайте необходимые переменные. Пример содержимого:

```ini
BOT_TOKEN=токен_бота_Telegram
TEST_BOT_TOKEN=токен_тестового_бота_Telegram
OPENAI_API_KEY=API_ключ_OpenAI
SECRET_KEY=секретный_ключ_базы_данных
ADMIN_PASSWORD=пароль_администратора
HELPDESK_EMAIL=почта_техподдержки
```

### Настройка конфигурационного файла

Создайте файл `config.json` в корне проекта, используя следующий шаблон:

```json
{
    "TESTING": false,
    "BOT_NAME": "AntiSpam_bot",
    "TARGET_CHAT_ID": -123456789,
    "NOTIFICATION_CHAT_ID": -987654321,
    "NOTIFICATION_CHAT_98_SPAM_THREAD": 1,
    "NOTIFICATION_CHAT_94_SPAM_THREAD": 2,
    "NOTIFICATION_CHAT_NS_SPAM_THREAD": 3,
    "NOTIFICATION_CHAT_MUTED_THREAD": 4,
    "COLLECT_ALL_MESSAGES": false,
    "LOGS_DIR": "logs",
    "MODELS_DIR": "models",
    "BERT_MODEL": "models/finetuned_rubert_tiny2",
    "BERT_THRESHOLD": 0.945,
    "BERT_SURE_THRESHOLD": 0.98,
    "CHECK_REPLY_MARKUP": true,
    "CHECK_CAS": true,
    "CHECK_LOLS": true,
    "ENABLE_CHATGPT": false,
    "ENABLE_DELETING": true,
    "ENABLE_AUTOMUTING": false,
    "PANEL_PORT": 2222,
    "PERMANENT_SESSION_LIFETIME": 60,
    "REMEMBER_COOKIE_DURATION": 10080,
    "PER_PAGE": 10
}
```

**Описание ключей:**

- `TESTING` – Режим тестирования. Если `true`, система использует тестовые параметры.
- `BOT_NAME` – @username Telegram бота, под которым его можно найти в Telegram.
- `TARGET_CHAT_ID` – Идентификатор чата, в котором бот будет удалять спам-сообщения.
- `NOTIFICATION_CHAT_ID` – Идентификатор чата, в который бот будет присылать уведомления о спам-сообщениях.
- `NOTIFICATION_CHAT_98_SPAM_THREAD` – Номер подтемы чата (супергруппы), в которую бот будет присылать уведомления о спам-сообщениях.
- `NOTIFICATION_CHAT_94_SPAM_THREAD` – Номер подтемы чата (супергруппы), в которую бот будет присылать уведомления о спам-сообщениях, имеющих вероятность между BERT_THRESHOLD и BERT_SURE_THRESHOLD (не удаляются автоматически).
- `NOTIFICATION_CHAT_NS_SPAM_THREAD` – Номер подтемы чата (супергруппы), в которую бот будет присылать уведомления о спам-сообщениях, не прошедших проверку модели, но содержащих электронную почту.
- `NOTIFICATION_CHAT_MUTED_THREAD` – Номер подтемы чата (супергруппы), в которую бот будет присылать уведомления об ограниченных пользователях. 
- `COLLECT_ALL_MESSAGES` – Флаг, включающий сбор всех сообщений в отдельный файл `../data/collected_messages.txt`.
- `LOGS_DIR` – Директория для хранения логов работы системы.
- `MODELS_DIR` – Путь к каталогу с обученными моделями.
- `BERT_MODEL` – Путь к модели RuBERT, используемой для классификации сообщений.
- `BERT_THRESHOLD` – Порог уверенности для классификации сообщения как спам (значение от 0 до 1).
- `BERT_SURE_THRESHOLD` – Порог уверенности для классификации сообщения как спам у его удаления (значение от 0 до 1).
- `CHECK_REPLY_MARKUP` – Флаг, включающий проверку на вложенную клавиатуру.
- `CHECK_CAS` – Флаг, включающий проверку в Combot Anti-Spam (CAS).
- `CHECK_LOLS` – Флаг, включающий проверку в LOLS.
- `ENABLE_CHATGPT` – Флаг, включающий или отключающий использование ChatGPT для дополнительных оценок (true/false).
- `ENABLE_DELETING` – Флаг, включающий удаление рекламного сообщения.
- `ENABLE_AUTOMUTING` – Флаг, включающий последовательное ограничение пользователя. Пользователь теряет право отправлять сообщения и медиафайлы на 24 часа / 7 дней / навсегда, в зависимости от рецидива нарушения.
- `PANEL_PORT` – Порт, на котором будет запущена веб-панель управления.
- `PERMANENT_SESSION_LIFETIME` – Время жизни пользовательской сессии (в минутах).
- `REMEMBER_COOKIE_DURATION` – Продолжительность действия опции "Запомнить меня" (в минутах).
- `PER_PAGE` – Количество записей, отображаемых на одной странице веб-панели.

### Подготовка моделей

Загрузите модели машинного обучения для распознавания сообщений из вкладки [`Releases`](https://github.com/overklassniy/STANKIN_AntiSpam_Bot/releases/latest) либо последовательно запустите `.ipynb` файлы в соответствующей папке.

### Инициализация базы данных

Перед запуском проекта необходимо выполнить инициализацию базы данных. Выполните следующие команды из корня проекта в активированном виртуальном окружении:

```bash
flask --app panel.app init_db
flask --app panel.app init_admin
flask --app panel.app init_spam
flask --app panel.app init_muted
```

Эти команды:
- **init_db** – создают и настраивают базу данных,
- **init_admin** – добавляют администратора для веб-панели,
- **init_spam** – добавляет тестовое спам-сообщение в базу данных,
- **init_muted** – добавляет тестового ограниченного пользователя в базу данных.

---

## Используемые данные

Все исходные данные расположены в директории `data/` и включают файлы различных форматов (JSON, CSV, TXT) с наборами данных для обучения и тестирования моделей. Некоторые файлы были получены из внешних источников (источники указаны в соответствующих Jupyter Notebook). Перед запуском обучения убедитесь, что данные корректно предобработаны, используя блокнот `ipynb/1. Подготовка данных.ipynb`.

---

## Скрипты и утилиты

В каталоге `utils/` находятся вспомогательные скрипты, которые облегчают работу с проектом:

- **apis.py** – Функции для работы с внешними API.
- **basic.py** – Основные утилиты и вспомогательные функции.
- **config_web.py** – Конфигурация для веб-сервиса.
- **predictions.py** – Функции для получения предсказаний от обученных моделей.
- **preprocessing.py** – Скрипты для предобработки и очистки данных.

---

## Запуск компонентов проекта

### Обучение и анализ моделей

Для подготовки данных, обучения моделей и оценки их эффективности используются Jupyter Notebook файлы, расположенные в каталоге `ipynb/`. Вы можете запустить их в [Jupyter Notebook](https://jupyter.org/) или [JupyterLab](https://jupyterlab.readthedocs.io/).

### Telegram бот

Запустите Telegram бота, используя следующую команду:

```bash
python run_bot.py
```

Бот использует токены, указанные в файле `.env`, для подключения к API Telegram и мониторинга входящих сообщений.

### Веб-панель управления

Для запуска веб-панели выполните команду:

```bash
python run_panel.py
```

Веб-панель предоставляет административный интерфейс для управления системой, просмотра статистики, логов и выполнения других операций.

### Основной скрипт

Файл `run.py` предназначен для интегрированного запуска нескольких компонентов системы или выполнения основных задач проекта.

---

## Структура проекта

После всех манипуляций структура проекта должна выглядеть так:

```
.
├── .info/
│   └── ascii-art.txt
├── data/
│   ├── dataset.json
│   ├── dataset_discord.json
│   ├── dataset_telegram_kaggle.csv
│   ├── parsed_lols_2023.txt
│   ├── parsed_lols_2024.txt
│   ├── preprocessed.csv
│   ├── spam_samples_umputun.txt
│   └── test_clear.json
├── instance/
│   └── db.sqlite
├── ipynb/
│   ├── 1. Подготовка данных.ipynb
│   ├── 2. Обучение различных моделей.ipynb
│   ├── 3.1. Дообучение RuBert.ipynb
│   ├── 3.2. Дообучение RuBert с числовыми значениями.ipynb
│   └── 4. Дополнительные оценки.ipynb
├── models/
│   ├── finetuned_rubert_tiny2/
│   │   ├── config.json
│   │   ├── model.safetensors
│   │   ├── special_tokens_map.json
│   │   ├── tokenizer.json
│   │   ├── tokenizer_config.json
│   │   └── vocab.txt
│   ├── finetuned_rubert_tiny2_p/
│   │   ├── config.json
│   │   ├── model.safetensors
│   │   ├── special_tokens_map.json
│   │   ├── tokenizer.json
│   │   ├── tokenizer_config.json
│   │   └── vocab.txt
│   ├── finetuned_rubert_tiny2_with_numeric/
│   │   ├── config.json
│   │   ├── model.pth
│   │   ├── special_tokens_map.json
│   │   ├── tokenizer.json
│   │   ├── tokenizer_config.json
│   │   └── vocab.txt
│   ├── lr_model.pkl
│   ├── lr_sm_model.pkl
│   ├── nb_model.pkl
│   ├── nb_sm_model.pkl
│   ├── rf_model.pkl
│   ├── rf_sm_model.pkl
│   ├── scaler.pkl
│   └── vectorizer.pkl
├── panel/
│   ├── static/
│   │   ├── fonts/
│   │   │   ├── ALS_Sirius_Bold.otf
│   │   │   └── ALS_Sirius_Regular.otf
│   │   ├── images/
│   │   │   ├── stankin-logo.svg
│   │   │   └── stankin_max.svg
│   │   ├── scripts/
│   │   │   ├── hamburger.js
│   │   │   └── login_faq.js
│   │   └── styles/
│   │       ├── login.css
│   │       ├── main.css
│   │       ├── root.css
│   │       └── settings.css
│   ├── templates/
│   │   ├── login.html
│   │   ├── main.html
│   │   └── settings.html
│   ├── app.py
│   ├── auth.py
│   ├── db_models.py
│   └── main.py
├── utils/
│   ├── apis.py
│   ├── basic.py
│   ├── config_web.py
│   ├── predictions.py
│   └── preprocessing.py
├── .env
├── bot.py
├── config.json
├── requirements.txt
├── run_bot.py
├── run_panel.py
└── run.py
```

---

## Поддержка

Если у вас возникли вопросы, предложения или вы хотите внести улучшения, пожалуйста, создавайте [Issues](https://github.com/overklassniy/STANKIN_AntiSpam_Bot/issues) и [Pull Requests](https://github.com/overklassniy/STANKIN_AntiSpam_Bot/pulls). Ваш вклад очень важен для развития проекта!

---

## Технологии

- **[Python](https://github.com/python/cpython)** – основной язык разработки.
- **[Aiogram (3.17.0)](https://github.com/aiogram/aiogram)** – асинхронный фреймворк для работы с Telegram Bot API, используемый для взаимодействия с пользователями в режиме реального времени.
- **[Flask](https://github.com/pallets/flask)** – лёгкий веб-фреймворк, обеспечивающий создание API и интеграцию с другими сервисами.
- **[Flask-SQLAlchemy](https://github.com/pallets-eco/flask-sqlalchemy/)** – ORM для работы с базой данных, позволяющая удобно управлять хранимыми данными.
- **[Flask-Login](https://github.com/maxcountryman/flask-login)** – механизм аутентификации пользователей, необходимый для управления доступом к системе.
- **[Pandas](https://github.com/pandas-dev/pandas)** – библиотека для обработки и анализа данных, используемая при анализе текстов и метаданных сообщений.
- **[Scikit-learn](https://github.com/scikit-learn/scikit-learn)** – набор инструментов для машинного обучения, применяемый для построения и обучения моделей классификации спама.
- **[Scipy](https://github.com/scipy/scipy)** – библиотека для работы с вычислениями, используемая в алгоритмах обработки данных.
- **[Transformers (с поддержкой Torch)](https://github.com/huggingface/transformers)** – библиотека от Hugging Face для работы с моделями обработки естественного языка.
- **[OpenAI](https://github.com/openai/openai-python)** – API для интеграции ChatGPT.
- **[Emoji](https://github.com/carpedm20/emoji)** – библиотека для работы с эмодзи, позволяющая анализировать их использование в текстах сообщений.
- **[Requests](https://github.com/psf/requests)** – инструмент для выполнения HTTP-запросов, необходимый для взаимодействия с API и внешними сервисами.
- **[Python-dotenv](https://github.com/theskumar/python-dotenv)** – библиотека для загрузки конфигурационных переменных из `.env`-файлов, обеспечивающая удобное управление настройками проекта.
- **[Waitress](https://github.com/Pylons/waitress)** – WSGI-сервер для развертывания веб-приложения на базе Flask в продакшене.