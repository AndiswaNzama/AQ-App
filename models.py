from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Integer, nullable=False)   # in cents
    duration = db.Column(db.Integer, nullable=False)  # in minutes
    is_active = db.Column(db.Boolean, default=True)
    is_full_day = db.Column(db.Boolean, default=False)
    bookings = db.relationship('Booking', backref='service', lazy=True)


class TimeSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_booked = db.Column(db.Boolean, default=False)
    booking = db.relationship('Booking', backref='slot', uselist=False, lazy=True)


class AvailableDate(db.Model):
    """Dates the photographer is open for bookings."""
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)


class GalleryImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    caption = db.Column(db.String(200))
    order = db.Column(db.Integer, default=0)
    role = db.Column(db.String(20), default='gallery')  # gallery, hero, about
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)


class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(100), nullable=False)
    client_email = db.Column(db.String(120), nullable=False)
    client_phone = db.Column(db.String(20))
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey('time_slot.id'), nullable=False)
    stripe_session_id = db.Column(db.String(200))
    stripe_payment_intent = db.Column(db.String(200))
    status = db.Column(db.String(20), default='pending')  # pending, paid, cancelled
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
