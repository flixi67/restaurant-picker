from flask_sqlalchemy import SQLAlchemy
import datetime as dt
from uuid import uuid4

### --- Define database and models -----

db = SQLAlchemy()

class Meetings(db.Model):
    __tablename__ = 'meetings'

    id = db.Column(db.String(12), primary_key=True)
    datetime = db.Column(db.Text, nullable=False)
    group_size = db.Column(db.Integer)  # CHECK constraint: group_size > 0 should be handled in application or migration
    created_at = db.Column(db.Text, default=dt.datetime.utcnow)

    def __repr__(self):
        return f"<Meeting {self.id}>"

# This is the NEW association table for the many-to-many relationship between Restaurants and Meetings
RestaurantsMeetings = db.Table('restaurants_meetings',
    db.Column('restaurant_id', db.String, db.ForeignKey('restaurants.id'), primary_key=True),
    db.Column('meeting_id', db.Integer, db.ForeignKey('meetings.id'), primary_key=True),
    db.Column('distance_from_centroid', db.Float),
    db.Column('composite_score', db.Float)
)
class Restaurants(db.Model):
    __tablename__ = 'restaurants'

    id = db.Column(db.String(100), primary_key=True)
    name = db.Column(db.String(100), nullable=False) # New column
    description = db.Column(db.Text) # New column
    # meeting_id = db.Column(db.String, db.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False) # Turn into a list
    meeting_id_list = db.relationship("Meetings", secondary=RestaurantsMeetings, backref="restaurants")
    rating = db.Column(db.Numeric(3, 2), nullable=True)
    google_maps_uri = db.Column(db.String(200), nullable=False)
    website_uri = db.Column(db.String(200))
    formatted_address = db.Column(db.String(200))
    international_phone_number = db.Column(db.String(20))
    primary_type = db.Column(db.String(50))
    user_rating_count = db.Column(db.Integer)
    serves_vegetarian_food = db.Column(db.Boolean, default=False)
    accepts_cash_only = db.Column(db.Boolean, default=False)
    start_price = db.Column(db.Numeric)
    end_price = db.Column(db.Numeric)
    price_level = db.Column(db.String(50))
    #distance_from_centroid = db.Column(db.Float) # Moved to association table
    #composite_score = db.Column(db.Float) # Moved to association table

    def __repr__(self):
        return f"<Restaurant {self.id}>"

class Members(db.Model):
    __tablename__ = 'members'

    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid4()))
    meeting_id = db.Column(db.String, db.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False)
    budget = db.Column(db.Integer)
    uses_cash = db.Column(db.Boolean, default=False)
    uses_card = db.Column(db.Boolean, default=False)
    is_vegetarian = db.Column(db.Boolean, default=False)
    current_location = db.Column(db.String(100))
    min_rating = db.Column(db.Integer)
    rating_preference = db.Column(db.Integer)
    location_preference = db.Column(db.Integer)
    budget_preference = db.Column(db.Integer)

    # Manual check: uses_cash OR uses_card should be enforced in validation logic
    def __repr__(self):
        return f"<Member {self.id}>"
