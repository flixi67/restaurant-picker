from flask import Flask, render_template, request
from matching_algorithm import create_group_code

app = Flask(__name__)

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