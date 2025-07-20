import re

import emoji
import regex

from utils.basic import logger

# Регулярное выражение для поиска ссылок
url_pattern = r'(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)'


def count_emojis(text: str) -> int:
    """
    Считает количество эмодзи в тексте.

    Аргументы:
        text (str): Исходный текст.

    Возвращает:
        int: Количество найденных эмодзи.
    """
    data = regex.findall(r'\X', text)  # Разбиваем текст на "графемные кластеры"
    emoji_counter = sum(emoji.is_emoji(word) for word in data)
    logger.debug("Количество эмодзи: %d", emoji_counter)
    return emoji_counter


def count_newlines(text: str) -> int:
    """
    Считает количество символов новой строки (\n) в тексте.
    """
    newline_count = text.count('\n')
    logger.debug("Количество новых строк: %d", newline_count)
    return newline_count


def count_whitespaces(text: str) -> int:
    """
    Считает количество последовательных пробелов (два или более) в тексте.
    """
    extra_spaces_count = len(re.findall(r'\s{2,}', text))
    logger.debug("Количество лишних пробелов: %d", extra_spaces_count)
    return extra_spaces_count


def count_links(text: str) -> int:
    """
    Считает количество ссылок в тексте.
    """
    links = re.findall(url_pattern, text)
    logger.debug("Количество ссылок: %d", len(links))
    return len(links)


def count_tags(text: str) -> int:
    """
    Считает количество упоминаний (тегов) в тексте.
    """
    tag_count = text.count('@')
    logger.debug("Количество тегов: %d", tag_count)
    return tag_count


def remove_emojis(text: str) -> str:
    """
    Удаляет все эмодзи из текста.
    """
    data = regex.findall(r'\X', text)
    text_without_emojis = ''.join(word for word in data if not emoji.is_emoji(word))
    logger.debug("Текст после удаления эмодзи: %s", text_without_emojis)
    return text_without_emojis


def replace_links(text: str) -> str:
    """
    Заменяет все ссылки в тексте на "[LINK]".
    """
    text = re.sub(url_pattern, '[LINK]', text)
    logger.debug("Текст после замены ссылок: %s", text)
    return text


def replace_tags(text: str) -> str:
    """
    Заменяет все упоминания (теги) в тексте на "[TAG]".
    """
    tag_pattern = r'@[a-zA-Z0-9_]+'
    text = re.sub(tag_pattern, '[TAG]', text)
    logger.debug("Текст после замены тегов: %s", text)
    return text


def contains_email(text):
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    return bool(re.search(email_pattern, text))


def preprocess_text(
        text: str,
        lower: bool = True,
        remove_punctuation: bool = True,
        remove_emoji: bool = True,
        remove_whitespaces: bool = True,
        remove_links: bool = True,
        remove_tags: bool = True
) -> str:
    """
    Предобрабатывает текст, включая нормализацию регистра, удаление пунктуации, эмодзи, ссылок, тегов и пробелов.

    Аргументы:
        text (str): Исходный текст.
        lower (bool): Приводить ли текст к нижнему регистру (по умолчанию True).
        remove_punctuation (bool): Удалять ли пунктуацию (по умолчанию True).
        remove_emoji (bool): Удалять ли эмодзи (по умолчанию True).
        remove_whitespaces (bool): Удалять ли лишние пробелы (по умолчанию True).
        remove_links (bool): Удалять ли ссылки (по умолчанию True).
        remove_tags (bool): Удалять ли теги (по умолчанию True).

    Возвращает:
        str: Обработанный текст.
    """
    logger.info("Начало предобработки текста: %s", text)

    if lower:
        text = text.lower()
        logger.debug("Текст после приведения к нижнему регистру: %s", text)

    if remove_links:
        text = replace_links(text)

    if remove_tags:
        text = replace_tags(text)

    if remove_punctuation:
        text = re.sub(r'[^\w\s]', '', text)
        logger.debug("Текст после удаления пунктуации: %s", text)
        if remove_links:
            text = text.replace('LINK', '[LINK]')
        if remove_tags:
            text = text.replace('TAG', '[TAG]')

    if remove_emoji:
        text = remove_emojis(text)

    if remove_whitespaces:
        text = re.sub(r'\s+', ' ', text).strip()
        logger.debug("Текст после удаления лишних пробелов: %s", text)

    logger.info("Предобработка завершена. Итоговый текст: %s", text)
    return text
