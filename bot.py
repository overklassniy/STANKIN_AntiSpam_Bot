import os
import secrets
import string
from copy import copy
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ChatType, ParseMode
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

from panel.app import create_app, db
from panel.db_models import SpamMessage, User, MutedUser
from utils.apis import get_cas, get_lols
from utils.basic import config, logger, add_hours_get_timestamp
from utils.predictions import chatgpt_predict, bert_predict, get_predictions

# Загрузка переменных окружения
load_dotenv()

# Флаг тестирования
testing = False
if config['TESTING']:
    testing = True
    bot_token = 'TEST_BOT_TOKEN'
else:
    bot_token = 'BOT_TOKEN'

# Получаем токен из переменных окружения
TOKEN = os.getenv(bot_token)
if not TOKEN:
    logger.critical("Токен не найден в переменных окружения!")
    raise Exception("Токен не найден!")

# Инициализация диспетчера событий
dp = Dispatcher()

# Глобальная переменная для хранения ID бота
bot_id = None

# Получение адреса технической поддержки
helpdesk_email = os.getenv('HELPDESK_EMAIL')
if not helpdesk_email:
    logger.warning("E-mail технической поддержки не задан в переменных окружения")


# Обработчик команды /start с параметром deep_link
@dp.message(CommandStart(deep_link=True))
async def handle_start_command(message: types.Message, command: CommandObject) -> None:
    """
    Обрабатывает команду /start с возможным deep_link параметром.

    Аргументы:
        message (types.Message): Сообщение, содержащее команду /start.
        command (CommandObject): Объект команды, содержащий аргументы.
    """
    logger.info(f"Получена команда /start от пользователя {message.from_user.id} с аргументом: {command.args}")
    args = command.args
    if args == 'get_password':
        await handle_get_password_command(message)


# Обработчик команды /code
@dp.message(Command(BotCommand(command='code', description='Получить ссылку на GitHub репозиторий бота')))
async def handle_code_command(message: types.Message) -> None:
    """
    Обрабатывает команду /code и отправляет пользователю ссылку на GitHub репозиторий.

    Аргументы:
        message (types.Message): Сообщение, содержащее команду /code.
    """
    github_link = "https://github.com/overklassniy/STANKIN_AntiSpam_Bot/"
    try:
        await message.answer(f"Исходный код бота доступен на GitHub: {github_link}")
        logger.info(f"Отправлена ссылка на GitHub репозиторий пользователю {message.chat.id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке ссылки на GitHub пользователю {message.chat.id}: {e}")


# Обработчик команды /get_password
@dp.message(Command(BotCommand(command='get_password', description='Получить пароль для авторизации в панели управления Анти-Спам системы')))
async def handle_get_password_command(message: types.Message) -> None:
    """
    Обрабатывает команду /get_password, проверяет права пользователя в группе и создает/обновляет запись пользователя в базе данных с новым сгенерированным паролем.

    Аргументы:
        message (types.Message): Сообщение, содержащее команду /get_password.
    """
    logger.info(f"Начало обработки команды /get_password для пользователя {message.from_user.id}")
    author = message.from_user
    author_id = author.id
    author_name = author.username

    # Получаем идентификатор чата из конфига
    chat_id = config.get("TARGET_CHAT_ID")
    try:
        author_chat_member = await bot.get_chat_member(chat_id=chat_id, user_id=author_id)
        logger.debug(f"Пользователь {author_id} является членом чата {chat_id} со статусом {author_chat_member.status}")
    except Exception as e:
        logger.error(f"Ошибка при получении информации о пользователе {author_id} в чате {chat_id}: {e}")
        await message.answer(
            f"Произошла ошибка при проверке ваших прав доступа. Пожалуйста, попробуйте позже или свяжитесь с технической поддержкой по адресу {helpdesk_email}."
        )
        return

    # Проверка: является ли пользователь администратором или владельцем группы
    sent_by_admin = author_chat_member.status in ["administrator", "creator"]
    if not sent_by_admin:
        try:
            await message.answer(
                "Вы не обладаете достаточными правами в группе (требуется статус администратора или владельца).\n\n"
                f"В случае возникновения вопросов – пожалуйста, свяжитесь с технической поддержкой по адресу {helpdesk_email}"
            )
            logger.info(f"Попытка получения пароля от пользователя {author_id} без соответствующих прав")
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения пользователю {author_id}: {e}")
        return

    try:
        # Создаем контекст приложения для работы с базой данных
        app = create_app()
        with app.app_context():
            # Получаем запись пользователя из базы данных
            user = User.query.get(author_id)

            # Генерируем новый пароль и его хэш
            password = secrets.token_urlsafe(9)
            hashed_password = generate_password_hash(password, method='scrypt')

            if not user:
                if not author_name:
                    author_name = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))

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
            logger.debug(f"Изменения в БД успешно зафиксированы для пользователя {author_id}")

        # Отправляем пользователю его имя и новый пароль
        await message.answer(f"Ваше имя пользователя: `{author_name}`\nВаш пароль: `{password}`", parse_mode='markdown')
        logger.info(f"Пароль успешно отправлен пользователю {author_id}")
    except Exception as e:
        logger.error(f"Ошибка при обработке команды /get_password для пользователя {author_id}: {e}")
        await message.answer(
            f"Произошла внутренняя ошибка при обработке запроса. Пожалуйста, попробуйте позже или свяжитесь с технической поддержкой по адресу {helpdesk_email}."
        )


