import pandas as pd
from flask import Blueprint, render_template, redirect,request

# Internal imports
from app.models import db, Meetings, Members, Restaurants, TopRestaurants
from app.modules.data_pipeline import run_pipeline_for_meeting
from app.matching_algorithm import create_group_code, propose_restaurants


### --- Define blueprints

main_bp = Blueprint("main", __name__)
pipeline_bp = Blueprint("pipeline", __name__, url_prefix="/recommendations")

### --- Routes of the app ------

@main_bp.route("/")
def home():
    return render_template("layout.html")

@main_bp.route("/new_meeting")
def new_meeting():
    if request.method == 'POST':
        meeting_datetime = request.form['meetingdatetime']
        meeting_size = request.form['meetingsize']
        
        # Generate the group code
        group_code = create_group_code()

        # Create ORM model and populate its fields with IDs
        entered_meeting_data = Meetings(group_code, meeting_datetime, meeting_size)
        # Add to session and commit
        db.session.add(entered_meeting_data)
        db.session.commit() # Write this into the Meetings

        # Debugging: Print the group code
        print(f"Generated Group Code: {group_code}")

        # Render the confirmation page with meeting data and group code
        return render_template("meeting_confirmation.html", 
                                group_code=group_code,
                               meeting_datetime=meeting_datetime,
                               meeting_size=meeting_size)
    
    # If it's a GET request, show the form
    return render_template("meeting_form.html")

@main_bp.route("/join_meeting")
def join_meeting():
    return render_template("member_form.html")

@main_bp.route("/recommendations")
def recommendations_output():
    return render_template("restaurant_form.html")

@main_bp.route("/restaurant_preferences/<group_code>", methods=['GET', 'POST'])
def restaurant_preferences(group_code):
    if request.method == 'POST':
        try:
            candidates = pd.read_csv("cleaned_data.csv")
           
            preferences = {
                "cuisine_type": (request.form.get("cuisine"), 0.4),
                "dietary": (request.form.get("dietary"), 0.3)
            }
            budget = float(request.form.get("budget", 20))
           
            results = propose_restaurants(candidates, preferences, budget)
            return render_template("recommendations.html",
                               restaurants=results.head(10).to_dict('records'),
                               group_code=group_code)
        except Exception as e:
            return f"Error processing recommendations: {str(e)}", 400
   
    return render_template("restaurant_form.html", group_code=group_code)

@main_bp.route('/recommendations', methods=['GET', 'POST'])
def recommendations_redirect():
    if request.method == 'POST':
        meeting_id = request.form.get('meeting_id')
        return redirect(f'/recommendations/{meeting_id}')
    return render_template('recommendations_redirect.html')

@pipeline_bp.route("/<string:meeting_id>")
def recommendations_output(meeting_id):
    # Step 1: Check if results already exist
    results = TopRestaurants.query.filter_by(meeting_id=meeting_id).all()

    if not results:
        print("✨ No results found. Calculating your ideal restaurant!")
        
        try:
            run_pipeline_for_meeting(meeting_id)
            results = TopRestaurants.query.filter_by(meeting_id=meeting_id).all()
            return render_template("recommendations.html", results=results)
    
        except ValueError as e:
            # This is where you handle the missing meeting
            return render_template("error.html", message=str(e))

    if not results:
            return "😬 Oops. Something went wrong while generating results.", 500
    else:
        print("✅ Cached results found. Serving with flair!")

    # Step 2: Render the template with the results
    return render_template("restaurant_form.html", results=results) ###
