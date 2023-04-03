"""Server for Forkd"""

from flask import (Flask, render_template, request,
                   flash, session, redirect)
from model import connect_to_db, db
from jinja2 import StrictUndefined
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ['FLASK_KEY']
app.jinja_env.undefined = StrictUndefined

@app.route('/')
def show_homepage():
    return f"<h1>HELLO WORLD!!</h1>"

if __name__ == '__main__':
    connect_to_db(app)
    app.run(host='0.0.0.0', debug=True)