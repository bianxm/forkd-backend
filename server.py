"""Server for Forkd"""

from flask import (Flask, render_template, request,
                   flash, session, redirect, jsonify)
from model import connect_to_db, db
from jinja2 import StrictUndefined
from dotenv import load_dotenv
import os
import model

load_dotenv()

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

# Sign Up
@app.route('/users', methods=['POST'])
def register_user():
    given_email = request.form.get('email')
    given_username = request.form.get('username')
    given_password = request.form.get('password')
    confirm_password = request.form.get('confirmPassword')
    print(given_password)
    print(confirm_password)
    print(given_password != confirm_password)
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
    new_user = model.User.create(given_email, given_password, given_username)
    db.session.add(new_user)
    db.session.commit()
    flash(f"User created! {new_user}", 'success')
    return redirect('/')

@app.route('/login', methods=['POST'])
def login():
    given_id = request.form.get('login_id')
    given_password = request.form.get('password')
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
            # save user_id in session
            session['user_id'] = this_user.id
            session['username'] = this_user.username
            flash('Logged in!')
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

# API ROUTES
@app.route('/api/experiment/<id>')
def experiment_details(id):
    # get experiment from server by id
    this_experiment = model.Experiment.get_by_id(id)
    # return in json
    return jsonify(commit_msg=this_experiment.commit_msg,
                   notes=this_experiment.notes,
                   commit_date=this_experiment.commit_date)

if __name__ == '__main__':
    connect_to_db(app)
    app.run(host='0.0.0.0', debug=True)