import numpy as np
import pandas as pd
import requests
import datetime
import wtforms
import random
import geopandas

# Function: Create and return random group code
def create_group_code():
    code = random.randint(0,6)
    return code

# Function: Take latitutde and longitude, and create a tuple of coordinates
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

# Function: Add weights to each item and calculate a composite score
def create_weighting(list_of_items):
    """
    Inputs: List of ordered items
    Output: Dictionary of item and its weight
    """
    weights = {}
    weights[list_of_items[0]] = 0.5 # Most important item
    weights[list_of_items[1]] = 0.3 # Second weight
    weights[list_of_items[2]] = 0.2 # Third weight

# Function: Return restaurants within radial circle
def get_radius_restaurants(circle):
    # Obtain all restaurants in Berlin then turn into spatial objects
    # Or do this without geopandas?
    

# Function: Return restaurants with weights
def filter_restaurants(restaurants, weights_dictionary):
    # Refer to weights dictionary
    # Filter restaurants with weights







