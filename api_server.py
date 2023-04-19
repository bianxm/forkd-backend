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
import re

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

@app.route('/api/tokens', methods=['POST']) # login - give a token
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

@app.route('/api/tokens', methods=['DELETE']) # logout - revoke token
@token_auth.login_required
def revoke_token():
    token_auth.current_user().revoke_token()
    db.session.commit()
    return '', 204

@app.route('/api/me')
@token_auth.login_required
def get_user():
    return {'username' : token_auth.current_user().username}

################ Endpoint '/api/users' ############################
# GET -- return all users TO PAGINATE
@app.route('/api/users')
def read_all_users():
    return [user.to_dict() for user in model.User.get_all()], 200

# POST -- create a new user
@app.route('/api/users', methods=['POST'])
def create_user():
    # parse out POST params 
    params = request.get_json(force=True)
    print(params)
    given_email = params.get('email')
    given_username = params.get('username')
    given_password =  params.get('password')
    # given_email = request.form.get('email')
    # given_username = request.form.get('username')
    # given_password = request.form.get('password')
    
    ### input validation
    # validate that fields are not empty!!!!
    if not all([given_email, given_password, given_username]) or re.match(given_username, r'^[A-Za-z0-9_-]+$'):
        return error_response(400)
    # validate that email or username not already taken
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
    
    return 'Account successfully created', 201


################ Endpoint '/api/users/<username>' ############################
# GET -- return user details and list of recipes
@app.route('/api/users/<username>')
@token_auth.login_required(optional=True)
def read_user_profile(username):
    owner = model.User.get_by_username(username)
    if not owner:
        return error_response(404)

    user_details = owner.to_dict()
    viewer = token_auth.current_user()
    
    if viewer is not owner:
        viewable_recipes = ph.get_viewable_recipes(owner.id, viewer.id if viewer else None)
        user_details['recipes'] = [recipe.to_dict() for recipe in viewable_recipes]
    else:
        # return everything the user owns, plus everything shared with them
        own_recipes = owner.recipes
        shared_recipes = ph.get_shared_with_me(owner.id)
        user_details['my_recipes'] = [recipe.to_dict() for recipe in own_recipes]
        user_details['my_recipes'] = [recipe.to_dict() for recipe in shared_recipes]
    return user_details

# DELETE -- Delete this user
@app.route('/api/users/<id>', methods=['DELETE'])
@token_auth.login_required()
def delete_user(id):
    submitter = token_auth.current_user()
    if submitter.id != id:
        return error_response(403)
    
    if submitter.is_temp_user:
        # go through all their recipes and delete and commit
        for recipe in submitter.recipes:
            db.session.delete(recipe)
        db.session.commit()
        # go through all their edits, experiments and delete (basically in other's recipes)
        for edit in submitter.committed_edits:
            db.session.delete(edit)
        for experiment in submitter.committed_experiments:
            db.session.delete(experiment)
        db.session.commit()
        db.session.delete(submitter)
        db.session.commit()
        return 'Delete successful', 200
        # EDITING EXPERIMENTS: they can't edit other people's experiments in other people's recipes
        # they can't delete edits and experiments in other people's recipes either (but can in their own)
        # but they can in their own recipes
    else:
        # go through user's recipes
        # get all permissions, and pass ownership to someone with highest permission 
        # then delete all recipes
        # then delete user
        # their edits and experiments in other people's recipes will be kept but dis-associated (put 'deactivated user')
        pass

# PUT (or PATCH?) -- Edit user details
# @app.route('/api/users/<id>', methods=['PATCH'])
# @token_auth.login_required()
# def update_user(id):
#     submitter = token_auth.current_user()
#     if submitter.id != id:
#         return error_response(403)
    
#     # parse out PATCH form params
#     # could only be one of: email, 


#     # update db and commit
#     pass
    

################ Endpoint '/api/recipes' ############################
# GET -- return list of all recipes (paginated, with filters)
# @app.route('/api/recipes')
# @token_auth.login_required(optional=True)

