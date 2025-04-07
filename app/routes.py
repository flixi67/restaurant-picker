from flask import Flask, render_template, redirect
from matching_algorithm import create_group_code
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from requests import request
sys.path.append(os.path.abspath("app/modules/"))
# from "01_data-pipeline-google-API" import run_pipeline_for_meeting

app = Flask(__name__)

### --- Define database and models -----

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurants.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Meetings(db.Model):
    __tablename__ = 'meetings'

    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    datetime = db.Column(db.String, nullable=False)
    group_size = db.Column(db.Integer, )
    created_at = db.Column(db.String, default=datetime.utcnow)

    def __repr__(self):
        return f"<Meetings(id={self.id}, name={self.name}, datetime={self.datetime}, group_size={self.group_size}, budget={self.budget}, uses_cash={self.uses_cash}, uses_card={self.uses_card}, is_vegetarian={self.is_vegetarian}, centroid={self.centroid}, created_at={self.created_at})>"

class Restaurants(db.Model):
    __tablename__ = 'restaurants'

    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, )
    lat = db.Column(db.Float(10, 8), nullable=False)
    lng = db.Column(db.Float(11, 8), nullable=False)
    price_range = db.Column(db.Integer, )
    accepts_cash = db.Column(db.Boolean, default=False)
    accepts_card = db.Column(db.Boolean, default=False)
    vegetarian_friendly = db.Column(db.Boolean, default=False)
    rating = db.Column(db.Float(3, 2), )
    Prevent = db.Column(db.String, )

    def __repr__(self):
        return f"<Restaurants(id={self.id}, name={self.name}, description={self.description}, lat={self.lat}, lng={self.lng}, price_range={self.price_range}, accepts_cash={self.accepts_cash}, accepts_card={self.accepts_card}, vegetarian_friendly={self.vegetarian_friendly}, rating={self.rating}, Prevent={self.Prevent})>"

class Members(db.Model):
    __tablename__ = 'members'

    id = db.Column(db.String, primary_key=True)
    meeting_id = db.Column(db.String, nullable=False)
    budget = db.Column(db.Integer, )
    uses_cash = db.Column(db.Boolean, default=False)
    uses_card = db.Column(db.Boolean, default=False)
    is_vegetarian = db.Column(db.Boolean, default=False)
    location_preference = db.Column(db.String(100), )
    CONSTRAINT = db.Column(db.String, )

    def __repr__(self):
        return f"<Members(id={self.id}, meeting_id={self.meeting_id}, budget={self.budget}, uses_cash={self.uses_cash}, uses_card={self.uses_card}, is_vegetarian={self.is_vegetarian}, location_preference={self.location_preference}, CONSTRAINT={self.CONSTRAINT})>"

class Top_restaurants(db.Model):
    __tablename__ = 'top_restaurants'

    id = db.Column(db.String, primary_key=True)
    meeting_id = db.Column(db.String, nullable=False)
    restaurant_id = db.Column(db.String, nullable=False)
    features = db.Column(db.String(100), )
    added_at = db.Column(db.String, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    Prevent = db.Column(db.String, ) ###

    def __repr__(self):
        return f"<Top_restaurants(id={self.id}, meeting_id={self.meeting_id}, restaurant_id={self.restaurant_id}, features={self.features}, added_at={self.added_at}, is_active={self.is_active}, Prevent={self.Prevent})>"

### --- Routes of the app ------

@app.route("/")
def home():
    return render_template("layout.html")

@app.route("/new_meeting")
def new_meeting():
    return render_template("meeting_form.html", printed_result = create_group_code())

@app.route("/join_meeting")
def join_meeting():
    return render_template("member_form.html")

@app.route('/recommendations', methods=['GET', 'POST'])
def recommendations_redirect():
    if request.method == 'POST':
        meeting_id = request.form.get('meeting_id')
        return redirect(f'/recommendations/{meeting_id}')
    return render_template('recommendations_redirect.html')

@app.route("/recommendations/<string:meeting_id>")
def recommendations_output(meeting_id):
    # Step 1: Check if results already exist
    results = Top_restaurants.query.filter_by(meeting_id=meeting_id).all()

    if not results:
        print("✨ No results found. Calculating your ideal restaurant!")
        run_pipeline_for_meeting(meeting_id) # saves to restaurants
        # run_algorithm_for_meeting(meetind_id) # fetches from resraurants and saves to Top_restaurants

        # Fetch data from results table
        results = Top_restaurants.query.filter_by(meeting_id=meeting_id).all()

        if not results:
            return "😬 Oops. Something went wrong while generating results.", 500
    else:
        print("✅ Cached results found. Serving with flair!")

    # Step 2: Render the template with the results
    return render_template("restaurant_form.html", results=results) ###