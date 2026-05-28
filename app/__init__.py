from flask import Flask, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_babel import Babel
from flask_mail import Mail

db = SQLAlchemy()
migrate = Migrate()
babel = Babel()
mail = Mail()

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

    with app.app_context():
        from app import models
        db.create_all()
    from app.routes import main
    app.register_blueprint(main)
    
    return app
