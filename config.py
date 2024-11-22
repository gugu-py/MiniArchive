import os
from google.cloud import storage

class Config:
    # Example database URI for SQLAlchemy
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://username:password@/database_name?unix_socket=/cloudsql/project-id:region:instance-name"
    # Example for local development
    # SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:password@localhost:3306/database_name'

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Use a securely generated secret key for session encryption
    SECRET_KEY = os.urandom(24)

    # Replace with your Google Cloud Storage bucket name
    CLOUD_STORAGE_BUCKET = 'your-bucket-name'

    # Caching configuration
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 1000

    # Security settings
    csrf_enabled = True
    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript from accessing cookies
    SESSION_COOKIE_SECURE = True    # Ensure cookies are sent only over HTTPS
    SESSION_COOKIE_SAMESITE = 'Strict'  # Options: 'Strict' or 'Lax'

    # File link expiration time in minutes (adjust as needed, must be > 1)
    FILE_LINK_EXPIRE_TIME_MIN = 5

    # Preferred URL scheme
    PREFERRED_URL_SCHEME = 'https'

    # Admin credentials for local testing (replace with environment variables in production)
    ADMIN_USERNAME = 'admin'
    ADMIN_PASSWORD = 'adminadmin'

    @classmethod
    def init_google_cloud_storage(cls):
        """
        Initialize Google Cloud Storage client.
        Replace 'path-to-service-account.json' with the path to your service account JSON file.
        """
        service_account_file = 'path-to-service-account.json'  # Specify your JSON key file
        cls.storage_client = storage.Client.from_service_account_json(service_account_file)
        
        # Replace with your bucket name
        cls.bucket = cls.storage_client.bucket(cls.CLOUD_STORAGE_BUCKET)

        return service_account_file
