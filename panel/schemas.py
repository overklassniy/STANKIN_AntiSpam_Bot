"""Pydantic-схемы для REST API."""

from typing import Optional, Union

from pydantic import BaseModel


class PaginationMeta(BaseModel):
    """Метаданные пагинации для списочных ответов API."""
    current_page: int
    total_pages: int
    total: int
    per_page: int


class SpamMessageOut(BaseModel):
    """Спам-сообщение с результатами проверки."""
    id: int
    chat_id: int
    message_id: int
    timestamp: float
    author_id: int
    author_username: Optional[str] = None
    message_text: str
    has_reply_markup: Optional[bool] = None
    cas: Optional[bool] = None
    lols: Optional[bool] = None
    chatgpt_prediction: Optional[int] = None
    bert_prediction: Optional[float] = None


class MutedUserOut(BaseModel):
    """Ограниченный пользователь с информацией о сроке ограничения."""
    id: int
    chat_pk: int
    user_id: int
    username: Optional[str] = None
    timestamp: float
    muted_till_timestamp: Optional[float] = None
    relapse_number: int


class SettingOut(BaseModel):
    """Настройка системы с описанием и признаком глобальности."""
    key: str
    value: Union[str, int, float, bool]
    description: str = ''
    is_global: bool = True
    chat_pk: Optional[int] = None


class SettingUpdate(BaseModel):
    """Запрос на обновление настроек."""
    settings: dict[str, Union[str, int, float, bool]]


class ChatUserOut(BaseModel):
    """Пользователь, имеющий доступ к чату."""
    id: int
    name: str
    telegram_id: int
    is_superadmin: bool


class ChatOut(BaseModel):
    """Информация о чате."""
    pk: int
    chat_id: int
    title: str
    is_active: bool
    users: list[ChatUserOut] = []


class UserInfoOut(BaseModel):
    """Информация о текущем авторизованном пользователе."""
    id: int
    username: str
    is_superadmin: bool


class ChatAddIn(BaseModel):
    """Запрос на добавление чата по Telegram ID."""
    chat_id: int


class LoginIn(BaseModel):
    """Данные для входа в систему."""
    username: str
    password: str
    remember: bool = False


class PaginatedResponse(BaseModel):
    """Обёртка ответа с пагинацией для списочных эндпоинтов."""
    items: list
    pagination: PaginationMeta
