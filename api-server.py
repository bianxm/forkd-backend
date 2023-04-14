"""API Server for Forkd"""

from flask import (Flask, request, jsonify)
from model import connect_to_db, db
from jinja2 import StrictUndefined
from dotenv import load_dotenv
import os
import model
from datetime import datetime
import requests
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth
from werkzeug.http import HTTP_STATUS_CODES
import permissions_helper as ph

load_dotenv()
SPOONACULAR_KEY = os.environ['SPOONACULAR_KEY']

app = Flask(__name__)
app.secret_key = os.environ['FLASK_KEY']
app.jinja_env.undefined = StrictUndefined

### Error response helper
def error_response(status_code=500, message=None):
    payload = {'error': HTTP_STATUS_CODES.get(status_code, 'Unknown error')}
    if message:
        payload['message'] = message
    response = jsonify(payload)
    response.status_code = status_code
    return response
    

################ Endpoint '/api/tokens' ############################
################ BASIC AUTH ENDPOINT ###############################
################ For login  ########################################
basic_auth = HTTPBasicAuth()

@basic_auth.verify_password
def verify_password(login: str, password: str) -> model.User:
    if '@' in login:
        this_user = model.User.get_by_email(login)
    else:
        this_user = model.User.get_by_username(login)

    if this_user and this_user.is_password_correct(password):
        return this_user

@basic_auth.error_handler
def basic_auth_error(status):
    return error_response(status)

@app.route('/tokens', methods=['POST']) # login - give a token
@basic_auth.login_required
def get_token():
    token = basic_auth.current_user().get_token()
    db.session.commit()
    return {'token': token}, 200

token_auth = HTTPTokenAuth()

@token_auth.verify_token
def verify_token(token):
    return model.User.check_token(token) if token else None

@token_auth.error_handler
def token_auth_error(status):
    return error_response(status)

@app.route('/tokens', methods=['DELETE']) # logout - revoke token
@token_auth.login_required
def revoke_token():
    token_auth.current_user().revoke_token()
    db.session.commit()
    return '', 204

################ Endpoint '/api/users' ############################
# GET -- return all users TO PAGINATE
@app.route('/api/users')
def read_all_users():
    return [user.to_dict() for user in model.User.get_all()], 200

# POST -- create a new user
@app.route('/api/users', methods=['POST'])
def create_user():
    # parse out POST params 
    given_email = request.form.get('email')
    given_username = request.form.get('username')
    given_password = request.form.get('password')
    print(request.form)
    
    # input validation
    # validate that fields are not empty!!!!
    if model.User.get_by_email(given_email):
        return error_response(409, 'Email already taken')
    if model.User.get_by_username(given_username):
        return error_response(409, 'Username already taken')
    # password the same check will be done client-side 
    # validate that fields are not empty!!!!

    # if input is valid, create the user
    new_user = model.User.create(given_email, given_password, given_username)
    db.session.add(new_user)
    db.session.commit()
    
    return 'Account successfully created', 200


################ Endpoint '/api/users/<id>' ############################
# GET -- return user details and list of recipes
@app.route('/api/users/<id>')
@token_auth.login_required(optional=True)
def read_user_profile(id):
    this_user = model.User.get_by_id(id)
    user_details = this_user.to_dict()
    viewable_recipes = ph.get_viewable_recipes(id, token_auth.current_user().id if token_auth.current_user() else None)
    recipe_list = []
    for recipe in viewable_recipes:
        recipe_dict= recipe.to_dict() 
        recipe_dict['title'] = recipe.edits[0].title
        recipe_dict['description'] = recipe.edits[0].description
        recipe_dict['img_url'] = recipe.edits[0].img_url
        recipe_list.append(recipe_dict)
    user_details['recipes'] = recipe_list
    return user_details

# DELETE -- Delete this user
# @app.route('/api/users/<id>', methods=['DELETE'])
# @token_auth.login_required()

# PUT (or PATCH?) -- Edit user details
# @app.route('/api/users/<id>', methods=['PUT']) or PATCH?
# @token_auth.login_required()
# def update_user(id):
#     if token_auth.current_user().id != id:
#         return error_response(403)
    

################ Endpoint '/api/recipes' ############################
# GET -- return list of all recipes (paginated, with filters)
# @app.route('/api/recipes')
# @token_auth.login_required(optional=True)

# POST -- create a new recipe
@app.route('/api/recipes', methods=['POST'])
@token_auth.login_required()
def create_new_recipe():
    # parse out POST params
    title = request.form.get('title')
    description = request.form.get('description')
    ingredients = request.form.get('ingredients')
    instructions = request.form.get('instructions')
    given_url = request.form.get('url')
    forked_from_id = request.form.get('forked-from') 
    img_url = request.form.get('img-url') 
    is_public = request.form.get('set-is-public')
    is_experiments_public = request.form.get('set-is-exps-public')

    print('REQUEST.FORM',request.form)

    submitter = token_auth.current_user()
    now = datetime.now()

    # input validation needed!

    # db changes
    newRecipe = model.Recipe.create(owner=submitter, modified_on=now, 
                                    source_url=given_url, forked_from=forked_from_id) # create recipe
    model.Edit.create(newRecipe, title, description, ingredients, instructions, now) # create first edit
    model.db.session.add(newRecipe)
    model.db.session.commit()
    return 'Recipe successfully created', 204

