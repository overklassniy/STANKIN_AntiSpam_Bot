"""REST API роуты для веб-панели.

Все эндпоинты находятся под префиксом /api/v1/.
Возвращают JSON-данные для клиентского TypeScript.
"""

from typing import List, Optional, Union

from fastapi import APIRouter, Request, Query, Depends, HTTPException
from fastapi.responses import JSONResponse

from core.repository.spam import SpamRepository
from core.repository.muted import MutedRepository
from core.repository.settings import SettingsRepository
from core.repository.chat import ChatRepository
from core.repository.user import UserRepository
from panel.routes.auth import require_user_api
from panel.schemas import (
    PaginationMeta,
    SpamMessageOut,
    MutedUserOut,
    SettingOut,
    SettingUpdate,
    ChatOut,
    ChatUserOut,
    ChatAddIn,
    UserInfoOut,
    LoginIn,
)
from core.logging import logger

router = APIRouter(prefix='/api/v1')


async def _get_accessible_chat_pks(user: dict) -> Optional[List[int]]:
    """Асинхронно получает список PK чатов, доступных пользователю.

    Аргументы:
        user (dict): Данные текущего пользователя.

    Возвращаемое значение:
        chat_pks (Optional[List[int]]): Список PK чатов или None (все чаты).
    """
    if user['is_superadmin']:
        return None
    accessible = await UserRepository.get_accessible_chat_pks(user['id'])
    if not accessible:
        return []
    return accessible


@router.get('/auth/me', tags=['Аутентификация'], summary='Получение информации о текущем пользователе')
async def get_current_user(request: Request):
    """# Получение информации о текущем пользователе

    Возвращает данные авторизованного пользователя: имя, идентификатор и флаг суперпользователя.

    ## Когда использовать

    Используйте этот эндпоинт после загрузки клиентского приложения, чтобы определить, авторизован ли пользователь и какие у него есть права.

    ## Требуемые права

    Запрос доступен только авторизованному пользователю.

    ## Успешный ответ

    Возвращает объект с полями `id`, `username`, `is_superadmin`.

    ## Возможные ошибки

    ### 401 Не авторизован

    Сессия не содержит данных пользователя. Необходимо выполнить вход через `POST /api/v1/auth/login`.

    ### 401 Пользователь не найден

    Пользователь, указанный в сессии, больше не существует в системе.

    Аргументы:
        request (Request): Запрос FastAPI.

    Возвращаемое значение:
        UserInfoOut: Данные текущего пользователя.
    """
    user_pk = request.session.get('user_pk')
    if not user_pk:
        raise HTTPException(status_code=401, detail='Не авторизован')

    user = await UserRepository.get_user_by_id(user_pk)
    if not user:
        raise HTTPException(status_code=401, detail='Пользователь не найден')

    return UserInfoOut(
        id=user['id'],
        username=user['name'],
        is_superadmin=user['is_superadmin'],
    )


@router.post('/auth/login', tags=['Аутентификация'], summary='Вход в систему')
async def login(request: Request, data: LoginIn):
    """# Вход в систему

    Проверяет учётные данные пользователя и создаёт сессию.

    ## Когда использовать

    Используйте этот эндпоинт для аутентификации пользователя по имени и паролю перед вызовом защищённых эндпоинтов.

    ## Что происходит

    После успешного выполнения запроса:

    * создаётся сессия пользователя;
    * пользователь получает доступ к защищённым эндпоинтам.

    ## Параметры запроса

    | Поле | Тип | Обязательное | Описание |
    | --- | --- | --- | --- |
    | username | string | Да | Имя пользователя. |
    | password | string | Да | Пароль пользователя. |
    | remember | boolean | Нет | Флаг продления сессии. |

    ## Успешный ответ

    Возвращает объект `{"status": "ok"}`.

    ## Возможные ошибки

    ### 401 Неверные учётные данные

    Имя пользователя не найдено или пароль не совпадает.

    ## Особенности

    * Имя пользователя обрезается от пробельных символов перед проверкой.
    * Сессия хранится в cookie.

    Аргументы:
        request (Request): Запрос FastAPI.
        data (LoginIn): Данные для входа.
    """
    from panel.routes.auth import verify_password

    user = await UserRepository.get_user_by_name(data.username.strip())
    if not user or not user.get('password_hash'):
        raise HTTPException(status_code=401, detail='Неверные учётные данные')

    if not verify_password(data.password, user['password_hash']):
        raise HTTPException(status_code=401, detail='Неверные учётные данные')

    request.session['user_pk'] = user['id']
    logger.info(f"API: пользователь '{data.username}' вошёл в систему.")
    return {'status': 'ok'}


