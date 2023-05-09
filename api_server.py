"""API Server for Forkd"""

from flask import (Flask, request, jsonify)
from dotenv import load_dotenv # COMMENT OUT WHEN BUILDING IMAGE
import requests
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth
from werkzeug.http import HTTP_STATUS_CODES
import cloudinary.uploader

import model
import permissions_helper as ph

import re
import os
from datetime import datetime


load_dotenv() # COMMENT OUT WHEN BUILDING IMAGE
SPOONACULAR_KEY = os.environ['SPOONACULAR_KEY']
CLOUDINARY_KEY = os.environ['CLOUDINARY_KEY']
CLOUDINARY_SECRET = os.environ['CLOUDINARY_SECRET']
RDS_URI = os.environ['RDS_URI'] # for prod
DEV_URI = os.environ['DEV_URI']
CLOUD_NAME = 'dw0c9rwkd'

app = Flask(__name__)
app.secret_key = os.environ['FLASK_KEY']
# model.connect_to_db(app, RDS_URI, False)      # using Amazon RDS instance, uncomment to build image

### Error response helper
def error_response(status_code=500, message=None):
    payload = {'error': HTTP_STATUS_CODES.get(status_code, 'Unknown error')}
    if message:
        payload['message'] = message
    response = jsonify(payload)
    response.status_code = status_code
    return response
    

##################### Endpoint '/api/tokens' ---- for login ############################
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
    return '', 403

# POST -- expects Basic Auth Header
@app.route('/api/tokens', methods=['POST']) # login - give a token
@basic_auth.login_required
def get_token():
    token = basic_auth.current_user().get_token()
    model.db.session.commit()
    return {'token': token}, 200

token_auth = HTTPTokenAuth()

@token_auth.verify_token
def verify_token(token):
    return model.User.check_token(token) if token else None

@token_auth.error_handler
def token_auth_error(status):
    return error_response(status)

# DELETE -- expects Authentication: Bearer Header, logout - revoke token
@app.route('/api/tokens', methods=['DELETE'])
@token_auth.login_required
def revoke_token():
    if token_auth.current_user() == 'expired':
        return '', 204
    
    if token_auth.current_user().is_temp_user:
        submitter = token_auth.current_user()
        for recipe in submitter.recipes:
            model.db.session.delete(recipe)
        model.db.session.commit()
        # go through all their edits, experiments and delete (basically in other's recipes)
        for edit in submitter.committed_edits:
            model.db.session.delete(edit)
        for experiment in submitter.committed_experiments:
            model.db.session.delete(experiment)
        model.db.session.delete(submitter)
    else:
        token_auth.current_user().revoke_token()

    model.db.session.commit()
    return '', 204

# GET /api/me -- expects Authentication: Bearer Header containing session token
# returns user details corresponding to the session token
@app.route('/api/me')
@token_auth.login_required
def get_user():
    user = token_auth.current_user()
    if user == 'expired':
        return {}, 403
    user_dict = user.to_dict()
    user_dict['email'] = user.email 
    return user_dict

################ Endpoint '/api/users' ############################
# GET -- return all users; unused in Frontend
@app.route('/api/users')
def read_all_users():
    return [user.to_dict() for user in model.User.get_all()], 200

# POST -- create a new user
@app.route('/api/users', methods=['POST'])
def create_user():
    """Creates a new user.

    Expects:    {email: <string, untaken email>,
                username: <string, can only contain alphanumeric, underscore, and dash>,
                password: <string>,
                is_temp_user: <bool; if True, user will be completely deleted on logout>}
    Returns:    201 if successful
    """
    # parse out POST params 
    params = request.get_json(force=True)
    given_email = params.get('email')
    given_username = params.get('username')
    given_password =  params.get('password')
    is_temp_user = params.get('is_temp_user',False)

    ### input validation
    # validate that fields are not empty!!!! and that username is valid format
    if not all([given_email, given_password, given_username]) or not re.match(r'^[A-Za-z0-9_-]+$',given_username):
        return error_response(400)
    # validate that email or username not already taken
    if model.User.get_by_email(given_email):
        return error_response(409, 'Email already taken')
    if model.User.get_by_username(given_username):
        return error_response(409, 'Username already taken')

    # if input is valid, create the user
    new_user = model.User.create(given_email, given_password, given_username, is_temp_user)
    model.db.session.add(new_user)
    try:
        model.db.session.commit()
        return 'Account successfully created', 201
    except:
        error_response(500,'Cannot commit to db')


