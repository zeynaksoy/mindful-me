from flask import Flask, request, session, render_template
import os
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_babel import Babel
from flask_mail import Mail
from flask_apscheduler import APScheduler

db = SQLAlchemy()
migrate = Migrate()
babel = Babel()
mail = Mail()
scheduler = APScheduler()

def get_locale():
    if 'language' in session:
        return session['language']
    return request.accept_languages.best_match(['tr', 'en'])

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object('config.Config')

    db.init_app(app)
    migrate.init_app(app, db)
    babel.init_app(app, locale_selector=get_locale)
    mail.init_app(app)
    scheduler.init_app(app)
    
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        scheduler.start()

    with app.app_context():
        from app import models
        db.create_all()
        
        # Sadece debug (geliştirme) modunda otomatik migration ve upgrade
        if app.config.get('DEBUG') or app.debug:
            try:
                from flask_migrate import upgrade, migrate as db_migrate
                db_migrate(message="Auto-migration on startup")
                upgrade()
                print("✅ Veritabanı şeması otomatik olarak kontrol edildi ve güncellendi.")
            except Exception as e:
                print("⚠️ Otomatik migration sırasında bir bilgi/hata (Zaten güncel olabilir):", e)

    from app.routes import main
    app.register_blueprint(main)
    
    # Global Hata Yoneticileri
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500
    
    return app