@router.post('/auth/logout', tags=['Аутентификация'], summary='Выход из системы')
async def logout(request: Request):
    """# Выход из системы

    Завершает сессию пользователя.

    ## Когда использовать

    Используйте этот эндпоинт, когда пользователь нажимает кнопку выхода из системы.

    ## Что происходит

    После успешного выполнения запроса:

    * сессия пользователя очищается;
    * доступ к защищённым эндпоинтам прекращается.

    ## Требуемые права

    Запрос доступен без авторизации, но имеет смысл только при активной сессии.

    ## Успешный ответ

    Возвращает объект `{"status": "ok"}`.

    Аргументы:
        request (Request): Запрос FastAPI.
    """
    request.session.clear()
    return {'status': 'ok'}


@router.get('/spam', tags=['Спам'], summary='Получение списка обнаруженного спама')
async def get_spam(
    request: Request,
    page: int = Query(1, ge=1),
    user: dict = Depends(require_user_api),
):
    """# Получение списка обнаруженного спама

    Возвращает постраничный список сообщений, обнаруженных как спам.

    ## Когда использовать

    Используйте этот эндпоинт для отображения таблицы обнаруженного спама в веб-панели.

    ## Требуемые права

    Запрос доступен только авторизованному пользователю.

    ## Пагинация

    Список возвращается постранично. Параметр `page` задаёт номер страницы, начиная с 1. Количество записей на странице определяется глобальной настройкой `PER_PAGE`.

    ## Успешный ответ

    Возвращает объект с массивом `items` и метаданными `pagination`.

    ## Возможные ошибки

    ### 401 Не авторизован

    Сессия не содержит данных пользователя.

    ## Особенности

    * Суперпользователь видит записи из всех чатов.
    * Обычный пользователь видит записи только из доступных ему чатов.

    Аргументы:
        request (Request): Запрос FastAPI.
        page (int): Номер страницы, начиная с 1.
        user (dict): Данные текущего пользователя.

    Возвращаемое значение:
        dict: JSON с массивом items и метаданными pagination.
    """
    per_page = await SettingsRepository.get_global('PER_PAGE', 10)
    chat_pks = await _get_accessible_chat_pks(user)

    pagination = await SpamRepository.get_spam_messages(
        chat_pks=chat_pks, page=page, per_page=per_page
    )

    items = [
        SpamMessageOut(
            id=item['id'],
            chat_id=item.get('chat_id', 0),
            message_id=item.get('message_id', 0),
            timestamp=item['timestamp'],
            author_id=item['author_id'],
            author_username=item.get('author_username'),
            message_text=item['message_text'],
            has_reply_markup=item.get('has_reply_markup'),
            cas=item.get('cas'),
            lols=item.get('lols'),
            chatgpt_prediction=item.get('chatgpt_prediction'),
            bert_prediction=item.get('bert_prediction'),
        ).model_dump()
        for item in pagination['items']
    ]

    return {
        'items': items,
        'pagination': PaginationMeta(
            current_page=pagination['current_page'],
            total_pages=pagination['total_pages'],
            total=pagination['total'],
            per_page=per_page,
        ).model_dump(),
    }


@router.get('/muted', tags=['Ограниченные пользователи'], summary='Получение списка ограниченных пользователей')
async def get_muted(
    request: Request,
    page: int = Query(1, ge=1),
    user: dict = Depends(require_user_api),
):
    """# Получение списка ограниченных пользователей

    Возвращает постраничный список пользователей, ограниченных за спам.

    ## Когда использовать

    Используйте этот эндпоинт для отображения таблицы ограниченных пользователей в веб-панели.

    ## Требуемые права

    Запрос доступен только авторизованному пользователю.

    ## Пагинация

    Список возвращается постранично. Параметр `page` задаёт номер страницы, начиная с 1. Количество записей на странице определяется глобальной настройкой `PER_PAGE`.

    ## Успешный ответ

    Возвращает объект с массивом `items` и метаданными `pagination`.

    ## Возможные ошибки

    ### 401 Не авторизован

    Сессия не содержит данных пользователя.

    ## Особенности

    * Суперпользователь видит записи из всех чатов.
    * Обычный пользователь видит записи только из доступных ему чатов.

    Аргументы:
        request (Request): Запрос FastAPI.
        page (int): Номер страницы, начиная с 1.
        user (dict): Данные текущего пользователя.

    Возвращаемое значение:
        dict: JSON с массивом items и метаданными pagination.
    """
    per_page = await SettingsRepository.get_global('PER_PAGE', 10)
    chat_pks = await _get_accessible_chat_pks(user)

    pagination = await MutedRepository.get_muted_users(
        chat_pks=chat_pks, page=page, per_page=per_page
    )

    items = [
        MutedUserOut(
            id=item['id'],
            chat_pk=item.get('chat_pk', 0),
            user_id=item['user_id'],
            username=item.get('username'),
            timestamp=item['timestamp'],
            muted_till_timestamp=item.get('muted_till_timestamp'),
            relapse_number=item.get('relapse_number', 0),
        ).model_dump()
        for item in pagination['items']
    ]

    return {
        'items': items,
        'pagination': PaginationMeta(
            current_page=pagination['current_page'],
            total_pages=pagination['total_pages'],
            total=pagination['total'],
            per_page=per_page,
        ).model_dump(),
    }


