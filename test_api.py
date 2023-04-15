import unittest
import model
from api_server import app
from datetime import datetime, timedelta

# Global setup: Connect to Flask app & db and register test_client
app.config['TESTING'] = True
model.connect_to_db(app, 'forkd-testdb',False)
app.app_context().push()
client = app.test_client()

## drop and re-create tables so that we start from scratch
model.db.drop_all()
model.db.create_all()

## seed test database
user = model.User.create(email='joker@tokyo.com',password='phantomthieves',username='joker')
model.db.session.add(user)
model.db.session.commit()
# TODO Create a bunch of recipes for this guy, of varying publicity levels
hour = timedelta(hours=1)
for i in range(3):
    now = datetime.now()
    recipe = model.Recipe.create(user, now + hour*3, bool(i), i>1)
    base_edit = model.Edit.create(recipe,
                                  f'Recipe {i}',
                                  '', 'ingredients', 'instructions',
                                  now + hour*3, user.id)
    experiment = model.Experiment.create(recipe,
                                         'One experiment','', now + hour,
                                         now + hour*2, user.id)
    model.db.session.add(recipe)

model.db.session.commit()

# TODO Test visibility for a public user
class TestPublicUserVisibility(unittest.TestCase):
    def test_public_cant_view_private_recipe(self):
        response = client.get('/api/recipes/1')
        self.assertEqual(response.status_code, 403)
    
    def test_public_can_view_public_edits(self):
        response = client.get('/api/recipes/2')
        self.assertEqual(response.status_code, 200)
        edits_only = [True if item.get('item_type') == 'edit' else False for item in response.json['timeline_items']] #should only contain edits
        self.assertTrue(all(edits_only))
        self.assertFalse(response.json['can_experiment'])
        self.assertFalse(response.json['can_edit'])
    
    def test_public_can_view_public_all(self):
        response = client.get('/api/recipes/3')
        self.assertEqual(response.status_code, 200)
        # can view both edits and experiments
        has_edits_and_exps = (False, False)
        for item in response.json['timeline_items']:
            if item['item_type'] == 'edit': 
                has_edits_and_exps[0] = True 
            if item['item_type'] == 'experiment': 
                has_edits_and_exps[1] = True 
        self.assertTrue(all(has_edits_and_exps))
        self.assertFalse(response.json['can_experiment'])
        self.assertFalse(response.json['can_edit'])

class TestSignUp(unittest.TestCase):
    def test_api_register_user_empty_fields(self):
        response = client.post('/api/users', data={
            'email': '',
            'username': '',
            'password': ''
        })
        self.assertEqual(response.status_code, 400, "Should be rejected as bad request")
        self.assertEqual(len(model.User.get_all()), 1, "No new user should have been made")

    def test_api_register_existing_username(self):
        response = client.post('/api/users', data={
            'email': 'sojiro@leblanc.com',
            'username': 'joker',
            'password': 'password123'
        })
    
        self.assertEqual(response.status_code, 409, "Should be rejected as bad request")
        self.assertEqual(len(model.User.get_all()), 1, "No new user should have been made")
    
    def test_api_register_existing_email(self):
        response = client.post('/api/users', data={
            'email': 'joker@tokyo.com',
            'username': 'sojiro',
            'password': 'password123'
        })
        
        self.assertEqual(response.status_code, 409, "Should be rejected as bad request")
        self.assertEqual(len(model.User.get_all()), 1, "No new user should have been made")
    
    # TODO test registering a new user

class TestAuthentication(unittest.TestCase):
    def test_login_no_inputs(self):
        response = client.post('/tokens', auth=('', ''))
        self.assertEqual(response.status_code, 400, 'Login attempt must be rejected')
    
    def test_login_no_username(self):
        response = client.post('/api/tokens', auth=('', 'phantomthieves'))
        self.assertEqual(response.status_code, 400, 'Login attempt must be rejected')
        
    def test_login_no_password(self):
        response = client.post('/api/tokens', auth=('joker', ''))
        self.assertEqual(response.status_code, 400, 'Login attempt must be rejected')
    
    def test_login_unregistered_user(self):
        response = client.post('/tokens', auth=('ryuji', 'ryuji'))
        self.assertEqual(response.status_code, 404)
    
    def test_login_registered_user_via_email(self):
        response = client.post('/api/tokens', auth=('joker@tokyo.com', 'phantomthieves'))
        self.assertEqual(response.status_code, 200)
    
    def test_login_registered_user_via_email_wrong_password(self):
        response = client.post('/api/tokens', auth=('joker@tokyo.com', 'wrongpassword'))
        self.assertEqual(response.status_code, 401, 'Login attempt must be rejected')
    
    def test_login_registered_user_via_username(self):
        response = client.post('/api/tokens', auth=('joker', 'phantomthieves'))
        self.assertEqual(response.status_code, 200)
    
    def test_login_registered_user_via_username_wrong_password(self):
        response = client.post('/api/tokens', auth=('joker', 'wrongpassword'))
        self.assertEqual(response.status_code, 401, 'Login attempt must be rejected')

class LoggedInUser(): #Mixin for logging in
    def get_api_token(self):
        response = client.post('/api/tokens', auth=('joker', 'phantomthieves'))
        return response.json['token']
    
class TestCreate(LoggedInUser, unittest.TestCase):
    def test_create_new_recipe(self):
        token = self.get_api_token()
        response = client.post('/api/recipes', data={
            'title':'Testing Recipe Creation',
            'ingredients':'Ingredients',
            'instructions':'Instructions'
            }, headers = {'Authorization': f'Bearer {token}'})
        self.assertEqual(response.status_code, 201, 'Server should return 201')
        # and check that it was reflected in data
        # self.assertEqual(model.User.get_by_username('joker').recipes[0].edits[0].title, 'Testing Recipe Creation')
    
    # TODO test create edit for this recipe
    # TODO test create experiment for this recipe

# TODO test permissions and visibility
# grant permission one by one
# and check if the other user can see it as they should
# and if they can edit it as they should

# TODO test delete

        

if __name__ == "__main__":
    unittest.main()