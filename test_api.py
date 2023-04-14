import unittest
import sys
import model
from api_server import app
import os

app.config['TESTING'] = True
model.connect_to_db(app, 'forkd-testdb')
app.app_context().push()
model.db.drop_all()
model.db.create_all()
user = model.User.create(email='joker@tokyo.com',password='phantomthieves',username='joker')
model.db.session.add(user)
model.db.session.commit()
client = app.test_client()

# class BaseTestCase(unittest.TestCase):
#     @staticmethod
#     def populate_db():
#         user = model.User.create(email='joker@tokyo.com',password='phantomthieves',username='joker')
#         model.db.session.add(user)
#         model.db.session.commit()

    # @classmethod
    # def setUpClass(cls):
    #     cls.app = app
    #     cls.app_context = cls.app.app_context()
    #     cls.app_context.push()
    #     model.db.create_all()
    #     cls.populate_db()
    #     cls.client = app.test_client()

    # @classmethod
    # def tearDownClass(cls):
    #     # model.db.session.close()
    #     # model.db.session.remove()
    #     model.db.drop_all()
    #     # model.db.engine.dispose()
    #     cls.app_context.pop()

class TestPublicViewer(unittest.TestCase):
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
        self.assertEqual(response.status_code, 401, 'Login attempt must be rejected')
    
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


class TestLoggedInUser(unittest.TestCase):
    def get_api_token(self):
        response = client.post('/api/tokens', auth=('joker', 'phantomthieves'))
        return response.json['token']
    
    def test_create_new_recipe(self):
        token = self.get_api_token()
        response = client.post('/api/recipes', data={
            'title':'Testing Recipe Creation',
            'ingredients':'Ingredients',
            'instructions':'Instructions'
            }, headers = {'Authorization': f'Bearer {token}'})
        self.assertEqual(response.status_code, 201, 'Server should return 201')
        # and check that it was reflected in data
        self.assertEqual(model.User.get_by_username('joker').recipes[0].edits[0].title, 'Testing Recipe Creation')
        

# def setUp(self):
#     self.app = app
#     self.app_context = app.app_context()
#     self.app_context.push()
#     self.client = self.app.test_client()
#     app.config['TESTING'] = True

#     model.connect_to_db(app, 'forkd-testdb')
#     model.db.create_all()

#     populate_db()

# def tearDown(self):
#     model.db.session.remove()
#     model.db.drop_all()
#     model.db.engine.dispose()
    

    


if __name__ == "__main__":
    unittest.main()