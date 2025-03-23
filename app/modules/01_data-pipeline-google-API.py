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

locations = ["Friedrichstraße 180, Berlin", "Brandenburger Tor, Berlin"]  # Example list of addresses, add database fetch here

points = []

for address in locations:
    coord = geocoder.geocode_address(address)
    if coord:  # Check that result was returned
        points.append([coord[k] for k in ["lat", "lng"]])
    else:
        print(f"For the adress: {address} geocoding failed. It will not be included.")
    
    centroid = MultiPoint(points).centroid

if centroid:
    print("Centroid Latitude:", centroid["lat"])
    print("Centroid Longitude:", centroid["lng"])

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
    df = 
else:
    print(f"Error {response.status_code}: {response.text}")

# Here goes the filtering pipeline, e.g. for card only restaurants or vegetarian options
# fetch binaries from database and calculate sum (OR)
# cash = # 1 or 0 (not needed for now, for the unlikely case of friends wanting to pay cash but restaurants only accept card)
card = # 1 or 0
vegetarian = # 1 or 0 

# FILTERS
# businessStatus = OPERATIONAL
# servesVegetarianFood = true in case of vegetarian = 1
# paymentOptions.acceptsDebitCards = true in case of card = 1


# Calculating distance from centroid
def get_lat_lng(address):
    result = geocoder.geocode_address(address)
    if result:
        return result['lat'], result['lng']
    return None, None

df[['lat', 'lng']] = df['formattedAddress'].apply(lambda x: pd.Series(get_lat_lng(x)))

centroid_latlng = (centroid.y, centroid.x)  # geopy expects (lat, lon)

def calc_distance(row):
    if pd.notnull(row['lat']) and pd.notnull(row['lng']):
        return geodesic((row['lat'], row['lng']), centroid_latlng).meters
    return None

df['distance_from_centroid'] = df.apply(calc_distance, axis=1)