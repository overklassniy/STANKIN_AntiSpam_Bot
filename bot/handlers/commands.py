"""Обработчики команд бота.

Команда /get_password работает только в ЛС с ботом.
Бот проверяет, что пользователь является админом хотя бы в одной
из групп, где бот присутствует. В не-приватных чатах — тихий игнор.
"""

import secrets
import string

from aiogram import types, F
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import BotCommand

from bot.core import dp, get_bot, HELPDESK_EMAIL, GITHUB_URL
from bot.services.moderation import ModerationService
from core.repository.chat import ChatRepository
from core.repository.user import UserRepository
from core.logging import logger


@dp.message(CommandStart(deep_link=True))
async def handle_start_command(message: types.Message, command: CommandObject) -> None:
    """Обрабатывает команду /start с deep_link параметром.

    Аргументы:
        message (Message): Входящее сообщение Telegram.
        command (CommandObject): Объект команды с аргументами.
    """
    logger.info(f"Получена команда /start от пользователя {message.from_user.id} с аргументом: {command.args}")

    if command.args == 'get_password':
        await handle_get_password_command(message)


@dp.message(Command(BotCommand(command='code', description='Получить ссылку на GitHub репозиторий бота')))
async def handle_code_command(message: types.Message) -> None:
    """Обрабатывает команду /code и отправляет ссылку на GitHub.

    Аргументы:
        message (Message): Входящее сообщение Telegram.
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
    """Обрабатывает команду /get_password.

    Команда работает только в ЛС с ботом. В не-приватных чатах — тихий игнор.
    Проверяет, что пользователь является админом хотя бы в одной из групп,
    где бот присутствует. Даёт доступ ко всем чатам, где пользователь админ.

    Аргументы:
        message (Message): Входящее сообщение Telegram.
    """
    # Тихий игнор в не-приватных чатах
    if message.chat.type != ChatType.PRIVATE:
        return

    author = message.from_user
    author_id = author.id
    author_name = author.username

    logger.info(f"Обработка команды /get_password для пользователя {author_id}")

    bot = get_bot()

    # Получаем все активные чаты, где бот присутствует
    active_chats = await ChatRepository.get_active_chats()

    if not active_chats:
        await message.answer(
            "Бот не добавлен ни в одну группу. "
            f"По вопросам обращайтесь: {HELPDESK_EMAIL}"
        )
        return

    # Проверяем, является ли пользователь админом хотя бы в одном чате
    admin_chats = []
    for chat in active_chats:
        is_admin = await ModerationService.check_if_admin(
            bot, chat['chat_id'], author_id
        )
        if is_admin:
            admin_chats.append(chat)

    if not admin_chats:
        await message.answer(
            "Вы не являетесь администратором ни в одной из групп, где присутствует бот.\n\n"
            f"По вопросам обращайтесь: {HELPDESK_EMAIL}"
        )
        logger.info(f"Попытка получения пароля от пользователя {author_id} без прав админа")
        return

    try:
        # Генерируем пароль
        password = secrets.token_urlsafe(9)

        # Хешируем пароль
        import hashlib
        import os as _os
        salt = _os.urandom(16)
        dk = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=64)
        scrypt_params = 'n=16384,r=8,p=1'
        hashed_password = f"scrypt${scrypt_params}${salt.hex()}${dk.hex()}"

        # Генерируем имя, если отсутствует
        if not author_name:
            author_name = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))

        # Создаём или обновляем пользователя
        user_pk = await UserRepository.create_or_update_user(
            telegram_id=author_id,
            name=author_name,
            password_hash=hashed_password,
            is_superadmin=False
        )

        # Даём доступ ко всем чатам, где пользователь админ
        chat_titles = []
        for chat in admin_chats:
            await UserRepository.grant_chat_access(user_pk, chat['id'])
            chat_titles.append(chat.get('title') or str(chat['chat_id']))

        # Отправляем пароль
        chat_list = '\n'.join(f"- `{title}`" for title in chat_titles)
        await message.answer(
            f"Ваше имя пользователя: `{author_name}`\n"
            f"Ваш пароль: `{password}`\n\n"
            f"Доступ предоставлен к чатам:\n{chat_list}",
            parse_mode='markdown'
        )
        logger.info(f"Пароль отправлен пользователю {author_id}, доступ к {len(admin_chats)} чатам")

    except Exception as e:
        logger.error(f"Ошибка при обработке /get_password для пользователя {author_id}: {e}")
        await message.answer(
            f"Произошла внутренняя ошибка. "
            f"Пожалуйста, свяжитесь с технической поддержкой: {HELPDESK_EMAIL}"
        )


@dp.message(F.chat.func(lambda chat: chat.type == ChatType.PRIVATE))
async def handle_private_message(message: types.Message) -> None:
    """Обрабатывает личные сообщения боту.

    Аргументы:
        message (Message): Входящее сообщение Telegram.
    """
    logger.info(f"Получено личное сообщение от пользователя {message.from_user.id}")
    try:
        await message.answer(
            "Здравствуйте! Пожалуйста, ознакомьтесь со списком моих команд в соответствующем меню."
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения пользователю {message.from_user.id}: {e}")
