import hashlib
import urllib.parse
from flask import Blueprint, render_template, request, jsonify, current_app, url_for
from models import Service, TimeSlot, Booking, AvailableDate
from extensions import db
from datetime import date, datetime, time

booking_bp = Blueprint('booking_bp', __name__)

HOUR_START = 9
HOUR_END = 23


def _payfast_signature(data, passphrase=''):
    items = []
    for key in sorted(data.keys()):
        val = str(data[key]).strip()
        if val:
            items.append(f"{key}={urllib.parse.quote_plus(val)}")
    query = '&'.join(items)
    if passphrase:
        query += f"&passphrase={urllib.parse.quote_plus(passphrase.strip())}"
    return hashlib.md5(query.encode()).hexdigest()


@booking_bp.route('/')
def index():
    services = Service.query.filter_by(is_active=True).all()
    selected_service_id = request.args.get('service_id', type=int)
    return render_template('booking.html', services=services,
                           selected_service_id=selected_service_id,
                           photographer_name=current_app.config['PHOTOGRAPHER_NAME'],)


@booking_bp.route('/available-dates')
def available_dates():
    today = date.today()
    dates = AvailableDate.query.filter(AvailableDate.date >= today).all()
    return jsonify([str(d.date) for d in dates])


@booking_bp.route('/available-slots')
def available_slots():
    date_str = request.args.get('date')
    service_id = request.args.get('service_id', type=int)
    if not date_str:
        return jsonify([])
    try:
        chosen_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify([])

    if not AvailableDate.query.filter_by(date=chosen_date).first():
        return jsonify([])

    # Full-day service — check if day is already taken by any full-day booking
    if service_id:
        service = Service.query.get(service_id)
        if service and service.is_full_day:
            full_day_taken = TimeSlot.query.filter_by(
                date=chosen_date, start_time=time(0, 0), is_booked=True
            ).first()
            return jsonify({'full_day': True, 'available': not full_day_taken})

    # Hourly: hide dates fully booked by a full-day booking
    full_day_taken = TimeSlot.query.filter_by(
        date=chosen_date, start_time=time(0, 0), is_booked=True
    ).first()

    booked_hours = {
        s.start_time.hour
        for s in TimeSlot.query.filter_by(date=chosen_date, is_booked=True).all()
    }

    slots = []
    for h in range(HOUR_START, HOUR_END + 1):
        end_h = h + 1 if h < 23 else 0
        slots.append({
            'hour': h,
            'start': time(h, 0).strftime('%I:%M %p').lstrip('0'),
            'end': '12:00 AM' if h == 23 else time(end_h, 0).strftime('%I:%M %p').lstrip('0'),
            'booked': h in booked_hours or bool(full_day_taken),
        })

    return jsonify(slots)


@booking_bp.route('/create', methods=['POST'])
def create():
    data = request.get_json()
    service_id = data.get('service_id')
    date_str = data.get('date')
    hour = data.get('hour')
    client_name = data.get('client_name', '').strip()
    client_email = data.get('client_email', '').strip().lower()
    client_phone = data.get('client_phone', '').strip()
    notes = data.get('notes', '').strip()

    if not all([service_id, date_str, client_name, client_email]):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        chosen_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid date.'}), 400

    service = Service.query.get(service_id)
    if not service:
        return jsonify({'error': 'Invalid service.'}), 400

    if not AvailableDate.query.filter_by(date=chosen_date).first():
        return jsonify({'error': 'That date is not available.'}), 400

    # Full-day booking uses start_time=00:00 as a sentinel
    if service.is_full_day:
        start_time = time(0, 0)
        end_time = time(23, 59)
        existing = TimeSlot.query.filter_by(date=chosen_date, start_time=start_time, is_booked=True).first()
        if existing:
            return jsonify({'error': 'This date is already fully booked.'}), 409
    else:
        try:
            hour = int(data.get('hour'))
            if hour < HOUR_START or hour > HOUR_END:
                raise ValueError
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid time selected.'}), 400
        start_time = time(hour, 0)
        end_time = time(0, 0) if hour == 23 else time(hour + 1, 0)
        existing = TimeSlot.query.filter_by(date=chosen_date, start_time=start_time, is_booked=True).first()
        if existing:
            return jsonify({'error': 'This time has just been booked. Please choose another.'}), 409

    slot = TimeSlot.query.filter_by(date=chosen_date, start_time=start_time).first()
    if not slot:
        slot = TimeSlot(date=chosen_date, start_time=start_time, end_time=end_time)
        db.session.add(slot)
        db.session.flush()

    booking = Booking(
        client_name=client_name,
        client_email=client_email,
        client_phone=client_phone,
        service_id=service_id,
        slot_id=slot.id,
        notes=notes,
        status='pending',
    )
    db.session.add(booking)
    db.session.flush()
    db.session.commit()

    # Build PayFast redirect
    cfg = current_app.config
    base_url = cfg['BASE_URL']
    amount = f"{service.price / 100:.2f}"
    sandbox = cfg['PAYFAST_SANDBOX']

    pf_data = {
        'merchant_id': cfg['PAYFAST_MERCHANT_ID'],
        'merchant_key': cfg['PAYFAST_MERCHANT_KEY'],
        'return_url': f"{base_url}/payment/success?booking_id={booking.id}",
        'cancel_url': f"{base_url}/payment/cancel",
        'notify_url': f"{base_url}/payment/itn",
        'name_first': client_name.split()[0],
        'name_last': client_name.split()[-1] if len(client_name.split()) > 1 else '',
        'email_address': client_email,
        'amount': amount,
        'item_name': service.name,
        'item_description': f"{chosen_date.strftime('%B %d, %Y')} at {start_time.strftime('%I:%M %p')}",
        'custom_int1': booking.id,
    }

    # Remove empty values
    pf_data = {k: v for k, v in pf_data.items() if str(v).strip()}

    pf_data['signature'] = _payfast_signature(pf_data, cfg['PAYFAST_PASSPHRASE'])

    payfast_url = 'https://sandbox.payfast.co.za/eng/process' if sandbox else 'https://www.payfast.co.za/eng/process'
    query_string = urllib.parse.urlencode(pf_data)
    checkout_url = f"{payfast_url}?{query_string}"

    return jsonify({'checkout_url': checkout_url})
