"""Script to seed the database"""

import sys
import os
# from random import randint
import model
import server
from datetime import datetime, timedelta

# if instructed, drop and re-create the db
print(sys.argv[1:2])

if sys.argv[1:2] == ['drop']:
    os.system('dropdb forkd')
    os.system('createdb forkd')
    print("Database 'forkd' dropped and re-created")
else: 
    print('Adding to existing database...')

# connect to db (and re-create tables, if needed)
model.connect_to_db(server.app)
server.app.app_context().push()
if sys.argv[1:2] == ['drop']:
    model.db.create_all()

# Create 10 users
for i in range(10):
    email = f'user{i}@test.com'
    password = 'test'
    username = f'user{i}'

    this_user = model.User.create(email, password, username)
    
    # Create 2 recipes per user
    for j in range(1,3):
        now = datetime.now()
        hour = timedelta(hours=1)
        this_recipe = model.Recipe.create(this_user, now)
        base_edit = model.Edit.create(this_recipe, 
                                      f"User{i}'s Recipe {j}",
                                      f"desc: User{i}'s Recipe {j}",
                                      f'User{i} Recipe{j} eggs and milk and stuff',
                                      f'User{i} Recipe{j} mix ingredients and cook',
                                      now)
        first_edit = model.Edit.create(this_recipe, 
                                      f"User{i}'s Recipe {j}",
                                      f"desc: User{i}'s Recipe {j}",
                                      f'User{i} Recipe{j} Edit!!',
                                      f'User{i} Recipe{j} Edit!!',
                                      now+hour*5)
        for k in range(1,4):
            first_exp = model.Experiment.create(this_recipe,
                                f'Experiment {k}',
                                f'It went ok experiment {k}',
                                now+hour*k)
        
    model.db.session.add(this_user)

model.db.session.commit()