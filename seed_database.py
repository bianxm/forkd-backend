"""Script to seed the database"""
# TODO Redo this using api_server file and current model!!!

import sys
import os
# from random import randint
import model
# import server
import api_server
from datetime import datetime, timedelta

# if instructed, drop and re-create the db
print(sys.argv[1:2])
db_name = '/test'

if sys.argv[1:2] and sys.argv[2:3]:
    db_name = sys.argv[2]
    if sys.argv[1:2] == ['recreate']:
        os.system(f'dropdb {db_name}')
        os.system(f'createdb {db_name}')
        print(f"Database '${db_name}' dropped and re-created")
    else: 
        print("Adding to existing database 'test'...")

# connect to db (and re-create tables, if needed)
model.connect_to_db(api_server.app, f'/{db_name}')
api_server.app.app_context().push()
if sys.argv[1:2] == ['recreate']:
    model.db.create_all()

# Create 3 users
for i in range(1,4):
    email = f'user{i}@test.com'
    password = 'test'
    username = f'user{i}'

    this_user = model.User.create(email, password, username)
    
    # Create 3 recipes per user
    # one private, then one public edits, then one public experiments
    for j in range(3):
        now = datetime.now()
        hour = timedelta(hours=1)
        this_recipe = model.Recipe.create(this_user, now + hour*5, bool(j), j%2)
        base_edit = model.Edit.create(this_recipe, 
                                      f"User{i}'s Recipe {j}",
                                      f"desc: User{i}'s Recipe {j}",
                                      f'User{i} Recipe{j} eggs and milk and stuff',
                                      f'User{i} Recipe{j} mix ingredients and cook',
                                      '',
                                      now, this_user)
        first_edit = model.Edit.create(this_recipe, 
                                      f"User{i}'s Recipe {j}",
                                      f"desc: User{i}'s Recipe {j}",
                                      f'User{i} Recipe{j} Edit!!',
                                      f'User{i} Recipe{j} Edit!!',
                                      '',
                                      now+hour*5, this_user)
        for k in range(1,3):
            this_exp = model.Experiment.create(this_recipe,
                                f'Experiment {k}',
                                f'It went ok experiment {k}',
                                now+hour*k, now+hour*k, this_user)
            model.db.session.add(this_exp)
        
    model.db.session.add(this_user)
model.db.session.commit()


# # Some permissions:
# # add can_experiment to a public recipe
# # User1 can_experiment on User2's public recipe id=4
# permission1 = model.Permission(user_id=1,recipe_id=4,can_experiment=True)

# # add can_edit to a public recipe
# # User2 can_edit on User3's public recipe id=6
# permission2 = model.Permission(user_id=2,recipe_id=6,can_experiment=True, can_edit=True)

# # add can view to a private recipe
# # User 3 can view User1's private recipe id=1
# permission3 = model.Permission(user_id=3,recipe_id=1)

# # add can_experiment to a private recipe
# # User 1 can_experiment User2's private recipe id=3
# permission4 = model.Permission(user_id=1,recipe_id=3,can_experiment=True)

# # add can_edit to a private recipe
# # User2 can_edit on User3's private recipe id=5
# permission5 = model.Permission(user_id=2,recipe_id=5,can_experiment=True,can_edit=True)

# model.db.session.add_all([permission1, permission2, permission3, permission4, permission5])

for i in range(1,4): # for every user id
    # this_permission = model.Permission(user_id=i,recipe_id=((i%3)+1))
    for j in range(1,4): # for the next user's recipes
        this_permission = model.Permission(user_id=i,recipe_id=((3*(i%3))+j),can_experiment=bool(i-1),can_edit=(i-1)%2)
        model.db.session.add(this_permission)

model.db.session.commit()