import numpy as np
import pandas as pd
import requests
import datetime
import wtforms
import random
import geopandas

# Function: Create and return random group code
def create_group_code():
    """
    Inputs: None
    Output: 6 digit code
    Later: Add a list; only create a code that is not already in the list
    """
    # Generate a random 6 digit number
    code = random.randint(100000, 999999)
    if code:
        # Check if the code already exists in the database
        existing_codes = db.session.query(Meetings.meeting_id).all()
    return code

# Function: Add weights to each item and calculate a composite score
def create_weighting(list_of_items):
    """
    Inputs: List of ordered items;
            possible items: min_rating, max_cost, dist_from_centroid
    Output: Dictionary of item and its weight
    """
    weights = {}
    weights[list_of_items[0]] = 0.5 # Most important item
    weights[list_of_items[1]] = 0.3 # Second weight
    weights[list_of_items[2]] = 0.2 # Third weight

# Create a class for a single group member
class Member:
    def __init__(self, preferences):

        """
        preferences should be in the following format:

        preferences = {
            'rating' = (0,0) # Minimum rating, weighting
            'max_budget' = (0,0) # Maximum budget, weighting
            'dist_from_centroid' = 0 # Weighting
        }
        """
        """
        For example:
        preferences = {
            'rating' = (4,0.5)
            'max_budget' = (100,0.3)
            'dist_from_centroid' = 0.2
        }"""
        self.preferences = preferences
    


# Create a class for the group
class Group:
    def __init__(self, members):
        self.members = members
    def group_preferences(members):
        # Initialise weightings and preferences
        group_min_rating = 0
        group_rating_weight = 0
        group_max_budget = 0
        group_budget_weight = 0
        dist_weight = 0
        for member in members:
            rating_pref = member.preferences['rating'][0]
            rating_weight = member.preferences['rating'][1]
            budget_max = member.preferences['max_budget'][1]
            budget_weighting = member.preferences['max_budget'][1]
            if rating_pref > group_min_rating:
                group_min_rating = rating_pref
            group_rating_weight += rating_weight
            if budget_max < group_max_budget:
                group_max_budget = budget_max
            group_budget_weight += budget_max
            group_dist_weight += member.preference['dist_from_centroid']
        # Calculate the average group rating weight
        group_rating_weight = group_rating_weight / len(members)
        # Calculate the average group budget weight
        group_budget_weight = group_budget_weight / len(members)
        # Calculate average group distance weight
        group_dist_weight = group_dist_weight / len(members)

        group_preferences = {
            'dist': group_dist_weight,
            'rating': (group_min_rating, group_rating_weight),
            'max_budget_per_person': (group_max_budget, group_budget_weight)
        }

        return group_preferences

def propose_restaurants(candidates, group_preferences):
    """
    Recommends restaurants with budget constraints and dietary options.
    
    Args:
        candidates: DataFrame of restaurants from spatial filtering
        group_preferences: {
            'dietary': ('vegetarian | vegan', 0.3), 
            'rating': ('4 | 5', 0.4),
            'max_budget_per_person': Maximum $$ per person (e.g., 20)
        }
        
    
    Returns:
        DataFrame sorted by composite score with budget filtering
    """
    candidates = candidates.copy()
    scores = []

    for _, restaurant in candidates.iterrows():
        score = 0
        
        # 1. Apply cuisine type weighting (exact match)
        cuisine_pref, cuisine_weight = group_preferences.get('cuisine_type', (None, 0))
        if cuisine_pref and restaurant['cuisine_type'] == cuisine_pref:
            score += cuisine_weight
        
        # 2. Dietary options (partial match)
        dietary_pref, dietary_weight = group_preferences.get('dietary', (None, 0))
        if dietary_pref:
            # Check if restaurant offers the preferred dietary option
            if dietary_pref.lower() in restaurant['dietary_options'].lower():
                score += dietary_weight
            # Bonus for fully vegan restaurants if vegetarian preferred
            elif dietary_pref == 'vegetarian' and 'vegan' in restaurant['dietary_options'].lower():
                score += dietary_weight * 0.8  # Partial credit
        
        # 3. Budget constraint (hard filter + soft scoring)
        budget_ok = restaurant['priceRange.endPrice.units'] <= group_preferences['max_budget_per_person']
        if not budget_ok:
            continue  # Skip restaurants over budget
            
        # Budget scoring (cheaper = better within limit)
        budget_score = 1 - (restaurant['priceRange.endPrice.units'] / group_preferences['max_budget_per_person'])
        score += 0.2 * budget_score  # 20% weight to budget efficiency
        
        # 4. Rating (normalized 0-1 scale)
        score += 0.1 * (restaurant['rating'] / 5)
        
        scores.append(score)
    
    # Apply scoring and filter
    candidates['composite_score'] = scores
    return candidates.sort_values('composite_score', ascending=False)
        



""" ---- Functions that are no longer needed ---- """
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

