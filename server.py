"""Server for Forkd"""

from flask import (Flask, render_template, request,
                   flash, session, redirect, make_response)
from model import connect_to_db, db
from jinja2 import StrictUndefined
from dotenv import load_dotenv
import os
import model
from datetime import datetime
import requests

load_dotenv()
SPOONACULAR_KEY = os.environ['SPOONACULAR_KEY']

app = Flask(__name__)
app.secret_key = os.environ['FLASK_KEY']
app.jinja_env.undefined = StrictUndefined


# DISPLAY ROUTES
@app.route('/')
def show_homepage():
    return render_template('homepage.html')

# mainly for dev purposes only: display all users
@app.route('/users') 
def show_all_users():
    all_users = model.User.get_all()
    return render_template('all_users.html', all_users=all_users)

@app.route('/signup')
def show_signup_form():
    return render_template('signup.html')

@app.route('/login')
def show_login_form():
    return render_template('login.html')

# Sign Up
@app.route('/signup', methods=['POST'])
def register_user():
    # parse out POST params 
    given_email = request.form.get('email')
    given_username = request.form.get('username')
    given_password = request.form.get('password')
    confirm_password = request.form.get('confirmPassword')
    
    # input validation
    if model.User.get_by_email(given_email):
        flash('Sorry, that email is already registered. Please sign in instead','danger')
        return redirect('/')
    if model.User.get_by_username(given_username):
        # better as AJAX perhaps?
        flash('Sorry, that username is already taken. Please try another one.','danger')
        return redirect('/')
    if given_password != confirm_password:
        flash("Sorry, passwords don't match",'danger') 
        return redirect('/')
    
    # if input is valid, create the user
    new_user = model.User.create(given_email, given_password, given_username)
    db.session.add(new_user)
    db.session.commit()
    flash(f"User created! {new_user}", 'success')
    return redirect('/')

@app.route('/login', methods=['POST'])
def login():
    # parse out POST params
    given_id = request.form.get('login_id')
    given_password = request.form.get('password')
    
    # input validation
    if '@' in given_id:
        this_user = model.User.get_by_email(given_id)
    else:
        this_user = model.User.get_by_username(given_id)
    if not this_user:
        flash('User not found. Please sign up','warning')
    else:
        if not this_user.password == given_password:
            flash('Wrong password','danger')
        else:
            # input is valid, so save user_id in session
            session['user_id'] = this_user.id
            session['username'] = this_user.username
            flash('Logged in!', 'success')
            return redirect(f'/{this_user.username}') 
    return redirect('/')


@app.route('/logout')
def logout():
    session.pop('user_id')
    session.pop('username')
    flash('Successfully logged out','success')
    return redirect('/')

@app.route('/<username>')
def show_user_profile(username):
    this_user = model.User.get_by_username(username)
    if this_user is None:
        return render_template('404.html')
    else:
        return render_template('user_profile.html', user=this_user)

@app.route('/<username>/<recipe_id>')
def show_recipe(username, recipe_id):
    this_recipe = model.Recipe.get_by_id(recipe_id)
    owner = model.User.get_by_username(username)
    
    # if given owner in url doesn't own the recipe, 404 error
    if this_recipe not in owner.recipes:
        return render_template('404.html')

    timeline = this_recipe.experiments + this_recipe.edits # combine lists to get full timeline
    return render_template('recipe.html', owner=owner, recipe=this_recipe, timeline_items=timeline)

@app.route('/newRecipe')
def new_recipe_form():
    return render_template('new_recipe_form.html')

@app.route('/newRecipe', methods=['POST'])
def submit_new_recipe():
    # parse out POST params
    title = request.form.get('title')
    description = request.form.get('description')
    ingredients = request.form.get('ingredients')
    instructions = request.form.get('instructions')
    given_url = request.form.get('url')
    forked_from_id = request.form.get('forked-from') 

    submitter_id = session.get('user_id')
    submitter = model.User.get_by_id(submitter_id)
    now = datetime.now()

    # db changes
    newRecipe = model.Recipe.create(owner=submitter, modified_on=now, source_url=given_url, forked_from=forked_from_id) # create recipe
    model.Edit.create(newRecipe, title, description, ingredients, instructions, now) # create first edit
    model.db.session.add(newRecipe)
    model.db.session.commit()
    return redirect(f"/{session.get('username')}")

