from flask import Flask
from extensions import db, login_manager, mail
from config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    login_manager.login_view = 'admin_bp.login'

    from routes.public import public_bp
    from routes.booking import booking_bp
    from routes.payment import payment_bp
    from routes.admin import admin_bp
    from routes.auth import auth_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(booking_bp, url_prefix='/booking')
    app.register_blueprint(payment_bp, url_prefix='/payment')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(auth_bp, url_prefix='/account')

    with app.app_context():
        db.create_all()
        _seed_defaults()

    return app


def _seed_defaults():
    from models import Admin, Service

    if not Admin.query.first():
        admin = Admin(username='admin')
        admin.set_password('admin123')
        db.session.add(admin)

    if not Service.query.first():
        services = [
            Service(
                name='Portrait Session',
                description='1-hour studio portrait session. Perfect for headshots, family, or individual portraits. Includes 10 edited digital images.',
                price=2500,
                duration=60,
            ),
            Service(
                name='Couples Session',
                description='2-hour outdoor or studio session for couples. Romantic and relaxed atmosphere. Includes 20 edited digital images.',
                price=3500,
                duration=120,
            ),
            Service(
                name='Event Coverage',
                description='Full-day event coverage up to 8 hours. Weddings, birthdays, corporate events. Includes 100+ edited digital images.',
                price=10000,
                duration=480,
            ),
        ]
        for s in services:
            db.session.add(s)

    db.session.commit()


@login_manager.user_loader
def load_user(user_id):
    from models import Admin
    return Admin.query.get(int(user_id))


app = create_app()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
