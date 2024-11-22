from flask_wtf import FlaskForm
from wtforms import FormField, FieldList, HiddenField, BooleanField, IntegerField, StringField, PasswordField, FileField, SubmitField, TextAreaField, DateField
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
    view_power = IntegerField('view power(viewed by equal or greater power, 1-5)', validators=[DataRequired()], default=1)
    submit = SubmitField('Upload')

class UpdateForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    author = StringField('Author', validators=[DataRequired()])
    file = FileField('Upload New File(leave blank if no update)', validators=[Optional()])
    issued_time = DateField('Issued Date', format='%Y-%m-%d', validators=[DataRequired()]) 
    view_power = IntegerField('view power(viewed by equal or greater power, 1-5)', validators=[DataRequired()], default=1)
    submit = SubmitField('Upload')

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

    