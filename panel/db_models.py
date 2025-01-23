from flask_login import UserMixin

from panel.app import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000))
    password = db.Column(db.String(1000))
    can_configure = db.Column(db.Boolean, default=False)
