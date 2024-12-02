from extensions import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    credits = db.Column(db.Integer, default=100)  # Default iniziale per i crediti
    is_admin = db.Column(db.Boolean, default=False)

    # Nuovi campi
    annual_holiday_days = db.Column(db.Integer, default=33)  # Giorni di ferie di diritto annuale
    remaining_holiday_days = db.Column(db.Integer, default=33)  # Giorni di ferie residui


class Holiday(db.Model):
    __tablename__ = 'holidays'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)
    cost = db.Column(db.Integer, nullable=False)

class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    holiday_id = db.Column(db.Integer, db.ForeignKey('holidays.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


