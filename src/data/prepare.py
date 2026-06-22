"""
Модуль подготовки данных.

Запускается через `python -m src.data.prepare`.
Выполняет: загрузку raw + external данных, очистку, предобработку текста,
извлечение признаков и сохранение в data/processed/preprocessed.csv.
"""

import os
import re
from copy import deepcopy

import numpy as np
import pandas as pd

from src.config import EXTERNAL_DIR, PROCESSED_DIR, RAW_DIR
from src.data.loaders import load_txt_lines
from src.data.preprocessing import preprocess_text
from src.features.extractors import (
    avg_word_length,
    capital_ratio,
    count_digits,
    count_emojis,
    count_exclamation,
    count_links,
    count_newlines,
    count_phone_numbers,
    count_punctuation,
    count_tags,
    count_whitespaces,
    has_crypto_mention,
    repeat_char_ratio,
    unique_word_ratio,
    url_ratio,
    word_count,
)


def _normalize_for_dedup(text: str) -> str:
    """
    Нормализует текст для поиска near-дубликатов.

    Алгоритм работы:
        1. Привести к нижнему регистру.
        2. Удалить пунктуацию.
        3. Сжать повторяющиеся пробелы.

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        str: Нормализованный текст.
    """
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text


def _resolve_conflicts(df: pd.DataFrame) -> pd.DataFrame:
    """
    Разрешает конфликтные метки: оставляет метку по majority vote.

    Если метки 50/50, удаляет строку как неоднозначную.

    Аргументы:
        df (pd.DataFrame): DataFrame с колонками text и label.

    Возвращаемое значение:
        pd.DataFrame: DataFrame без конфликтных меток.
    """
    label_counts = df.groupby("text")["label"].agg(["sum", "count"])
    label_counts["spam_votes"] = label_counts["sum"]
    label_counts["ham_votes"] = label_counts["count"] - label_counts["sum"]
    label_counts["resolved_label"] = label_counts.apply(
        lambda row: 1 if row["spam_votes"] > row["ham_votes"]
        else (0 if row["ham_votes"] > row["spam_votes"] else -1),
        axis=1,
    )
    ambiguous = label_counts[label_counts["resolved_label"] == -1].index
    df = df[~df["text"].isin(ambiguous)].copy()
    label_map = label_counts[label_counts["resolved_label"] != -1]["resolved_label"].to_dict()
    df["label"] = df["text"].map(label_map)
    df = df.drop_duplicates(subset="text", keep="first")
    return df


