"""Server for Forkd"""

from flask import (Flask, render_template, request,
                   flash, session, redirect)
from model import connect_to_db, db
from jinja2 import StrictUndefined
from dotenv import load_dotenv
import os
import model

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ['FLASK_KEY']
app.jinja_env.undefined = StrictUndefined

@app.route('/')
def show_homepage():
    return render_template('homepage.html')

# mainly for dev purposes only: display all users
@app.route('/users') 
def show_all_users():
    all_users = model.User.get_all()
    return render_template('all_users.html', all_users=all_users)

@app.route('/<username>')
def show_user_profile(username):
    this_user = model.User.get_by_username(username)
    if this_user is None:
        return render_template('user_not_found.html')
        # edit this to redirect to a 404 page
    else:
        return render_template('user_profile.html', user=this_user)

@app.route('/<username>/<recipe_id>')
def show_recipe(username, recipe_id):
    this_recipe = model.Recipe.get_by_id(recipe_id)
    this_user = model.User.get_by_username(username)
    # combine recipe.experiments and recipe.edits lists
    # and sort 
    timeline = this_recipe.experiments + this_recipe.edits
    return render_template('recipe.html', user=this_user, recipe=this_recipe, timeline_items=timeline)

if __name__ == '__main__':
    connect_to_db(app)
    app.run(host='0.0.0.0', debug=True)