# POST -- create a new recipe
@app.route('/api/recipes', methods=['POST'])
@token_auth.login_required()
def create_new_recipe():
    # parse out POST params
    params = request.get_json()
    title = params.get('title')
    description = params.get('description')
    ingredients = params.get('ingredients')
    instructions = params.get('instructions')
    given_url = params.get('url')
    forked_from_id = params.get('forked-from') 
    img_url = params.get('img-url') 
    is_public = params.get('set-is-public')
    is_experiments_public = params.get('set-is-exps-public')
    # title = request.form.get('title')
    # description = request.form.get('description')
    # ingredients = request.form.get('ingredients')
    # instructions = request.form.get('instructions')
    # given_url = request.form.get('url')
    # forked_from_id = request.form.get('forked-from') 
    # img_url = request.form.get('img-url') 
    # is_public = request.form.get('set-is-public')
    # is_experiments_public = request.form.get('set-is-exps-public')


    submitter = token_auth.current_user()
    now = datetime.now()

    # input validation needed!

    # db changes
    newRecipe = model.Recipe.create(owner=submitter, modified_on=now, 
                                    is_public=is_public, is_experiments_public=is_experiments_public,
                                    source_url=given_url, forked_from=forked_from_id) # create recipe
    model.Edit.create(newRecipe, title, description, ingredients, instructions, img_url, now, submitter) # create first edit
    model.db.session.add(newRecipe)
    model.db.session.commit()
    return 'Recipe successfully created', 201

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
    # if recipe doesnt exist
    if not this_recipe:
        return error_response(404)

    # check if sender is allowed to delete this recipe
    if token_auth.current_user() != this_recipe.owner:
        return error_response(403)
    
    db.session.delete(this_recipe)
    db.session.commit()
    return 'Recipe successfully deleted', 200

# POST -- Create a new experiment
@app.route('/api/recipes/<id>', methods=['POST'])
@token_auth.login_required()
def create_new_exp(id):
    # parse out POST params
    params = request.get_json()
    commit_msg = params.get('commit-msg')
    notes = params.get('notes')
    # commit_msg = request.form.get('commit-msg')
    # notes = request.form.get('notes')
    now = datetime.now()
    this_recipe = model.Recipe.get_by_id(id)
    submitter = token_auth.current_user()

    # check that submitter is allowed to add a new experiment to given recipe
    # if this_recipe.owner.id != session.get('user_id'):
    #     flash('You are not allowed to add an experiment to that recipe!','danger')
    #     return render_template('404.html')
    if this_recipe.user_id != submitter.id:
        permission = model.Permission.get_by_user_and_recipe(submitter.id, id)
        if not permission or not permission.can_experiment:
            return error_response(403)
    
    # db changes
    new_experiment = model.Experiment.create(this_recipe, commit_msg, notes, now,
                                             now, token_auth.current_user()) # create experiment
    this_recipe.update_last_modified(now) # update recipe's last_modified field
    model.db.session.add_all([new_experiment, this_recipe])
    model.db.session.commit()
    return 'Experiment successfully created', 201

# PUT (or PATCH?) -- Create a new edit
@app.route('/api/recipes/<id>', methods=['PUT']) #or PATCH?
@token_auth.login_required()
def create_new_edit(id):
    # parse out POST params
    params = request.get_json()
    title = params.get('title')
    description = params.get('description')
    ingredients = params.get('ingredients')
    instructions = params.get('instructions')
    img_url = params.get('img-url')
    # title = request.form.get('title')
    # description = request.form.get('description')
    # ingredients = request.form.get('ingredients')
    # instructions = request.form.get('instructions')
    # img_url = request.form.get('img-url')
    now = datetime.now()
    this_recipe = model.Recipe.get_by_id(id)
    submitter = token_auth.current_user()
    pending_approval = False
    
    # check that submitter is allowed to add a new edit to given recipe
    if this_recipe.user_id != submitter.id:
        permission = model.Permission.get_by_user_and_recipe(submitter.id, id)
        if not permission or not permission.can_experiment:
            return error_response(403)
        if not permission.can_edit and permission.can_experiment:
            # submit for approval, basically pending approval flag is True,
            # and commit date is empty
            # and recipe last_modified is not changed
            now = None
            pending_approval = True

    # db changes
    new_edit = model.Edit.create(this_recipe,
                                 title, description,
                                 ingredients, instructions,
                                 img_url,
                                 now, submitter,
                                 pending_approval) # create new edit
    if now:
        this_recipe.update_last_modified(now) # update recipe's last_modified field
    model.db.session.add_all([new_edit, this_recipe])
    model.db.session.commit()
    return 'Experiment successfully created', 201
    
    # handle if recipe does not exist