################ Endpoint '/api/users/<username>' ############################
# GET -- return user details and list of recipes
@app.route('/api/users/<username>')
@token_auth.login_required(optional=True)
def read_user_profile(username):
    """Gets a user's profile -- user details, plus their viewable recipes. Token auth is optional, but determines which recipes are visible depending on permissions.

    Returns:    {id: <int, unique id for user>,
                 username: <string>,
                 img_url: <string, link to user's avatar image>,
                 is_temp_user: <bool>,
                 recipes: <list of dicts:   {id: <int, unique recipe id>
                                             title: <string>,
                                             description: <string>,
                                             user_id: <int, user id of recipe owner>
                                             owner: <string, username of recipe owner>
                                             owner_avatar: <link to avatar of recipe owner>
                                             source_url: <link from which recipe was extracted>
                                             img_url: <link to image associated with recipe>,
                                             forked_from: <int, recipe id of parent recipe>,
                                             forked_from_username: <username of owner of parent recipe>,
                                             forked_from_avatar: <link to avatar of owner of parent recipe>,
                                             is_experiments_public: <bool>,
                                             is_public: <bool>,
                                             last_modified: <datetime>,
                                            }>,
                 (shared_with_me): <list, similar to recipes above. only if viewer is viewing their own username>}
    """
    viewer = token_auth.current_user()
    status = 200
    if viewer == 'expired': 
        status = 401
        viewer = None

    owner = model.User.get_by_username(username)
    if not owner:
        return error_response(404)

    user_details = owner.to_dict()
    
    if viewer is not owner:
        viewable_recipes = ph.get_viewable_recipes(owner.id, viewer.id if viewer else None)
        user_details['recipes'] = [recipe.to_dict() for recipe in viewable_recipes]
    else:
        # return everything the user owns, plus everything shared with them
        own_recipes = owner.recipes
        shared_recipes = ph.get_shared_with_me(owner.id)
        user_details['recipes'] = [recipe.to_dict() for recipe in own_recipes]
        user_details['shared_with_me'] = [recipe.to_dict() for recipe in shared_recipes]
    return user_details, status

# DELETE -- Delete this user -- UNIMPLEMENTED, returns 501
@app.route('/api/users/<id>', methods=['DELETE'])
@token_auth.login_required()
def delete_user(id):
    submitter = token_auth.current_user()
    if submitter == 'expired': 
        return error_response(401)
    if submitter.id != id:
        return error_response(403)
    # go through user's recipes
    # get all permissions, and pass ownership to someone with highest permission 
    # then delete all recipes
    # then delete user
    # their edits and experiments in other people's recipes will be kept but dis-associated (put 'deactivated user')
    return error_response(501) # Not Implemented
    

# PATCH -- Edit user details
@app.route('/api/users/<id>', methods=['PATCH'])
@token_auth.login_required()
def update_user(id):
    """Update a user's details.

    Expects ONE OF:
        - {new_email: <string for new email>}
        - {new_username: <string for new username, must adhere to username format>}
        - {password: <existing password; must be correct for change to take place>
            new_password: <string, new password>}
        - {img_url: <url of new user avatar>}
        - FORM DATA img_file: <file to be uploaded to Cloudinary> -- will return generated Cloudinary link
    Returns: 200 if successful
    """
    submitter = token_auth.current_user()
    if submitter.id != id:
        error_response(403)
    
    new_email = new_username = password = new_password = new_avatar = file = None
    
    # parse out PATCH form params
    if request.headers.get('Content-Type') == 'application/json':
        params = request.get_json(force=True)
        new_email = params.get('new_email')
        new_username = params.get('new_username')
        password =  params.get('password') # only required to change password
        new_password =  params.get('new_password')
        new_avatar = params.get('img_url')
    else:
        file = request.files.get('img_file')


    # update db and commit
    if new_email:
        # check that email isn't already taken
        if model.User.get_by_email(new_email):
            return {'message':'Email already taken'}, 409
        submitter.email = new_email
    elif new_username:
        # check that username isn't already taken, and is valid
        if not re.match(r'^[A-Za-z0-9_-]+$',new_username):
            return {'message':'Username invalid'}, 400
        if model.User.get_by_username(new_username):
            return {'message':'Username already taken'}, 409
        submitter.username = new_username
    elif new_password:
        # validate that the password given matches the password of logged in user
        if not submitter.is_password_correct(password):
            return error_response(403)
        submitter.change_password(new_password)
    elif new_avatar:
        submitter.img_url = new_avatar
    elif file:
        result = cloudinary.uploader.upload(file, 
                                            api_key=CLOUDINARY_KEY,
                                            api_secret=CLOUDINARY_SECRET,
                                            cloud_name=CLOUD_NAME)
        img_url = result['secure_url']
        submitter.img_url = img_url
        return {'new_avatar':img_url}, 200
    else:
        return {'message':'No change made'}, 400

    model.db.session.add(submitter)
    
    try:
        model.db.session.commit()
        return {'message':'User successfully updated'}, 200
    except:
        return error_response(500, 'Cannot commit to db')
        
    

