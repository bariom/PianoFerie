from extensions import db
from datetime import datetime
from flask_login import UserMixin

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    credits = db.Column(db.Integer, default=410)
    annual_holiday_days = db.Column(db.Float, default=33.0)  # Cambiato da Integer a Float
    remaining_holiday_days = db.Column(db.Float, default=33.0)  # Cambiato da Integer a Float


class Holiday(db.Model):
    __tablename__ = 'holidays'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)
    cost = db.Column(db.Integer, nullable=False)

class Booking(db.Model):
    __tablename__ = 'booking'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Collegamento con User
    holiday_id = db.Column(db.Integer, db.ForeignKey('holidays.id'), nullable=False)  # Collegamento con Holiday
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_validated = db.Column(db.Boolean, default=False)
    is_half_day = db.Column(db.Boolean, default=False)  # True se è una mezza giornata
    session = db.Column(db.String(10), nullable=True)  # 'morning' o 'afternoon' per mezze giornate

    # Relazioni
    user = db.relationship('User', backref='bookings')
    holiday = db.relationship('Holiday', backref='bookings')

    def __repr__(self):
        return f'<Booking ID={self.id}, User={self.user_id}, Holiday={self.holiday_id}, HalfDay={self.is_half_day}, Session={self.session}>'





