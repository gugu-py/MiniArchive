from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_caching import Cache
from config import Config


from sqlalchemy import text

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
    from .routes import main_bp, page_not_found
    app.register_blueprint(main_bp)

    app.register_error_handler(404, page_not_found)


    # Initializes the database, creates tables, and ensures default records exist.
    from .models import Config as db_Config, Category  # Import your Config model
    from .utils import ini_users  # Assuming ini_users is in utils.py
    # print("ini1!!!")
    with app.app_context():
        db.create_all()  # Create all tables if they don't already exist

        # Ensure there is at least one Config record
        if not db_Config.query.first():
            default_config = db_Config(stopwords='')
            db.session.add(default_config)
            db.session.commit()
        Category.get_or_create_default()
        # Initialize default users or other essential data
        ini_users()
        try:
            sql = text('ALTER TABLE newspaper_issue ADD FULLTEXT INDEX idx_fulltext_content (content);')
            db.session.execute(sql)
        except:
            pass

    return app
