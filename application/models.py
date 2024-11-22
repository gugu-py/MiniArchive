from . import login_manager, db

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

from flask_login import UserMixin


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), default='user')  # 'user' or 'admin'
    view_power = db.Column(db.Integer, nullable=False) # [0,5] higher is stronger

    def is_admin(self):
        return self.role == 'admin'

class NewspaperIssue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    author = db.Column(db.String(255))
    content = db.Column(db.Text) #ALTER TABLE newspaper_issue ADD FULLTEXT INDEX idx_fulltext_content (content);
    issued_time = db.Column(db.Date)
    file_blob = db.Column(db.String(255))
    view_power = db.Column(db.Integer, nullable=False, default=1) # viewed by equal or greater power

class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stopwords = db.Column(db.Text, nullable=False, default='')
    about_content = db.Column(db.Text, nullable=True)
