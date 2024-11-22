from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_caching import Cache
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
cache = Cache()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    cache.init_app(app)
    
    # Set up Google Cloud credentials
    import os
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = Config.init_google_cloud_storage()
    
    # Register blueprints
    from .routes import main_bp
    app.register_blueprint(main_bp)
    
    return app
