from flask_wtf import FlaskForm
from wtforms import FormField, SelectField, FieldList, HiddenField, BooleanField, IntegerField, StringField, PasswordField, FileField, SubmitField, TextAreaField, DateField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=25)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=25)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Register')

class UploadForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    author = StringField('Author', validators=[DataRequired()])
    file = FileField('Upload File', validators=[DataRequired()])
    issued_time = DateField('Issued Date', format='%Y-%m-%d', validators=[DataRequired()])
    view_power = IntegerField('View Power (viewed by equal or greater power, 1-5)', validators=[DataRequired()], default=1)
    category = SelectField('Category', coerce=int, validators=[DataRequired()])  # New field for category selection
    submit = SubmitField('Upload')

class UpdateForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    author = StringField('Author', validators=[DataRequired()])
    file = FileField('Upload New File (leave blank if no update)', validators=[Optional()])
    issued_time = DateField('Issued Date', format='%Y-%m-%d', validators=[DataRequired()])
    view_power = IntegerField('View Power (viewed by equal or greater power, 1-5)', validators=[DataRequired()], default=1)
    category = SelectField('Category', coerce=int, validators=[DataRequired()])  # New field for category selection
    submit = SubmitField('Update')

class StopwordsForm(FlaskForm):
    stopwords = TextAreaField('Stopwords', validators=[DataRequired()], render_kw={"rows": 10, "cols": 70})
    submit = SubmitField('Save')

class AboutForm(FlaskForm):
    about_content = TextAreaField('About Content', validators=[DataRequired()])

class IndividualUserForm(FlaskForm):
    user_id = HiddenField()  # To identify the user in the form data
    confirm = BooleanField()
    delete = BooleanField()
    username = StringField('Username', validators=[Optional(), Length(min=1, max=80)])
    password = PasswordField('New Password', validators=[Optional(), Length(min=6)])
    view_power = IntegerField('View Power', validators=[Optional(), NumberRange(min=0, max=5)])

class ManageUsersForm(FlaskForm):
    users = FieldList(FormField(IndividualUserForm), min_entries=0)
    submit = SubmitField('Submit Changes')

class CreateUserForm(FlaskForm):
    new_username = StringField('Username', validators=[DataRequired(), Length(min=1, max=80)])
    new_password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    new_view_power = IntegerField('View Power', validators=[DataRequired(), NumberRange(min=0, max=5)])
    create = SubmitField('Create User')

class IndividualCategoryForm(FlaskForm):
    category_id = HiddenField()  # Hidden field for category ID
    category_name = StringField('Category Name', validators=[Optional()])
    category_description = TextAreaField('Description', validators=[Optional()])
    confirm = BooleanField('Confirm Changes')  # Must be checked to process this category
    delete = BooleanField('Delete This Category')  # Mark category for deletion

class ManageCategoriesForm(FlaskForm):
    categories = FieldList(FormField(IndividualCategoryForm), label='Existing Categories')  # List of existing categories
    new_name = StringField('New Category Name', validators=[Optional()])
    new_description = TextAreaField('New Category Description', validators=[Optional()])
    new_confirm = BooleanField('Confirm New Category')  # Must be checked to add new category
    submit = SubmitField('Update Categories')
    