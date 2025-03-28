from flask_login import UserMixin
from panel.app import db
from utils.basic import logger


class User(UserMixin, db.Model):
    """
    Модель пользователя.

    Аргументы:
        id (int): Первичный ключ.
        name (str): Имя пользователя.
        password (str): Хэшированный пароль пользователя.
        can_configure (bool): Флаг, указывающий, может ли пользователь настраивать систему.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000))
    password = db.Column(db.String(1000))
    can_configure = db.Column(db.Boolean, default=False)

    def __init__(self, *args, **kwargs) -> None:
        """
        Инициализирует объект пользователя.
        """
        super().__init__(*args, **kwargs)
        logger.info("Создан новый объект User: %s", self)

    def __repr__(self) -> str:
        """
        Возвращает строковое представление объекта пользователя.
        """
        return f"<User {self.id}: {self.name}>"


class SpamMessage(db.Model):
    """
    Модель спам-сообщения.

    Аргументы:
        id (int): Первичный ключ.
        timestamp (float): Метка времени сообщения.
        author_id (int): Идентификатор автора сообщения.
        author_username (str): Имя пользователя автора сообщения.
        message_text (str): Текст сообщения.
        has_reply_markup (bool, optional): Наличие inline-клавиатуры.
        cas (bool, optional): Флаг, указывающий на бан в CAS.
        lols (bool, optional): Флаг, указывающий на бан в LOLS.
        chatgpt_prediction (float, optional): Вердикт ChatGPT.
        bert_prediction (float, optional): Вердикт RuBert.
    """
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.Float, nullable=False)
    author_id = db.Column(db.BigInteger, nullable=False)
    author_username = db.Column(db.String(255), nullable=True)
    message_text = db.Column(db.Text, nullable=False)
    has_reply_markup = db.Column(db.Boolean, nullable=True)
    cas = db.Column(db.Boolean, nullable=True)
    lols = db.Column(db.Boolean, nullable=True)
    chatgpt_prediction = db.Column(db.Float, nullable=True)
    bert_prediction = db.Column(db.Float, nullable=True)

    def __init__(self, *args, **kwargs) -> None:
        """
        Инициализирует объект спам-сообщения.
        """
        super().__init__(*args, **kwargs)
        logger.info("Создан новый объект SpamMessage: %s", self)

    def __repr__(self) -> str:
        """
        Возвращает строковое представление объекта спам-сообщения.
        """
        return f"<SpamMessage {self.id} от {self.author_username}>"


class MutedUser(db.Model):
    """
    Модель ограниченного пользователя.

    Аргументы:
        id (int): Первичный ключ.
        muted_till_timestamp (float): Метка времени окончания блокировки.
        relapse_number (int, optional): Номер рецидива (по умолчанию 0).
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.Float, nullable=False)
    muted_till_timestamp = db.Column(db.Float, nullable=True)
    relapse_number = db.Column(db.Integer, nullable=True, default=0)

    def __init__(self, *args, **kwargs) -> None:
        """
        Инициализирует объект ограниченного пользователя.
        """
        super().__init__(*args, **kwargs)
        logger.info("Создан новый объект MutedUser: %s", self)

    def __repr__(self) -> str:
        """
        Возвращает строковое представление объекта ограниченного пользователя.
        """
        return f"<MutedUser {self.username} ({self.id}), заблокирован до {self.muted_till_timestamp}, рецидивов: {self.relapse_number}>"
