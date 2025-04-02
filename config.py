import os
from google.cloud import storage

class Config:
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://admin:admin_password@localhost:3306/newspaper' # your database URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.urandom(24)
    CLOUD_STORAGE_BUCKET = 'Bucket_name' # your google cloud storage bucket name
    CACHE_TYPE='SimpleCache'
    CACHE_DEFAULT_TIMEOUT=1000
    csrf_enabled = True
    # Other configurations:
    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript from accessing cookies
    SESSION_COOKIE_SECURE = True    # Ensure cookies are sent only over HTTPS
    # Optionally, set the SESSION_COOKIE_SAMESITE attribute
    SESSION_COOKIE_SAMESITE = 'Strict'  # or 'Lax' depending on your needs
    FILE_LINK_EXPIRE_TIME_SEC = 666 # should greater than 1
    PREFERRED_URL_SCHEME = 'https'

    ADMIN_USERNAME = 'admin'
    ADMIN_PASSWORD = 'adminadmin' # your admin password

    CLOUDFLARE_PROXY_WORKER_URL = "https://worker.workers.dev/generate-link" # your cloudflare file proxy worker url

    @classmethod
    def init_google_cloud_storage(cls):
        # Specify the path to your service account JSON file
        service_account_file = 'path_to_service_account.json'

        # Initialize the Google Cloud Storage client with the service account
        cls.storage_client = storage.Client.from_service_account_json(service_account_file)
        cls.bucket = cls.storage_client.bucket(cls.CLOUD_STORAGE_BUCKET)

        return service_account_file
