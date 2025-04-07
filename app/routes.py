from flask import Flask, render_template, request
from matching_algorithm import create_group_code

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("layout.html")

@app.route("/new_meeting", methods=['GET', 'POST'])
def new_meeting():
    if request.method == 'POST':
        # Retrieve form data from POST request
        meeting_datetime = request.form['meetingdatetime']
        meeting_size = request.form['meetingsize']
        
        # Generate the group code
        group_code = create_group_code()

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