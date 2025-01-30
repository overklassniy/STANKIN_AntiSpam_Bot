from flask_login import UserMixin

from panel.app import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000))
    password = db.Column(db.String(1000))
    can_configure = db.Column(db.Boolean, default=False)


class SpamMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.Float, nullable=False)
    author_id = db.Column(db.BigInteger, nullable=False)
    author_username = db.Column(db.String(255), nullable=False)
    message_text = db.Column(db.Text, nullable=False)
    has_reply_markup = db.Column(db.Boolean, default=False)
    cas = db.Column(db.Boolean, default=False)
    lols = db.Column(db.Boolean, default=False)
    chatgpt_prediction = db.Column(db.Float, nullable=True)
    bert_prediction = db.Column(db.Float, nullable=True)
