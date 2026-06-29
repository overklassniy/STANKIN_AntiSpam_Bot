"""Сервис модерации: анализ сообщений, принятие решений, выполнение действий."""

from datetime import datetime
from typing import Optional, Dict, Any

from aiogram import Bot
from aiogram.types import Message, ChatPermissions

from core.repository.chat import ChatRepository
from core.repository.settings import SettingsRepository
from core.repository.spam import SpamRepository
from core.repository.muted import MutedRepository
from core.repository.whitelist import WhitelistRepository
from core.repository.collected import CollectedRepository
from bot.services.notifications import NotificationService
from bot.keyboards import create_spam_notification_keyboard
from core.utils import add_hours_get_timestamp
from core.logging import logger
from core.config import TESTING


class ModerationService:
    """Сервис модерации сообщений."""

    @staticmethod
    async def check_if_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
        """Проверяет, является ли пользователь админом в чате.

        Аргументы:
            bot (Bot): Экземпляр бота.
            chat_id (int): ID чата.
            user_id (int): ID пользователя.

        Возвращаемое значение:
            bool: True если пользователь админ.
        """
        try:
            member = await bot.get_chat_member(chat_id, user_id)
            return member.status in ('administrator', 'creator')
        except Exception as e:
            logger.warning(f"Не удалось проверить статус админа {user_id} в чате {chat_id}: {e}")
            return False

    @staticmethod
    async def analyze_message(
        message_text: str,
        author_id: int,
        settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Анализирует сообщение на спам.

        Аргументы:
            message_text (str): Текст сообщения.
            author_id (int): ID автора.
            settings (Dict[str, Any]): Настройки чата.

        Возвращаемое значение:
            Dict[str, Any]: Результат анализа с ключами:
                bert_prediction, cas, lols, chatgpt, ausure.
        """
        from bot.services.spam_detection import predict_spam
        from pathlib import Path
        from core.config import MODELS_DIR

        bert_threshold = settings.get('BERT_THRESHOLD', 0.945)
        bert_sure_threshold = settings.get('BERT_SURE_THRESHOLD', 0.98)

        # Путь к BERT модели из настроек
        model_name = settings.get('BERT_MODEL', 'finetuned_rubert_tiny2')
        model_path = str(Path(MODELS_DIR) / model_name)

        # BERT предсказание
        bert_result = predict_spam(message_text, model_path)
        bert_score = bert_result[1][1] if bert_result else 0.0

        # CAS проверка
        cas_result = None
        if settings.get('CHECK_CAS', False):
            from bot.services.external_apis import check_cas
            cas_result = await check_cas(author_id)

        # LOLS проверка
        lols_result = None
        if settings.get('CHECK_LOLS', False):
            from bot.services.external_apis import check_lols
            lols_result = await check_lols(author_id)

        # ChatGPT проверка
        chatgpt_result = None
        if settings.get('ENABLE_CHATGPT', False):
            from bot.services.spam_detection import check_spam_chatgpt
            chatgpt_result = await check_spam_chatgpt(message_text)

        # Определение уверенности
        ausure = bert_score >= bert_sure_threshold

        return {
            'bert_prediction': bert_result,
            'bert_score': round(bert_score, 7),
            'cas': cas_result,
            'lols': lols_result,
            'chatgpt': chatgpt_result,
            'ausure': ausure,
        }

    @staticmethod
    def determine_spam_status(
        analysis: Dict[str, Any],
        has_reply_markup: bool,
        is_forwarded: bool = False
    ) -> Optional[bool]:
        """Определяет, является ли сообщение спамом.

        Аргументы:
            analysis (Dict[str, Any]): Результат анализа.
            has_reply_markup (bool): Есть ли inline-клавиатура.
            is_forwarded (bool): Является ли пересланным.

        Возвращаемое значение:
            Optional[bool]: True — спам, False — не спам, None — неопределено.
        """
        bert_score = analysis.get('bert_score', 0.0)
        bert_threshold = 0.945  # Будет браться из settings в вызывающем коде

        if analysis.get('cas') or analysis.get('lols'):
            return True

        if bert_score >= bert_threshold:
            return True

        if has_reply_markup and bert_score >= 0.5:
            return True

        return None

    @staticmethod
    async def handle_message(message: Message, bot: Bot) -> None:
        """Обрабатывает входящее сообщение: проверка на спам и модерация.

        Алгоритм работы:
            1. Проверить, что чат наблюдаемый.
            2. Загрузить per-chat настройки.
            3. Проверить, является ли автор админом.
            4. Проверить белый список.
            5. Анализ на спам.
            6. Если спам — удалить/замьютить, отправить уведомление.

        Аргументы:
            message (Message): Входящее сообщение.
            bot (Bot): Экземпляр бота.
        """
        chat_id = message.chat.id
        author = message.from_user

        if author is None:
            return

        author_id = author.id
        author_name = author.username

        # Проверяем, что чат наблюдаемый
        chat_pk = await ChatRepository.get_chat_pk(chat_id)
        if chat_pk is None:
            return

        # Загружаем per-chat настройки
        settings = await SettingsRepository.get_all_chat_settings(chat_pk)

        # Сбор сообщений (если включено)
        collect_all = settings.get('COLLECT_ALL_MESSAGES', False)
        collect_text = message.text or message.caption
        if collect_all and collect_text:
            try:
                await CollectedRepository.add_collected_message(
                    chat_id=chat_id,
                    user_id=author_id,
                    username=author_name,
                    message_text=collect_text
                )
            except Exception as e:
                logger.error(f"Ошибка при сохранении сообщения: {e}")

        logger.info(f"Обработка сообщения от {author_id} в чате {chat_id}")

        try:
            # Пропускаем сообщения от администраторов
            is_admin = await ModerationService.check_if_admin(bot, chat_id, author_id)

            if TESTING:
                is_admin = False

            if is_admin:
                logger.debug(f"Сообщение от администратора {author_id} пропускается")
                return

            # Проверяем белый список
            if await WhitelistRepository.is_whitelisted(chat_pk, author_id):
                logger.debug(f"Пользователь {author_id} в белом списке чата {chat_id}")
                return

            # Получаем текст сообщения
            message_text = message.text or message.caption
            if not message_text:
                logger.debug(f"Сообщение от {author_id} без текста — игнорируется")
                return

            # Проверяем наличие inline клавиатуры
            check_reply_markup = settings.get('CHECK_REPLY_MARKUP', True)
            has_reply_markup = bool(message.reply_markup) if check_reply_markup else None

            # Определяем, является ли сообщение пересланным
            is_forwarded = (
                message.forward_from is not None
                or message.forward_from_chat is not None
            )

            # Анализируем сообщение
            analysis = await ModerationService.analyze_message(
                message_text, author_id, settings
            )

            # Определяем статус спама
            bert_threshold = settings.get('BERT_THRESHOLD', 0.945)
            is_spam = ModerationService._determine_spam(
                analysis, bert_threshold, has_reply_markup or False, is_forwarded
            )

            # Проверка на email для категории NOT SURE
            not_sure = False
            check_email_not_sure = settings.get('CHECK_EMAIL_NOT_SURE', True)
            if check_email_not_sure:
                from bot.services.text_analysis import contains_email
                if contains_email(message_text):
                    if is_spam is None:
                        # Модель не распознала как спам, но есть email — NOT SURE
                        is_spam = True
                        not_sure = True
                    elif is_spam is True:
                        # Модель распознала как спам — помечаем NOT SURE для ручной проверки
                        not_sure = True

            if not is_spam:
                logger.debug(f"Сообщение от {author_id} не является спамом")
                return

            logger.info(
                f"Сообщение от {author_id} идентифицировано как спам "
                f"(ausure={analysis['ausure']}, not_sure={not_sure}) в чате {chat_id}"
            )

            # Сохраняем в БД
            current_timestamp = datetime.now().timestamp()
            bert_score = analysis['bert_score']

            await SpamRepository.add_spam_message(
                chat_id=chat_id,
                message_id=message.message_id,
                timestamp=current_timestamp,
                author_id=author_id,
                author_username=author_name,
                message_text=message_text,
                has_reply_markup=has_reply_markup,
                cas=analysis['cas'],
                lols=analysis['lols'],
                chatgpt_prediction=analysis['chatgpt'],
                bert_prediction=bert_score
            )

            # Настройки автоматических действий
            enable_deleting = settings.get('ENABLE_DELETING', True)
            enable_automuting = settings.get('ENABLE_AUTOMUTING', False)
            ausure = analysis['ausure'] and not not_sure

            # Авто-удаление
            auto_deleted = False
            if enable_deleting and is_spam is True and ausure:
                try:
                    await message.delete()
                    auto_deleted = True
                    logger.info(f"Сообщение от {author_id} автоматически удалено")
                except Exception as e:
                    logger.error(f"Ошибка при автоматическом удалении: {e}")

            # Обработка записи о нарушениях
            muted = await MutedRepository.get_muted_user(chat_pk, author_id)
            if not muted:
                relapse = 1
                until = add_hours_get_timestamp(24) if (enable_automuting and ausure) else None
                await MutedRepository.create_muted_user(
                    chat_pk, author_id, author_name, current_timestamp, until, relapse
                )
            else:
                relapse = muted['relapse_number'] + 1
                hours = 168 if relapse == 2 else 999
                until = (
                    add_hours_get_timestamp(hours)
                    if (enable_automuting and ausure)
                    else muted.get('muted_till_timestamp')
                )
                await MutedRepository.update_muted_user(
                    chat_pk, author_id, current_timestamp, until, relapse
                )

            # Формируем уведомление
            muted_until_str = None
            if until and ausure and enable_automuting:
                muted_until_str = datetime.fromtimestamp(until).strftime("%d.%m.%Y %H:%M:%S")

            from bot.notifications import format_spam_notification
            notification_text = format_spam_notification(
                timestamp=current_timestamp,
                author_id=author_id,
                author_name=author_name,
                message_text=message_text,
                has_reply_markup=has_reply_markup,
                bert_score=bert_score,
                relapse_number=relapse,
                auto_deleted=auto_deleted,
                muted_until=muted_until_str,
                chat_title=message.chat.title or str(chat_id),
                chat_id=chat_id,
            )

            # Авто-мьютинг
            mute_success = False
            if enable_automuting and enable_deleting and ausure:
                try:
                    await bot.restrict_chat_member(
                        chat_id=chat_id,
                        user_id=author_id,
                        permissions=ChatPermissions(can_send_messages=False),
                        until_date=until
                    )
                    logger.info(f"Пользователь {author_id} ограничен до {muted_until_str}")
                    mute_success = True
                except Exception as e:
                    logger.error(f"Ошибка при ограничении {author_id}: {e}")

            # Отправляем уведомления
            notification_thread = NotificationService.get_spam_thread(ausure, not_sure)

            if enable_automuting and enable_deleting and ausure and mute_success:
                await NotificationService.send_spam_notification(
                    bot, notification_text, keyboard=None, thread_id=notification_thread
                )
                await NotificationService.send_mute_notification(
                    bot, author_id, author_name, muted_until_str, relapse, chat_id
                )
            else:
                keyboard = create_spam_notification_keyboard(
                    message_id=message.message_id,
                    user_id=author_id,
                    chat_id=chat_id,
                    include_delete=not auto_deleted,
                    include_mute=True,
                    include_not_spam=True
                )
                await NotificationService.send_spam_notification(
                    bot, notification_text, keyboard=keyboard, thread_id=notification_thread
                )

        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения в чате {chat_id}: {e}")

    @staticmethod
    def _determine_spam(
        analysis: Dict[str, Any],
        bert_threshold: float,
        has_reply_markup: bool,
        is_forwarded: bool = False
    ) -> Optional[bool]:
        """Определяет, является ли сообщение спамом.

        Аргументы:
            analysis (Dict[str, Any]): Результат анализа.
            bert_threshold (float): Порог BERT.
            has_reply_markup (bool): Есть ли inline-клавиатура.
            is_forwarded (bool): Является ли пересланным.

        Возвращаемое значение:
            Optional[bool]: True — спам, False — не спам, None — неопределено.
        """
        bert_score = analysis.get('bert_score', 0.0)

        if analysis.get('cas') or analysis.get('lols'):
            return True

        if bert_score >= bert_threshold:
            return True

        if has_reply_markup and bert_score >= 0.5:
            return True

        return None
