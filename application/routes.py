from flask import render_template, request, redirect, url_for, flash, Response, Blueprint, current_app
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
        'about_content': about_html
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
    if form.validate_on_submit():
        file = form.file.data
        title = form.title.data
        author = form.author.data
        issued_time = form.issued_time.data

        # Generate a unique file name
        random_filename = secure_filename(generate_random_filename() + os.path.splitext(file.filename)[1])  # Preserve the original file extension

        # Upload to Google Cloud Storage
        client = storage.Client()
        bucket = client.bucket(current_app.config['CLOUD_STORAGE_BUCKET'])
        blob = bucket.blob(random_filename)  # Use the unique random file name
        blob.upload_from_file(file)
        cache.delete('get_issue_date_interval')
        cache.delete('get_archive')

        # Extract text from PDF
        text_content = ""
        if file.filename.endswith('.pdf'):
            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    text_content += page.extract_text() + "\n"

        # Store in MySQL
        new_issue = NewspaperIssue(
            title=title,
            author=author,
            issued_time=issued_time,
            content=text_content,  # Save the extracted text
            file_blob=random_filename
        )
        db.session.add(new_issue)

        # new_blob = SignedBlob(
        #     blob_name = random_filename,
        #     signed_url = 'placeholder'
        # )
        # db.session.add(new_blob)
        db.session.commit()
        flash('Newspaper issue uploaded successfully!')
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
        config.stopwords = form.stopwords.data.strip()
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
    
    if form.validate_on_submit():
        try:
            # Update the issue fields from the form data
            issue.title = form.title.data
            issue.author = form.author.data
            issue.issued_time = form.issued_time.data
            issue.view_power = form.view_power.data
            
            # Handle file upload
            if form.file.data:
                # Secure the filename and save the file
                # Generate a unique file name
                random_filename = secure_filename(generate_random_filename() + os.path.splitext(file.filename)[1])  # Preserve the original file extension
                file = form.file.data
                # Upload to Google Cloud Storage
                client = storage.Client()
                bucket = client.bucket(current_app.config['CLOUD_STORAGE_BUCKET'])
                blob = bucket.blob(random_filename)  # Use the unique random file name
                blob.upload_from_file(file)

                # Extract text from PDF
                text_content = ""
                if file.filename.endswith('.pdf'):
                    with pdfplumber.open(file) as pdf:
                        for page in pdf.pages:
                            text_content += page.extract_text() + "\n"

            # Commit changes to the database
            db.session.commit()
            cache.delete_memoized(get_issue,issue.id)
            cache.delete('get_issue_date_interval')
            cache.delete('get_archive')
            flash('The issue was successfully updated.', 'success')
            return redirect(url_for('main.view_document', issue_id=issue.id))  # Replace 'view_issue' with your view route
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
    
    return render_template('edit_issue.html', form=form, issue=issue)


@main_bp.route('/delete_issue/<int:issue_id>', methods=['POST'])
@login_required
@admin_required
def delete_issue(issue_id):
    issue = get_issue(issue_id)
    # blob = db.session.query(SignedBlob).filter_by(blob_name=issue.blob_name).first()
    # db.session.delete(blob)
    db.session.delete(issue)
    db.session.commit()
    flash('Newspaper issue deleted successfully!')
    return redirect(url_for('main.admin_dashboard'))

@main_bp.route('/archive')
@login_required
def archive():
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
    issues_by_year = {year: sorted(issues_by_year[year]) for year in sorted_years}
    
    # List of month names
    months_list = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    return render_template('archive.html',
                           issues_by_year=issues_by_year,
                           issues_by_month=issues_by_month,
                           months_list=months_list)

@main_bp.route('/search', methods=['GET'])
@login_required
def search():
    ori_query = request.args.get('q')
    title_query = request.args.get('title')
    author_query = request.args.get('author')
    issued_time_start = request.args.get('issued_time_start')
    issued_time_end = request.args.get('issued_time_end')
    page = request.args.get('page', 1, type=int)  # Get the current page number

    # Get the min and max issued_time from the database
    min_date, max_date = get_issue_date_interval()

    filters = []
    context = {}

    # Ensure only results with an appropriate view_power are shown
    filters.append(NewspaperIssue.view_power <= current_user.view_power)

    if title_query:
        context['title_query'] = title_query
        filters.append(NewspaperIssue.title.like(f'%{title_query}%'))
    if author_query:
        context['author_query'] = author_query
        filters.append(NewspaperIssue.author.like(f'%{author_query}%'))
    if ori_query:
        context['query'] = ori_query
        query = remove_stopwords(ori_query)
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

    # Modify the query to use pagination
    per_page = 15  # Number of results per page
    pagination = NewspaperIssue.query.filter(*filters).order_by(NewspaperIssue.issued_time.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    results = pagination.items

    context['results'] = results
    context['pagination'] = pagination

    return render_template(
        'results.html',
        **context
    )

@main_bp.route('/file/<path:blob_name>', methods=['GET'])
def proxy_to_signed_url(blob_name):
    # Generate the signed URL
    signed_url = get_db_signed_url(blob_name)
    if signed_url:
    # Fetch the content from the signed URL
        response = requests.get(signed_url, stream=True)

        # Proxy the response back to the client
        return Response(
            response.iter_content(chunk_size=8192),
            content_type=response.headers.get('Content-Type'),
            status=response.status_code
        )
    else:
        return "file not available"


@main_bp.route('/view_document/<int:issue_id>')
@login_required
def view_document(issue_id):
    query = request.args.get('q', '')  # Get the search query
    issue = get_issue(issue_id)
    if current_user.view_power<issue.view_power:
        return redirect('/')
    tmp_blob_name=generate_random_filename()+'.'+str(issue.file_blob).split('.')[-1]
    proxied_url = url_for('main.proxy_to_signed_url', blob_name=tmp_blob_name, _external=True)
    create_signed_url(issue.file_blob,tmp_blob_name)

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

# Error handler for 401 Unauthorized
@main_bp.errorhandler(401)
# @cache.cached(timeout=86400)
def unauthorized_error(error):
    return render_template('errors/unauthorized.html'), 401

@main_bp.errorhandler(404)
@cache.cached(timeout=86400)
def page_not_found(error):
    return render_template('errors/404.html'), 404