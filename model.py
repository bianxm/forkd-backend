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
    recipes = db.relationship('Recipe', back_populates='owner') # list of corresponding Recipe objects

    # Class Methods
    def __repr__(self):
        return f'<User username={self.username}>'

# Recipes
class Recipe(db.Model):
    """A recipe."""
    
    # SQL-side setup
    __tablename__ = 'recipes'

    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    source_url = db.Column(db.String)
    ## should we put last modified date here?? or query?

    ## 2.0 or stretch features
    forked_from = db.Column(db.Integer)
    is_public = db.Column(db.Boolean)

    # Relationships
    owner = db.relationship('User', back_populates='recipes') # one corresponding User object
    experiments = db.relationship('Experiment', back_populates='recipe') # list of corresponding Experiment objects
    edits = db.relationship('Edit', back_populates='recipe') # list of corresponding Edit objects

    # Class Methods
    def __repr__(self):
        return f'<Recipe id={self.id}>'

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