from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models import Admin, Service, TimeSlot, Booking, GalleryImage, AvailableDate
from extensions import db
from datetime import datetime, date, timedelta
from werkzeug.utils import secure_filename
import os

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'gif'}
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB per image

def _allowed(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


admin_bp = Blueprint('admin_bp', __name__)


# ── Login / Logout ──

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_bp.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Username and password are required.', 'danger')
        else:
            admin = Admin.query.filter_by(username=username).first()
            if admin and admin.check_password(password):
                login_user(admin)
                return redirect(url_for('admin_bp.dashboard'))
            flash('Invalid username or password.', 'danger')

    return render_template('admin/login.html',
                           photographer_name=current_app.config['PHOTOGRAPHER_NAME'])


@admin_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('admin_bp.login'))


# ── Dashboard ──

@admin_bp.route('/')
@admin_bp.route('/dashboard')
@login_required
def dashboard():
    today = date.today()
    upcoming = (Booking.query
                .join(TimeSlot)
                .filter(TimeSlot.date >= today, Booking.status == 'paid')
                .order_by(TimeSlot.date, TimeSlot.start_time)
                .limit(10).all())
    total_paid = Booking.query.filter_by(status='paid').count()
    total_pending = Booking.query.filter_by(status='pending').count()
    return render_template('admin/dashboard.html',
                           upcoming=upcoming,
                           total_paid=total_paid,
                           total_pending=total_pending,
                           photographer_name=current_app.config['PHOTOGRAPHER_NAME'])


# ── Bookings ──

@admin_bp.route('/bookings')
@login_required
def bookings():
    status_filter = request.args.get('status', '')
    valid_statuses = {'paid', 'pending', 'cancelled', 'confirmed'}
    if status_filter and status_filter not in valid_statuses:
        status_filter = ''
    query = Booking.query.join(TimeSlot).order_by(TimeSlot.date.desc(), TimeSlot.start_time.desc())
    if status_filter:
        query = query.filter(Booking.status == status_filter)
    all_bookings = query.all()
    return render_template('admin/bookings.html', bookings=all_bookings,
                           status_filter=status_filter,
                           photographer_name=current_app.config['PHOTOGRAPHER_NAME'])


@admin_bp.route('/bookings/<int:booking_id>/accept', methods=['POST'])
@login_required
def accept_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.status != 'pending':
        flash('Only pending bookings can be accepted.', 'danger')
    else:
        booking.status = 'confirmed'
        booking.slot.is_booked = True
        db.session.commit()
        flash(f'Booking #{booking.id} confirmed — slot locked in.', 'success')
    return redirect(url_for('admin_bp.bookings'))


