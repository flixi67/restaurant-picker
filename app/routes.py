import pandas as pd
from flask import Blueprint, render_template, redirect,request

# Internal imports
from app.models import db, Meetings, Members, Restaurants, RestaurantsMeetings
from app.modules.data_pipeline import run_pipeline_for_meeting
from app.matching_algorithm import create_group_code, propose_restaurants


### --- Define blueprints

main_bp = Blueprint("main", __name__)
pipeline_bp = Blueprint("pipeline", __name__, url_prefix="/recommendations")

### --- Routes of the app ------

@main_bp.route("/")
def home():
    return render_template("layout.html")

@main_bp.route("/new_meeting", methods=['GET', 'POST'])
def new_meeting():
    if request.method == 'POST':
        meeting_datetime = request.form['meetingdatetime']
        meeting_size = request.form['meetingsize']
        
        # Generate the group code
        group_code = create_group_code()

        # Create ORM model and populate its fields with IDs
        entered_meeting_data = Meetings(id = group_code, datetime = meeting_datetime, group_size = meeting_size)
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

@main_bp.route("/join_meeting", methods=['GET', 'POST'])
def join_meeting():
    # Need to fill this in
    if request.method == 'POST':
        meeting_id = request.form['meetingcode']
        member_current_location = request.form['memberloc']
        member_max_budget = request.form['memberbudget']
        member_budget_preference = request.form['memberbudgetpreference']
        member_min_rating = request.form['memberminrating']
        member_rating_preference = request.form['ratingpreference']
        member_location_preference = request.form['restaurantslocation']
        member_cash = request.form.get('membercash') == 'on' # If ticked, shows True. Otherwise False.
        member_card = request.form.get('membercard') == 'on'  # Will be True if 'on', False if not present
        member_veg = request.form.get('memberveggie') == 'on'

        entered_member_data = Members(meeting_id = meeting_id,
                                      budget = member_max_budget,
                                      uses_cash = member_cash,
                                      uses_card = member_card,
                                      is_vegetarian = member_veg,
                                      current_location = member_current_location,
                                      min_rating = member_min_rating,
                                      location_preference = member_location_preference,
                                      rating_preference = member_rating_preference, 
                                      budget_preference = member_budget_preference
                                      )

        # Add to session and commit
        db.session.add(entered_member_data)
        db.session.commit() # Write this into the Members

        # Render the confirmation page with meeting data and group code
        return render_template("member_confirmation.html",
                               meeting_id = meeting_id,
                               member_current_location=member_current_location,
                               member_budget=member_max_budget
                               )
    
    # If it's a GET request, show the form
    return render_template("member_form.html")

@main_bp.route('/recommendations', methods=['GET', 'POST'])
def recommendations_redirect():
    if request.method == 'POST':
        meeting_id = request.form.get('meeting_id')
        return redirect(f'/recommendations/{meeting_id}')
    return render_template('recommendations_redirect.html')

@pipeline_bp.route("/<string:meeting_id>")
def recommendations_output(meeting_id):
    
    meeting = Meetings.query.filter_by(id=meeting_id).first()
    if not meeting:
        return render_template("error.html", message="Meeting not found.")

    group_size = meeting.group_size

    submitted_count = Members.query.filter_by(meeting_id=meeting_id).count()

    print(f"🔁 Running pipeline with {submitted_count}/{group_size} participants.")
    try:
        run_pipeline_for_meeting(meeting_id)
        print("✨ Pipeline completed successfully!")
        results = db.session.query(Restaurants).join(RestaurantsMeetings).filter(RestaurantsMeetings.c.meeting_id == meeting_id).all() # ATTEMPTED CHANGE
        print(f"✨ Found {len(results)} results!")
        
        return render_template(
            "recommendations.html",
            results=results,
            submitted_count=submitted_count,
            group_size=group_size
        )
    except ValueError as e:
        return render_template("error.html", message=str(e))

