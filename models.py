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
    annual_holiday_days = db.Column(db.Integer, default=33)
    remaining_holiday_days = db.Column(db.Integer, default=33)


class Holiday(db.Model):
    __tablename__ = 'holidays'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)
    cost = db.Column(db.Integer, nullable=False)

class Booking(db.Model):
    __tablename__ = 'booking'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Nota: 'users.id' deve corrispondere al nome della tabella e della colonna
    holiday_id = db.Column(db.Integer, db.ForeignKey('holidays.id'), nullable=False)  # Nota: 'holidays.id' deve corrispondere al nome della tabella e della colonna
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_validated = db.Column(db.Boolean, default=False)

    # Relazioni
    user = db.relationship('User', backref='bookings')
    holiday = db.relationship('Holiday', backref='bookings')




