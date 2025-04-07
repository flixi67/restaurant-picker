from flask import Flask, render_template, request
from matching_algorithm import create_group_code, propose_restaurants
import pandas as pd

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("layout.html")

@app.route("/new_meeting", methods=['GET', 'POST'])
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

@app.route("/join_meeting")
def join_meeting():
    return render_template("member_form.html")

@app.route("/recommendations")
def recommendations_output():
    return render_template("restaurant_form.html")

@app.route("/restaurant_preferences/<group_code>", methods=['GET', 'POST'])
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