@router.get('/settings', tags=['Настройки'], summary='Получение глобальных настроек')
async def get_settings(
    request: Request,
    user: dict = Depends(require_user_api),
):
    """# Получение глобальных настроек

    Возвращает список всех глобальных настроек системы с их текущими значениями и описаниями.

    ## Когда использовать

    Используйте этот эндпоинт для отображения формы редактирования глобальных настроек в веб-панели.

    ## Требуемые права

    Запрос доступен только суперпользователю.

    ## Успешный ответ

    Возвращает объект с массивом `items`, каждый элемент содержит поля `key`, `value`, `description`, `is_global`, `chat_pk`.

    ## Возможные ошибки

    ### 401 Не авторизован

    Сессия не содержит данных пользователя.

    ### 403 Недостаточно прав

    Пользователь не является суперпользователем.

    Аргументы:
        request (Request): Запрос FastAPI.
        user (dict): Данные текущего пользователя.

    Возвращаемое значение:
        dict: JSON с массивом настроек.
    """
    if not user['is_superadmin']:
        raise HTTPException(status_code=403, detail='Недостаточно прав')

    settings = await SettingsRepository.get_all_global()

    from core.config import DEFAULT_SETTINGS
    from core.repository.settings import SETTING_DESCRIPTIONS

    items = [
        SettingOut(
            key=key,
            value=settings.get(key, DEFAULT_SETTINGS.get(key)),
            description=SETTING_DESCRIPTIONS.get(key, ''),
            is_global=True,
            chat_pk=None,
        ).model_dump()
        for key in DEFAULT_SETTINGS
    ]

    return {'items': items}


@router.get('/settings/chat/{chat_pk}', tags=['Настройки'], summary='Получение настроек чата')
async def get_chat_settings(
    request: Request,
    chat_pk: int,
    user: dict = Depends(require_user_api),
):
    """# Получение настроек чата

    Возвращает список всех настроек конкретного чата с их текущими значениями и описаниями.

    ## Когда использовать

    Используйте этот эндпоинт для отображения формы редактирования настроек конкретного чата в веб-панели.

    ## Требуемые права

    Запрос доступен только авторизованному пользователю. Суперпользователь имеет доступ ко всем чатам. Обычный пользователь имеет доступ только к чатам, которые ему назначены.

    ## Успешный ответ

    Возвращает объект с массивом `items`, каждый элемент содержит поля `key`, `value`, `description`, `is_global`, `chat_pk`.

    ## Возможные ошибки

    ### 401 Не авторизован

    Сессия не содержит данных пользователя.

    ### 403 Нет доступа к чату

    Пользователь не имеет доступа к запрошенному чату.

    Аргументы:
        request (Request): Запрос FastAPI.
        chat_pk (int): PK чата.
        user (dict): Данные текущего пользователя.

    Возвращаемое значение:
        dict: JSON с массивом настроек чата.
    """
    if not user['is_superadmin']:
        accessible = await UserRepository.get_accessible_chat_pks(user['id'])
        if chat_pk not in accessible:
            raise HTTPException(status_code=403, detail='Нет доступа к чату')

    settings = await SettingsRepository.get_all_chat_settings(chat_pk)

    from core.config import DEFAULT_SETTINGS
    from core.repository.settings import SETTING_DESCRIPTIONS

    items = [
        SettingOut(
            key=key,
            value=settings.get(key, DEFAULT_SETTINGS.get(key)),
            description=SETTING_DESCRIPTIONS.get(key, ''),
            is_global=False,
            chat_pk=chat_pk,
        ).model_dump()
        for key in DEFAULT_SETTINGS
    ]

    return {'items': items}