# Обработчик личных сообщений
@dp.message(F.chat.func(lambda chat: chat.type == ChatType.PRIVATE))
async def handle_private_message(message: types.Message) -> None:
    """
    Обрабатывает личные сообщения, отправляемые боту, и информирует пользователя о доступных командах.

    Аргументы:
        message (types.Message): Личное сообщение от пользователя.
    """
    logger.info(f"Получено личное сообщение от пользователя {message.from_user.id}")
    response_text = "Здравствуйте, пожалуйста, ознакомьтесь со списком моих комманд в соответствующем меню."
    try:
        await message.answer(response_text)
        logger.info(f"Отправлено приветственное сообщение пользователю {message.from_user.id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке личного сообщения пользователю {message.from_user.id}: {e}")


@dp.callback_query(lambda c: c.data.startswith("mute_user"))
async def process_mute_user_callback(callback: types.CallbackQuery) -> None:
    """
    Обрабатывает нажатие на кнопку "Ограничить пользователя".
    Из callback_data извлекается ID пользователя, затем:
      - Получается или создается запись о пользователе в БД,
      - Определяется новое время ограничения (в зависимости от количества нарушений),
      - Применяется ограничение в чате,
      - Исходное сообщение редактируется: удаляется клавиатура и добавляется строка с датой окончания ограничения.
    """
    try:
        # Извлекаем user_id из callback_data. Ожидаем формат "mute_user:<user_id>"
        parts = callback.data.split(":")
        if len(parts) != 2:
            await callback.answer("Неверные данные для ограничения!")
            return

        user_id = int(parts[1])
        chat_id = config["TARGET_CHAT_ID"]
        mute = types.ChatPermissions(can_send_messages=False)

        # Работа с базой данных через контекст приложения
        app = create_app()
        with app.app_context():
            muted_user_db = MutedUser.query.filter_by(id=user_id).first()
            if muted_user_db.relapse_number == 1:
                new_until_date = add_hours_get_timestamp(24)
            elif muted_user_db.relapse_number == 2:
                new_until_date = add_hours_get_timestamp(168)
            else:
                new_until_date = add_hours_get_timestamp(999)
            muted_user_db.muted_till_timestamp = new_until_date
            muted_user_db.timestamp = datetime.now().timestamp()
            db.session.commit()

        # Применяем ограничение для пользователя в чате
        await bot.restrict_chat_member(chat_id=chat_id, user_id=user_id, permissions=mute, until_date=new_until_date)
        date_untildate = datetime.fromtimestamp(new_until_date).strftime("%d.%m.%Y %H:%M:%S")

        # Чтобы сохранить исходное форматирование, используем html-версию текста, если она доступна
        original_text = getattr(callback.message, "html_text", callback.message.text)
        new_text = original_text + f'\n<b>Ограничен до:</b> {date_untildate}'

        orig_kb = callback.message.reply_markup.inline_keyboard
        new_kb_buttons = []
        for row in orig_kb:
            new_row = [btn for btn in row if not btn.callback_data.startswith("mute_user")]
            if new_row:
                new_kb_buttons.append(new_row)
        new_markup = InlineKeyboardMarkup(inline_keyboard=new_kb_buttons)

        # Редактируем сообщение
        await callback.message.edit_text(new_text, parse_mode=ParseMode.HTML, reply_markup=new_markup)

        await callback.answer("Пользователь ограничен!")
        logger.info(f"Пользователь {user_id} ограничен до {date_untildate} (Рецидив №{muted_user_db.relapse_number})")
    except Exception as e:
        logger.error(f"Ошибка в обработчике mute_user: {e}")
        await callback.answer("Ошибка при ограничении пользователя!")


