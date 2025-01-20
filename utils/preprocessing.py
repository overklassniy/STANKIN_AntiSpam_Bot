import re

import emoji
import regex


def count_emojis(text: str) -> int:
    """
    Считает количество эмодзи в тексте.

    Параметры:
        text (str): Исходный текст.

    Возвращает:
        int: Количество найденных эмодзи.
    """
    # Разбиваем текст на "графемные кластеры" (учитывая составные эмодзи)
    data = regex.findall(r'\X', text)
    # Считаем эмодзи
    emoji_counter = sum(emoji.is_emoji(word) for word in data)
    return emoji_counter


def count_newlines(text: str) -> int:
    """
    Считает количество символов новой строки (\n) в тексте.

    Параметры:
        text (str): Исходный текст.

    Возвращает:
        int: Количество символов новой строки.
    """
    # Подсчёт символов новой строки
    newline_count = text.count('\n')
    return newline_count


def count_whitespaces(text: str) -> int:
    """
    Считает количество последовательных пробелов (два или более) в тексте.

    Параметры:
        text (str): Исходный текст.

    Возвращает:
        int: Количество найденных последовательных пробелов.
    """
    # Считаем последовательности из двух и более пробелов
    extra_spaces_count = len(re.findall(r'\s{2,}', text))
    return extra_spaces_count


# Регулярное выражение для поиска ссылок
url_pattern = r'(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)'


def count_links(text: str) -> int:
    """
    Считает количество ссылок в тексте.

    Параметры:
        text (str): Исходный текст.

    Возвращает:
        int: Количество найденных ссылок.
    """
    # Найти все ссылки в тексте
    links = re.findall(url_pattern, text)
    return len(links)


def count_tags(text: str) -> int:
    """
    Считает количество упоминаний (тегов) в тексте.

    Параметры:
        text (str): Исходный текст.

    Возвращает:
        int: Количество найденных тегов.
    """
    # Подсчёт символов "@" как маркеров тегов
    tag_count = text.count('@')
    return tag_count


def remove_emojis(text: str) -> str:
    """
    Удаляет все эмодзи из текста.

    Параметры:
        text (str): Исходный текст.

    Возвращает:
        str: Текст без эмодзи.
    """
    # Разбиваем текст на "графемные кластеры"
    data = regex.findall(r'\X', text)
    # Удаляем все эмодзи
    text_without_emojis = ''.join(word for word in data if not emoji.is_emoji(word))
    return text_without_emojis


def replace_links(text: str) -> str:
    """
    Заменяет все ссылки в тексте на "[LINK]".

    Параметры:
        text (str): Исходный текст.

    Возвращает:
        str: Текст с заменёнными ссылками.
    """
    # Заменить ссылки на [LINK]
    text = re.sub(url_pattern, '[LINK]', text)
    return text


def replace_tags(text: str) -> str:
    """
    Заменяет все упоминания (теги) в тексте на "[TAG]".

    Параметры:
        text (str): Исходный текст.

    Возвращает:
        str: Текст с заменёнными тегами.
    """
    # Регулярное выражение для тегов
    tag_pattern = r'@[a-zA-Z0-9_]+'
    # Замена тегов на [TAG]
    text = re.sub(tag_pattern, '[TAG]', text)
    return text


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

    Параметры:
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
    # Приведение текста к нижнему регистру
    if lower:
        text = text.lower()
    # Замена ссылок на [LINK]
    if remove_links:
        text = replace_links(text)
    # Замена тегов на [TAG]
    if remove_tags:
        text = replace_tags(text)
    # Удаление пунктуации
    if remove_punctuation:
        text = re.sub(r'[^\w\s]', '', text)  # Удаляет пунктуацию
        # Восстановление [LINK] после очистки пунктуации
        if remove_links:
            text = text.replace('LINK', '[LINK]')
        # Восстановление [TAG] после очистки пунктуации
        if remove_tags:
            text = text.replace('TAG', '[TAG]')
    # Удаление эмодзи
    if remove_emoji:
        text = remove_emojis(text)
    # Удаление лишних пробелов и символов новой строки
    if remove_whitespaces:
        text = re.sub(r'\s+', ' ', text).strip()
    return text
