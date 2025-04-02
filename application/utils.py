from flask import redirect, url_for, flash, current_app, abort
from flask_login import current_user
from werkzeug.security import generate_password_hash
import uuid
from google.cloud import storage
from sqlalchemy import func
import datetime
from functools import wraps
import markdown
from datetime import timedelta
from sqlalchemy.orm import joinedload

from . import cache
from .models import db, User, NewspaperIssue, Config, Category
from .forms import *

    # List of month names
MONTHS_LIST = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

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

def clean_query(query: str) -> str:
    query=remove_stopwords(query).lower()
    return query

def create_signed_url(file_blob: str, tmp_blob_name: str = "") -> str:
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
        expiration=timedelta(minutes=current_app.config['FILE_LINK_EXPIRE_TIME_SEC']),  # Set link expiration time
        method='GET'
    )
    return signed_url

@cache.memoize(timeout=86400)
def get_year_month_issues(year: int,month: int) -> NewspaperIssue:
    """
    Retrieves all newspaper issues for a specific year and month that the current user is authorized to view.

    This function filters issues based on the provided year and month, ensuring that the user's view power 
    is sufficient to access the issues. The results are cached for 24 hours (86400 seconds) to improve performance.

    Args:
        year (int): The year for which issues are to be retrieved.
        month (int): The month for which issues are to be retrieved.

    Returns:
        list[NewspaperIssue]: A list of newspaper issues ordered by their issued time in ascending order.

    Caching:
        The result of this function is cached for 24 hours to minimize redundant database queries.
    """
    issues = NewspaperIssue.query.filter(
        db.extract('year', NewspaperIssue.issued_time) == year,
        db.extract('month', NewspaperIssue.issued_time) == month,
        NewspaperIssue.view_power <= current_user.view_power
    ).order_by(NewspaperIssue.issued_time.asc()).all()
    return issues

@cache.memoize(timeout=86400)
def get_day_issues(year: int, month: int, day: int) -> list:
    """
    Retrieves all newspaper issues for a specific year, month, and day that the current user is authorized to view.

    This function filters issues based on the provided year, month, and day, ensuring that the user's view power
    is sufficient to access the issues. The results are cached for 24 hours (86400 seconds) to improve performance.

    Args:
        year (int): The year for which issues are to be retrieved.
        month (int): The month for which issues are to be retrieved.
        day (int): The day for which issues are to be retrieved.

    Returns:
        list[NewspaperIssue]: A list of newspaper issues ordered by their issued time in ascending order.

    Caching:
        The result of this function is cached for 24 hours to minimize redundant database queries.
    """
    issues = NewspaperIssue.query.filter(
        db.extract('year', NewspaperIssue.issued_time) == year,
        db.extract('month', NewspaperIssue.issued_time) == month,
        db.extract('day', NewspaperIssue.issued_time) == day,
        NewspaperIssue.view_power <= current_user.view_power
    ).order_by(NewspaperIssue.issued_time.asc()).all()
    return issues


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
    issue = NewspaperIssue.query.options(joinedload(NewspaperIssue.category)).get_or_404(issue_id)
    return issue

@cache.cached(key_prefix="get_all_category", timeout=86400)
def get_all_category():
    return Category.query.all()

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
            return abort(401)
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

def update_cache(modified_issue: NewspaperIssue) -> None:
    """
    Updates the application cache to ensure consistency after a newspaper issue is modified.

    This function invalidates cache entries that might be affected by changes to the 
    given issue, ensuring stale data is removed. Specifically, it clears cached results for:
    - Issue retrieval by ID, date ranges, and specific time intervals (year, month, day).
    - Functions retrieving the archive or related metadata like issue date intervals.
    - Category-related functions to reflect potential changes in categorization.

    Args:
        modified_issue (NewspaperIssue): The newspaper issue object that was modified.

    Cache Entries Invalidated:
        - `get_issue_date_interval`: Clears the date range cache.
        - `get_archive`: Clears the entire archive cache.
        - `get_issue`: Clears the cache for the specific issue by ID.
        - `get_year_month_issues`: Clears cached issues for the issue's year and month.
        - `get_day_issues`: Clears cached issues for the issue's specific day.
        - `get_all_category`: Clears category-related caches in case of category updates.

    Returns:
        None
    """
    cache.delete('get_issue_date_interval')
    cache.delete('get_archive')
    cache.delete_memoized(get_issue, modified_issue.id)
    cache.delete_memoized(
        get_year_month_issues,
        modified_issue.issued_time.year,
        modified_issue.issued_time.month
    )
    cache.delete_memoized(
        get_day_issues,
        modified_issue.issued_time.year,
        modified_issue.issued_time.month,
        modified_issue.issued_time.day
    )
    cache.delete('get_all_category')
