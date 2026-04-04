import hashlib
import urllib.parse
import requests
from flask import Blueprint, request, current_app, render_template, redirect, url_for
from models import Booking, TimeSlot
from extensions import db, mail
from flask_mail import Message

payment_bp = Blueprint('payment_bp', __name__)


def _payfast_url(sandbox):
    if sandbox:
        return 'https://sandbox.payfast.co.za/eng/process'
    return 'https://www.payfast.co.za/eng/process'


def _generate_signature(data, passphrase=''):
    """Generate PayFast MD5 signature."""
    # Sort keys and build query string
    items = []
    for key in sorted(data.keys()):
        val = str(data[key]).strip()
        if val:
            items.append(f"{key}={urllib.parse.quote_plus(val)}")
    query = '&'.join(items)
    if passphrase:
        query += f"&passphrase={urllib.parse.quote_plus(passphrase.strip())}"
    return hashlib.md5(query.encode()).hexdigest()


def send_confirmation_emails(booking):
    photographer_name = current_app.config['PHOTOGRAPHER_NAME']
    photographer_email = current_app.config['PHOTOGRAPHER_EMAIL']
    slot = booking.slot
    service = booking.service
    date_str = slot.date.strftime('%A, %B %d, %Y')

    if service.is_full_day:
        time_str = 'Full Day (9:00 AM – 12:00 AM)'
    else:
        time_str = f"{slot.start_time.strftime('%I:%M %p')} – {slot.end_time.strftime('%I:%M %p')}"

    client_html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#f9f9f9;padding:0">
      <div style="background:#0c0c0c;padding:2rem;text-align:center">
        <h1 style="color:#c9a84c;margin:0;font-size:1.6rem">{photographer_name}</h1>
        <p style="color:#888;margin:.5rem 0 0;font-size:.85rem">Where quality matters</p>
      </div>
      <div style="background:#fff;padding:2rem">
        <h2 style="color:#222;margin-top:0">Booking Confirmed ✓</h2>
        <p style="color:#444">Hi <strong>{booking.client_name}</strong>,</p>
        <p style="color:#444">Your booking has been confirmed. We look forward to working with you!</p>

        <div style="background:#f5f5f5;border-left:4px solid #c9a84c;padding:1.2rem;border-radius:4px;margin:1.5rem 0">
          <table style="width:100%;border-collapse:collapse">
            <tr><td style="padding:.4rem 0;color:#888;width:40%"><strong>Service</strong></td><td style="color:#222">{service.name}</td></tr>
            <tr><td style="padding:.4rem 0;color:#888"><strong>Date</strong></td><td style="color:#222">{date_str}</td></tr>
            <tr><td style="padding:.4rem 0;color:#888"><strong>Time</strong></td><td style="color:#222">{time_str}</td></tr>
            <tr><td style="padding:.4rem 0;color:#888"><strong>Duration</strong></td><td style="color:#222">{service.duration} minutes</td></tr>
            <tr><td style="padding:.4rem 0;color:#888"><strong>Amount Paid</strong></td><td style="color:#c9a84c;font-weight:bold">R{service.price / 100:.2f}</td></tr>
          </table>
        </div>

        {"<p style='color:#444'><strong>Notes:</strong> " + booking.notes + "</p>" if booking.notes else ""}

        <p style="color:#444">If you have any questions or need to make changes, please reply to this email.</p>
        <p style="color:#444">See you soon!<br/><strong>{photographer_name}</strong></p>
      </div>
      <div style="background:#0c0c0c;padding:1rem;text-align:center">
        <p style="color:#555;font-size:.75rem;margin:0">&copy; {photographer_name}. All rights reserved.</p>
      </div>
    </div>
    """

    photographer_html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
      <div style="background:#0c0c0c;padding:1.5rem;text-align:center">
        <h2 style="color:#c9a84c;margin:0">New Booking Received</h2>
      </div>
      <div style="background:#fff;padding:2rem">
        <table style="width:100%;border-collapse:collapse">
          <tr style="border-bottom:1px solid #eee"><td style="padding:.6rem 0;color:#888;width:40%"><strong>Client</strong></td><td style="color:#222">{booking.client_name}</td></tr>
          <tr style="border-bottom:1px solid #eee"><td style="padding:.6rem 0;color:#888"><strong>Email</strong></td><td style="color:#222">{booking.client_email}</td></tr>
          <tr style="border-bottom:1px solid #eee"><td style="padding:.6rem 0;color:#888"><strong>Phone</strong></td><td style="color:#222">{booking.client_phone or 'Not provided'}</td></tr>
          <tr style="border-bottom:1px solid #eee"><td style="padding:.6rem 0;color:#888"><strong>Service</strong></td><td style="color:#222">{service.name}</td></tr>
          <tr style="border-bottom:1px solid #eee"><td style="padding:.6rem 0;color:#888"><strong>Date</strong></td><td style="color:#222">{date_str}</td></tr>
          <tr style="border-bottom:1px solid #eee"><td style="padding:.6rem 0;color:#888"><strong>Time</strong></td><td style="color:#222">{time_str}</td></tr>
          <tr style="border-bottom:1px solid #eee"><td style="padding:.6rem 0;color:#888"><strong>Amount</strong></td><td style="color:#222;font-weight:bold">R{service.price / 100:.2f}</td></tr>
          <tr><td style="padding:.6rem 0;color:#888"><strong>Notes</strong></td><td style="color:#222">{booking.notes or 'None'}</td></tr>
        </table>
      </div>
    </div>
    """

    try:
        mail.send(Message(
            subject=f'Booking Confirmed – {service.name} | {date_str}',
            recipients=[booking.client_email],
            html=client_html
        ))
    except Exception as e:
        current_app.logger.error(f'Failed to send client email: {e}')

    if photographer_email:
        try:
            mail.send(Message(
                subject=f'New Booking – {booking.client_name} | {date_str}',
                recipients=[photographer_email],
                html=photographer_html
            ))
        except Exception as e:
            current_app.logger.error(f'Failed to send photographer email: {e}')


