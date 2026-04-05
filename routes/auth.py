from flask import Blueprint, render_template, redirect, url_for, request, flash, session, current_app
from models import Client, Booking, TimeSlot
from extensions import db
from sqlalchemy import func
from datetime import date, timedelta
import re

auth_bp = Blueprint('auth_bp', __name__)


def current_client():
    """Return the logged-in client or None."""
    client_id = session.get('client_id')
    if client_id:
        return Client.query.get(client_id)
    return None


def _valid_email(email):
    return re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_client():
        return redirect(url_for('auth_bp.dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if not name or not email or not password:
            flash('All fields are required.', 'danger')
        elif not _valid_email(email):
            flash('Please enter a valid email address.', 'danger')
        elif len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
        elif password != confirm:
            flash('Passwords do not match.', 'danger')
        elif Client.query.filter_by(email=email).first():
            flash('An account with that email already exists.', 'danger')
        else:
            client = Client(name=name, email=email)
            client.set_password(password)
            db.session.add(client)
            db.session.commit()
            session['client_id'] = client.id
            flash(f'Welcome, {client.name}! Your account has been created.', 'success')
            return redirect(url_for('auth_bp.dashboard'))

    return render_template('auth/register.html',
                           photographer_name=current_app.config['PHOTOGRAPHER_NAME'])


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_client():
        return redirect(url_for('auth_bp.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        client = Client.query.filter_by(email=email).first()

        if client and client.check_password(password):
            session['client_id'] = client.id
            flash(f'Welcome back, {client.name}!', 'success')
            next_url = request.args.get('next')
            return redirect(next_url or url_for('auth_bp.dashboard'))

        flash('Invalid email or password.', 'danger')

    return render_template('auth/login.html',
                           photographer_name=current_app.config['PHOTOGRAPHER_NAME'])


@auth_bp.route('/logout')
def logout():
    session.pop('client_id', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('public_bp.index'))


@auth_bp.route('/dashboard')
def dashboard():
    client = current_client()
    if not client:
        return redirect(url_for('auth_bp.login', next=url_for('auth_bp.dashboard')))

    bookings = (Booking.query
                .filter(func.lower(Booking.client_email) == client.email.lower())
                .order_by(Booking.created_at.desc())
                .all())

    today = date.today()
    cancellable_ids = {
        b.id for b in bookings
        if b.status in ('pending', 'paid', 'confirmed')
        and b.slot.date >= today + timedelta(days=2)
    }

    return render_template('auth/dashboard.html',
                           client=client,
                           bookings=bookings,
                           cancellable_ids=cancellable_ids,
                           photographer_name=current_app.config['PHOTOGRAPHER_NAME'])


@auth_bp.route('/cancel/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    client = current_client()
    if not client:
        return redirect(url_for('auth_bp.login'))

    booking = Booking.query.get_or_404(booking_id)

    # Must belong to this client
    if booking.client_email.lower() != client.email.lower():
        flash('You are not authorised to cancel this booking.', 'danger')
        return redirect(url_for('auth_bp.dashboard'))

    # Must be at least 2 days away
    if booking.slot.date < date.today() + timedelta(days=2):
        flash('Cancellations must be made at least 2 days before the session.', 'danger')
        return redirect(url_for('auth_bp.dashboard'))

    if booking.status in ('cancelled',):
        flash('This booking is already cancelled.', 'danger')
        return redirect(url_for('auth_bp.dashboard'))

    booking.status = 'cancelled'
    booking.slot.is_booked = False
    db.session.commit()
    flash('Your booking has been cancelled. The time slot is now available again.', 'success')
    return redirect(url_for('auth_bp.dashboard'))
