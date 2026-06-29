"""Репозитории для доступа к данным.

Каждый репозиторий инкапсулирует SQL-запросы для своей сущности.
Все используют общий asyncpg pool из core.db.
"""

from core.repository.settings import SettingsRepository
from core.repository.chat import ChatRepository
from core.repository.spam import SpamRepository
from core.repository.muted import MutedRepository
from core.repository.whitelist import WhitelistRepository
from core.repository.collected import CollectedRepository
from core.repository.user import UserRepository

__all__ = [
    'SettingsRepository',
    'ChatRepository',
    'SpamRepository',
    'MutedRepository',
    'WhitelistRepository',
    'CollectedRepository',
    'UserRepository',
]
