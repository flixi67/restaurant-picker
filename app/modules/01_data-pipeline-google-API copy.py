import requests
import json
import pandas as pd
import sys
import os
sys.path.append(os.path.abspath("app/modules/"))
from geocode import GoogleGeocodingAPI
# from openinghours import OpenNow
from flatten import FlattenPlacesResponse
from shapely.geometry import MultiPoint
from geopy.distance import geodesic

# --- DATA FETCHING PIPELINE ---

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
    print("Centroid Latitude:", centroid.x)
    print("Centroid Longitude:", centroid.y)

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
                "latitude": centroid.x,
                "longitude": centroid.y
            },
            "radius": 500.0
        }
    }
}

# Make the request
response = requests.post(url, headers=headers, data=json.dumps(payload))

# ininiate flattener

flattener = FlattenPlacesResponse(full_scope=True)

# Print response
if response.status_code == 200:
    print("Success! Response data:")
    print(json.dumps(response.json(), indent=2))
    df =  flattener.flatten(response.json())
else:
    print(f"Error {response.status_code}: {response.text}")

# --- FILTER PIPELINE ---

card =  1 # Example list of addresses, add database fetch here
vegetarian =  1 # Example list of addresses, add database fetch here
datetime = "2025-03-22T14:30:00" # Example list of addresses, add database fetch here 

# 1. Filter operational businesses
# df = df[df['businessStatus'] == 'OPERATIONAL']

# 2. Filter vegetarian-friendly places if requested
if vegetarian == 1 and 'servesVegetarianFood' in df.columns:
    df = df[df['servesVegetarianFood'] == True]
else:
    NameError("No information on vegetarian options in database. Not filtering for dietary restrictions, please manually check.")

# 3. Filter for debit card support if requested
if card == 1 and 'paymentOptions.acceptsDebitCards' in df.columns:
    df = df[df['paymentOptions.acceptsDebitCards'] == True]
else:
    NameError("No information on payment options in database. Not filtering for card payments, please manually check.")


# 4. Filter open places

# def check_open(row):
#     try:
#         return IsOpenNow(row['opening_hours'], datetime)
#     except:
#         return False

# if 'opening_hours' in df.columns:
#     df['is_open'] = df.apply(check_open, axis=1)
#     df = df[df['is_open'] == True]

# --- TRANSFORM PIPELINE ---

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

df.to_csv("flattened_data.csv")