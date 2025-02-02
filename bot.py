import os
import secrets
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import BotCommand
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

from panel.app import create_app, db
from panel.db_models import SpamMessage, User
from utils.apis import get_cas, get_lols
from utils.basic import config, logger
from utils.predictions import chatgpt_predict, bert_predict, get_predictions

# Загрузка переменных окружения
load_dotenv()

testing = False
if config['TESTING']:
    testing = True
    bot_token = 'TEST_BOT_TOKEN'
else:
    bot_token = 'BOT_TOKEN'

TOKEN = os.getenv(bot_token)

# Инициализация диспетчера событий
dp = Dispatcher()

# Идентификатор бота
bot_id = None

helpdesk_email = os.getenv('helpdesk_email')


# Обработчик команды /start
@dp.message(CommandStart(deep_link=True))
async def handle_start_command(message: types.Message, command: CommandObject) -> None:
    """
    Обрабатывает команду /start.

    Параметры:
        message (types.Message): Сообщение, содержащее команду /start.
        command (aiogram.filters.CommandObject): Объект содержащий аргументы /start.
    """
    args = command.args
    if args == 'get_password':
        await handle_get_password_command(message)


# Обработчик команды /code
@dp.message(Command(BotCommand(command='code', description='Получить ссылку на GitHub репозиторий бота')))
async def handle_code_command(message: types.Message) -> None:
    """
    Обрабатывает команду /code и отправляет ссылку на GitHub репозиторий.

    Параметры:
        message (types.Message): Сообщение, содержащее команду /code.
    """
    github_link = "https://github.com/overklassniy/STANKIN_AntiSpam_Bot/"
    try:
        # Пробуем отправить пользователю ссылку на репозиторий
        await message.answer(f"Исходный код бота доступен на GitHub: {github_link}")
        logger.info(f"Sent GitHub link to {message.chat.id}")
    except Exception as e:
        logger.error(f"Error sending GitHub link to {message.chat.id}: {e}")


# Обработчик команды /get_password
@dp.message(Command(BotCommand(command='get_password', description='Получить пароль для авторизации в панели управления Анти-Спам системы')))
async def handle_get_password_command(message: types.Message) -> None:
    """
    Обрабатывает команду /get_password и создает нового пользователя в базе данных Анти-Спам системы.

    Параметры:
        message (types.Message): Сообщение, содержащее команду /get_password.
    """
    author = message.from_user
    author_id = author.id
    author_name = author.username

    # Получаем корректный идентификатор чата из конфига.
    chat_id = config.get("CHAT_ID")
    try:
        author_chat_member = await bot.get_chat_member(chat_id=chat_id, user_id=author_id)
    except Exception as e:
        logger.error(f"Ошибка при получении информации о члене чата для пользователя {author_id} в чате {chat_id}: {e}")
        await message.answer(
            f"Произошла ошибка при проверке ваших прав доступа. Пожалуйста, попробуйте позже или свяжитесь с технической поддержкой по адресу {helpdesk_email}.")
        return

    # Проверка: является ли пользователь администратором или владельцем группы
    sent_by_admin = author_chat_member.status in ["administrator", "creator"]
    if not sent_by_admin:
        try:
            await message.answer(
                f"Вы не обладаете достаточными правами в группе (требуется статус администратора или владельца).\n\n"
                f"В случае возникновения вопросов – пожалуйста, свяжитесь с технической поддержкой по адресу {helpdesk_email}"
            )
            logger.info(f"Попытка доступа без прав: пользователь {author_id} (чат {message.chat.id})")
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения пользователю {message.chat.id}: {e}")
        return

    try:
        # Создаем контекст приложения для работы с базой данных
        app = create_app()
        with app.app_context():
            # Получаем пользователя из БД
            user = User.query.get(author_id)

            # Генерируем новый пароль
            password = secrets.token_urlsafe(9)
            hashed_password = generate_password_hash(password, method='scrypt')

            if not user:
                user = User(
                    id=author_id,
                    name=author_name,
                    password=hashed_password,
                    can_configure=False
                )
                db.session.add(user)
                logger.info(f"Добавлен новый пользователь {author_id} в базу данных")
            else:
                user.password = hashed_password
                logger.info(f"Обновлен пароль для пользователя {author_id}")

            # Фиксируем изменения в базе данных
            db.session.commit()

        # Отправляем пользователю его данные
        await message.answer(f"Ваше имя пользователя: `{author_name}`\nВаш пароль: `{password}`", parse_mode='markdown')

    except Exception as e:
        logger.error(f"Ошибка при обработке команды /get_password для пользователя {message.chat.id}: {e}")
        await message.answer(
            f"Произошла внутренняя ошибка при обработке запроса. Пожалуйста, попробуйте позже или свяжитесь с технической поддержкой по адресу {helpdesk_email}.")


