from flask import redirect, url_for, flash, current_app
from flask_login import current_user
from werkzeug.security import generate_password_hash
import uuid
from google.cloud import storage
from sqlalchemy import func
import datetime
from functools import wraps
import markdown
from datetime import timedelta

from . import cache
from .models import db, User, NewspaperIssue, Config
from .forms import *

def generate_random_filename() -> str:
    """
    Generates a random filename using the first 16 characters of a UUID.

    Returns:
        str: A randomly generated filename.
    """
    return str(uuid.uuid4())[:16]

@cache.cached(key_prefix='stopwords', timeout=86400)
def get_stopwords() -> set:
    """
    Retrieves stopwords from the configuration stored in the database.

    Returns:
        set: A set of stopwords retrieved from the Config table. If no stopwords
        are found, an empty set is returned.
    """
    config = Config.query.first()
    if config and config.stopwords:
        stopwords_list = config.stopwords.strip().split()
        return set(stopwords_list)
    return set()


@cache.cached(key_prefix='get_issue_date_interval', timeout=86400)
def get_issue_date_interval() -> tuple:
    """
    Retrieves the earliest and latest issued dates of newspaper issues.

    Returns:
        tuple: A tuple containing two dates:
            - The earliest issued date (min_date).
            - The latest issued date (max_date).
        Defaults:
            - If no records exist, min_date defaults to January 1, 2015.
            - max_date defaults to today's date.
    """
    
    # Query the minimum and maximum issue dates
    min_date = db.session.query(func.min(NewspaperIssue.issued_time)).scalar()
    max_date = db.session.query(func.max(NewspaperIssue.issued_time)).scalar()
    
    # Set default values if dates are None
    if min_date is None:
        min_date = datetime.date(2015, 1, 1)
    if max_date is None:
        max_date = datetime.date.today()
    
    return min_date, max_date

@cache.cached(key_prefix="get_about_markdown", timeout=86400)
def get_about_markdown() -> str:
    """
    Retrieves the 'About' content from the configuration and converts it to HTML using Markdown.

    Returns:
        str: The 'About' content in HTML format. Returns an empty string if no content exists.
    """
    # Fetch the first configuration record
    config = Config.query.first()

    # Convert the 'About' content to HTML if it exists
    about_html = ""
    if config and config.about_content:
        about_html = markdown.markdown(config.about_content)
    
    return about_html


@cache.cached(key_prefix="get_archive", timeout=86400)
def get_archive() -> list:
    """
    Retrieves a list of newspaper issues that the current user has permission to view,
    ordered by issued time in descending order.

    Returns:
        list: A list of `NewspaperIssue` objects that the current user can view.
    """
    # Query for issues the current user can view
    issues = NewspaperIssue.query.filter(
        NewspaperIssue.view_power <= current_user.view_power
    ).order_by(NewspaperIssue.issued_time.desc()).all()
    
    return issues


def remove_stopwords(query: str) -> str:
    """
    Removes stopwords from a given query string.

    Args:
        query (str): The input query string.

    Returns:
        str: The query string with stopwords removed.
    """
    words = query.strip().split()
    stopwords = get_stopwords()
    filtered_words = [word for word in words if word.lower() not in stopwords]
    return ' '.join(filtered_words)

def create_signed_url(file_blob: str, tmp_blob_name: str) -> str:
    """
    Generates a signed URL for a file in Google Cloud Storage and caches it.

    Args:
        file_blob (str): The path to the file blob in the storage bucket.
        tmp_blob_name (str): A temporary name used as a key in the cache.

    Returns:
        str: The generated signed URL for the file.
    """
    client = storage.Client()
    bucket = client.bucket(current_app.config['CLOUD_STORAGE_BUCKET'])
    blob = bucket.blob(file_blob)

    # Generate signed URL
    signed_url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=current_app.config['FILE_LINK_EXPIRE_TIME_MIN']),  # Set link expiration time
        method='GET'
    )
    cache.set(
        key="signed_url"+tmp_blob_name,
        value=str(signed_url),
        timeout=current_app.config['FILE_LINK_EXPIRE_TIME_MIN']-1
    )
    return signed_url

@cache.memoize(timeout=86400)
def get_issue(issue_id: int) -> NewspaperIssue:
    """
    Retrieves a NewspaperIssue object from the database using its ID.
    The result is cached for 24 hours (86400 seconds).

    Args:
        issue_id (int): The ID of the newspaper issue to retrieve.

    Returns:
        NewspaperIssue: The newspaper issue object.

    Raises:
        werkzeug.exceptions.NotFound: If no issue is found with the given ID.
    """
    issue = NewspaperIssue.query.get_or_404(issue_id)
    return issue

def get_db_signed_url(blob_name: str) -> str:
    """
    Retrieves a signed URL for accessing a blob from the cache.

    Args:
        blob_name (str): The name of the blob for which the signed URL is retrieved.

    Returns:
        str: The signed URL if it exists in the cache, otherwise None.
    """
    return cache.get("signed_url"+blob_name)

def admin_required(f):
    """
    Custom decorator to restrict access to admin users only.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():  # Check if the user has admin role
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.search'))  # Redirect to dashboard or any other page
        return f(*args, **kwargs)
    return decorated_function

def ini_users() -> None:
    """
    Initializes the admin user in the database if it does not already exist.

    The admin user's details (username and password) are retrieved from the
    application's configuration. If the user does not exist, a new admin user is
    created with a default role of 'admin' and view power of 100.

    Raises:
        KeyError: If 'ADMIN_USERNAME' or 'ADMIN_PASSWORD' is not configured in the app.
    """
    admin_user = User.query.filter_by(username=current_app.config['ADMIN_USERNAME']).first()
    if not admin_user:
        admin_user = User(username=current_app.config['ADMIN_USERNAME'], password_hash=generate_password_hash(current_app.config['ADMIN_PASSWORD']), role='admin', view_power=100)
        db.session.add(admin_user)
        db.session.commit()