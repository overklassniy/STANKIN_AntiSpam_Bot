"""
Модуль извлечения числовых признаков из текста.

Содержит функции для подсчёта эмодзи, переносов строк, пробелов, ссылок, тегов,
пунктуации, цифр, слов, stylistic features и других признаков.
"""

import re

import emoji
import regex

from src.data.preprocessing import URL_PATTERN

PHONE_PATTERN = re.compile(
    r"(?:\+7|8|7)?[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}"
)
CRYPTO_PATTERN = re.compile(
    r"\b(?:биткоин|bitcoin|btc|эфириум|ethereum|eth|usdt| tether|бинанс|binance|"
    r"крипт[аыоуе]|crypto|trading|трейдинг|инвестици[ия]|заработок|"
    r"майнинг|mining|nft|blockchain|блокчейн)\b",
    re.IGNORECASE,
)


def count_emojis(text: str) -> int:
    """
    Считает количество эмодзи в тексте.

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        int: Количество найденных эмодзи.
    """
    graphemes = regex.findall(r"\X", text)
    return sum(1 for g in graphemes if emoji.is_emoji(g))


def count_newlines(text: str) -> int:
    """
    Считает количество символов новой строки в тексте.

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        int: Количество символов новой строки.
    """
    return text.count("\n")


def count_whitespaces(text: str) -> int:
    """
    Считает количество последовательностей из двух и более пробелов.

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        int: Количество найденных последовательностей пробелов.
    """
    return len(re.findall(r"\s{2,}", text))


def count_links(text: str) -> int:
    """
    Считает количество ссылок в тексте.

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        int: Количество найденных ссылок.
    """
    return len(URL_PATTERN.findall(text))


def count_tags(text: str) -> int:
    """
    Считает количество упоминаний (тегов) в тексте.

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        int: Количество найденных тегов.
    """
    return text.count("@")


def capital_ratio(text: str) -> float:
    """
    Вычисляет долю заглавных букв в тексте.

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        float: Доля заглавных букв от 0.0 до 1.0.
    """
    if not text:
        return 0.0
    alpha_count = sum(1 for c in text if c.isalpha())
    if alpha_count == 0:
        return 0.0
    return sum(1 for c in text if c.isupper()) / alpha_count


def count_punctuation(text: str) -> int:
    """
    Считает количество знаков пунктуации в тексте.

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        int: Количество знаков пунктуации.
    """
    return sum(1 for c in text if not c.isalnum() and not c.isspace())


def count_digits(text: str) -> int:
    """
    Считает количество цифр в тексте.

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        int: Количество цифр.
    """
    return sum(1 for c in text if c.isdigit())


def avg_word_length(text: str) -> float:
    """
    Вычисляет среднюю длину слова в тексте.

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        float: Средняя длина слова. Возвращает 0.0 для пустого текста.
    """
    words = text.split()
    if not words:
        return 0.0
    return sum(len(w) for w in words) / len(words)


def word_count(text: str) -> int:
    """
    Считает количество слов в тексте.

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        int: Количество слов.
    """
    return len(text.split())


def unique_word_ratio(text: str) -> float:
    """
    Вычисляет ratio уникальных слов (Type-Token Ratio).

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        float: Доля уникальных слов от 0.0 до 1.0.
    """
    words = text.lower().split()
    if not words:
        return 0.0
    return len(set(words)) / len(words)


def repeat_char_ratio(text: str) -> float:
    """
    Вычисляет долю повторяющихся символов (ааа, !!! и т.д.).

    Считает символы, которые повторяются 3 и более раз подряд.

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        float: Доля повторяющихся символов от 0.0 до 1.0.
    """
    if not text:
        return 0.0
    repeats = len(re.findall(r"(.)\1{2,}", text))
    return repeats / max(len(text), 1)


def count_phone_numbers(text: str) -> int:
    """
    Считает количество телефонных номеров в тексте.

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        int: Количество найденных телефонных номеров.
    """
    return len(PHONE_PATTERN.findall(text))


def has_crypto_mention(text: str) -> int:
    """
    Проверяет наличие упоминаний криптовалюты/биржи/заработка в тексте.

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        int: 1 если найдено, 0 если нет.
    """
    return 1 if CRYPTO_PATTERN.search(text) else 0


def count_exclamation(text: str) -> int:
    """
    Считает количество восклицательных знаков в тексте.

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        int: Количество восклицательных знаков.
    """
    return text.count("!")


def url_ratio(text: str) -> float:
    """
    Вычисляет долю текста, занимаемую ссылками.

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        float: Доля длины ссылок от общей длины текста.
    """
    if not text:
        return 0.0
    url_chars = sum(len(m) for m in URL_PATTERN.findall(text))
    return url_chars / len(text)


_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")

_MARKDOWN_PATTERN = re.compile(
    r"(?:\*\*|__|##|###|####|#####|######|"
    r"^>|^\s*-\s+|^\s*\d+\.\s+|`|~~|\|\|)",
    re.MULTILINE,
)


def count_html_tags(text: str) -> int:
    """
    Считает количество HTML-тегов в тексте.

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        int: Количество найденных HTML-тегов.
    """
    return len(_HTML_TAG_PATTERN.findall(text))


def has_markdown_formatting(text: str) -> int:
    """
    Проверяет наличие markdown-разметки в тексте.

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        int: 1 если найдена markdown-разметка, 0 если нет.
    """
    return 1 if _MARKDOWN_PATTERN.search(text) else 0


def emoji_diversity(text: str) -> int:
    """
    Считает количество уникальных эмодзи в тексте.

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        int: Количество уникальных эмодзи.
    """
    graphemes = regex.findall(r"\X", text)
    unique_emojis = {g for g in graphemes if emoji.is_emoji(g)}
    return len(unique_emojis)
