import asyncio
import os
import sys
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ChatType, ParseMode
from aiogram.filters import Command
from aiogram.types import BotCommand, CallbackQuery
from dotenv import load_dotenv

sys.path.append("utils")
from basic import config, logger, update_detected_spam_json_file
from apis import get_cas, get_lols
from predictions import chatgpt_predict, bert_predict, get_predictions

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

detected_spam_json_path = config['DETECTED_SPAM_JSON']


# Обработчик команды /code
@dp.message(Command(BotCommand(command='code', description='Получить ссылку на GitHub репозиторий бота')))
async def handle_code_command(message: types.Message) -> None:
    """
    Обрабатывает команду /code и отправляет ссылку на GitHub репозиторий.

    Args:
        message (types.Message): Сообщение, содержащее команду /code.
    """
    github_link = "https://github.com/overklassniy/STANKIN_AntiSpam_Bot/"
    try:
        # Пробуем отправить пользователю ссылку на репозиторий
        await message.answer(f"Исходный код бота доступен на GitHub: {github_link}")
        logger.info(f"Sent GitHub link to {message.chat.id}")
    except Exception as e:
        logger.error(f"Error sending GitHub link to {message.chat.id}: {e}")


# Обработчик личных сообщений
@dp.message(F.chat.func(lambda chat: chat.type == ChatType.PRIVATE))
async def handle_private_message(message: types.Message) -> None:
    """
    Обрабатывает личные сообщения пользователей.

    Args:
        message (types.Message): Сообщение, полученное ботом.
    """
    # Ответ пользователю, когда бот получает личное сообщение
    response_text = "tet"
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

    Args:
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
            update_detected_spam_json_file(detected_spam_json_path, result_dict)

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
    global bot_id
    global bot
    bot = Bot(token=TOKEN)
    bot_id = bot.id
    await dp.start_polling(bot, polling_timeout=30)