# Обработчик личных сообщений
@dp.message(F.chat.func(lambda chat: chat.type == ChatType.PRIVATE))
async def handle_private_message(message: types.Message) -> None:
    """
    Обрабатывает личные сообщения пользователей.

    Параметры:
        message (types.Message): Сообщение, полученное ботом.
    """
    # Ответ пользователю, когда бот получает личное сообщение
    response_text = "Здравствуйте, пожалуйста, ознакомьтесь со списком моих комманд в соответствующем меню."
    try:
        await message.answer(response_text)
        logger.info(f"Sent private message to {message.chat.id}")
    except Exception as e:
        logger.error(f"Error sending private message to {message.chat.id}: {e}")


# Обработчик сообщений
@dp.message()
async def handle_message(message: types.Message) -> None:
    """
    Обрабатывает сообщения пользователей.

    Параметры:
        message (types.Message): Сообщение, обрабатываемое ботом.
    """
    global bot
    try:
        author = message.from_user
        author_id = author.id
        author_name = author.username
        author_chat_member = await bot.get_chat_member(chat_id=message.chat.id, user_id=author_id)
        sent_by_admin = int(author_chat_member.status in ["administrator", "creator"])
        if testing:
            sent_by_admin = 0
        if sent_by_admin:
            return None
        message_text = message.text
        if not message_text:
            message_text = message.caption
        has_reply_markup = int(bool(message.reply_markup))
        cas_banned = get_cas(author_id)
        lols_banned = get_lols(author_id)
        chatgpt_prediction = None
        if config['ENABLE_CHATGPT'] and os.getenv('OPENAI_API_KEY'):
            chatgpt_prediction = await chatgpt_predict(message_text)
        bert_prediction = bert_predict(message_text, config["BERT_THRESHOLD"])
        if not testing:
            is_spam = False
            if has_reply_markup or cas_banned or lols_banned or chatgpt_prediction or bert_prediction[0]:
                is_spam = True

            if not is_spam:
                return None

            result_dict = {
                "timestamp": datetime.now().timestamp(),
                "author_id": author_id,
                "author_username": author_name,
                "message_text": message_text,
                "has_reply_markup": has_reply_markup,
                "cas": cas_banned,
                "lols": lols_banned,
                "chatgpt_prediction": chatgpt_prediction,
                "bert_prediction": bert_prediction
            }

            new_spam = SpamMessage(
                timestamp=result_dict["timestamp"],
                author_id=result_dict["author_id"],
                author_username=result_dict["author_username"],
                message_text=result_dict["message_text"],
                has_reply_markup=result_dict["has_reply_markup"],
                cas=result_dict["cas"],
                lols=result_dict["lols"],
                chatgpt_prediction=result_dict.get("chatgpt_prediction", 0),
                bert_prediction=round(result_dict["bert_prediction"][1][1], 7)
            )
            with create_app().app_context():
                db.session.add(new_spam)
                db.session.commit()

            await message.delete()
        else:
            cmodels_predictions = get_predictions(message_text)

            reply_message = f'''ID пользователя: {author_id}
Имя пользователя: {author_name}
Отправлено админом: {sent_by_admin}
Имеет inline клавиатуру: {has_reply_markup}
Забанен ли в CAS: {cas_banned}
Забанен ли в LOLS: {lols_banned}
Предикт BERT: {bert_prediction}
Предикт кастомных моделей: {cmodels_predictions}'''

            await message.reply(reply_message)
            logger.info(f"Sent message to {message.chat.id}")
    except Exception as e:
        logger.error(f"Error processing message to {message.chat.id}: {e}")


async def start_bot() -> None:
    """
    Запускает бота и инициализирует диспетчер событий.
    """
    global bot
    global bot_id

    bot = Bot(token=TOKEN)
    bot_id = bot.id
    await dp.start_polling(bot, polling_timeout=30)
