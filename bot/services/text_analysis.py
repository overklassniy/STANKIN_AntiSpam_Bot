"""Сервис обработки текста для анализа спама.

Содержит функции предобработки текста, извлечения признаков
и регулярные выражения для поиска ссылок, email, тегов.
"""

import re
from typing import List

import emoji
import regex

from core.logging import logger

# Регулярные выражения
URL_PATTERN = re.compile(
    r'(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)'
)
EMAIL_PATTERN = re.compile(
    r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
)
TAG_PATTERN = re.compile(r'@[a-zA-Z0-9_]+')
MULTIPLE_SPACES_PATTERN = re.compile(r'\s{2,}')
PUNCTUATION_PATTERN = re.compile(r'[^\w\s]')


def count_emojis(text: str) -> int:
    """Считает количество эмодзи в тексте.

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        int: Количество эмодзи.
    """
    graphemes = regex.findall(r'\X', text)
    count = sum(1 for g in graphemes if emoji.is_emoji(g))
    logger.debug(f"Количество эмодзи: {count}")
    return count


def count_newlines(text: str) -> int:
    """Считает количество переносов строки.

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        count (int): Количество переносов строки.
    """
    return text.count('\n')


def count_whitespaces(text: str) -> int:
    """Считает количество множественных пробелов.

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        count (int): Количество множественных пробелов.
    """
    return len(MULTIPLE_SPACES_PATTERN.findall(text))


def count_links(text: str) -> int:
    """Считает количество ссылок.

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        count (int): Количество ссылок.
    """
    return len(URL_PATTERN.findall(text))


def count_tags(text: str) -> int:
    """Считает количество @-упоминаний.

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        count (int): Количество @-упоминаний.
    """
    return text.count('@')


def remove_emojis(text: str) -> str:
    """Удаляет эмодзи из текста.

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        result (str): Текст без эмодзи.
    """
    graphemes = regex.findall(r'\X', text)
    return ''.join(g for g in graphemes if not emoji.is_emoji(g))


def replace_links(text: str, replacement: str = '[LINK]') -> str:
    """Заменяет ссылки на placeholder.

    Аргументы:
        text (str): Исходный текст.
        replacement (str): Строка замены.

    Возвращаемое значение:
        result (str): Текст с заменёнными ссылками.
    """
    return URL_PATTERN.sub(replacement, text)


def replace_tags(text: str, replacement: str = '[TAG]') -> str:
    """Заменяет @-упоминания на placeholder.

    Аргументы:
        text (str): Исходный текст.
        replacement (str): Строка замены.

    Возвращаемое значение:
        result (str): Текст с заменёнными тегами.
    """
    return TAG_PATTERN.sub(replacement, text)


def contains_email(text: str) -> bool:
    """Проверяет, содержит ли текст email-адрес.

    Аргументы:
        text (str): Текст для проверки.

    Возвращаемое значение:
        bool: True если содержит email.
    """
    return bool(EMAIL_PATTERN.search(text))


def extract_emails(text: str) -> List[str]:
    """Извлекает все email-адреса из текста.

    Аргументы:
        text (str): Текст для поиска.

    Возвращаемое значение:
        List[str]: Список найденных email-адресов.
    """
    return EMAIL_PATTERN.findall(text)


def preprocess_text(
    text: str,
    lower: bool = True,
    remove_punctuation: bool = True,
    remove_emoji: bool = True,
    remove_whitespaces: bool = True,
    remove_links: bool = True,
    remove_tags: bool = True
) -> str:
    """Предобрабатывает текст для ML-моделей.

    Аргументы:
        text (str): Исходный текст.
        lower (bool): Приводить к нижнему регистру.
        remove_punctuation (bool): Удалять пунктуацию.
        remove_emoji (bool): Удалять эмодзи.
        remove_whitespaces (bool): Нормализовать пробелы.
        remove_links (bool): Заменять ссылки на [LINK].
        remove_tags (bool): Заменять теги на [TAG].

    Возвращаемое значение:
        str: Обработанный текст.
    """
    if lower:
        text = text.lower()

    if remove_links:
        text = replace_links(text)

    if remove_tags:
        text = replace_tags(text)

    if remove_punctuation:
        text = PUNCTUATION_PATTERN.sub('', text)
        if remove_links:
            text = text.replace('LINK', '[LINK]')
        if remove_tags:
            text = text.replace('TAG', '[TAG]')

    if remove_emoji:
        text = remove_emojis(text)

    if remove_whitespaces:
        text = re.sub(r'\s+', ' ', text).strip()

    return text


def get_text_features(text: str) -> dict:
    """Извлекает числовые признаки из текста.

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        dict: Словарь с признаками.
    """
    return {
        'emojis': count_emojis(text),
        'newlines': count_newlines(text),
        'whitespaces': count_whitespaces(text),
        'links': count_links(text),
        'tags': count_tags(text),
        'length': len(text),
        'has_email': contains_email(text)
    }