########### Endpoint '/api/recipes/<id>/permissions' ###################
# GET - return is_public, is_experiments_public, and list of users with permissions
@app.route('/api/recipes/<recipe_id>/permissions')
@token_auth.login_required()
def read_permissions(recipe_id):
    response = dict()
    submitter = token_auth.current_user()
    recipe = model.Recipe.get_by_id(recipe_id)
    permission = None
    if submitter is not recipe.owner:
        permission = model.Permission.get_by_user_and_recipe(submitter.id, recipe_id)
        if not (permission or recipe.is_public):
            return error_response(403)
    response['is_public'] = recipe.is_public
    response['is_experiments_public'] = recipe.is_experiments_public
    # if viewer is owner, or has edit access:
    # if submitter is recipe.owner or 
    if recipe.owner == submitter or permission.can_edit:
        # show shared_with
        shared_with = []
        for row in ph.get_recipe_shared_with(recipe):
            this_dict = dict()
            this_dict['username'] = row.username
            this_dict['can_edit'] = row.can_edit
            this_dict['can_experiment'] = row.can_experiment 
            shared_with.append(this_dict)
        response['shared_with'] = shared_with
    return response
# {is_public: t/f, is_experiments_public: t/f, 
# shared_with: [{username: int, can_experiment: t/f, can_edit: t/f}]}

# POST - create new permission (give new user a new permission)
# do it one by one
@app.route('/api/recipes/<recipe_id>/permissions', methods=['POST'])
@token_auth.login_required()
def create_permission(recipe_id):
    # parse out POST params
    params = request.get_json()
    new_user_id = params.get('user_id')
    can_experiment = params.get('can_experiment')
    can_edit = params.get('can_edit')
    # new_user_id = request.form.get('user_id')
    # can_experiment = request.form.get('can_experiment')
    # can_edit = request.form.get('can_edit')
    submitter = token_auth.current_user()
    recipe = model.Recipe.get_by_id(recipe_id)
    
    ## input validation
    # can_edit can only be True if can_experiment is also True
    if can_edit and not can_experiment:
        return error_response(400)
    # only if submitter is owner or can_edit
    if recipe.user_id!=submitter.id:
        submitters_p = model.Permission.get_by_user_and_recipe(submitter.id, recipe_id)
        if (not submitters_p) or (not submitters_p.can_edit):
            return error_response(403)
    # if association already exists, error out (409 - Conflict)
    if model.Permission.get_by_user_and_recipe(new_user_id, recipe_id):
        return error_response(409)

    # otherwise, make a new permission row
    new_permission = model.Permission.create(new_user_id, recipe_id,can_experiment,can_edit)
    db.session.add(new_permission)
    db.session.commit()
    return 'New permission added', 204

# PATCH - edit permission level
@app.route('/api/recipes/<recipe_id>/permissions', methods=['PUT'])
@token_auth.login_required()
def update_or_delete_permission(recipe_id):
    # parse out POST params
    params = request.get_json()
    new_user_id = params.get('user_id')
    # new_user_id = request.form.get('user_id')
    ## TODO CONVERT THESE
    can_experiment = params.get('can_experiment')
    can_edit = params.get('can_edit')
    # can_experiment = request.form.get('can_experiment')
    # can_edit = request.form.get('can_edit')
    recipe = model.Recipe.get_by_id(recipe_id)
    submitter = token_auth.current_user()

    ## validation
    # only if submitter is owner or can_edit
    if recipe.user_id!=submitter.id:
        submitters_p = model.Permission.get_by_user_and_recipe(submitter.id, recipe_id)
        if (not submitters_p) or (not submitters_p.can_edit):
            return error_response(403)
    # if association doesn't exist, error out (404 - Not Found)
    permission = model.Permission.get_by_user_and_recipe(new_user_id, recipe_id)
    if not permission:
        return error_response(409)

    # otherwise, update permission
    # if can_edit and can_experiment both set to False, delete the row
    if not can_edit and not can_experiment: # perhaps set to 1 or 0? anyway just remember need to cast the form.get
        # delete the permission
        db.session.delete(permission)
    else:
        # edit the permission
        permission.can_edit = can_edit
        permission.can_experiment = can_experiment
        db.session.add(permission)
    db.session.commit()
    return 'Permission modified', 200

