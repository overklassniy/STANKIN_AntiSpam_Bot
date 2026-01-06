"""
Обработчики команд бота.
"""

import secrets
import string

from aiogram import types, F
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import BotCommand
from werkzeug.security import generate_password_hash

from bot.core import dp, get_bot, HELPDESK_EMAIL, GITHUB_URL
from bot.database import create_or_update_user
from utils.config import TARGET_CHAT_ID
from utils.logging import logger


@dp.message(CommandStart(deep_link=True))
async def handle_start_command(message: types.Message, command: CommandObject) -> None:
    """
    Обрабатывает команду /start с deep_link параметром.
    """
    logger.info(f"Получена команда /start от пользователя {message.from_user.id} с аргументом: {command.args}")

    if command.args == 'get_password':
        await handle_get_password_command(message)


@dp.message(Command(BotCommand(command='code', description='Получить ссылку на GitHub репозиторий бота')))
async def handle_code_command(message: types.Message) -> None:
    """
    Обрабатывает команду /code и отправляет ссылку на GitHub.
    """
    try:
        await message.answer(f"Исходный код бота доступен на GitHub: {GITHUB_URL}")
        logger.info(f"Отправлена ссылка на GitHub пользователю {message.chat.id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке ссылки на GitHub пользователю {message.chat.id}: {e}")


@dp.message(Command(BotCommand(
    command='get_password',
    description='Получить пароль для авторизации в панели управления'
)))
async def handle_get_password_command(message: types.Message) -> None:
    """
    Обрабатывает команду /get_password.
    Проверяет права пользователя и генерирует пароль для панели управления.
    """
    logger.info(f"Обработка команды /get_password для пользователя {message.from_user.id}")

    author = message.from_user
    author_id = author.id
    author_name = author.username

    bot = get_bot()

    try:
        chat_member = await bot.get_chat_member(chat_id=TARGET_CHAT_ID, user_id=author_id)
        logger.debug(f"Пользователь {author_id}: статус {chat_member.status}")
    except Exception as e:
        logger.error(f"Ошибка при получении информации о пользователе {author_id}: {e}")
        await message.answer(
            f"Произошла ошибка при проверке ваших прав доступа. "
            f"Пожалуйста, попробуйте позже или свяжитесь с технической поддержкой: {HELPDESK_EMAIL}"
        )
        return

    # Проверяем, является ли пользователь администратором
    if chat_member.status not in ["administrator", "creator"]:
        await message.answer(
            "Вы не обладаете достаточными правами (требуется статус администратора).\n\n"
            f"По вопросам обращайтесь: {HELPDESK_EMAIL}"
        )
        logger.info(f"Попытка получения пароля от пользователя {author_id} без соответствующих прав")
        return

    try:
        # Генерируем пароль
        password = secrets.token_urlsafe(9)
        hashed_password = generate_password_hash(password, method='scrypt')

        # Генерируем имя, если отсутствует
        if not author_name:
            author_name = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))

        # Сохраняем в БД
        await create_or_update_user(author_id, author_name, hashed_password, can_configure=False)

        # Отправляем пользователю
        await message.answer(
            f"Ваше имя пользователя: `{author_name}`\nВаш пароль: `{password}`",
            parse_mode='markdown'
        )
        logger.info(f"Пароль успешно отправлен пользователю {author_id}")

    except Exception as e:
        logger.error(f"Ошибка при обработке /get_password для пользователя {author_id}: {e}")
        await message.answer(
            f"Произошла внутренняя ошибка. "
            f"Пожалуйста, свяжитесь с технической поддержкой: {HELPDESK_EMAIL}"
        )


@dp.message(F.chat.func(lambda chat: chat.type == ChatType.PRIVATE))
async def handle_private_message(message: types.Message) -> None:
    """
    Обрабатывает личные сообщения боту.
    """
    logger.info(f"Получено личное сообщение от пользователя {message.from_user.id}")
    try:
        await message.answer(
            "Здравствуйте! Пожалуйста, ознакомьтесь со списком моих команд в соответствующем меню."
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения пользователю {message.from_user.id}: {e}")
