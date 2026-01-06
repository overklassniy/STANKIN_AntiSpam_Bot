"""
STANKIN AntiSpam Bot - Telegram Bot Module
"""

from bot.core import dp, start_bot, get_bot
from bot.database import (
    init_database,
    get_setting,
    update_setting,
    get_all_settings,
    reload_settings_cache,
    get_user_by_id,
    create_or_update_user,
    get_muted_user,
    create_muted_user,
    update_muted_user,
    add_spam_message,
    add_collected_message,
)

__all__ = [
    'dp',
    'start_bot',
    'get_bot',
    'init_database',
    'get_setting',
    'update_setting',
    'get_all_settings',
    'reload_settings_cache',
    'get_user_by_id',
    'create_or_update_user',
    'get_muted_user',
    'create_muted_user',
    'update_muted_user',
    'add_spam_message',
    'add_collected_message',
]
