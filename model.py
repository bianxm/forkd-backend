"""Models for Forkd (recipe journaling app)"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped
from datetime import datetime, timedelta
from passlib.hash import argon2
import base64
import os

db = SQLAlchemy()

# Mixin
class DictableColumn():
    def to_dict(self):
        crowded_dict = self.__dict__
        # cleaned_dict = {}
        # for key, val in crowded_dict.items():
        #     if isinstance(val, (str,int,float,bool, type(None), datetime)):
        #         cleaned_dict[key] = val
        #     elif isinstance(val, list):
        #         if isinstance(val[0], (Edit, Experiment)):
        #             cleaned_dict[key] = [i.to_dict() for i in val]
        return {key:val for key, val in crowded_dict.items() 
                if isinstance(val,(str,int,float,bool, dict, type(None), datetime))}
        # return cleaned_dict

# DATA MODEL
# Users
class User(DictableColumn, db.Model):
    """A user."""
    
    # SQL-side setup
    __tablename__ = 'users'

    id = db.Column(db.Integer, autoincrement = True, primary_key=True)
    email = db.Column(db.String, unique = True)
    password = db.Column(db.String)
    username = db.Column(db.String, unique = True)

    # new 11 April - for profile pic
    img_url = db.Column(db.String)
    is_temp_user = db.Column(db.Boolean)
    # for login
    token = db.Column(db.String(32), index=True, unique=True)
    token_expiration = db.Column(db.DateTime)

    # Relationships
    recipes = db.relationship('Recipe', back_populates='owner', order_by='desc(Recipe.last_modified)') # list of corresponding Recipe objects
    permissions = db.relationship('Permission', back_populates='user')
    committed_edits = db.relationship('Edit', back_populates='committer')
    committed_experiments = db.relationship('Experiment', back_populates='committer')

    # Class Methods
    def __repr__(self):
        return f'<User username={self.username}>'
    
    ## Class CRUD Methods
    @classmethod
    def create(cls, email: str, password: str, username: str, is_temp_user: bool = False) -> 'User':
        """Create and return a new user."""
        password = argon2.hash(password)
        return cls(email=email, password=password, username=username, is_temp_user=is_temp_user)
    
    @classmethod
    def get_all(cls):
        return cls.query.all()
    
    @classmethod
    def get_by_id(cls, id: int) -> 'User':
        return cls.query.get(id)
    
    @classmethod
    def get_by_username(cls, username: str) -> 'User':
        try:
            return cls.query.filter_by(username=username).one()
        except:
            return None 
    
    @classmethod
    def get_by_email(cls, email: str) -> 'User':
        try:
            return cls.query.filter_by(email=email).one()
        except:
            return None 

    ### LOGIN METHODS
    # instance method -- check if password is correct
    def is_password_correct(self, given_password: str) -> bool:
        return argon2.verify(given_password, self.password)
    
    def get_token(self, expires_in_hrs: int = 2):
        now = datetime.utcnow()
        if self.token and self.token_expiration > now + timedelta(seconds=60):
            return self.token
        self.token = base64.b64encode(os.urandom(24)).decode('utf-8')
        self.token_expiration = now + timedelta(hours=expires_in_hrs)
        db.session.add(self)
        return self.token

    def revoke_token(self):
        self.token_expiration = datetime.utcnow() - timedelta(seconds=1)
    
    @staticmethod
    def check_token(token):
        user = User.query.filter_by(token=token).first()
        if user is None or user.token_expiration < datetime.utcnow():
            return None
        return user
    
    ### to_dict method == exclude password, token, token_expiration
    def to_dict(self):
        dirty_dict = super().to_dict()
        del dirty_dict['password']
        del dirty_dict['email']
        del dirty_dict['token']
        del dirty_dict['token_expiration']

        return dirty_dict

# Recipes
class Recipe(DictableColumn, db.Model):
    """A recipe."""
    
    # SQL-side setup
    __tablename__ = 'recipes'

    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    source_url = db.Column(db.String)
    last_modified = db.Column(db.DateTime)
    forked_from = db.Column(db.Integer, db.ForeignKey('recipes.id'))
    
    # changed 11 April
    ## permissions
    is_public = db.Column(db.Boolean) # default true
    is_experiments_public = db.Column(db.Boolean) # default true

    # Relationships
    owner = db.relationship('User', back_populates='recipes') # one corresponding User object
    experiments = db.relationship('Experiment', back_populates='recipe', order_by='desc(Experiment.commit_date)', cascade='save-update, merge, delete') # list of corresponding Experiment objects
    edits = db.relationship('Edit', back_populates='recipe', order_by='desc(Edit.commit_date)', cascade='save-update, merge, delete', lazy='selectin') # list of corresponding Edit objects
    parent = db.relationship('Recipe', backref='children', remote_side=[id])

    permissions = db.relationship('Permission', back_populates='recipe')

    # Class Methods
    def __repr__(self):
        return f'<Recipe id={self.id}>'

    ## Class CRUD Methods
    @classmethod
    def create(cls, owner: User, modified_on: datetime, is_public: bool = True, is_experiments_public: bool = True, 
               source_url: str = None, forked_from=None) -> 'Recipe':
        """Create and return a new recipe."""
        is_public = True if is_public is None else is_public
        is_experiments_public = True if is_experiments_public is None else is_experiments_public
        return cls(owner=owner, last_modified=modified_on, 
                   is_public=is_public, is_experiments_public=is_experiments_public, 
                   source_url=source_url, forked_from=forked_from)
    
    @classmethod
    def get_by_id(cls, id: int) -> 'Recipe':
        return cls.query.get(id)

    # instance methods
    def update_last_modified(self, modified_date: datetime) -> None:
        self.last_modified = modified_date
    
    def to_dict(self):
        dirty_dict = super().to_dict()
        dirty_dict['title'] = self.edits[0].title
        dirty_dict['description'] = self.edits[0].description
        dirty_dict['img_url'] = self.edits[0].img_url

        return dirty_dict
    

# Experiments
class Experiment(DictableColumn, db.Model):
    """An experiment or journal entry that belongs to a recipe."""

    # SQL-side setup
    __tablename__ = 'experiments'

    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id'))
    commit_msg = db.Column(db.String)
    notes = db.Column(db.Text)
    commit_date = db.Column(db.DateTime)

    ## planning an experiment
    create_date = db.Column(db.DateTime) # to allow planning experiments in advance

    ## permissions
    commit_by = db.Column(db.Integer, db.ForeignKey('users.id')) # to allow experiments submitted by collaborators

    # Relationships
    recipe = db.relationship('Recipe', back_populates='experiments') # one corresponsding Recipe object
    committer = db.relationship('User', back_populates='committed_experiments')

    # misc class variable
    htmlclass = 'experiment'

    # Class Methods
    def __repr__(self):
        return f'<Experiment id={self.id} commit_date={self.commit_date}>'
    
    def to_dict(self):
        dicted = super().to_dict()
        dicted['item_type'] = 'experiment'
        return dicted

    ## Class CRUD Methods
    @classmethod
    def create(cls, parent_recipe: Recipe, commit_msg: str, notes: str,
               commit_date: datetime, create_date: datetime, committer: User):
        """Create and return a new experiment"""
        return cls(recipe=parent_recipe, commit_msg=commit_msg,
                   notes=notes, commit_date=commit_date, 
                   create_date=create_date, committer=committer)
    
    @classmethod
    def get_by_id(cls, id: int) -> 'Experiment':
        return cls.query.get(id)

# Edits
class Edit(DictableColumn, db.Model):
    """An edit to a recipe."""

    # SQL-side setup
    __tablename__ = 'edits'

    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id'))
    title = db.Column(db.String)
    description = db.Column(db.String)
    ingredients = db.Column(db.Text)
    instructions = db.Column(db.Text)
    commit_date = db.Column(db.DateTime)
    
    # new 11 April - for display pic
    img_url = db.Column(db.String)

    # permissions
    commit_by = db.Column(db.Integer, db.ForeignKey('users.id')) # to allow edits submitted by collaborators
    pending_approval = db.Column(db.Boolean) # for users with no edit access, to be approved
    # on submission: pending_approval -> true
    # if approved: pending_approval -> null, treated as normal edit

    # Relationships
    recipe = db.relationship('Recipe', back_populates='edits') # one corresponding Recipe object
    committer = db.relationship('User', back_populates='committed_edits')

    # misc class variable
    htmlclass = 'edit'

    # Class Methods
    def __repr__(self):
        return f'<Edit id={self.id} commit_date={self.commit_date}>'
    
    def to_dict(self):
        dicted = super().to_dict()
        dicted['item_type'] = 'edit'
        return dicted
    
    ## Class CRUD Methods
    @classmethod
    def create(cls, recipe: Recipe, title: str, desc: str, ingredients: str, 
               instructions: str, img_url: str, commit_date: datetime|None, 
               committer: User|None=None, pending_approval: bool = False) -> 'Edit':
        return cls(recipe=recipe, title=title, description=desc,
                   ingredients=ingredients, instructions=instructions,
                   img_url=img_url, pending_approval=pending_approval,
                   commit_date=commit_date, committer=committer)
    
    @classmethod
    def get_by_id(cls, id: int) -> 'Edit':
        return cls.query.get(id)
    
    # instance method
    ## get the previous edit object to this one. or None if it is the creation edit
    def get_previous(self) -> 'Edit':
        edits_list = self.recipe.edits
        return None if edits_list[-1] == self else edits_list[edits_list.index(self) + 1]

# Permissions
class Permission(db.Model):
    """Middle table to map users to recipes they can view or edit"""

    __tablename__ = 'permissions'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id'), primary_key=True)
    can_experiment = db.Column(db.Boolean)
    can_edit = db.Column(db.Boolean)

    # # Relationships
    recipe = db.relationship('Recipe', back_populates='permissions') # one corresponding Recipe object
    user = db.relationship('User', back_populates='permissions')

    @classmethod
    def get_by_user_and_recipe(cls, user_id, recipe_id):
        return cls.query.get({'user_id': user_id, 'recipe_id':recipe_id})
    
    @classmethod
    def create(cls, user_id, recipe_id, can_experiment=True, can_edit=True):
        return cls(user_id=user_id,recipe_id=recipe_id, can_experiment=can_experiment, can_edit=can_edit)

# CONNECTING TO DB
def connect_to_db(flask_app, db_uri="test", echo=True):
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql:///{db_uri}'
    flask_app.config['SQLALCHEMY_ECHO'] = echo
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.app = flask_app
    db.init_app(flask_app)

    print(f"Connected to the db '{db_uri}'!")

if __name__ == '__main__':
    from server import app
    import sys

    if sys.argv[1:2]:
        connect_to_db(app, sys.argv[1])
    else:
        connect_to_db(app)
    
    app.app_context().push()