################ Endpoint '/api/edits/<id>' ############################
# @app.route('/api/edits/<id>')
# @token_auth.login_required(optional=True)

@app.route('/api/edits/<id>', methods=['DELETE'])
@token_auth.login_required()
def delete_edit(id):
    # get experiment from server by id
    this_edit = model.Edit.get_by_id(id)
    submitter = token_auth.current_user()
    # handle if edit does not exist
    if not this_edit:
        return error_response(404)
    # handle if first edit -- CANNOT DELETE
    if this_edit == this_edit.recipe.edits[-1]:
        return error_response(409, 'Cannot delete creation edit')

    # check if sender is allowed to delete
    # can delete if user is owner of recipe or has edit access
    if submitter.id != this_edit.recipe.user_id:
        permission = model.Permission.get_by_user_and_recipe(submitter.id, this_edit.recipe_id)
        if not permission or not permission.can_edit or submitter.is_temp_user:
            return error_response(403)
    
    # delete edit
    db.session.delete(this_edit)
    db.session.commit()
    return 'Edit successfully deleted', 200


@app.route('/api/edits/<id>', methods=['PATCH'])
@token_auth.login_required()
def approve_pending_edit(id):
    edit = model.Edit.get_by_id(id)
    if not edit:
        return error_response(404)
    if not edit.pending_approval:
        return error_response(409)
    # only if submitter is owner or has edit access (and isn't a temp user)
    # check if sender is allowed to delete
    # can delete if user is owner of recipe or has edit access
    submitter = token_auth.current_user()
    if submitter.id != edit.recipe.user_id:
        permission = model.Permission.get_by_user_and_recipe(submitter.id, edit.recipe_id)
        if not permission or not permission.can_edit or submitter.is_temp_user:
            return error_response(403)

    now = datetime.now()
    edit.pending_approval = False
    edit.commit_date = now
    edit.recipe.update_last_modified(now)
    db.session.add_all([edit, edit.recipe])
    db.session.commit()
    return 'Edit approved', 200

################ Endpoint '/api/experiments/<id>' ############################
# @app.route('/api/experiments/<id>')
# @token_auth.login_required(optional=True)

@app.route('/api/experiments/<id>', methods=['DELETE'])
@token_auth.login_required()
def delete_experiment(id):
    # get experiment from server by id
    this_experiment = model.Experiment.get_by_id(id)
    submitter = token_auth.current_user()
    # handle if experiment does not exist
    if not this_experiment:
        return error_response(404)

    # check if sender is allowed to delete
    # can delete if user is owner of recipe, has edit access, or is committer of experiment
    if submitter.id != this_experiment.recipe.user_id and this_experiment.commit_by != submitter.id:
        permission = model.Permission.get_by_user_and_recipe(submitter.id, this_experiment.recipe_id)
        if not permission or not permission.can_edit or submitter.is_temp_user:
            return error_response(403)
    
    # delete experiment
    db.session.delete(this_experiment)
    db.session.commit()
    return 'Experiment successfully deleted', 200

@app.route('/api/experiments/<id>', methods=['PUT'])
@token_auth.login_required()
def edit_experiment(id):
    # get experiment from server by id
    this_experiment = model.Experiment.get_by_id(id)
    submitter = token_auth.current_user()
    # handle if experiment does not exist
    if not this_experiment:
        return error_response(404)
    # can edit if user is owner of recipe, has edit access, or is committer of experiment
    if submitter.id != this_experiment.recipe.user_id and this_experiment.commit_by != submitter.id:
        permission = model.Permission.get_by_user_and_recipe(submitter.id, this_experiment.recipe_id)
        if not permission or not permission.can_edit or submitter.is_temp_user:
            return error_response(403)
    
    # parse out POST params
    params = request.get_json()
    commit_msg = params.get('commit_msg')
    notes = params.get('notes')
    date = params.get('date')
    committer = params.get('commit_by')
    # commit_msg = request.form.get('commit_msg')
    # notes = request.form.get('notes')
    # date = request.form.get('date')
    # committer = request.form.get('commit_by')

    # edit experiment
    this_experiment.commit_msg = commit_msg
    this_experiment.notes = notes
    this_experiment.commit_date = date
    this_experiment.commit_by = committer
    db.session.commit(this_experiment)
    return 'Experiment successfully updated', 200
    # return the updated experiment?

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