from flask import Flask, render_template
from matching_algorithm import create_group_code
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurants.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Optional: define models if you want to use ORM
class User(db.Model):  # Example
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))


@app.route("/")
def home():
    return render_template("layout.html")

@app.route("/new_meeting")
def new_meeting():
    return render_template("meeting_form.html", printed_result = create_group_code())

@app.route("/join_meeting")
def join_meeting():
    return render_template("member_form.html")

@app.route("/recommendations")
def recommendations_output():
    return render_template("restaurant_form.html")