@dp.callback_query(lambda c: c.data.startswith("delete_message"))
async def process_delete_message_callback(callback: types.CallbackQuery) -> None:
    parts = callback.data.split(":")
    if len(parts) != 2:
        await callback.answer("Неверные данные для удаления!")
        return
    msg_id = int(parts[1])
    target_chat = config["TARGET_CHAT_ID"]

    try:
        await bot.delete_message(chat_id=target_chat, message_id=msg_id)

        original_text = getattr(callback.message, "html_text", callback.message.text)
        new_text = original_text + f'\n\n<i>Сообщение удалено вручную</i>'

        # Удаляем кнопку "удалить", оставляем "ограничить", если она была
        orig_kb = callback.message.reply_markup.inline_keyboard
        new_kb_buttons = []
        for row in orig_kb:
            new_row = [btn for btn in row if not btn.callback_data.startswith("delete_message")]
            if new_row:
                new_kb_buttons.append(new_row)
        new_markup = InlineKeyboardMarkup(inline_keyboard=new_kb_buttons)

        # Редактируем сообщение
        await callback.message.edit_text(new_text, parse_mode=ParseMode.HTML, reply_markup=new_markup)

        await callback.answer("Сообщение удалено!")
        logger.info(f"Сообщение {msg_id} удалено из чата {target_chat}")
    except Exception as e:
        logger.error(f"Ошибка при удалении сообщения: {e}")
        await callback.answer("Не удалось удалить сообщение!")