################ Endpoint '/api/recipes' ############################
# GET -- return details of featured recipes (hard coded by recipe id)
@app.route('/api/recipes')
def get_featured_recipes():
    # featured_ids = [20, 10, 12, 11]
    featured_ids = [1,2]
    featured = []
    for id in featured_ids:
        featured.append(model.Recipe.get_by_id(id).to_dict())
    return featured

# POST -- create a new recipe
@app.route('/api/recipes', methods=['POST'])
@token_auth.login_required()
def create_new_recipe():
    """Create a new recipe

    Expects:    {title, description, ingredients, instructions, url, forked_from, set_is_public, set_is_exps_public}
    Returns:    200 if successful
    """
    if token_auth.current_user() == 'expired': 
        return error_response(401)
    # parse out POST params
    params = request.get_json()
    title = params.get('title')
    description = params.get('description')
    ingredients = params.get('ingredients')
    instructions = params.get('instructions')
    given_url = params.get('url')
    forked_from_id = params.get('forked_from') 
    img_url = params.get('img_url') 
    is_public = params.get('set_is_public')
    is_experiments_public = params.get('set_is_exps_public')

    submitter = token_auth.current_user()
    now = datetime.utcnow()

    # make sure title, ingredients, and instructions are not empty
    if not title and not ingredients and not instructions:
        return error_response(400)

    # db changes
    newRecipe = model.Recipe.create(owner=submitter, modified_on=now, 
                                    is_public=is_public, is_experiments_public=is_experiments_public,
                                    source_url=given_url, forked_from=forked_from_id) # create recipe
    model.Edit.create(newRecipe, title, description, ingredients, instructions, img_url, now, submitter) # create first edit
    model.db.session.add(newRecipe)

    try:
        model.db.session.commit()
        return {'message':'Recipe successfully created'}, 201
    except:
        return error_response(500, 'Cannot commit to db')

################ Endpoint '/api/recipes/<id>' ############################
# GET -- return timeline-items list, can_edit bool, can_exp bool
@app.route('/api/recipes/<id>')
@token_auth.login_required(optional=True)
def read_recipe_timeline(id):
    """Return all information needed for recipe details and timeline
    
    Returns:    {id, title, description, user_id, owner, owner_avatar, source_url,
                 forked_from, forked_from_username, forked_from_avatar,
                 is_experiments_public, is_public, last_modified,
                ^^^^^^ same as in /api/users/<username> GET route ^^^^^^
                 timeline_items: {
                    edits: list of dicts 
                        {id:        <int, unique edit id>,
                         recipe_id: <int, unique id of corresponding recipe>,
                         item_type: "edit",
                         commit_by, commit_by_avatar, commit_date,
                         title, description, ingredients, instructions:,
                         (included, but as yet unused: img_url, pending_approval)
                        }
                    experiments: list of dicts 
                        {id:        <int, unique experiment id>,
                         recipe_id: <int, unique id of corresponding recipe>,
                         item_type: "experiment",
                         commit_by, commit_by_avatar, commit_date,
                         commit_msg, notes,
                         (included, but as yet unused: create_date)
                        }
                 },
                 can_edit: <bool>
                 can_experiment: <bool>
                }
    """
    current_user = token_auth.current_user()
    response_code = 200
    if current_user == 'expired': 
        current_user = None
        response_code = 401
    query_owner = request.args.get('owner')
    recipe = model.Recipe.get_by_id(id)
    if not recipe:
        return error_response(404)
    recipe_owner = recipe.owner.username
    if query_owner and query_owner != recipe_owner:
        return error_response(404)
    timeline_items = ph.get_timeline(current_user.id if current_user else None, id)
    if not timeline_items:
        return error_response(404)
    if not timeline_items[0]:
        return error_response(403, 'User cannot view this recipe')
    response = recipe.to_dict()
    response['timeline_items'] = timeline_items[0]
    response['can_experiment'] = timeline_items[1]
    response['can_edit'] = timeline_items[2]
    return response, response_code

