from flask import render_template, request, redirect, url_for, flash, Response, Blueprint, current_app, abort
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from google.cloud import storage
import os
import pdfplumber
import datetime
from collections import defaultdict
import requests

from . import cache
from .utils import *
from .forms import *
from .models import *

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Get the min and max issued_time from the database
    min_date,max_date = get_issue_date_interval()
    # If no issues are in the database, set default dates
    if min_date is None:
        min_date = datetime.date(2015, 1, 1)
    if max_date is None:
        max_date = datetime.date.today()

    about_html=get_about_markdown()

    context = {
        'issued_time_start': min_date,
        'issued_time_end': max_date,
        'about_content': about_html,
        'categories': get_all_category(),
    }

    return render_template('landingpage.html', **context)

@main_bp.route('/admin/edit_about', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_about():
    form = AboutForm()
    # Fetch the existing "About" content from the database (only one record in Config table)
    config = Config.query.first()  # Assume only one row in the Config table
    if not config:
        # Create a default config record if it doesn't exist
        config = Config(stopwords='',about_content='# Please Configure about')
        db.session.add(config)
        db.session.commit()
    if form.validate_on_submit():
        # Update the about_content field with new Markdown content
        config.about_content = form.about_content.data
        db.session.commit()  # Save the changes to the database
        cache.delete('get_about_markdown')
        flash('About page content updated successfully!', 'success')
        return redirect('/')  # Redirect to the landing page

    # Pre-fill the form with the existing about_content
    if config:
        form.about_content.data = config.about_content
    
    return render_template('edit_about.html', form=form)

@main_bp.route('/admin/manage_categories', methods=['GET', 'POST'])
@login_required
@admin_required  # Ensure only admins can access this route
def manage_categories():

    # Query all categories
    categories = Category.query.filter(Category.name != 'Uncategorized').all()

    if request.method == 'POST':
        manage_form = ManageCategoriesForm(request.form)
        if manage_form.validate_on_submit():
            # Process existing categories
            for category_form in manage_form.categories.entries:
                if category_form.confirm.data:  # Only process if confirm is checked
                    category = Category.query.get(int(category_form.category_id.data))
                    if category_form.delete.data:
                        # Avoid deleting the default 'Uncategorized' category
                        if category.issues.count() > 0:
                            flash(f"Cannot delete category '{category.name}' because it has associated issues.", 'danger')
                        else:
                            db.session.delete(category)
                    else:
                        # Update category details
                        category.name = category_form.category_name.data
                        category.description = category_form.category_description.data
            
            # Process new category
            if manage_form.new_name.data and manage_form.new_confirm.data:
                new_category = Category(
                    name=manage_form.new_name.data,
                    description=manage_form.new_description.data
                )
                db.session.add(new_category)

            db.session.commit()
            flash('Categories updated successfully!', 'success')
        else:
            flash(f"Form validation failed: {manage_form.errors}", 'danger')
        return redirect(url_for('main.manage_categories'))
    else:
        manage_form = ManageCategoriesForm()
        # Pre-populate the categories FieldList
        for category in categories:
            category_form = manage_form.categories.append_entry()
            if category:
                category_form.category_id.data = category.id
                category_form.category_name.data = category.name
                category_form.category_description.data = category.description
            # print(category.name)
        

    return render_template('manage_categories.html', manage_form=manage_form)

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=True)
            return redirect(url_for('main.search'))
        flash('Invalid username or password')
    return render_template('login.html', form=form)


@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    # form = RegistrationForm()
    # if form.validate_on_submit():
    #     new_user = User(username=form.username.data, password_hash=generate_password_hash(form.password.data))
    #     db.session.add(new_user)
    #     db.session.commit()
    #     flash('Registration successful! Please log in.')
    #     return redirect(url_for('main.login'))
    # return render_template('register.html', form=form)
    return 'not available service'

