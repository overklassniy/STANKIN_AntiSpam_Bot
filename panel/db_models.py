"""
Модели базы данных для панели управления.
"""

from flask_login import UserMixin
from panel.app import db


class User(UserMixin, db.Model):
    """
    Модель пользователя панели управления.
    """
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000))
    password = db.Column(db.String(1000))
    can_configure = db.Column(db.Boolean, default=False)

    def __repr__(self) -> str:
        return f"<User {self.id}: {self.name}>"


class SpamMessage(db.Model):
    """
    Модель обнаруженного спам-сообщения.
    """
    __tablename__ = 'spam_message'

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

    def __repr__(self) -> str:
        return f"<SpamMessage {self.id} от {self.author_username}>"


class MutedUser(db.Model):
    """
    Модель ограниченного пользователя.
    """
    __tablename__ = 'muted_user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.Float, nullable=False)
    muted_till_timestamp = db.Column(db.Float, nullable=True)
    relapse_number = db.Column(db.Integer, nullable=True, default=0)

    def __repr__(self) -> str:
        return f"<MutedUser {self.username} ({self.id})>"


class Setting(db.Model):
    """
    Модель настройки системы.

    Хранит настройки, которые могут быть изменены через панель управления.
    """
    __tablename__ = 'setting'

    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text, nullable=False)
    value_type = db.Column(db.String(20), nullable=False, default='str')
    description = db.Column(db.String(500), nullable=True)

    def __repr__(self) -> str:
        return f"<Setting {self.key}={self.value}>"

    def get_typed_value(self):
        """Возвращает значение с правильным типом."""
        if self.value_type == 'bool':
            return self.value.lower() in ('true', '1', 'yes')
        elif self.value_type == 'int':
            return int(self.value)
        elif self.value_type == 'float':
            return float(self.value)
        return self.value

    @classmethod
    def set_value(cls, key: str, value, value_type: str = None, description: str = None):
        """Устанавливает значение настройки."""
        if value_type is None:
            if isinstance(value, bool):
                value_type = 'bool'
            elif isinstance(value, int):
                value_type = 'int'
            elif isinstance(value, float):
                value_type = 'float'
            else:
                value_type = 'str'

        setting = cls.query.get(key)
        if setting:
            setting.value = str(value)
            if value_type:
                setting.value_type = value_type
            if description:
                setting.description = description
        else:
            setting = cls(
                key=key,
                value=str(value),
                value_type=value_type,
                description=description
            )
            db.session.add(setting)
        return setting


class CollectedMessage(db.Model):
    """
    Модель собранного сообщения.

    Хранит все сообщения для анализа (если включен сбор сообщений).
    """
    __tablename__ = 'collected_message'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.Float, nullable=False)
    chat_id = db.Column(db.BigInteger, nullable=False)
    user_id = db.Column(db.BigInteger, nullable=False)
    username = db.Column(db.String(255), nullable=True)
    message_text = db.Column(db.Text, nullable=False)

    def __repr__(self) -> str:
        return f"<CollectedMessage {self.id} from {self.user_id}>"


class WhitelistUser(db.Model):
    """
    Модель пользователя в белом списке.

    Пользователи из белого списка не проверяются на спам.
    """
    __tablename__ = 'whitelist_user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), nullable=True)
    added_at = db.Column(db.Float, nullable=False)
    added_by = db.Column(db.BigInteger, nullable=True)
    reason = db.Column(db.Text, nullable=True)

    def __repr__(self) -> str:
        return f"<WhitelistUser {self.username} ({self.id})>"