# DELETE -- Delete given recipe
@app.route('/api/recipes/<id>', methods=['DELETE'])
@token_auth.login_required()
def delete_recipe(id):
    if token_auth.current_user() == 'expired':
        return error_response(401)
    this_recipe = model.Recipe.get_by_id(id)
    if not this_recipe:
        return error_response(404)

    # only recipe owner can delete a recipe
    if token_auth.current_user() != this_recipe.owner:
        return error_response(403)
    
    model.db.session.delete(this_recipe)
    
    try:
        model.db.session.commit()
        return {'message':'Recipe successfully deleted'}, 200
    except:
        return error_response(500, 'Cannot commit to db')


################ Endpoint '/api/recipes/<id>/experiments' ############################
# POST -- Create a new experiment for a recipe
@app.route('/api/recipes/<id>/experiments', methods=['POST'])
@token_auth.login_required()
def create_new_exp(id):
    """Create a new experiment for a recipe

    Expects:    {commit_msg, notes}
    Returns:    200 if successful
    """

    if token_auth.current_user() == 'expired':
        return error_response(401)
    # parse out POST params
    params = request.get_json()
    commit_msg = params.get('commit_msg')
    notes = params.get('notes')
    now = datetime.utcnow()
    this_recipe = model.Recipe.get_by_id(id)
    if not this_recipe:
        return error_response(404)
    submitter = token_auth.current_user()

    # check that submitter is allowed to add a new experiment to given recipe
    if this_recipe.user_id != submitter.id:
        permission = model.Permission.get_by_user_and_recipe(submitter.id, id)
        if not permission or not permission.can_experiment:
            return error_response(403)
    
    # db changes
    new_experiment = model.Experiment.create(this_recipe, commit_msg, notes, now,
                                             now, token_auth.current_user()) # create experiment
    model.db.session.add(new_experiment)
    model.db.session.flush()
    this_recipe.update_last_modified(now) # update recipe's last_modified field
    model.db.session.add(this_recipe)
    try:
        model.db.session.commit()
        return {'id': new_experiment.id,
                'commit_date': now,
                'commit_by': submitter.username,
                'commit_by_avatar': submitter.img_url,
                'item_type': 'experiment',
                'commit_msg': commit_msg,
                'notes': notes,
                'recipe_id': this_recipe.id
                }, 200
    except:
        return error_response(500,'Cannot commit to db')

################ Endpoint '/api/recipes/<id>/edits' ############################
# POST -- Create a new edit for a recipe
@app.route('/api/recipes/<id>/edits', methods=['POST'])
@token_auth.login_required()
def create_new_edit(id):
    """Create a new edit for a recipe

    Expects:    {title, description, ingredients, instructions, img-url}
    Returns:    200 if successful
    """
    if token_auth.current_user() == 'expired':
        return error_response(401)
    # parse out POST params
    params = request.get_json()
    title = params.get('title')
    description = params.get('description')
    ingredients = params.get('ingredients')
    instructions = params.get('instructions')
    img_url = params.get('img-url')
    now = datetime.utcnow()
    this_recipe = model.Recipe.get_by_id(id)
    if not this_recipe:
        return error_response(404)
    submitter = token_auth.current_user()
    pending_approval = False
    
    # check that submitter is allowed to add a new edit to given recipe
    if this_recipe.user_id != submitter.id:
        permission = model.Permission.get_by_user_and_recipe(submitter.id, id)
        if not permission or not permission.can_edit:
            return error_response(403)

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
    try:
        model.db.session.commit()
        return {'id': new_edit.id,
                'commit_date': now,
                'commit_by': submitter.username,
                'commit_by_avatar': submitter.img_url,
                'item_type': 'edit',
                'title': title,
                'description': description,
                'ingredients': ingredients,
                'instructions': instructions,
                'img_url': new_edit.img_url,
                'recipe_id': this_recipe.id
                }, 200
    except:
        return error_response(500,'Cannot commit to db')