@main_bp.route('/admin/manage_users', methods=['GET', 'POST'])
@login_required
@admin_required  # Ensure only admins can access this route
def manage_users():
    users = User.query.filter(User.role != 'admin').all()  # Exclude admin user

    # Initialize the form with request.form on POST or None on GET

    if request.method == 'POST':
        manage_form = ManageUsersForm(request.form)
        if manage_form.validate_on_submit():
            # Process existing users
            for user_form in manage_form.users.entries:
                if user_form.confirm.data:
                    user = User.query.get(int(user_form.user_id.data))
                    if user_form.delete.data:
                        db.session.delete(user)
                    else:
                        # Update user details
                        user.username = user_form.username.data
                        if user_form.password.data:
                            user.password_hash = generate_password_hash(user_form.password.data)
                        user.view_power = user_form.view_power.data
            db.session.commit()
            flash('Users updated successfully!', 'success')
        else:
            flash(f'oh no! {manage_form.errors}')
        return redirect(url_for('main.manage_users'))
    else:
        manage_form = ManageUsersForm()
        # Pre-populate the users FieldList
        for user in users:
            user_form = manage_form.users.append_entry()  # Append a new entry to the FieldList
            user_form.user_id.data = user.id             # Set the user_id field
            user_form.username.data = user.username      # Set the username field
            user_form.password.data = ''                 # Set the password field
            user_form.view_power.data = user.view_power  # Set the view_power field

    return render_template('manage_users.html', manage_form=manage_form)



@main_bp.route('/admin/manage_users/add_user', methods=['GET', 'POST'])
@login_required
@admin_required  # Ensure only admins can access this route
def add_user():
    create_form = CreateUserForm()
    if request.method == 'POST' and create_form.create.data and create_form.validate_on_submit():
        # Handle new user creation
        new_username = create_form.new_username.data
        new_password = create_form.new_password.data
        new_view_power = create_form.new_view_power.data
        existing_user = User.query.filter_by(username=new_username).first()
        if existing_user:
            flash('Username already exists.', 'danger')
        else:
            new_user = User(
                username=new_username,
                password_hash=generate_password_hash(new_password),
                role='user',
                view_power=new_view_power
            )
            db.session.add(new_user)
            db.session.commit()
            flash('User created successfully!', 'success')
        return redirect(url_for('main.manage_users'))
    return render_template('add_user.html', create_form=create_form)
    

@main_bp.route('/admin/upload', methods=['GET', 'POST'])
@login_required
@admin_required
def upload():
    form = UploadForm()
    
    # Populate the category dropdown
    form.category.choices = [(c.id, c.name) for c in Category.query.all()]
    
    if form.validate_on_submit():
        file = form.file.data
        title = form.title.data
        author = form.author.data
        issued_time = form.issued_time.data
        category_id = form.category.data  # Get the selected category ID

        # Generate a unique file name
        random_filename = secure_filename(generate_random_filename() + os.path.splitext(file.filename)[1])  # Preserve the original file extension

        # Upload to Google Cloud Storage
        client = storage.Client()
        bucket = client.bucket(current_app.config['CLOUD_STORAGE_BUCKET'])
        blob = bucket.blob(random_filename)  # Use the unique random file name
        blob.upload_from_file(file)

        # Extract text from PDF
        text_content = ""
        if file.filename.endswith('.pdf'):
            file.seek(0)  # Reset the file pointer before reading it again
            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    text_content += page.extract_text().lower() + "\n"

        # Assign the selected category or default to "Uncategorized"
        category = Category.query.get(category_id) or Category.get_or_create_default()

        # Store in MySQL
        new_issue = NewspaperIssue(
            title=title,
            author=author,
            issued_time=issued_time,
            content=text_content,  # Save the extracted text
            file_blob=random_filename,
            category=category  # Assign the selected category
        )
        db.session.add(new_issue)
        db.session.commit()

        flash('Newspaper issue uploaded successfully!')

        # Update cache (if applicable)
        update_cache(new_issue)
        
        return redirect(url_for('main.upload'))

    return render_template('upload.html', form=form)


