"""Models for Forkd (recipe journaling app)"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# DATA MODEL
# Users
class User(db.Model):
    """A user."""
    
    # SQL-side setup
    __tablename__ = 'users'

    id = db.Column(db.Integer, autoincrement = True, primary_key=True)
    email = db.Column(db.String, unique = True)
    password = db.Column(db.String)
    username = db.Column(db.String, unique = True)

    # Relationships
    recipes = db.relationship('Recipe', back_populates='owner', order_by='desc(Recipe.last_modified)') # list of corresponding Recipe objects

    # Class Methods
    def __repr__(self):
        return f'<User username={self.username}>'
    
    ## Class CRUD Methods
    @classmethod
    def create(cls, email: str, password: str, username: str):
        """Create and return a new user."""
        return cls(email=email, password=password, username=username)
    
    @classmethod
    def get_all(cls):
        return cls.query.all()
    
    @classmethod
    def get_by_username(cls, username):
        try:
            return cls.query.filter_by(username=username).one()
        except:
            return None 

# Recipes
class Recipe(db.Model):
    """A recipe."""
    
    # SQL-side setup
    __tablename__ = 'recipes'

    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    source_url = db.Column(db.String)
    ## should we put last modified date here?? or query?
    last_modified = db.Column(db.DateTime)

    ## 2.0 or stretch features
    forked_from = db.Column(db.Integer)
    is_public = db.Column(db.Boolean)

    # Relationships
    owner = db.relationship('User', back_populates='recipes') # one corresponding User object
    experiments = db.relationship('Experiment', back_populates='recipe', order_by='desc(Experiment.commit_date)') # list of corresponding Experiment objects
    edits = db.relationship('Edit', back_populates='recipe', order_by='desc(Edit.commit_date)') # list of corresponding Edit objects

    # Class Methods
    def __repr__(self):
        return f'<Recipe id={self.id}>'

    ## Class CRUD Methods
    @classmethod
    def create(cls, owner, modified_on, is_public=True, source_url=None, forked_from=None):
        """Create and return a new recipe."""
        return cls(owner=owner, last_modified=modified_on, 
                   is_public=is_public, source_url=source_url, forked_from=forked_from)
    
    @classmethod
    def get_by_id(cls, id):
        return cls.query.get(id)
    
    # @classmethod
    # def createNew(cls, owner, modified_on, is_public=True, source_url=None, forked_from=None,
    #               ):
    #     """Create and return a new recipe, with associated first edit"""
    #     this_recipe = cls(owner=owner, last_modified=modified_on, 
    #                is_public=is_public, source_url=source_url, forked_from=forked_from)
    #     first_edit = Edit.create()

# Experiments
class Experiment(db.Model):
    """An experiment or journal entry that belongs to a recipe."""

    # SQL-side setup
    __tablename__ = 'experiments'

    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id'))
    commit_msg = db.Column(db.String)
    notes = db.Column(db.Text)
    commit_date = db.Column(db.DateTime)

    ## 2.0 or stretch features
    create_date = db.Column(db.DateTime) # to allow planning experiments in advance
    commit_by = db.Column(db.Integer) # to allow experiments submitted by collaborators

    # Relationships
    recipe = db.relationship('Recipe', back_populates='experiments') # one corresponsding Recipe object

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

# Edits
class Edit(db.Model):
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

    ## 2.0 or stretch features
    commit_by = db.Column(db.Integer) # to allow edits submitted by collaborators

    # Relationships
    recipe = db.relationship('Recipe', back_populates='edits') # one corresponding Recipe object

    # Class Methods
    def __repr__(self):
        return f'<Edit id={self.id} commit_date={self.commit_date}>'
    
    ## Class CRUD Methods
    @classmethod
    def create(cls, recipe, title, desc, ingredients, 
               instructions, commit_date, commit_by=None):
        return cls(recipe=recipe, title=title, description=desc,
                   ingredients=ingredients, instructions=instructions,
                   commit_date=commit_date, commit_by=commit_by)

# CONNECTING TO DB
def connect_to_db(flask_app, db_uri="postgresql:///forkd", echo=True):
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    flask_app.config['SQLALCHEMY_ECHO'] = echo
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.app = flask_app
    db.init_app(flask_app)

    print("Connected to the db!")

if __name__ == '__main__':
    from server import app

    connect_to_db(app)
    app.app_context().push()