########### Endpoint '/api/recipes/<id>/permissions' ###################
# GET -- return is_public, is_experiments_public, and list of users with permissions
@app.route('/api/recipes/<recipe_id>/permissions')
@token_auth.login_required()
def read_permissions(recipe_id):
    """Returns permissions for a recipe -- both global and per-user.

    {is_experiments_public: <bool>,
     is_public: <bool>,
     shared_with: [{username: str, user_id: int, can_edit: bool, can_experiment: bool}]}
    """
    if token_auth.current_user() == 'expired':
        return error_response(401)
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
    if recipe.owner == submitter or permission.can_edit:
        # show shared_with
        shared_with = []
        for row in ph.get_recipe_shared_with(recipe):
            shared_with.append({
                'username': row.username,
                'can_edit': row.can_edit,
                'can_experiment': row.can_experiment,
                'user_id': row.id
            })
        response['shared_with'] = shared_with
    return response

# PUT -- edit permission level for recipe globally
@app.route('/api/recipes/<recipe_id>/permissions', methods=['PUT'])
@token_auth.login_required()
def update_global_permissions(recipe_id):
    """Change a recipe's global permissions.

    Expects:    {is_public: bool, is_experiments_public: bool}
    Returns:    200 if successful
    """
    submitter = token_auth.current_user()
    recipe = model.Recipe.get_by_id(recipe_id)

    # check if submitter is allowed to change permissions: owner or can_edit
    if recipe.user_id!=submitter.id:
        submitters_p = model.Permission.get_by_user_and_recipe(submitter.id, recipe_id)
        if (not submitters_p) or (not submitters_p.can_edit):
            return error_response(403)

    # parse out POST params
    params = request.get_json()
    is_public = params.get('is_public')
    is_experiments_public = params.get('is_experiments_public')

    # if is_experiments_public is true, is_public has to be true
    if is_experiments_public:
        is_public = True
    
    # update recipe!
    try:
        recipe.is_public = is_public
        recipe.is_experiments_public = is_experiments_public
        model.db.session.add(recipe)
        model.db.session.commit()

        return {'message':'Global permissions successfully updated'}, 200
    except:
        return error_response(500, 'Cannot commit to db') 


# POST -- create new permission (give new user a new permission)
@app.route('/api/recipes/<recipe_id>/permissions', methods=['POST'])
@token_auth.login_required()
def create_permission(recipe_id):
    """Give a certain user permission for a certain recipe.

    Expects:    {username: str, can_experiment: bool, can_edit: bool}
    Returns:    200 if successful
    """
    if token_auth.current_user() == 'expired':
        return error_response(401)
    # parse out POST params
    params = request.get_json()
    new_user_name = params.get('username')
    can_experiment = params.get('can_experiment')
    can_edit = params.get('can_edit')
    submitter = token_auth.current_user()
    recipe = model.Recipe.get_by_id(recipe_id)
    
    # check that user they want to add exists
    new_user = model.User.get_by_username(new_user_name)
    if not new_user:
        return error_response(404)
    
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
    if model.Permission.get_by_user_and_recipe(new_user.id, recipe_id):
        return error_response(409)

    # otherwise, make a new permission row
    new_permission = model.Permission.create(new_user.id, recipe_id,can_experiment,can_edit)
    model.db.session.add(new_permission)
    try:
        model.db.session.commit()
        return {'message':'New permission added','user_id':new_user.id}, 200
    except:
        return error_response(500, 'Cannot commit to db')

########### Endpoint '/api/recipes/<id>/permissions/<user_id>' ###################
# DELETE -- revoke a user's permission to a recipe
@app.route('/api/recipes/<recipe_id>/permissions/<user_id>', methods=['DELETE'])
@token_auth.login_required()
def delete_permission(recipe_id, user_id):
    if token_auth.current_user() == 'expired':
        return error_response(401)
    recipe = model.Recipe.get_by_id(recipe_id)
    submitter = token_auth.current_user()

    ## validation
    # only if submitter is owner or can_edit
    if recipe.user_id!=submitter.id:
        submitters_p = model.Permission.get_by_user_and_recipe(submitter.id, recipe_id)
        if (not submitters_p) or (not submitters_p.can_edit):
            return error_response(403)
    permission = model.Permission.get_by_user_and_recipe(user_id, recipe_id)
    if permission: 
        # delete the permission
        # if permission doesn't exist, there's no permission to delete but the user won't have access anyway
        model.db.session.delete(permission)

    try:
        model.db.session.commit()
        return{'message':'Permission deleted'}, 200
    except:
        return error_response(500, 'Cannot commit to db')