@app.route('/newExp')
def new_exp_form():
    parent_recipe_id = request.args.get('recipe')
    this_recipe = model.Recipe.get_by_id(parent_recipe_id)
    return render_template('new_experiment_form.html',recipe=this_recipe)

@app.route('/newExp', methods=['POST'])
def submit_new_exp():
    # parse out POST params
    commit_msg = request.form.get('commit-msg')
    notes = request.form.get('notes')
    recipe_id = request.form.get('recipe_id')
    now = datetime.now()
    this_recipe = model.Recipe.get_by_id(recipe_id)
    
    # db changes
    new_experiment = model.Experiment.create(this_recipe, commit_msg, notes, now) # create experiment
    this_recipe.update_last_modified(now) # update recipe's last_modified field
    model.db.session.add_all([new_experiment, this_recipe])
    model.db.session.commit()
    flash('New experiment created!','success')
    return redirect(f"/{session.get('username')}/{recipe_id}")

@app.route('/newEdit')
def new_edit_form():
    parent_recipe_id = request.args.get('recipe')
    this_recipe = model.Recipe.get_by_id(parent_recipe_id)
    return render_template('new_edit_form.html',recipe=this_recipe)

@app.route('/newEdit', methods=['POST'])
def submit_new_edit():
    # parse out POST params
    recipe_id = request.form.get('recipe_id')
    title = request.form.get('title')
    description = request.form.get('description')
    ingredients = request.form.get('ingredients')
    instructions = request.form.get('instructions')
    now = datetime.now()
    this_recipe = model.Recipe.get_by_id(recipe_id)
    
    # db changes
    new_edit = model.Edit.create(this_recipe,
                                 title, description,
                                 ingredients, instructions,
                                 now) # create new edit
    this_recipe.update_last_modified(now) # update recipe's last_modified field
    model.db.session.add_all([new_edit, this_recipe])
    model.db.session.commit()

    # route back to recipe timeline
    flash('New edit created!','success')
    return redirect(f"/{session.get('username')}/{recipe_id}")


# API ROUTES
@app.route('/api/extractRecipe')
def extract_recipe_from_url():
    given_url = request.args.get('url')
    # return info from spoonacular 
    # (just title, desc, ingredients, instructions)

    # consider using helper functions so it's not all in the route
    url = f'https://api.spoonacular.com/recipes/extract'
    res = requests.get(url, {'apiKey':SPOONACULAR_KEY,
                             'url': given_url,
                             'forceExtraction':'false',
                             'analyze': 'false',
                             'includeNutrition':'false',
                             'includeTaste':'false'})
    
    if res.status_code != 200:
        make_response('External API call failed', 400)
    
    recipe_details = res.json()

    return {'title': recipe_details.get('title'),
            'desc': f"Grabbed via Spoonacular from {recipe_details.get('sourceName')}\nGiven summary: {recipe_details.get('summary')}\nGiven license: {recipe_details.get('license')}",
            'ingredients': recipe_details.get('extendedIngredients'),
            'instructions': recipe_details.get('instructions'),
            'imgUrl': recipe_details.get('image')}

@app.route('/api/experiment/<id>')
def experiment_details(id):
    # get experiment from server by id
    this_experiment = model.Experiment.get_by_id(id)
    # return in json
    return this_experiment.to_dict()

@app.route('/api/edit/<id>')
def edit_details(id):
    # get given edit and previous edit from server by id
    this_edit = model.Edit.get_by_id(id)
    prev_edit = this_edit.get_previous()
    # return in json
    return {'curr':this_edit.to_dict(), 
            'prev':prev_edit.to_dict() if prev_edit is not None else None}

if __name__ == '__main__':
    connect_to_db(app)
    app.run(host='0.0.0.0', debug=True)