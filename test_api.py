import unittest
unittest.TestLoader.sortTestMethodsUsing = lambda *args: -1
import model
from api_server import app
from datetime import datetime, timedelta

# Test visibility for a public user
class TestPublicUser(unittest.TestCase):
    def test_public_cant_view_private_recipe(self):
        response = client.get('/api/recipes/1') # private recipe
        self.assertEqual(response.status_code, 403)
    
    def test_public_can_view_public_edits_only(self):
        response = client.get('/api/recipes/2') # edits public, but experiments private
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json['timeline_items']),1)
        self.assertFalse(response.json['can_experiment'])
        self.assertFalse(response.json['can_edit'])
    
    def test_public_can_view_public_all(self):
        response = client.get('/api/recipes/3') # edits and experiments both public
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json['timeline_items']),2)
        self.assertFalse(response.json['can_experiment'])
        self.assertFalse(response.json['can_edit'])
    
    def test_public_cant_create_recipe(self):
        initial_r_count = model.Recipe.query.count()
        response = client.post('/api/recipes', data={
            'title': 'Hello!',
            'ingredients': 'Hello!',
            'instructions': 'Hello!'
        })
    
        self.assertEqual(response.status_code, 401, "Should be rejected as unauthorized")
        self.assertEqual(model.Recipe.query.count(), initial_r_count, "No new recipe should have been made")
    
    def test_public_cant_create_exp(self):
        initial_exp_count = model.Experiment.query.count()
        response = client.post('/api/recipes/1', data={
            'commit_msg':'Hello!'
        })
    
        self.assertEqual(response.status_code, 401, "Should be rejected as unauthorized")
        self.assertEqual(model.Experiment.query.count(), initial_exp_count, "No new recipe should have been made")
    
    def test_public_cant_create_edit(self):
        initial_ed_count = model.Edit.query.count()
        response = client.put('/api/recipes/1', data={
            'title': 'Hello!',
            'ingredients': 'Hello!',
            'instructions': 'Hello!'
        })
    
        self.assertEqual(response.status_code, 401, "Should be rejected as unauthorized")
        self.assertEqual(model.Edit.query.count(), initial_ed_count, "No new recipe should have been made")
    
    def test_public_cant_delete_recipe(self):
        initial_r_count = model.Recipe.query.count()
        response = client.delete('/api/recipes/1')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(model.Recipe.query.count(), initial_r_count)
    
    def test_public_cant_delete_exp(self):
        initial_exp_count = model.Experiment.query.count()
        response = client.delete('/api/experiments/1')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(model.Experiment.query.count(), initial_exp_count)
    
    def test_public_cant_delete_edit(self):
        initial_edit_count = model.Edit.query.count()
        response = client.delete('/api/edits/1')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(model.Edit.query.count(), initial_edit_count)

    def test_public_can_only_see_users_public_recipes(self):
        response = client.get('/api/users/joker')
        recipes = response.json['recipes']
        self.assertTrue(all([True if recipe['is_public'] else False for recipe in recipes]))


class TestSignUp(unittest.TestCase):
    def test_api_register_user_empty_fields(self):
        initial_user_count = model.User.query.count()
        response = client.post('/api/users', json={
            'email': '',
            'username': '',
            'password': ''
        })
        self.assertEqual(response.status_code, 400, "Should be rejected as bad request")
        self.assertEqual(model.User.query.count(), initial_user_count, "No new user should have been made")

    def test_api_register_existing_username(self):
        initial_user_count = model.User.query.count()
        response = client.post('/api/users', json={
            'email': 'sojiro@leblanc.com',
            'username': 'joker',
            'password': 'password123'
        })
    
        self.assertEqual(response.status_code, 409, "Should be rejected as bad request")
        self.assertEqual(model.User.query.count(), initial_user_count, "No new user should have been made")
    
    def test_api_register_existing_email(self):
        initial_user_count = model.User.query.count()
        response = client.post('/api/users', json={
            'email': 'joker@tokyo.com',
            'username': 'sojiro',
            'password': 'password123'
        })
        
        self.assertEqual(response.status_code, 409, "Should be rejected as bad request")
        self.assertEqual(model.User.query.count(), initial_user_count, "No new user should have been made")
    
    # TODO test registering a new user success
    def test_api_successful_register(self):
        initial_user_count = model.User.query.count()
        response = client.post('/api/users', json={
            'email': 'sojiro@leblanc.com',
            'username': 'sojiro',
            'password': 'password123'
        })
        
        self.assertEqual(response.status_code, 201)
        self.assertEqual(model.User.query.count(), initial_user_count + 1, "New user should have been made")