# PUT - edit permission level for a user
@app.route('/api/recipes/<recipe_id>/permissions/<user_id>', methods=['PUT'])
@token_auth.login_required()
def update_or_delete_permission(recipe_id, user_id):
    """Update a certain user's permission for a certain recipe.

    Expects:    {username: str, can_experiment: bool, can_edit: bool}
    Returns:    200 if successful
    """
    if token_auth.current_user() == 'expired':
        return error_response(401)
    # parse out POST params
    params = request.get_json()
    can_experiment = params.get('can_experiment')
    can_edit = params.get('can_edit')
    recipe = model.Recipe.get_by_id(recipe_id)
    submitter = token_auth.current_user()

    ## validation
    # only if submitter is owner or can_edit
    if recipe.user_id!=submitter.id:
        submitters_p = model.Permission.get_by_user_and_recipe(submitter.id, recipe_id)
        if (not submitters_p) or (not submitters_p.can_edit):
            return error_response(403)
    # if association doesn't exist, create a new one!
    permission = model.Permission.get_by_user_and_recipe(user_id, recipe_id)
    if not permission:
        permission = model.Permission.create(user_id, recipe_id, can_experiment, can_edit)
    else:
        # if association exists, update permission
        permission.can_edit = can_edit
        permission.can_experiment = can_experiment
    model.db.session.add(permission)
    try:
        model.db.session.commit()
        return{'message':'Permission modified'}, 200
    except:
        return error_response(500, 'Cannot commit to db')

################ Endpoint '/api/edits/<id>' ############################
# DELETE -- delete given edit
@app.route('/api/edits/<id>', methods=['DELETE'])
@token_auth.login_required()
def delete_edit(id):
    if token_auth.current_user() == 'expired':
        return error_response(401)
    # get experiment from server by id
    this_edit = model.Edit.get_by_id(id)
    submitter = token_auth.current_user()
    # handle if edit does not exist
    if not this_edit:
        return error_response(404)
    # NOT ALLOWED TO DELETE THE FIRST (CREATION) EDIT
    if this_edit == this_edit.recipe.edits[-1]:
        return error_response(409, 'Cannot delete creation edit')

    # check if sender is allowed to delete
    # can delete if user is owner of recipe or has edit access
    if submitter.id != this_edit.recipe.user_id:
        permission = model.Permission.get_by_user_and_recipe(submitter.id, this_edit.recipe_id)
        if not permission or not permission.can_edit or submitter.is_temp_user:
            return error_response(403)
    
    # delete edit
    model.db.session.delete(this_edit)
    try:
        model.db.session.commit()
        return {'message': 'Edit successfully deleted'}, 200
    except:
        return error_response(500, 'Cannot commit to db')

################ Endpoint '/api/experiments/<id>' ############################
# DELETE -- delete given experiment
@app.route('/api/experiments/<id>', methods=['DELETE'])
@token_auth.login_required()
def delete_experiment(id):
    if token_auth.current_user() == 'expired':
        return error_response(401)
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
    model.db.session.delete(this_experiment)
    try:
        model.db.session.commit()
        return {'message': 'Experiment successfully deleted'}, 200
    except:
        return error_response(500, 'Cannot commit to db')

# PUT -- edit an experiment -- NOT HOOKED UP TO FRONTEND YET
@app.route('/api/experiments/<id>', methods=['PUT'])
@token_auth.login_required()
def edit_experiment(id):
    if token_auth.current_user() == 'expired':
        return error_response(401)
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

    # edit experiment
    this_experiment.commit_msg = commit_msg
    this_experiment.notes = notes
    this_experiment.commit_date = date
    this_experiment.commit_by = committer
    
    try:
        model.db.session.commit(this_experiment)
        return {'message':'Experiment successfully updated'}, 200
    except:
        return error_response(500, 'Cannot commit to db')

################ Endpoint '/api/extract-recipe' ############################
# GET, with url as a query string
@app.route('/api/extract-recipe')
def extract_recipe_from_url():
    """Uses Spoonacular API to extract recipe details from given url. Expects url to be extracted from as a GET query string"""
    given_url = request.args.get('url')
    # return info from spoonacular 
    # (just title, desc, ingredients, instructions, img)

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
    model.connect_to_db(app, DEV_URI, False)     # for local dev
    app.run(host='0.0.0.0', debug=True)
    # app.run(host='0.0.0.0', debug=False)