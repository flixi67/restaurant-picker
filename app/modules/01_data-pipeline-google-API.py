import requests
import json
import pandas as pd

# API endpoint
url = "https://places.googleapis.com/v1/places:searchNearby"

# Your API Key (Replace with your actual key)
api_key = "AIzaSyAwNuqmopqXKbaH1VM-P5SgQRm4V4lQa0o"

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
                "latitude": 37.7937,
                "longitude": -122.3965
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
    pd.json_normalize(response.json(), record_path=["places"]).to_csv("toydata.csv", index=False)
else:
    print(f"Error {response.status_code}: {response.text}")