@router.put('/settings/global', tags=['Настройки'], summary='Обновление глобальных настроек')
async def update_global_settings(
    request: Request,
    data: SettingUpdate,
    user: dict = Depends(require_user_api),
):
    """# Обновление глобальных настроек

    Обновляет значения глобальных настроек системы.

    ## Когда использовать

    Используйте этот эндпоинт при сохранении формы редактирования глобальных настроек в веб-панели.

    ## Требуемые права

    Запрос доступен только суперпользователю.

    ## Параметры запроса

    | Поле | Тип | Обязательное | Описание |
    | --- | --- | --- | --- |
    | settings | object | Да | Объект с парами ключ-значение настроек. |

    ## Успешный ответ

    Возвращает объект `{"status": "ok"}`.

    ## Возможные ошибки

    ### 401 Не авторизован

    Сессия не содержит данных пользователя.

    ### 403 Недостаточно прав

    Пользователь не является суперпользователем.

    ## Побочные эффекты

    * Изменения вступают в силу немедленно и влияют на все чаты.

    Аргументы:
        request (Request): Запрос FastAPI.
        data (SettingUpdate): Настройки для обновления.
        user (dict): Данные текущего пользователя.
    """
    if not user['is_superadmin']:
        raise HTTPException(status_code=403, detail='Недостаточно прав')

    for key, value in data.settings.items():
        await SettingsRepository.update_global(key, value)
        logger.info(f"API: глобальная настройка '{key}' обновлена: {value}")

    return {'status': 'ok'}


@router.put('/settings/chat/{chat_pk}', tags=['Настройки'], summary='Обновление настроек чата')
async def update_chat_settings(
    request: Request,
    chat_pk: int,
    data: SettingUpdate,
    user: dict = Depends(require_user_api),
):
    """# Обновление настроек чата

    Обновляет значения настроек конкретного чата.

    ## Когда использовать

    Используйте этот эндпоинт при сохранении формы редактирования настроек чата в веб-панели.

    ## Требуемые права

    Запрос доступен только авторизованному пользователю. Суперпользователь имеет доступ ко всем чатам. Обычный пользователь имеет доступ только к чатам, которые ему назначены.

    ## Параметры запроса

    | Поле | Тип | Обязательное | Описание |
    | --- | --- | --- | --- |
    | settings | object | Да | Объект с парами ключ-значение настроек. |

    ## Успешный ответ

    Возвращает объект `{"status": "ok"}`.

    ## Возможные ошибки

    ### 401 Не авторизован

    Сессия не содержит данных пользователя.

    ### 403 Нет доступа к чату

    Пользователь не имеет доступа к запрошенному чату.

    ## Побочные эффекты

    * Изменения вступают в силу немедленно и влияют только на указанный чат.

    Аргументы:
        request (Request): Запрос FastAPI.
        chat_pk (int): PK чата.
        data (SettingUpdate): Настройки для обновления.
        user (dict): Данные текущего пользователя.
    """
    if not user['is_superadmin']:
        accessible = await UserRepository.get_accessible_chat_pks(user['id'])
        if chat_pk not in accessible:
            raise HTTPException(status_code=403, detail='Нет доступа к чату')

    for key, value in data.settings.items():
        await SettingsRepository.update_chat_setting(chat_pk, key, value)
        logger.info(f"API: настройка чата {chat_pk} '{key}' обновлена: {value}")

    return {'status': 'ok'}


@router.get('/models', tags=['Модели'], summary='Список доступных BERT-моделей')
async def get_available_models(
    request: Request,
    user: dict = Depends(require_user_api),
):
    """# Список доступных BERT-моделей

    Возвращает список BERT-моделей, обнаруженных в директории models.

    ## Когда использовать

    Используйте этот эндпоинт для отображения списка доступных моделей в веб-панели, например, в выпадающем списке при выборе модели.

    ## Требуемые права

    Запрос доступен только авторизованному пользователю.

    ## Успешный ответ

    Возвращает объект с массивом `items`, каждый элемент — строка с именем модели.

    Аргументы:
        request (Request): Запрос FastAPI.
        user (dict): Данные текущего пользователя.

    Возвращаемое значение:
        dict: JSON с массивом имён моделей.
    """
    import os
    from core.config import MODELS_DIR

    models = []
    if os.path.isdir(MODELS_DIR):
        for name in os.listdir(MODELS_DIR):
            path = os.path.join(MODELS_DIR, name)
            if os.path.isdir(path) and os.path.isfile(os.path.join(path, 'config.json')):
                models.append(name)
    models.sort()

    return {'items': models}


