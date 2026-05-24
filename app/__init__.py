from flask import Flask

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # Register blueprints, models, etc. here
    
    return app
