from flask import Blueprint, render_template, current_app
from models import Service, GalleryImage

public_bp = Blueprint('public_bp', __name__)


@public_bp.route('/')
def index():
    images = GalleryImage.query.filter_by(role='gallery').order_by(GalleryImage.order, GalleryImage.uploaded_at).all()
    hero_img = GalleryImage.query.filter_by(role='hero').order_by(GalleryImage.uploaded_at).all()
    about_img = GalleryImage.query.filter_by(role='about').first()
    return render_template('index.html',
                           photographer_name=current_app.config['PHOTOGRAPHER_NAME'],
                           images=images,
                           hero_img=hero_img,
                           about_img=about_img)


@public_bp.route('/services')
def services():
    services = Service.query.filter_by(is_active=True).all()
    return render_template('services.html', services=services,
                           photographer_name=current_app.config['PHOTOGRAPHER_NAME'])
