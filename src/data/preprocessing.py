"""
Модуль предобработки текста.

Содержит функции для нормализации текста: Unicode-нормализация, удаление HTML,
удаление эмодзи, замену ссылок и тегов, удаление пунктуации и лишних пробелов.
"""

import re
import unicodedata

import emoji
import regex

URL_PATTERN = re.compile(
    r"(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)"
)
TAG_PATTERN = re.compile(r"@[a-zA-Z0-9_]+")

# Невидимые и control-символы: ASCII control, Unicode ZWSP/WJ/направления, BOM
_INVISIBLE_CHARS = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f"
    r"\u200b-\u200f\u2028-\u2029\ufeff]"
)

# HTML-теги: <br>, <br/>, <br /> и остальные теги
_BR_PATTERN = re.compile(r"<br\s*/?>", re.IGNORECASE)
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")

# Placeholder для ссылок и тегов: не содержат символов пунктуации,
# чтобы не удаляться при очистке пунктуации
_LINK_PLACEHOLDER = "LINKPLACEHOLDER"
_TAG_PLACEHOLDER = "TAGPLACEHOLDER"


def normalize_unicode(text: str) -> str:
    """
    Нормализует Unicode и удаляет невидимые/control-символы.

    Алгоритм работы:
        1. Применить NFKC-нормализацию (совмещает совместимые формы,
           нормализует гомоглифы, разные типы пробелов).
        2. Удалить невидимые и control-символы (ZWSP, BOM, direction marks).

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        str: Нормализованный текст без невидимых символов.
    """
    text = unicodedata.normalize("NFKC", text)
    text = _INVISIBLE_CHARS.sub("", text)
    return text


def strip_html(text: str) -> str:
    """
    Удаляет HTML-теги из текста.

    Теги <br> и <br/> заменяются на перенос строки,
    остальные HTML-теги удаляются полностью.

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        str: Текст без HTML-тегов.
    """
    text = _BR_PATTERN.sub("\n", text)
    text = _HTML_TAG_PATTERN.sub("", text)
    return text


def remove_emojis(text: str) -> str:
    """
    Удаляет все эмодзи из текста.

    Аргументы:
        text (str): Исходный текст.

    Возвращаемое значение:
        str: Текст без эмодзи.
    """
    graphemes = regex.findall(r"\X", text)
    return "".join(g for g in graphemes if not emoji.is_emoji(g))


def replace_links(text: str, replacement: str = "[LINK]") -> str:
    """
    Заменяет все ссылки в тексте на placeholder.

    Аргументы:
        text (str): Исходный текст.
        replacement (str): Строка замены для ссылок.

    Возвращаемое значение:
        str: Текст с заменёнными ссылками.
    """
    return URL_PATTERN.sub(replacement, text)


def replace_tags(text: str, replacement: str = "[TAG]") -> str:
    """
    Заменяет все упоминания (теги) в тексте на placeholder.

    Аргументы:
        text (str): Исходный текст.
        replacement (str): Строка замены для тегов.

    Возвращаемое значение:
        str: Текст с заменёнными тегами.
    """
    return TAG_PATTERN.sub(replacement, text)


def preprocess_text(
    text: str,
    lower: bool = True,
    remove_punctuation: bool = True,
    remove_emoji: bool = True,
    remove_whitespaces: bool = True,
    remove_links: bool = True,
    remove_tags: bool = True,
    normalize: bool = True,
    strip_html_tags: bool = True,
) -> str:
    """
    Предобрабатывает текст: Unicode-нормализация, удаление HTML, нормализация регистра,
    удаление пунктуации, эмодзи, ссылок, тегов и пробелов.

    Алгоритм работы:
        1. Unicode NFKC-нормализация и удаление невидимых символов.
        2. Удаление HTML-тегов (<br> -> перенос строки, остальные -> удаление).
        3. Приведение к нижнему регистру.
        4. Замена ссылок на placeholder (до удаления пунктуации).
        5. Замена тегов на placeholder (до удаления пунктуации).
        6. Удаление пунктуации (placeholder защищены, не содержат символов пунктуации).
        7. Восстановление placeholder в [LINK] и [TAG].
        8. Удаление эмодзи.
        9. Нормализация пробелов.

    Аргументы:
        text (str): Исходный текст.
        lower (bool): Приводить ли текст к нижнему регистру.
        remove_punctuation (bool): Удалять ли пунктуацию.
        remove_emoji (bool): Удалять ли эмодзи.
        remove_whitespaces (bool): Удалять ли лишние пробелы.
        remove_links (bool): Заменять ли ссылки на [LINK].
        remove_tags (bool): Заменять ли теги на [TAG].
        normalize (bool): Применять ли Unicode NFKC-нормализацию и удаление невидимых символов.
        strip_html_tags (bool): Удалять ли HTML-теги.

    Возвращаемое значение:
        str: Обработанный текст.
    """
    if normalize:
        text = normalize_unicode(text)
    if strip_html_tags:
        text = strip_html(text)
    if lower:
        text = text.lower()
    if remove_links:
        text = replace_links(text, replacement=_LINK_PLACEHOLDER)
    if remove_tags:
        text = replace_tags(text, replacement=_TAG_PLACEHOLDER)
    if remove_punctuation:
        text = re.sub(r"[^\w\s]", "", text)
    if remove_links:
        text = text.replace(_LINK_PLACEHOLDER, "[LINK]")
    if remove_tags:
        text = text.replace(_TAG_PLACEHOLDER, "[TAG]")
    if remove_emoji:
        text = remove_emojis(text)
    if remove_whitespaces:
        text = re.sub(r"\s+", " ", text).strip()
    return text