# Обработчик всех остальных сообщений
@dp.message()
async def handle_message(message: types.Message) -> None:
    """
    Обрабатывает все входящие сообщения от пользователей. Проводит анализ сообщения и, если оно считается спамом, удаляет его и при необходимости мьютит пользователя.
    В тестовом режиме отправляет диагностическое сообщение с предсказаниями моделей.

    Аргументы:
        message (types.Message): Сообщение, обрабатываемое ботом.
    """
    global bot

    chat_id = config["TARGET_CHAT_ID"]
    logger.info(f"Обработка сообщения {message.text}\nот пользователя {message.from_user.id} в чате {chat_id}")

    try:
        author = message.from_user
        author_id = author.id
        author_name = author.username

        # Получаем информацию о пользователе в чате
        author_chat_member = await bot.get_chat_member(chat_id=chat_id, user_id=author_id)
        sent_by_admin = int((author_chat_member.status in ["administrator", "creator"]) or (author_id in [777000, 1087968824]))
        logger.debug(f"Статус пользователя {author_id} в чате {chat_id}: {author_chat_member.status}")

        # В тестовом режиме админские сообщения обрабатываются
        if testing:
            sent_by_admin = 0

        if sent_by_admin:
            logger.info(f"Сообщение от администратора {author_id} пропускается")
            return None

        # Извлекаем текст сообщения (учитываем captions для медиа)
        message_text = message.text if message.text else message.caption
        if not message_text:
            logger.debug(f"Сообщение от {author_id} не содержит текста и игнорируется")
            return None

        # Проверяем наличие inline клавиатуры (reply_markup)
        has_reply_markup = bool(message.reply_markup) if config['CHECK_REPLY_MARKUP'] else None

        # Получаем данные по кастомным API для проверки спама
        cas_banned = get_cas(author_id) if config["CHECK_CAS"] else None
        lols_banned = get_lols(author_id) if config["CHECK_LOLS"] else None

        # Предикты моделей (ChatGPT и BERT)
        chatgpt_prediction = None
        if config['ENABLE_CHATGPT'] and os.getenv('OPENAI_API_KEY'):
            chatgpt_prediction = await chatgpt_predict(message_text)
            logger.debug(f"ChatGPT предикт для пользователя {author_id}: {chatgpt_prediction}")
        bert_prediction = bert_predict(message_text, config["BERT_THRESHOLD"])
        logger.debug(f"BERT предикт для пользователя {author_id}: {bert_prediction}")

        # Определяем, является ли сообщение спамом
        is_spam = any([has_reply_markup, cas_banned, lols_banned, chatgpt_prediction, bert_prediction[0]])
        if is_spam:
            logger.info(f"Сообщение от {author_id} идентифицировано как спам")
        else:
            logger.debug(f"Сообщение от {author_id} не считается спамом")
            return None

        # Формируем словарь с данными для записи в базу
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

        # Создаем запись о спаме
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
        # Сохраняем запись в базу данных
        with create_app().app_context():
            db.session.add(new_spam)
            db.session.commit()
            logger.info(f"Запись о спаме добавлена в БД для пользователя {author_id}")

        # Обработка настроек
        enable_deleting = config["ENABLE_DELETING"]
        enable_automuting = config["ENABLE_AUTOMUTING"]

        # Кнопки для уведомления
        delete_btn = None if enable_deleting else InlineKeyboardButton(
            text="🗑 Удалить сообщение",
            callback_data=f"delete_message:{message.message_id}"
        )
        mute_btn = None if enable_automuting else InlineKeyboardButton(
            text="🔨 Ограничить пользователя",
            callback_data=f"mute_user:{author_id}"
        )

        # Авто-удаление сообщения
        if enable_deleting:
            await message.delete()
            logger.info(f"Сообщение от {author_id} удалено")

        # Сохранение/обновление данных по пользователю
        with create_app().app_context():
            muted = MutedUser.query.filter_by(id=author_id).first()

            if not muted:
                relapse = 1
                until = add_hours_get_timestamp(24) if enable_automuting else None
                muted = MutedUser(
                    id=author_id,
                    username=author_name,
                    timestamp=result_dict["timestamp"],
                    muted_till_timestamp=until,
                    relapse_number=relapse
                )
                db.session.add(muted)
                logger.info(f"Создана новая запись о пользователе {author_id}")
            else:
                relapse = muted.relapse_number + 1
                muted.relapse_number = relapse
                hours = 168 if relapse == 2 else 999
                muted.muted_till_timestamp = add_hours_get_timestamp(hours) if enable_automuting else None
                logger.info(
                    f"Обновлена запись о пользователе {author_id} "
                    f"(Рецидив №{relapse})"
                )

            db.session.commit()

        # Формирование текста уведомления
        ts = datetime.fromtimestamp(result_dict["timestamp"]).strftime("%d.%m.%Y %H:%M:%S")
        has_kb = result_dict["has_reply_markup"]
        notif = (
            f"<b>Дата:</b> {ts}\n"
            f"<b>ID пользователя:</b> <code>{author_id}</code>\n"
            f"<b>Имя пользователя:</b> <code>{author_name}</code>\n"
            f"<b>Текст сообщения:</b>\n<blockquote>{result_dict['message_text']}</blockquote>\n"
            f"<b>Имеет inline-клавиатуру:</b> "
            f"{'Да' if has_kb else 'Нет' if has_kb is False else 'Отключено'}\n"
            f"<b>Вердикт RuBert:</b> "
            f"<code>{round(result_dict['bert_prediction'][1][1], 7)}</code>\n"
            f"<b>Количество нарушений:</b> {relapse}"
        )

        notification_kwargs = {
            "chat_id": config["NOTIFICATION_CHAT_ID"],
            "message_thread_id": config["NOTIFICATION_CHAT_SPAM_THREAD"],
            "text": notif,
            "parse_mode": ParseMode.HTML
        }

        # Если авто-мьютинг и авто-удаление — сначала ограничиваем права
        if enable_automuting and enable_deleting:
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=author_id,
                permissions=types.ChatPermissions(can_send_messages=False),
                until_date=muted.muted_till_timestamp
            )
            until_str = datetime.fromtimestamp(muted.muted_till_timestamp).strftime("%d.%m.%Y %H:%M:%S")
            logger.info(f"Пользователь {author_id} замьючен до {until_str}")
            notification_kwargs["text"] += f"\n<b>Ограничен до:</b> {until_str}"
            await bot.send_message(**notification_kwargs)
            logger.info("Сообщение-уведомление без inline-клавиатуры было отправлено")
        else:
            # Формируем клавиатуру (если есть что показывать)
            buttons = [btn for btn in (delete_btn, mute_btn) if btn]
            if buttons:
                notification_kwargs["reply_markup"] = InlineKeyboardMarkup(inline_keyboard=[[btn] for btn in buttons])
            await bot.send_message(**notification_kwargs)
            kb_desc = []
            if delete_btn: kb_desc.append("Удалить сообщение")
            if mute_btn: kb_desc.append("Ограничить пользователя")
            logger.info(
                f"Сообщение-уведомление с inline-клавиатурой "
                f"[{', '.join(kb_desc)}] было отправлено"
                if buttons else
                "Сообщение-уведомление без inline-клавиатуры было отправлено"
            )
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения в чате {chat_id}: {e}")


# Функция для запуска бота
async def start_bot() -> None:
    """
    Инициализирует объект бота, сохраняет его ID и запускает поллинг сообщений.\
    """
    global bot
    global bot_id

    bot = Bot(token=TOKEN)
    # Получаем ID бота
    bot_id = bot.id
    logger.info(f"Бот запущен с ID {bot_id}")

    # Запускаем цикл поллинга с таймаутом в 30 секунд
    await dp.start_polling(bot, polling_timeout=30)
