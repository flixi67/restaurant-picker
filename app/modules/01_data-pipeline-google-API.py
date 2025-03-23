import requests
import json
import pandas as pd
import sys
import os
sys.path.append(os.path.abspath("app/modules/"))
from geocode import GoogleGeocodingAPI
from shapely.geometry import MultiPoint
from geopy.distance import geodesic


# API endpoint
url = "https://places.googleapis.com/v1/places:searchNearby"

# Your API Key
api_key = "AIzaSyAwNuqmopqXKbaH1VM-P5SgQRm4V4lQa0o"

# Calculating centroid coordinates for API request
geocoder = GoogleGeocodingAPI(api_key=api_key)

locations = ["Friedrichstraße 180, Berlin", "Brandenburger Tor, Berlin"]  # Example list of addresses

points = []

for address in locations:
    coord = geocoder.geocode_address(address)
    if coord:  # Check that result was returned
        points.append([coord[k] for k in ["lat", "lng"]])
    
    centroid = MultiPoint(points).centroid

if location:
    print("Latitude:", location["lat"])
    print("Longitude:", location["lng"])

# Request headers
headers = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": api_key,
    "X-Goog-FieldMask": "*"
}

# Request body
payload = {
    "includedTypes": ["restaurant"],
    "maxResultCount": 10,
    "locationRestriction": {
        "circle": {
            "center": {
                "latitude": centroid["lat"],
                "longitude": centroid["lng"]
            },
            "radius": 500.0
        }
    }
}

# Make the request
response = requests.post(url, headers=headers, data=json.dumps(payload))

# Print response
if response.status_code == 200:
    print("Success! Response data:")
    print(json.dumps(response.json(), indent=2))
else:
    print(f"Error {response.status_code}: {response.text}")

# Here goes the filtering pipeline, e.g. for card only restaurants or vegetarian options

# Here goes the calculation of distance to centroid