def prepare() -> None:
    """
    Подготававливает объединённый датасет из всех источников.

    Алгоритм работы:
        1. Загрузить raw-данные (dataset.json, dataset_discord.json).
        2. Загрузить interim-данные (spam_samples_umputun.txt, parsed_lols_2024.txt).
        3. Объединить, очистить, дедуплицировать (точный и near-дедуп).
        4. Разрешить конфликтные метки через majority vote.
        5. Удалить пересечения с тестовой выборкой.
        6. Извлечь все числовые признаки.
        7. Предобработать текст.
        8. Сохранить в data/processed/preprocessed.csv.
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Загрузка raw-данных
    df_manual = pd.read_json(RAW_DIR / "dataset.json")
    df_discord = pd.read_json(RAW_DIR / "dataset_discord.json")

    # Загрузка external-данных
    spam_umputun = load_txt_lines(EXTERNAL_DIR / "spam_samples_umputun.txt")
    df_umputun = pd.DataFrame({"text": spam_umputun, "label": [1] * len(spam_umputun)})

    lols_2024 = load_txt_lines(EXTERNAL_DIR / "parsed_lols_2024.txt")
    lols_2024 = [line.replace("<br/>", "", 1).strip().replace("<br/>", "\n") for line in lols_2024]
    df_lols = pd.DataFrame({"text": lols_2024, "label": [1] * len(lols_2024)})

    # Объединение
    df = pd.concat([df_manual, df_umputun, df_discord, df_lols], ignore_index=True)

    # Незарегистрированный спам (если есть)
    unregistered_path = EXTERNAL_DIR / "unregistered_spam.json"
    if os.path.exists(unregistered_path):
        df_unregistered = pd.read_json(unregistered_path)
        df = pd.concat([df, df_unregistered], ignore_index=True)

    # Очистка
    df = df[df["text"].notna()]
    df = df[df["text"].str.strip() != ""]
    df = df[df["text"].astype(str).str.len() >= 5]

    # Точный дедуп
    df = df.drop_duplicates(subset="text", keep="first")

    # Разрешение конфликтных меток через majority vote
    df = _resolve_conflicts(df)

    # Near-дедуп: нормализованный дедуп
    df["_norm"] = df["text"].astype(str).apply(_normalize_for_dedup)
    df = df.drop_duplicates(subset="_norm", keep="first")
    df = df.drop(columns=["_norm"])

    # Удаление пересечений с тестовой выборкой (точное и near)
    test_clear_path = RAW_DIR / "test_clear.json"
    if os.path.exists(test_clear_path):
        df_test = pd.read_json(test_clear_path)
        test_texts = set(df_test["text"].tolist())
        test_norms = set(_normalize_for_dedup(t) for t in test_texts)
        df["_norm"] = df["text"].astype(str).apply(_normalize_for_dedup)
        df = df[~df["text"].isin(test_texts)]
        df = df[~df["_norm"].isin(test_norms)]
        df = df.drop(columns=["_norm"])

    lols_2023_path = EXTERNAL_DIR / "parsed_lols_2023.txt"
    if os.path.exists(lols_2023_path):
        lines_2023 = load_txt_lines(lols_2023_path)
        lols_2023_texts = set(
            line.replace("<br/>", "", 1).strip().replace("<br/>", "\n")
            for line in lines_2023
            if line.strip()
        )
        lols_2023_norms = set(_normalize_for_dedup(t) for t in lols_2023_texts)
        if "_norm" not in df.columns:
            df["_norm"] = df["text"].astype(str).apply(_normalize_for_dedup)
        df = df[~df["text"].isin(lols_2023_texts)]
        df = df[~df["_norm"].isin(lols_2023_norms)]
        df = df.drop(columns=["_norm"])

    df = df.reset_index(drop=True)

    # Извлечение всех числовых признаков
    df_preprocessed = deepcopy(df)
    df_preprocessed["emojis"] = df["text"].apply(count_emojis)
    df_preprocessed["newlines"] = df["text"].apply(count_newlines)
    df_preprocessed["whitespaces"] = df["text"].apply(count_whitespaces)
    df_preprocessed["links"] = df["text"].apply(count_links)
    df_preprocessed["tags"] = df["text"].apply(count_tags)
    df_preprocessed["length"] = df["text"].apply(len)
    df_preprocessed["capital_ratio"] = df["text"].apply(capital_ratio)
    df_preprocessed["punctuation_count"] = df["text"].apply(count_punctuation)
    df_preprocessed["digit_count"] = df["text"].apply(count_digits)
    df_preprocessed["avg_word_length"] = df["text"].apply(avg_word_length)
    df_preprocessed["word_count"] = df["text"].apply(word_count)
    df_preprocessed["unique_word_ratio"] = df["text"].apply(unique_word_ratio)
    df_preprocessed["repeat_char_ratio"] = df["text"].apply(repeat_char_ratio)
    df_preprocessed["phone_count"] = df["text"].apply(count_phone_numbers)
    df_preprocessed["has_crypto"] = df["text"].apply(has_crypto_mention)
    df_preprocessed["exclamation_count"] = df["text"].apply(count_exclamation)
    df_preprocessed["url_ratio"] = df["text"].apply(url_ratio)

    # Предобработка текста
    texts = []
    for text in df["text"]:
        processed = preprocess_text(str(text))
        texts.append(processed if processed else np.nan)
    df_preprocessed["text_preprocessed"] = texts

    # Удаление строк с пустым предобработанным текстом
    df_preprocessed.dropna(subset=["text_preprocessed"], inplace=True)

    # Сохранение
    output_path = PROCESSED_DIR / "preprocessed.csv"
    df_preprocessed.to_csv(output_path)
    print(f"Сохранено {len(df_preprocessed)} строк в {output_path}")


if __name__ == "__main__":
    prepare()