################ Endpoint '/api/recipes/<id>' ############################
# GET -- return timeline-items list, can_edit bool, can_exp bool
@app.route('/api/recipes/<id>')
@token_auth.login_required(optional=True)
def read_recipe_timeline(id):
    # viewable_recipes = ph.get_viewable_recipes(id, token_auth.current_user().id if token_auth.current_user() else None)
    response = dict()
    timeline_items = ph.get_timeline(token_auth.current_user().id if token_auth.current_user() else None, id)
    if not timeline_items:
        return error_response(404)
    if not timeline_items[0]:
        return error_response(403, 'User cannot view this recipe')
    response['timeline_items'] = [item.to_dict() for item in timeline_items[0]]
    response['can_experiment'] = timeline_items[1]
    response['can_edit'] = timeline_items[2]
    return response

# DELETE -- Delete given recipe
@app.route('/api/recipes/<id>', methods=['DELETE'])
@token_auth.login_required()
def delete_recipe(id):
    this_recipe = model.Recipe.get_by_id(id)

    # check if sender is allowed to delete this recipe
    if token_auth.current_user() != this_recipe.owner:
        return error_response(403)
    
    db.session.delete(this_recipe)
    db.session.commit()
    return 'Recipe successfully deleted', 204

# POST -- Create a new experiment
@app.route('/api/recipes/<id>', methods=['POST'])
@token_auth.login_required()
def submit_new_exp(id):
    # parse out POST params
    commit_msg = request.form.get('commit-msg')
    notes = request.form.get('notes')
    now = datetime.now()
    this_recipe = model.Recipe.get_by_id(id)

    # check that submitter is allowed to add a new experiment to given recipe
    # if this_recipe.owner.id != session.get('user_id'):
    #     flash('You are not allowed to add an experiment to that recipe!','danger')
    #     return render_template('404.html')
    permission = model.Permission.get_by_user_and_recipe(token_auth.current_user().id, id)
    if not (getattr(permission, 'can_experiment', False) or this_recipe.owner == token_auth.current_user()):
        return error_response(403)
    
    # db changes
    new_experiment = model.Experiment.create(this_recipe, commit_msg, notes, now) # create experiment
    this_recipe.update_last_modified(now) # update recipe's last_modified field
    model.db.session.add_all([new_experiment, this_recipe])
    model.db.session.commit()
    return 'Experiment successfully created', 204

# PUT (or PATCH?) -- Create a new edit
@app.route('/api/recipes/<id>', methods=['PUT']) #or PATCH?
@token_auth.login_required()
def submit_new_edit(id):
    # parse out POST params
    title = request.form.get('title')
    description = request.form.get('description')
    ingredients = request.form.get('ingredients')
    instructions = request.form.get('instructions')
    now = datetime.now()
    this_recipe = model.Recipe.get_by_id(id)
    
    # check that submitter is allowed to add a new edit to given recipe
    permission = model.Permission.get_by_user_and_recipe(token_auth.current_user().id, id)
    if not (getattr(permission, 'can_edit', False) or this_recipe.owner == token_auth.current_user()):
        return error_response(403)

    # db changes
    new_edit = model.Edit.create(this_recipe,
                                 title, description,
                                 ingredients, instructions,
                                 now) # create new edit
    this_recipe.update_last_modified(now) # update recipe's last_modified field
    model.db.session.add_all([new_edit, this_recipe])
    model.db.session.commit()
    return 'Experiment successfully created', 204
    
    # handle if recipe does not exist

########### Endpoint '/api/recipes/<id>/permissions' ###################
# GET - return is_public, is_experiments_public, and list of users with permissions
# POST - create new permission (give new user a new permission)
# PATCH - edit permission level
# DELETE - revoke a permission

################ Endpoint '/api/edits/<id>' ############################
# @app.route('/api/edits/<id>')
# @token_auth.login_required(optional=True)

@app.route('/api/edits/<id>', methods=['DELETE'])
@token_auth.login_required()
def delete_edit(id):
    # get experiment from server by id
    this_edit = model.Edit.get_by_id(id)
    # handle if edit does not exist
    # handle if first edit -- CANNOT DELETE

    # check if sender is allowed to delete
    if token_auth.current_user().id != this_edit.recipe.user_id:
        return error_response(403)
    
    # delete experiment
    db.session.delete(this_edit)
    db.session.commit()
    return 'Edit successfully deleted', 200


# @app.route('/api/edits/<id>', methods=['PUT']) or PATCH?
# @token_auth.login_required()

################ Endpoint '/api/experiments/<id>' ############################
# @app.route('/api/experiments/<id>')
# @token_auth.login_required(optional=True)

@app.route('/api/experiments/<id>', methods=['DELETE'])
@token_auth.login_required()
def delete_experiment(id):
    # get experiment from server by id
    this_experiment = model.Experiment.get_by_id(id)
    # handle if experiment does not exist

    # check if sender is allowed to delete
    if token_auth.current_user().id != this_experiment.recipe.user_id:
        return error_response(403)
    
    # delete experiment
    db.session.delete(this_experiment)
    db.session.commit()
    return 'Experiment successfully deleted', 200

# @app.route('/api/experiments/<id>', methods=['PUT']) or PATCH?
# @token_auth.login_required()

@app.route('/api/extract-recipe')
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
        return error_response(400,'External API call failed')
    
    recipe_details = res.json()

    return {'title': recipe_details.get('title'),
            'desc': f"Grabbed via Spoonacular from {recipe_details.get('sourceName')}\nGiven summary: {recipe_details.get('summary')}\nGiven license: {recipe_details.get('license')}",
            'ingredients': recipe_details.get('extendedIngredients'),
            'instructions': recipe_details.get('instructions'),
            'imgUrl': recipe_details.get('image')}, 200



if __name__ == '__main__':
    connect_to_db(app, 'forkd-p')
    app.run(host='0.0.0.0', debug=True)