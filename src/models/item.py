from db import db

class memberModel(db.Model):
    __tablename__ = "Members"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), unique=True, nullable=False)
    email_address = db.Column(db.String(40), unique=True, nullable=False)
    phone_number = db.Column(db.Integer, nullable=True)
    birthday = db.Column(db.DateTime, nullable=True)
    age_group = db.Column(db.String(20), nullable=False)