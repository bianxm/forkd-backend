from model import (db, connect_to_db, User, 
                   Recipe, Edit, Experiment, Permission)
from sqlalchemy import select, union, desc

# QUERIES I NEED NOW THAT I HAVE PERMISSIONS
## Given a user('s id), return recipes that have been shared to them 
    # basically, all recipes that are associated with that user in the permissions table
def get_shared_with_me(me_id: int) -> list('Recipe'):
   # SELECT <Recipe> FROM recipes JOIN permissions
   # WHERE permissions.user_id == <me_id>
   select_shared_with_me = select(Recipe).join(Recipe.permissions).where(Permission.user_id==me_id)
   return db.session.scalars(select_shared_with_me).all()

## Given a viewer's user id and an owner's user id, 
## return all recipes owned by owner
## that the viewer can view
## viewer id can be null --> meaning nobody is logged in
def get_viewable_recipes(owner_id: int, viewer_id: int | None) -> list[Recipe]:
    # SELECT <Recipe> FROM recipes WHERE user_id = <owner_id> AND is_public = True
    select_owners_public_recipes = select(Recipe).where(Recipe.user_id == owner_id).where(Recipe.is_public == True)
    # UNION
    # SELECT <Recipe> FROM recipes AS r JOIN permissions AS p
    # WHERE p.user_id = <viewer_id>
    # AND r.user_id = <owner_id>
    # ORDER BY Recipe.last_modified 
    select_shared_with_viewer = select(Recipe).join(Recipe.permissions).where(Permission.user_id==viewer_id).where(Recipe.user_id==owner_id)
    union_query = union(select_owners_public_recipes, select_shared_with_viewer).order_by(desc(Recipe.last_modified))
    union_query = select(Recipe).from_statement(union_query)
    return db.session.scalars(union_query).all()

def get_recipe_shared_with(recipe: Recipe) -> list[User]:
    stmt = select(User.username, Permission.can_edit, Permission.can_experiment).join(User.permissions).where(Permission.recipe_id == recipe.id)
    return db.session.execute(stmt)

## Given a user('s id) and a recipe id, return whether they can view it (bool)
def can_user_view(user: User, recipe: Recipe) -> bool:
    # this_recipe = Recipe.get_by_id(recipe_id)
    if recipe.is_public:
        return True
    select_permission = select(Permission).where(Permission.user_id==user.id).where(Permission.recipe_id==recipe.id)
    return bool(db.session.execute(select_permission).one_or_none())

## Given a user's id and a recipe id, 
# return a list of timeline items (recipes and edits) in descending chrono order
# that the user is allowed to view (so either just experiments, or both experiments and edits)
def get_timeline(viewer_id: int | None, recipe_id: int): # -> list('Edit'|'Experiment'):
    # return a dict:
    # timeline: list of timeline items
    # can_experiment: bool
    # can_edit: bool
    this_recipe = Recipe.get_by_id(recipe_id)
    if not this_recipe:
        return None
    timeline_items = None
    can_experiment = False
    can_edit = False
    this_permission = None
    if this_recipe.user_id == viewer_id:
        can_experiment = True
        can_edit = True
        timeline_items = this_recipe.edits + this_recipe.experiments
        return (timeline_items, can_experiment, can_edit)
    elif viewer_id is not None:
        this_permission = Permission.get_by_user_and_recipe(viewer_id, recipe_id) # returns the match, or None
        if this_permission is not None:
            can_experiment = this_permission.can_experiment
            can_edit = this_permission.can_edit
    
    if this_recipe.is_public:
        timeline_items = this_recipe.edits
    
    if this_recipe.is_experiments_public or this_permission is not None:
        timeline_items = this_recipe.edits + this_recipe.experiments # sort this!!!
    # return {'timeline_items': timeline_items,
    #         'can_experiment': can_experiment,
    #         'can_edit': can_edit}
    return (timeline_items, can_experiment, can_edit)
    

## Given a user('s id) and a recipe id, return whether they can submit an experiment (bool)
## Use to check on server-side POST - CREATE EXPERIMENT

## Given a user('s id) and a recipe id, return whether they can edit (bool)
# def can_user_edit(user: User, recipe: Recipe) -> bool:
#     if recipe.is_public:
#         return True
#     select_permission = select(Permission).where(Permission.user_id==user.id).where(Permission.recipe_id==recipe.id)
#     return bool(db.session.execute(select_permission).one_or_none())
    # if no, when they submit that experiment, there's a pending_approval flag
## Use to check on server-side POST - CREATE EDIT


# not for permissions, but
## Given a recipe, get the edit that it was forked from

if __name__== '__main__':
    from server import app
    connect_to_db(app, 'forkd-p')
    app.app_context().push()