@admin_bp.route('/bookings/<int:booking_id>/cancel', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.status == 'cancelled':
        flash('Booking is already cancelled.', 'danger')
    else:
        booking.status = 'cancelled'
        booking.slot.is_booked = False
        db.session.commit()
        flash('Booking cancelled and slot reopened.', 'success')
    return redirect(url_for('admin_bp.bookings'))


# ── Date Detail ──

@admin_bp.route('/date/<string:date_str>')
@login_required
def date_detail(date_str):
    try:
        chosen_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date.', 'danger')
        return redirect(url_for('admin_bp.availability'))

    bookings = (Booking.query
                .join(TimeSlot)
                .filter(TimeSlot.date == chosen_date)
                .order_by(TimeSlot.start_time)
                .all())
    return render_template('admin/date_detail.html',
                           chosen_date=chosen_date,
                           bookings=bookings,
                           photographer_name=current_app.config['PHOTOGRAPHER_NAME'])


# ── Availability ──

@admin_bp.route('/availability')
@login_required
def availability():
    today = date.today()
    open_dates = AvailableDate.query.filter(AvailableDate.date >= today).order_by(AvailableDate.date).all()
    # For each open date, count how many hours are booked
    booked_counts = {}
    for ad in open_dates:
        booked_counts[ad.id] = TimeSlot.query.filter_by(date=ad.date, is_booked=True).count()
    return render_template('admin/availability.html',
                           open_dates=open_dates,
                           booked_counts=booked_counts,
                           today=date.today().isoformat(),
                           photographer_name=current_app.config['PHOTOGRAPHER_NAME'])


@admin_bp.route('/availability/add', methods=['POST'])
@login_required
def add_slot():
    date_str = request.form.get('date', '').strip()
    bulk_days = request.form.get('bulk_days', '').strip()

    if not date_str:
        flash('Date is required.', 'danger')
        return redirect(url_for('admin_bp.availability'))

    try:
        chosen_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date format.', 'danger')
        return redirect(url_for('admin_bp.availability'))

    if chosen_date < date.today():
        flash('Cannot add past dates.', 'danger')
        return redirect(url_for('admin_bp.availability'))

    bulk = 1
    if bulk_days:
        try:
            bulk = int(bulk_days)
            if bulk < 1 or bulk > 90:
                raise ValueError
        except ValueError:
            flash('Repeat days must be between 1 and 90.', 'danger')
            return redirect(url_for('admin_bp.availability'))

    added = 0
    for i in range(bulk):
        d = chosen_date + timedelta(days=i)
        if not AvailableDate.query.filter_by(date=d).first():
            db.session.add(AvailableDate(date=d))
            added += 1

    db.session.commit()
    flash(f'{added} date(s) opened. Clients can now book 9:00 AM – 12:00 AM hourly.', 'success')
    return redirect(url_for('admin_bp.availability'))


@admin_bp.route('/availability/delete/<int:date_id>', methods=['POST'])
@login_required
def delete_slot(date_id):
    available = AvailableDate.query.get_or_404(date_id)
    booked = TimeSlot.query.filter_by(date=available.date, is_booked=True).count()
    if booked:
        flash(f'Cannot remove this date — {booked} booking(s) exist. Cancel them first.', 'danger')
    else:
        db.session.delete(available)
        db.session.commit()
        flash('Date removed.', 'success')
    return redirect(url_for('admin_bp.availability'))


# ── Services ──

@admin_bp.route('/services')
@login_required
def services():
    all_services = Service.query.all()
    return render_template('admin/services.html', services=all_services,
                           photographer_name=current_app.config['PHOTOGRAPHER_NAME'])


@admin_bp.route('/services/add', methods=['POST'])
@login_required
def add_service():
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    price_str = request.form.get('price', '').strip()
    duration_str = request.form.get('duration', '').strip()

    errors = []
    if not name:
        errors.append('Service name is required.')
    elif len(name) > 100:
        errors.append('Service name must be 100 characters or fewer.')
    if not description:
        errors.append('Description is required.')
    if not price_str:
        errors.append('Price is required.')
    if not duration_str:
        errors.append('Duration is required.')

    if errors:
        for e in errors:
            flash(e, 'danger')
        return redirect(url_for('admin_bp.services'))

    try:
        price_cents = int(round(float(price_str) * 100))
        if price_cents <= 0:
            raise ValueError
    except ValueError:
        flash('Price must be a positive number.', 'danger')
        return redirect(url_for('admin_bp.services'))

    try:
        duration_min = int(duration_str)
        if duration_min < 15 or duration_min > 1440:
            raise ValueError
    except ValueError:
        flash('Duration must be between 15 and 1440 minutes.', 'danger')
        return redirect(url_for('admin_bp.services'))

    is_full_day = request.form.get('is_full_day') == '1'
    db.session.add(Service(name=name, description=description,
                           price=price_cents, duration=duration_min,
                           is_full_day=is_full_day))
    db.session.commit()
    flash('Service added successfully.', 'success')
    return redirect(url_for('admin_bp.services'))


@admin_bp.route('/services/toggle/<int:service_id>', methods=['POST'])
@login_required
def toggle_service(service_id):
    service = Service.query.get_or_404(service_id)
    service.is_active = not service.is_active
    db.session.commit()
    flash(f"Service {'activated' if service.is_active else 'deactivated'}.", 'success')
    return redirect(url_for('admin_bp.services'))


@admin_bp.route('/services/delete/<int:service_id>', methods=['POST'])
@login_required
def delete_service(service_id):
    service = Service.query.get_or_404(service_id)
    if service.bookings:
        flash('Cannot delete a service that has existing bookings. Deactivate it instead.', 'danger')
    else:
        db.session.delete(service)
        db.session.commit()
        flash('Service deleted.', 'success')
    return redirect(url_for('admin_bp.services'))


# ── Gallery ──

@admin_bp.route('/gallery')
@login_required
def gallery():
    images = GalleryImage.query.order_by(GalleryImage.order, GalleryImage.uploaded_at).all()
    return render_template('admin/gallery.html', images=images,
                           photographer_name=current_app.config['PHOTOGRAPHER_NAME'])


@admin_bp.route('/gallery/upload', methods=['POST'])
@login_required
def upload_image():
    files = request.files.getlist('images')
    caption = request.form.get('caption', '').strip()

    if not files or all(f.filename == '' for f in files):
        flash('Please select at least one image to upload.', 'danger')
        return redirect(url_for('admin_bp.gallery'))

    if len(caption) > 200:
        flash('Caption must be 200 characters or fewer.', 'danger')
        return redirect(url_for('admin_bp.gallery'))

    upload_dir = os.path.join(current_app.root_path, 'static', 'images')
    os.makedirs(upload_dir, exist_ok=True)

    uploaded = 0
    rejected = []
    for f in files:
        if not f or not f.filename:
            continue
        if not _allowed(f.filename):
            rejected.append(f'{f.filename} (unsupported format)')
            continue
        # Check file size
        f.seek(0, 2)
        size = f.tell()
        f.seek(0)
        if size > MAX_IMAGE_BYTES:
            rejected.append(f'{f.filename} (exceeds 10 MB limit)')
            continue

        filename = secure_filename(f.filename)
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(os.path.join(upload_dir, filename)):
            filename = f'{base}_{counter}{ext}'
            counter += 1

        f.save(os.path.join(upload_dir, filename))
        db.session.add(GalleryImage(filename=filename, caption=caption))
        uploaded += 1

    db.session.commit()

    if uploaded:
        flash(f'{uploaded} image(s) uploaded successfully.', 'success')
    if rejected:
        flash(f'Skipped: {", ".join(rejected)}', 'danger')

    return redirect(url_for('admin_bp.gallery'))


@admin_bp.route('/gallery/setrole/<int:image_id>', methods=['POST'])
@login_required
def set_image_role(image_id):
    role = request.form.get('role', 'gallery')
    if role not in ('gallery', 'hero', 'about'):
        flash('Invalid role.', 'danger')
        return redirect(url_for('admin_bp.gallery'))
    # For 'about', only one image allowed — clear existing
    if role == 'about':
        GalleryImage.query.filter_by(role='about').update({'role': 'gallery'})
    img = GalleryImage.query.get_or_404(image_id)
    img.role = role
    db.session.commit()
    flash(f'Image set as {"Hero" if role == "hero" else "About"} photo.', 'success')
    return redirect(url_for('admin_bp.gallery'))


@admin_bp.route('/gallery/delete/<int:image_id>', methods=['POST'])
@login_required
def delete_image(image_id):
    img = GalleryImage.query.get_or_404(image_id)
    filepath = os.path.join(current_app.root_path, 'static', 'images', img.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    db.session.delete(img)
    db.session.commit()
    flash('Image deleted.', 'success')
    return redirect(url_for('admin_bp.gallery'))
