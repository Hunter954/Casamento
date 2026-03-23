import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///wedding.db').replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_DIR'] = os.getenv('UPLOAD_DIR', os.path.join(app.root_path, 'static', 'uploads'))
    app.config['ADMIN_EMAIL'] = os.getenv('ADMIN_EMAIL', 'admin@casamento.com')
    app.config['ADMIN_PASSWORD'] = os.getenv('ADMIN_PASSWORD', '123456')
    app.config['MERCADO_PAGO_ACCESS_TOKEN'] = os.getenv('MERCADO_PAGO_ACCESS_TOKEN', '')
    app.config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', '')
    app.config['WHATSAPP_SENDER_NUMBER'] = os.getenv('WHATSAPP_SENDER_NUMBER', '')

    os.makedirs(app.config['UPLOAD_DIR'], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'admin.login'
    migrate.init_app(app, db)

    from .models import AdminUser, SiteSettings

    @login_manager.user_loader
    def load_user(user_id):
        return AdminUser.query.get(int(user_id))

    from .public.routes import public_bp
    from .admin.routes import admin_bp
    from .api.routes import api_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')

    @app.context_processor
    def inject_global_settings():
        settings = SiteSettings.query.first()
        return {'site_settings': settings}

    return app
