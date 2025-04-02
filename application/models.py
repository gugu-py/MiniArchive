from . import login_manager, db
from sqlalchemy.dialects.mysql import LONGTEXT

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

from flask_login import UserMixin


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), default='user')  # 'user' or 'admin'
    view_power = db.Column(db.Integer, nullable=False) # [0,5] higher is stronger

    def is_admin(self):
        return self.role == 'admin'

class NewspaperIssue(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255))
    author = db.Column(db.String(255))
    content = db.Column(LONGTEXT) #ALTER TABLE newspaper_issue ADD FULLTEXT INDEX idx_fulltext_content (content);
    issued_time = db.Column(db.Date)
    file_blob = db.Column(db.String(255))
    view_power = db.Column(db.Integer, nullable=False, default=1) # viewed by equal or greater power

    # Foreign key to Category
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False,)
    category = db.relationship('Category', back_populates='issues')

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)

    # Relationship to NewspaperIssue
    issues = db.relationship('NewspaperIssue', back_populates='category', lazy='dynamic')

    @staticmethod
    def get_or_create_default():
        """Ensure the default 'Uncategorized' category exists."""
        default_category = Category.query.filter_by(name="Uncategorized").first()
        if not default_category:
            default_category = Category(name="Uncategorized", description="Default category for uncategorized issues")
            db.session.add(default_category)
            db.session.commit()
        return default_category

class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    stopwords = db.Column(db.Text, nullable=False, default='')
    about_content = db.Column(db.Text, nullable=True)
