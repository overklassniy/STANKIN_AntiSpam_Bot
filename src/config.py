"""
Модуль конфигурации проекта.

Содержит пути к директориям и константы проекта.
При импорте автоматически загружает переменные окружения из файла .env
и подавляет диагностические сообщения transformers при загрузке моделей.
"""

import logging
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

for name in logging.root.manager.loggerDict:
    if "transformers" in name.lower():
        logging.getLogger(name).setLevel(logging.ERROR)

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
EXTERNAL_DIR = DATA_DIR / "external"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
CHAT_EXPORTS_DIR = PROJECT_ROOT / "chat_exports"
