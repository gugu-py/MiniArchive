from application import create_app, db
from application.models import Config  # Import your Config model
from application.utils import ini_users  # Assuming ini_users is in utils.py

app = create_app()

def initialize_database():
    """
    Initializes the database, creates tables, and ensures default records exist.
    """
    with app.app_context():
        db.create_all()  # Create all tables if they don't already exist
        
        # Ensure there is at least one Config record
        if not Config.query.first():
            default_config = Config(stopwords='')
            db.session.add(default_config)
            db.session.commit()
        
        # Initialize default users or other essential data
        ini_users()

if __name__ == "__main__":
    # Initialize the database before running the app
    initialize_database()
    
    # Run the app
    app.run(debug=True)