@router.get('/chats', tags=['Чаты'], summary='Получение списка чатов')
async def get_chats(
    request: Request,
    user: dict = Depends(require_user_api),
):
    """# Получение списка чатов

    Возвращает список чатов, доступных пользователю для управления.

    ## Когда использовать

    Используйте этот эндпоинт для отображения списка чатов в веб-панели, например, для выбора чата при редактировании настроек.

    ## Требуемые права

    Запрос доступен только авторизованному пользователю. Суперпользователь получает список всех активных чатов. Обычный пользователь получает только список чатов, которые ему назначены.

    ## Успешный ответ

    Возвращает объект с массивом `items`, каждый элемент содержит поля `pk`, `chat_id`, `title`, `is_active`.

    ## Возможные ошибки

    ### 401 Не авторизован

    Сессия не содержит данных пользователя.

    Аргументы:
        request (Request): Запрос FastAPI.
        user (dict): Данные текущего пользователя.

    Возвращаемое значение:
        dict: JSON с массивом чатов.
    """
    if user['is_superadmin']:
        chats = await ChatRepository.get_active_chats()
    else:
        chats = await UserRepository.get_user_chats(user['id'])

    items = []
    for chat in chats:
        pk = chat.get('pk', chat.get('id', 0))
        chat_users = []
        if user['is_superadmin']:
            chat_users_data = await UserRepository.get_users_by_chat_pk(pk)
            chat_users = [
                ChatUserOut(
                    id=u['id'],
                    name=u['name'],
                    telegram_id=u['telegram_id'],
                    is_superadmin=u['is_superadmin'],
                ).model_dump()
                for u in chat_users_data
            ]
        items.append(
            ChatOut(
                pk=pk,
                chat_id=chat.get('chat_id', 0),
                title=chat.get('title', chat.get('chat_title', '')),
                is_active=chat.get('is_active', True),
                users=chat_users,
            ).model_dump()
        )

    return {'items': items}


@router.post('/chats', tags=['Чаты'], summary='Добавление чата по Telegram ID')
async def add_chat(
    request: Request,
    data: ChatAddIn,
    user: dict = Depends(require_user_api),
):
    """# Добавление чата по Telegram ID

    Добавляет чат в список наблюдаемых по его Telegram ID. Перед добавлением выполняется проверка: бот должен быть участником чата и иметь права администратора.

    ## Когда использовать

    Используйте этот эндпоинт, когда нужно вручную добавить чат в систему, например, если автообнаружение не нашло чат.

    ## Требуемые права

    Запрос доступен только суперпользователю.

    ## Параметры запроса

    | Поле | Тип | Обязательное | Описание |
    | --- | --- | --- | --- |
    | chat_id | int | Да | Telegram ID чата. |

    ## Успешный ответ

    Возвращает объект с полями `pk`, `chat_id`, `title`, `is_active`.

    ## Возможные ошибки

    ### 401 Не авторизован

    Сессия не содержит данных пользователя.

    ### 403 Недостаточно прав

    Пользователь не является суперпользователем.

    ### 400 Бот не добавлен в чат

    Бот не является участником указанного чата.

    ### 400 Бот не администратор

    Бот не является администратором в указанном чате.

    ### 400 Бот недоступен

    Бот не инициализирован. Добавление чата возможно только при совместном запуске бота и панели.

    ## Побочные эффекты

    * Чат добавляется в таблицу наблюдаемых и становится активным.
    * Если чат уже существовал, но был неактивен, он снова становится активным.

    Аргументы:
        request (Request): Запрос FastAPI.
        data (ChatAddIn): Данные запроса с Telegram ID чата.
        user (dict): Данные текущего пользователя.

    Возвращаемое значение:
        dict: JSON с информацией о добавленном чате.
    """
    if not user['is_superadmin']:
        raise HTTPException(status_code=403, detail='Недостаточно прав')

    try:
        from bot.core import get_bot
        bot = get_bot()
    except RuntimeError:
        raise HTTPException(
            status_code=400,
            detail='Бот недоступен. Добавление чата возможно только при совместном запуске бота и панели.',
        )

    try:
        chat = await bot.get_chat(data.chat_id)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail='Бот не добавлен в чат или чат не существует.',
        )

    try:
        bot_info = await bot.get_me()
        member = await bot.get_chat_member(data.chat_id, bot_info.id)
        if member.status not in ('administrator', 'creator'):
            raise HTTPException(
                status_code=400,
                detail='Бот не является администратором в указанном чате.',
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=400,
            detail='Не удалось проверить права бота в чате.',
        )

    title = chat.title or str(data.chat_id)
    pk = await ChatRepository.add_chat(data.chat_id, title)
    logger.info(f"API: чат {data.chat_id} добавлен вручную: {title}")

    return ChatOut(pk=pk, chat_id=data.chat_id, title=title, is_active=True).model_dump()
