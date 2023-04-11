"""Models for Forkd (recipe journaling app)"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped
from datetime import datetime
from passlib.hash import argon2

db = SQLAlchemy()

# Mixin
class DictableColumn():
    def to_dict(self):
        crowded_dict = self.__dict__
        return {key:val for key, val in crowded_dict.items() 
                if isinstance(val,(str,int,float,bool, list, dict, type(None), datetime))}

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

    # Relationships
    recipes = db.relationship('Recipe', back_populates='owner', order_by='desc(Recipe.last_modified)') # list of corresponding Recipe objects

    # Class Methods
    def __repr__(self):
        return f'<User username={self.username}>'
    
    ## Class CRUD Methods
    @classmethod
    def create(cls, email: str, password: str, username: str) -> 'User':
        """Create and return a new user."""
        password = argon2.hash(password)
        return cls(email=email, password=password, username=username)
    
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

    # instance method -- check if password is correct
    def is_password_correct(self, given_password: str) -> bool:
        return argon2.verify(given_password, self.password)

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

    # Relationships
    owner = db.relationship('User', back_populates='recipes') # one corresponding User object
    experiments = db.relationship('Experiment', back_populates='recipe', order_by='desc(Experiment.commit_date)', cascade='save-update, merge, delete', lazy='selectin') # list of corresponding Experiment objects
    edits = db.relationship('Edit', back_populates='recipe', order_by='desc(Edit.commit_date)', cascade='save-update, merge, delete', lazy='selectin') # list of corresponding Edit objects
    parent = db.relationship('Recipe', backref='children', remote_side=[id])

    # Class Methods
    def __repr__(self):
        return f'<Recipe id={self.id}>'

    ## Class CRUD Methods
    @classmethod
    def create(cls, owner: User, modified_on: datetime, is_public: bool = True, 
               source_url: str = None, forked_from=None) -> 'Recipe':
        """Create and return a new recipe."""
        return cls(owner=owner, last_modified=modified_on, 
                   is_public=is_public, source_url=source_url, forked_from=forked_from)
    
    @classmethod
    def get_by_id(cls, id: int) -> 'Recipe':
        return cls.query.get(id)

    # instance methods
    def update_last_modified(self, modified_date: datetime) -> None:
        self.last_modified = modified_date
    

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
    commit_by = db.Column(db.Integer) # to allow experiments submitted by collaborators

    # Relationships
    recipe = db.relationship('Recipe', back_populates='experiments') # one corresponsding Recipe object

    # misc class variable
    htmlclass = 'experiment'

    # Class Methods
    def __repr__(self):
        return f'<Experiment id={self.id} commit_date={self.commit_date}>'

    ## Class CRUD Methods
    @classmethod
    def create(cls, parent_recipe, commit_msg, notes, commit_date,
               create_date=None, commit_by=None):
        """Create and return a new experiment"""
        return cls(recipe=parent_recipe, commit_msg=commit_msg,
                   notes=notes, commit_date=commit_date, 
                   create_date=create_date, commit_by=commit_by)
    
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
    commit_by = db.Column(db.Integer) # to allow edits submitted by collaborators
    pending_approval = db.Column(db.Boolean) # for users with no edit access, to be approved
    # on submission: pending_approval -> true
    # if approved: pending_approval -> null, treated as normal edit

    # Relationships
    recipe = db.relationship('Recipe', back_populates='edits') # one corresponding Recipe object

    # misc class variable
    htmlclass = 'edit'

    # Class Methods
    def __repr__(self):
        return f'<Edit id={self.id} commit_date={self.commit_date}>'
    
    ## Class CRUD Methods
    @classmethod
    def create(cls, recipe: Recipe, title: str, desc: str, ingredients: str, 
               instructions: str, commit_date: datetime, commit_by=None) -> 'Edit':
        return cls(recipe=recipe, title=title, description=desc,
                   ingredients=ingredients, instructions=instructions,
                   commit_date=commit_date, commit_by=commit_by)
    
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
    # recipe = db.relationship('Recipe', back_populates='edits') # one corresponding Recipe object
    # user = db.relationship('User')

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