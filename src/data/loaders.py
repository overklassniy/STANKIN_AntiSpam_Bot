"""
Модуль загрузки данных из различных форматов.

Содержит функции для загрузки JSON и TXT файлов в pandas DataFrame.
"""

import json
from pathlib import Path
import pandas as pd


def load_json(path: str | Path) -> pd.DataFrame:
    """
    Загружает JSON-файл в DataFrame.

    Аргументы:
        path (str | Path): Путь к JSON-файлу.

    Возвращаемое значение:
        pd.DataFrame: DataFrame с данными из файла.

    Исключения:
        FileNotFoundError: Если файл не существует.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return pd.DataFrame(data)


def load_txt_lines(path: str | Path) -> list[str]:
    """
    Загружает текстовый файл как список строк.

    Аргументы:
        path (str | Path): Путь к TXT-файлу.

    Возвращаемое значение:
        list[str]: Список строк из файла.

    Исключения:
        FileNotFoundError: Если файл не существует.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]