class TestAuthentication(unittest.TestCase):
    # def test_login_no_inputs(self):
    #     response = client.post('/tokens', auth=('', ''))
    #     self.assertEqual(response.status_code//100, 4, 'Login attempt must be rejected')
    
    # def test_login_no_username(self):
    #     response = client.post('/api/tokens', auth=('', 'phantomthieves'))
    #     self.assertEqual(response.status_code, 400, 'Login attempt must be rejected')
        
    # def test_login_no_password(self):
    #     response = client.post('/api/tokens', auth=('joker', ''))
    #     self.assertEqual(response.status_code, 400, 'Login attempt must be rejected')
    
    def test_login_unregistered_user(self):
        response = client.post('/tokens', auth=('ryuji', 'ryuji'))
        self.assertEqual(response.status_code, 404)
    
    def test_login_registered_user_via_email(self):
        response = client.post('/api/tokens', auth=('joker@tokyo.com', 'phantomthieves'))
        self.assertEqual(response.status_code, 200)
    
    def test_login_registered_user_via_email_wrong_password(self):
        response = client.post('/api/tokens', auth=('joker@tokyo.com', 'wrongpassword'))
        self.assertEqual(response.status_code//100, 4, 'Login attempt must be rejected')
    
    def test_login_registered_user_via_username(self):
        response = client.post('/api/tokens', auth=('joker', 'phantomthieves'))
        self.assertEqual(response.status_code, 200)
    
    def test_login_registered_user_via_username_wrong_password(self):
        response = client.post('/api/tokens', auth=('joker', 'wrongpassword'))
        self.assertEqual(response.status_code//100, 4, 'Login attempt must be rejected')

class LoggedInUser(): #Mixin for logging in
    def get_api_token(self, login, password):
        response = client.post('/api/tokens', auth=(login, password))
        return response.json['token']
    
class TestCreateAndDelete(LoggedInUser, unittest.TestCase):
    def setUp(self):
        self.token = self.get_api_token('makoto','phantomthieves')
        self.user = model.User.get_by_username('makoto')
        self.recipe = self.user.recipes[0]
        self.initial_r_count = len(self.user.recipes)
        self.initial_exp_count = len(self.recipe.experiments)
        self.initial_ed_count = len(self.recipe.edits)

    def test_create_new_recipe(self):
        response = client.post('/api/recipes', json={
                'title':'Testing Recipe Creation',
                'ingredients':'Ingredients',
                'instructions':'Instructions'
            }, headers = {'Authorization': f'Bearer {self.token}'})
        self.assertEqual(response.status_code, 201, 'Server should return 201')
        # and check that it was reflected in data
        self.assertEqual(self.user.recipes[0].edits[-1].title, 'Testing Recipe Creation')
    
    def test_create_new_experiment(self):
        response = client.post(f'/api/recipes/{self.recipe.id}', json={
                'commit_msg':'New experiment',
                'notes':'notes!'
            }, headers = {'Authorization': f'Bearer {self.token}'})
        self.assertEqual(response.status_code, 200, 'Server should return 200')
        self.assertEqual(len(self.recipe.experiments), self.initial_exp_count+1)
        self.assertEqual(self.recipe.experiments[0].commit_msg,'New experiment')

    def test_create_new_edit(self):
        response = client.put(f'/api/recipes/{self.recipe.id}', json={
                'title':'New title'
            }, headers = {'Authorization': f'Bearer {self.token}'})
        self.assertEqual(response.status_code, 200, 'Server should return 200')
        self.assertEqual(len(self.recipe.edits), self.initial_ed_count+1)
        self.assertEqual(self.recipe.edits[0].title,'New title')

    def test_delete_edit(self):
        response1 = client.put(f'/api/recipes/{self.recipe.id}', json={
                'title':'New title'
            }, headers = {'Authorization': f'Bearer {self.token}'})
        response = client.delete(f'/api/edits/{self.recipe.edits[0].id}',
                                 headers = {'Authorization': f'Bearer {self.token}'})
        self.assertEqual(response.status_code, 200, 'Server should return 200')
        self.assertEqual(len(self.recipe.edits), self.initial_ed_count)
    
    def test_delete_experiment(self):
        response = client.delete(f'/api/experiments/{self.recipe.experiments[0].id}',
                                 headers = {'Authorization': f'Bearer {self.token}'})
        self.assertEqual(response.status_code, 200, 'Server should return 200')
        self.assertEqual(len(self.recipe.experiments), self.initial_exp_count-1)
    
    def test_delete_recipe(self):
        response = client.delete(f'/api/recipes/{self.recipe.id}',
                                 headers = {'Authorization': f'Bearer {self.token}'})
        self.assertEqual(response.status_code, 200, 'Server should return 200')
        self.assertEqual(len(self.user.recipes), self.initial_r_count-1)
        self.assertEqual(model.Edit.query.filter_by(recipe_id=self.recipe.id).count(), 0)
        self.assertEqual(model.Experiment.query.filter_by(recipe_id=self.recipe.id).count(), 0)

# TODO test permissions and visibility
class TestPermissions(LoggedInUser, unittest.TestCase):
    def setUp(self):
        self.token = self.get_api_token('joker','phantomthieves')
        self.user = model.User.get_by_username('joker')
        self.shared_token = self.get_api_token('makoto','phantomthieves')
        self.share_with = model.User.get_by_username('makoto')
        self.private_recipe = self.user.recipes[0]
    
    def test_share_to_user(self):
        i_response = client.get('/api/recipes/1', # private recipe
            headers = {'Authorization': f'Bearer {self.shared_token}'})
        self.assertEqual(i_response.status_code, 403)
        response = client.post('/api/recipes/1/permissions', json={
            'username': 'makoto',
            'can_experiment': True,
            'can_edit': True
            }, headers = {'Authorization': f'Bearer {self.token}'})
        self.assertEqual(response.status_code, 200)
        n_response = client.get('/api/recipes/1', # private recipe
            headers = {'Authorization': f'Bearer {self.shared_token}'})
        self.assertEqual(n_response.status_code, 200)

        
# grant permission one by one
# and check if the other user can see it as they should
# and if they can edit it as they should

# TODO test delete of edit, experiment, recipe
# by owner >> done in TestCreateAndDelete!
# TODO by other user

# TODO test changing user details


if __name__ == "__main__":
    app.config['TESTING'] = True
    model.connect_to_db(app, 'forkd-testdb',False)
    app.app_context().push()
    client = app.test_client()
   
    ## drop and re-create tables so that we start from scratch
    model.db.drop_all()
    model.db.create_all()

    ## seed test database
    user1 = model.User.create(email='joker@tokyo.com',password='phantomthieves',username='joker')
    user2 = model.User.create(email='makoto@tokyo.com',password='phantomthieves',username='makoto')
    model.db.session.add_all([user1, user2])
    model.db.session.commit()
    # Create a bunch of recipes for joker, of varying publicity levels
    hour = timedelta(hours=1)
    for j in range(1,3):
        this_user = model.User.get_by_id(j)
        for i in range(3):
            now = datetime.now()
            recipe = model.Recipe.create(this_user, now - hour*2, bool(i), i>1)
            base_edit = model.Edit.create(recipe,
                                        f'Recipe {i}',
                                        '', 'ingredients', 'instructions','',
                                        now - hour*3, this_user)
            experiment = model.Experiment.create(recipe,
                                                'One experiment','', now + hour,
                                                now - hour*2, this_user)
            model.db.session.add(recipe)

    model.db.session.commit()
  
    # Finally, run tests
    unittest.main()