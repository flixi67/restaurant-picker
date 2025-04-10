from flask import Blueprint, render_template, redirect
from matching_algorithm import create_group_code
from requests import request

# Internal imports
from .models import db, Meeting, Members, Restaurants, Top_restaurants
from modules.data_pipeline import run_pipeline_for_meeting


### --- Define blueprints

main_bp = Blueprint("main", __name__)
pipeline_bp = Blueprint("pipeline", __name__, url_prefix="/recommendations")

### --- Routes of the app ------

@main_bp.route("/")
def home():
    return render_template("layout.html")

@main_bp.route("/new_meeting")
def new_meeting():
    return render_template("meeting_form.html", printed_result = create_group_code())

@main_bp.route("/join_meeting")
def join_meeting():
    return render_template("member_form.html")

@main_bp.route('/', methods=['GET', 'POST'])
def recommendations_redirect():
    if request.method == 'POST':
        meeting_id = request.form.get('meeting_id')
        return redirect(f'/recommendations/{meeting_id}')
    return render_template('recommendations_redirect.html')

@pipeline_bp.route("/<string:meeting_id>")
def recommendations_output(meeting_id):
    # Step 1: Check if results already exist
    results = Top_restaurants.query.filter_by(meeting_id=meeting_id).all()

    if not results:
        print("✨ No results found. Calculating your ideal restaurant!")
        run_pipeline_for_meeting(meeting_id) # saves to restaurants
        # run_algorithm_for_meeting(meeting_id) # fetches from restaurants and saves to Top_restaurants
        # Fetch data from results table
        results = Top_restaurants.query.filter_by(meeting_id=meeting_id).all()

        if not results:
            return "😬 Oops. Something went wrong while generating results.", 500
    else:
        print("✅ Cached results found. Serving with flair!")

    # Step 2: Render the template with the results
    return render_template("restaurant_form.html", results=results) ###