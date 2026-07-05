"""
Модуль извлечения незарегистрированного спама из бэкапа базы данных.

Содержит функции для парсинга PostgreSQL-дампа и вычисления множества
сообщений, удалённых вручную, но не пойманных ботом.
"""

import json
import os

import pandas as pd

IGNORE_USER_IDS = {"777000", "1087968824"}


def _parse_copy_block(lines: list[str], table_name: str) -> tuple[list[str], list[list[str]]]:
    """Парсит блок COPY ... FROM stdin из PostgreSQL-дампа.

    Аргументы:
        lines (list[str]): Строки SQL-дампа.
        table_name (str): Имя таблицы для поиска.

    Возвращаемое значение:
        tuple: (cols, data_rows) — список имён колонок и список строк данных.
    """
    copy_header = f"COPY public.{table_name} "
    data_rows = []
    in_copy = False
    cols = []
    for line in lines:
        if line.startswith(copy_header):
            in_copy = True
            col_part = line[len(copy_header):]
            col_part = col_part.split("FROM stdin")[0].strip()
            cols = [c.strip().strip('"') for c in col_part.strip("()").split(",")]
            continue
        if in_copy:
            if line.strip() == "\\.":
                break
            parts = line.rstrip("\n").split("\t")
            data_rows.append(parts)
    return cols, data_rows


def _load_chat_texts(chat_exports_dir: str) -> set[str]:
    """Загружает множество текстов из экспортов чатов.

    Аргументы:
        chat_exports_dir (str): Путь к директории с экспортами чатов.

    Возвращаемое значение:
        set[str]: Множество текстов сообщений из чатов.
    """
    chat_texts = set()
    for subdir in sorted(os.listdir(chat_exports_dir)):
        result_path = os.path.join(chat_exports_dir, subdir, "result.json")
        if not os.path.exists(result_path):
            continue
        with open(result_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for msg in data.get("messages", []):
            if msg.get("type") == "service":
                continue
            text_entities = msg.get("text_entities")
            if text_entities:
                msg_text = "".join((e.get("text", "") for e in text_entities))
            elif isinstance(msg.get("text"), str):
                msg_text = msg["text"]
            else:
                continue
            msg_text = msg_text.strip()
            if msg_text:
                chat_texts.add(msg_text)
    return chat_texts


def extract_unregistered_spam(
    backup_path: str,
    chat_exports_dir: str,
    manual_texts: set[str] | None = None,
) -> pd.DataFrame:
    """Извлекает незарегистрированный спам из PostgreSQL-дампа.

    Алгоритм:
        1. Из дампа читаются таблицы collected_message и spam_message.
        2. Из collected_message исключаются сообщения от сервисных аккаунтов.
        3. Вычитаются тексты из экспортов чатов (остались в чате = безопасные).
        4. Вычитаются тексты из spam_message (уже пойманный спам).
        5. Вычитаются тексты из manual_texts (уже есть в dataset.json).
        6. Остаток — незарегистрированный спам.

    Аргументы:
        backup_path (str): Путь к SQL-дампу базы данных.
        chat_exports_dir (str): Путь к директории с экспортами чатов.
        manual_texts (set[str] | None): Множество текстов из dataset.json.

    Возвращаемое значение:
        pd.DataFrame: DataFrame с колонками 'text' и 'label'.
    """
    with open(backup_path, "r", encoding="utf-8") as f:
        sql_lines = f.readlines()

    collected_cols, collected_rows = _parse_copy_block(sql_lines, "collected_message")
    spam_cols, spam_rows = _parse_copy_block(sql_lines, "spam_message")

    df_collected = pd.DataFrame(collected_rows, columns=collected_cols)
    df_spam = pd.DataFrame(spam_rows, columns=spam_cols)

    df_collected = df_collected[~df_collected["user_id"].isin(IGNORE_USER_IDS)]

    chat_texts = _load_chat_texts(chat_exports_dir)
    collected_texts = set(df_collected["message_text"].tolist())
    spam_texts = set(df_spam["message_text"].tolist())

    if manual_texts is None:
        manual_texts = set()

    unregistered = collected_texts - chat_texts - spam_texts - manual_texts

    print(f"Собрано ботом:        {len(collected_texts)}")
    print(f"Экспорт чатов:        {len(chat_texts)}")
    print(f"Спам (поймано):       {len(spam_texts)}")
    print(f"Уже в dataset:        {len(manual_texts)}")
    print(f"Незарегистрировано:   {len(unregistered)}")

    if unregistered:
        return pd.DataFrame(
            [{"text": t, "label": 1} for t in unregistered if t.strip()]
        )

    return pd.DataFrame(columns=["text", "label"])