def _fulfill_booking(booking_id):
    booking = Booking.query.get(int(booking_id))
    if not booking or booking.status == 'paid':
        return
    booking.status = 'paid'
    slot = TimeSlot.query.get(booking.slot_id)
    if slot:
        slot.is_booked = True
    db.session.commit()
    send_confirmation_emails(booking)


@payment_bp.route('/itn', methods=['POST'])
def itn():
    """PayFast Instant Transaction Notification (webhook equivalent)."""
    data = request.form.to_dict()
    sandbox = current_app.config['PAYFAST_SANDBOX']
    passphrase = current_app.config['PAYFAST_PASSPHRASE']

    # Verify signature
    sig_received = data.pop('signature', '')
    expected_sig = _generate_signature(data, passphrase)
    if sig_received != expected_sig:
        return 'Invalid signature', 400

    # Verify with PayFast server
    verify_url = 'https://sandbox.payfast.co.za/eng/query/validate' if sandbox else 'https://www.payfast.co.za/eng/query/validate'
    try:
        verify_resp = requests.post(verify_url, data=request.form.to_dict(), timeout=10)
        if verify_resp.text.upper().strip() != 'VALID':
            return 'Invalid ITN', 400
    except Exception:
        return 'Verification error', 400

    if data.get('payment_status') == 'COMPLETE':
        booking_id = data.get('custom_int1')
        if booking_id:
            _fulfill_booking(booking_id)

    return '', 200


@payment_bp.route('/success')
def success():
    booking_id = request.args.get('booking_id')
    booking = None
    if booking_id:
        booking = Booking.query.get(int(booking_id))
        # Fulfil here as fallback if ITN hasn't fired yet
        if booking and booking.status == 'pending':
            _fulfill_booking(booking_id)
            db.session.refresh(booking)
    return render_template('confirmation.html', booking=booking,
                           photographer_name=current_app.config['PHOTOGRAPHER_NAME'])


@payment_bp.route('/cancel')
def cancel():
    return redirect(url_for('booking_bp.index'))