@main_bp.route('/admin/stopwords', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_stopwords():
    form = StopwordsForm()
    config = Config.query.first()
    if not config:
        # Create a default config record if it doesn't exist
        config = Config(stopwords='',about_content='# Please Configure about')
        db.session.add(config)
        db.session.commit()
    if form.validate_on_submit():
        config.stopwords = form.stopwords.data.strip().lower()
        db.session.commit()
        cache.delete('stopwords')  # Invalidate the cached stopwords
        flash('Stopwords updated successfully.')
        return redirect(url_for('main.manage_stopwords'))
    else:
        form.stopwords.data = config.stopwords
    return render_template('manage_stopwords.html', form=form)


@main_bp.route('/edit_issue/<int:issue_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_issue(issue_id):
    # Fetch the issue from the database
    issue = NewspaperIssue.query.get_or_404(issue_id)

    # Create the form and populate it with the existing issue data
    form = UpdateForm(obj=issue)

    # Populate the category field with existing categories from the database
    form.category.choices = []
    for c in Category.query.all():
        if c:
            form.category.choices.append((c.id, c.name))

    if form.validate_on_submit():
        try:
            # Update the issue fields from the form data
            issue.title = form.title.data
            issue.author = form.author.data
            issue.issued_time = form.issued_time.data
            issue.view_power = form.view_power.data
            
            # Update the category (fallback to default if none is selected)
            issue.category = Category.query.get(form.category.data) or Category.get_or_create_default()

            # Handle file upload
            if form.file.data:
                file = form.file.data
                random_filename = secure_filename(
                    generate_random_filename() + os.path.splitext(file.filename)[1]
                )  # Preserve the original file extension

                # Upload to Google Cloud Storage
                client = storage.Client()
                bucket = client.bucket(current_app.config['CLOUD_STORAGE_BUCKET'])
                blob = bucket.blob(random_filename)
                blob.upload_from_file(file)

                # Extract text from PDF
                if file.filename.endswith('.pdf'):
                    text_content = ""
                    with pdfplumber.open(file) as pdf:
                        for page in pdf.pages:
                            text_content += page.extract_text() + "\n"
                    issue.content = text_content  # Update the content field

                # Update the file_blob field in the database with the new filename
                issue.file_blob = random_filename

            # Commit changes to the database
            db.session.commit()

            # Update cache or any relevant external data
            update_cache(issue)

            flash('The issue was successfully updated.', 'success')
            return redirect(url_for('main.view_document', issue_id=issue.id))  # Replace with the correct route
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')

    return render_template('edit_issue.html', form=form, issue=issue)


@main_bp.route('/delete_issue/<int:issue_id>', methods=['POST'])
@login_required
@admin_required
def delete_issue(issue_id):
    issue = get_issue(issue_id)
    update_cache(issue)
    # blob = db.session.query(SignedBlob).filter_by(blob_name=issue.blob_name).first()
    # db.session.delete(blob)
    db.session.delete(issue)
    db.session.commit()
    flash('Newspaper issue deleted successfully!')
    return redirect(url_for('main.search'))

@main_bp.route('/archive')
@login_required
def archive():
    """
    Displays a year-month view of all issues. Each month links to a month view
    where issues are displayed, labeled by their dates.
    """
    # Query all newspaper issues, ordered by issued_time descending
    issues = get_archive()

    # Organize issues by year and month
    issues_by_month = defaultdict(list)
    issues_by_year = defaultdict(list)
    for issue in issues:
        year = issue.issued_time.strftime('%Y')
        month = issue.issued_time.strftime('%m')
        year_month = f"{year}-{month}"
        issues_by_month[year_month].append(issue)
        if month not in issues_by_year[year]:
            issues_by_year[year].append(month)

    # Sort the years and months
    sorted_years = sorted(issues_by_year.keys(), reverse=True)
    issues_by_year = {
        year: sorted(issues_by_year[year])
        for year in sorted_years
    }

    # Generate month view URLs for each month
    month_urls = {
        f"{year}-{month}": url_for('main.month_view', year=year, month=month)
        for year in issues_by_year
        for month in issues_by_year[year]
    }

    return render_template('archive.html',
                           issues_by_year=issues_by_year,
                           issues_by_month=issues_by_month,
                           months_list=MONTHS_LIST,
                           month_urls=month_urls)

@main_bp.route('/archive/<int:year>/<int:month>')
@login_required
def month_view(year, month):
    """
    Displays all issues for a specific month in a calendar-like view.
    """
    # Query issues for the specified year and month
    issues = get_year_month_issues(year,month)

    # Serialize issues to a list of dictionaries
    serialized_issues = [
        {
            "id": issue.id,
            "title": issue.title,
            "issued_time": issue.issued_time.strftime('%Y-%m-%d'),  # Format as string
            "url": url_for('main.view_document', issue_id=issue.id),
            "author": issue.author,
        }
        for issue in issues
    ]

    # Render template with serialized issues
    return render_template(
        'month_view.html',
        year=year,
        month=month,
        issues=serialized_issues,
        months_list=MONTHS_LIST,
    )

@main_bp.route('/archive/<int:year>/<int:month>/<int:day>')
@login_required
def day_view(year, month, day):
    """
    Displays all issues for a specific day in a detailed list view.
    """
    # Query issues for the specified year, month, and day
    issues = get_day_issues(year, month, day)

    # Serialize issues to a list of dictionaries
    serialized_issues = [
        {
            "id": issue.id,
            "title": issue.title,
            "issued_time": issue.issued_time.strftime('%Y-%m-%d'),  # Include time for more detail
            "url": url_for('main.view_document', issue_id=issue.id),
            "author": issue.author,
        }
        for issue in issues
    ]

    # Render template with serialized issues
    return render_template(
        'day_view.html',
        year=year,
        month=month,
        day=day,
        issues=serialized_issues,
        months_list=MONTHS_LIST,
    )


@main_bp.route('/search', methods=['GET'])
@login_required
def search():
    ori_query = request.args.get('q')
    title_query = request.args.get('title')
    author_query = request.args.get('author')
    issued_time_start = request.args.get('issued_time_start')
    issued_time_end = request.args.get('issued_time_end')
    category_query = request.args.get('category')  # Get the selected category ID
    page = request.args.get('page', 1, type=int)  # Get the current page number

    # Get the min and max issued_time from the database
    min_date, max_date = get_issue_date_interval()

    filters = []
    context = {}

    # Ensure only results with an appropriate view_power are shown
    filters.append(NewspaperIssue.view_power <= current_user.view_power)

    # Filter by title
    if title_query:
        context['title_query'] = title_query
        filters.append(NewspaperIssue.title.like(f'%{title_query}%'))

    # Filter by author
    if author_query:
        context['author_query'] = author_query
        filters.append(NewspaperIssue.author.like(f'%{author_query}%'))

    # Filter by content (using full-text search)
    if ori_query:
        context['query'] = ori_query
        query = clean_query(ori_query)
        filters.append(NewspaperIssue.content.match(query))

    # Parse issued_time_start
    if issued_time_start:
        issued_time_start = datetime.datetime.strptime(issued_time_start, '%Y-%m-%d').date()
        context['issued_time_start'] = issued_time_start.strftime('%Y-%m-%d')
    else:
        issued_time_start = min_date

    # Parse issued_time_end
    if issued_time_end:
        issued_time_end = datetime.datetime.strptime(issued_time_end, '%Y-%m-%d').date()
        context['issued_time_end'] = issued_time_end.strftime('%Y-%m-%d')
    else:
        issued_time_end = max_date

    filters.append(NewspaperIssue.issued_time.between(issued_time_start, issued_time_end))

    # Filter by category if a category is selected
    if category_query:
        context['category_query'] = int(category_query)  # Store selected category ID in the context
        filters.append(NewspaperIssue.category_id == int(category_query))

    # Modify the query to use pagination
    per_page = 15  # Number of results per page
    pagination = NewspaperIssue.query.filter(*filters).order_by(NewspaperIssue.issued_time.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    results = pagination.items

    # Add pagination and results to the context
    context['results'] = results
    context['pagination'] = pagination

    # Add categories to the context for dropdown rendering
    context['categories'] = get_all_category()

    return render_template(
        'results.html',
        **context
    )

# @main_bp.route('/file/<path:blob_name>', methods=['GET'])
# def proxy_to_signed_url(blob_name):
#     # Generate the signed URL
#     signed_url = get_db_signed_url(blob_name)
#     if signed_url:
#     # Fetch the content from the signed URL
#         response = requests.get(signed_url, stream=True)

#         # Proxy the response back to the client
#         return Response(
#             response.iter_content(chunk_size=8192),
#             content_type=response.headers.get('Content-Type'),
#             status=response.status_code
#         )
#     else:
#         return abort(404)


@main_bp.route('/view_document/<int:issue_id>')
@login_required
def view_document(issue_id):
    query = request.args.get('q', '')  # Get the search query
    issue = get_issue(issue_id)
    if current_user.view_power<issue.view_power:
        return redirect('/')
    signed_url = create_signed_url(issue.file_blob)
    # Generate the temporary URL using the Worker
    # Get the worker endpoint and expiration settings from the app configuration
    worker_url = current_app.config.get('CLOUDFLARE_PROXY_WORKER_URL')
    if not worker_url:
        current_app.logger.error("Worker URL not configured.")
        return redirect('/')
    
    expire_in_seconds = current_app.config.get('FILE_LINK_EXPIRE_TIME_SEC', 3600) - 1  # Default to 3600 seconds if not set

    try:
        # Call the Worker to generate the temporary URL
        response = requests.get(worker_url, params={
            'signedUrl': signed_url,
            'expireSeconds': expire_in_seconds  # Use correct parameter name
        })
        response.raise_for_status()

        # Parse the Worker response
        proxied_url = response.json().get('tmpLink')  # Use 'tmpLink' to match Worker response key
        if not proxied_url:
            current_app.logger.error('Failed to retrieve temporary link from Worker response.')
            return redirect('/')
    except requests.RequestException as e:
        current_app.logger.error(f'Error calling the Worker: {e}')
        return redirect('/')

    return render_template('view_pdf.html', issue=issue, query=query, file_url=proxied_url)

@main_bp.route('/view_text/<int:issue_id>')
@login_required
@cache.cached(timeout=86400)
def view_text(issue_id):
    issue = get_issue(issue_id)
    return issue.content

@main_bp.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    issues = NewspaperIssue.query.all()
    return render_template('admin.html', issues=issues)

@main_bp.route('/logout')
# @login_required
def logout():
    logout_user()
    return redirect('/')

@main_bp.errorhandler(400)
@cache.cached(timeout=86400)
def bad_request(error):
    context = {
        'title': 400,
        'error_info': "Bad Request! Your browser sent a request that this server couldn't understand.",
        'emoji': '❌',
    }
    return render_template('error.html', **context), 400

@main_bp.errorhandler(401)
@cache.cached(timeout=86400)
def unauthorized(error):
    context = {
        'title': 401,
        'error_info': "Unauthorized! You need to log in to access this resource.",
        'emoji': '🔒',
    }
    return render_template('error.html', **context), 401

@main_bp.errorhandler(403)
@cache.cached(timeout=86400)
def forbidden(error):
    context = {
        'title': 403,
        'error_info': "Forbidden! You don't have permission to access this resource.",
        'emoji': '⛔',
    }
    return render_template('error.html', **context), 403

@main_bp.errorhandler(404)
@cache.cached(timeout=86400)
def page_not_found(error):
    context = {
        'title': 404,
        'error_info': "Oops! The page you were looking for doesn’t exist.",
        'emoji': '🚀',
    }
    return render_template('error.html', **context), 404

@main_bp.errorhandler(408)
@cache.cached(timeout=86400)
def request_timeout(error):
    context = {
        'title': 408,
        'error_info': "Request Timeout! The server timed out waiting for your request.",
        'emoji': '⏳',
    }
    return render_template('error.html', **context), 408