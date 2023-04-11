from model import (db, connect_to_db, User, 
                   Recipe, Edit, Experiment, Permission)

# QUERIES I NEED NOW THAT I HAVE PERMISSIONS
## Given a user('s id), return recipes they can view on an ad-hoc basis (but they don't own)
    # basically, all recipes that are associated with that user in the permissions table
## Given a viewer user('s id) and an owner user's id, return all the recipes owned by the owner that the viewer is allowed to view
    # all owner's public recipes
    # UNION all the owner's recipes that the viewer has permission to
## Given a user('s id) and a recipe id, return whether they can view it (bool)
## Given a user('s id) and a recipe id, return whether they can submit an experiment
## Given a user('s id) and a recipe id, return whether they can submit an edit
    # if no, when they submit that experiment, there's an approval_required flag

# not for permissions, but
## Given a recipe, get the edit that it was forked from

if __name__== '__main__':
    from server import app
    connect_to_db(app, 'forkd-p')
    app.app_context().push()