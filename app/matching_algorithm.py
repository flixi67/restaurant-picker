from app.models import db, Meetings, Members, Restaurants
from app.context import pipeline_context
from app.modules.geocode import GoogleGeocodingAPI

import numpy as np
import pandas as pd
import requests
import datetime
import wtforms
import random
import geopandas

# Function: Create and return a random group code
def create_group_code():
    """
    Inputs: None
    Output: 6 digit code
    Later: Add a list; only create a code that is not already in the list
    """
    while True:
        # Generate a random 6-digit number
        code = random.randint(100000, 999999)
        # Check if the code already exists in the database
        existing_codes = db.session.query(Meetings.id).all()
        existing_codes = [code[0] for code in existing_codes]
        if code not in existing_codes:
            return code  # Return the code if it's unique

# Create a class for a single group member
class Member:
    def __init__(self, meeting_id):
        """
        preferences should be in the following format:

        preferences = {
            'rating': (min_rating, rating_weighting),
            'max_budget': (max_budget, budget_weighting),
            'dist_from_centroid': distance_weighting
        }
        """
        self.meeting_id = meeting_id

    

# Create a class for the group
class Group:
    def __init__(self, meeting_id):
        self.meeting_id = meeting_id
        self.members = self.get_members_for_group()
        
    def get_members_for_group(self):
        """
        Fetches all members associated with the given meeting ID.
        
        Returns:
            A list of members' preferences.
        """
        # Fetch member data from the database
        members_data = db.session.query(Members).filter_by(meeting_id=self.meeting_id).all()
        members_preferences = []
        
        # Collect preferences for each member
        for member in members_data:
            preferences = {
                'rating_preference': (member.min_rating, member.rating_preference),
                'max_budget': (member.budget, member.budget_preference),
                'dist_from_centroid': member.location_preference,
                'uses_cash': member.uses_cash,
                'uses_card': member.uses_card,
                'is_vegetarian': member.is_vegetarian,
                'current_location': member.current_location
            }
            members_preferences.append(preferences)
        
        return members_preferences

    def calculate_group_preferences(self):
        """
        Calculate the group preferences based on individual member preferences.
        Returns a dictionary with combined group preferences.
        """
        # Initialize variables to calculate group preferences
        group_min_rating = float('inf')
        group_rating_weight = 0
        group_max_budget = 0
        group_budget_weight = 0
        group_dist_weight = 0

        # Iterate through each member's preferences
        for member in self.members:
            rating_pref = member['rating_preference'][0]
            rating_weight = member['rating_preference'][1]
            budget_max = member['max_budget'][0]  # Corrected: use the first element for max budget
            budget_weight = member['max_budget'][1]
            dist_weight = member['dist_from_centroid']

            # Update group preferences
            if rating_pref < group_min_rating:
                group_min_rating = rating_pref
            group_rating_weight += rating_weight
            if budget_max > group_max_budget:
                group_max_budget = budget_max
            group_budget_weight += budget_weight
            group_dist_weight += dist_weight

        # Normalize weights by number of members
        num_members = len(self.members)
        group_rating_weight /= num_members
        group_budget_weight /= num_members
        group_dist_weight /= num_members

        # Create the group preferences dictionary
        group_preferences = {
            'dist': group_dist_weight,
            'rating': (group_min_rating, group_rating_weight),
            'max_budget_per_person': (group_max_budget, group_budget_weight)
        }

        return group_preferences

def propose_restaurants(candidates, group_preferences, meeting_id):
    """
    Recommends restaurants with budget constraints and dietary options.
    Looks at restaurants that were given from data_pipeline.py and filters them
    based on group preferences.
    
    Args:
        candidates: DataFrame of restaurants from spatial filtering
        group_preferences: {
            'distance_from_centroid':, 
            'rating': ('4 | 5', 0.4),
            'max_budget_per_person': Maximum $$ per person (e.g., 20)
        }
        meeting_id: The ID of the current meeting

    Returns:
        DataFrame sorted by composite score with budget filtering
    """
    with pipeline_context():
        # Fetch from DB
        candidates = db.session.query(Restaurants).filter_by(meeting_id=meeting_id).all()
        #preferences = db.session.query(Members).filter_by(meeting_id=meeting_id).all()
        
        # Create outcome vector
        scores = []

        # Iterate through restaurants
        for restaurant in candidates:
            score = 0

            # 1. Budget constraint (hard filter + soft scoring)
            if restaurant.end_price > group_preferences['max_budget_per_person'][0]:
                continue  # Skip if over budget

            budget_score = 1 - (restaurant['end_price'] / group_preferences['max_budget_per_person'][0])
            score += 0.2 * budget_score

            # 2. Rating (normalized 0-1 scale)
            score += 0.1 * (restaurant['rating'] / 5)

            # 3. Distance from centroid (closer = better)
            if 'distance_from_centroid' in restaurant:
                score += 0.05 * (1 / (1 + restaurant['distance_from_centroid']))  # Example: inverse distance

            scores.append(score)

        # Apply scoring and sort restaurants by composite score
        for i, restaurant in enumerate(candidates):
            restaurant.composite_score = scores[i]

        # Sort by composite score in descending order
        sorted_restaurants = sorted(candidates, key=lambda r: r.composite_score, reverse=True)

        return sorted_restaurants

        # Apply scoring and filter
        #candidates['composite_score'] = scores
        #return candidates.sort_values('composite_score', ascending=False)


""" ---- Functions that are no longer needed ----
# Function: Take latitude and longitude, and create a tuple of coordinates
def create_coord(lat1, long2):
    point = (lat1, long2)
    return point

# Function: Calculate centroid location
def calculate_centroid(*points):
    coords = [points]
    coords_array = np.array(coords)
    # Calculate the average of latitudes and longitudes
    centroid = np.mean(coords, axis=0)
    centroid = (centroid[0], centroid[1])
    return centroid

# Function: Calculate area of radial circle from centroid
def get_search_area():
    # Create 'Point' object with centroid
    centre = Point(centroid[1], centroid[0])
    # We will need to make the radius flexible in the future
    radius = 5
    # Create circle with 'buffer' method from geopandas
    circle = centre.buffer(radius / 111) # The '111' converts the radius to degrees
    return circle

# Function to filter restaurants
def filter_restaurants(restaurants_df, centroid, radius_km):
    # Step 1: Fast pre-filter (e.g., approximate bounding box or city)
    min_lat, max_lat = centroid[0] - 0.1, centroid[0] + 0.1  # ~11 km rough filter
    candidates = restaurants_df[
        (restaurants_df.lat.between(min_lat, max_lat)) & 
        (restaurants_df.lon.between(centroid[1] - 0.1, centroid[1] + 0.1))
    ]

    #Step 2: Convert only candidates to Shapely Points
    candidates["geometry"] = candidates.apply(
        lambda row: Point(row.lon, row.lat), axis=1 #Conversion to spatial objects
    )

# Step 3: Precise spatial filter
    search_area = Point(centroid[1], centroid[0]).buffer(max_distance_km / 111)
    return candidates[candidates.geometry.within(search_area)]
"""
