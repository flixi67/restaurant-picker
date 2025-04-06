def run_pipeline_for_meeting(meeting_id):
    from app import app, db, Meetings, Members
    import requests
    import json
    import pandas as pd
    import sys
    import os
    sys.path.append(os.path.abspath("app/modules/"))
    from geocode import GoogleGeocodingAPI
    # from openinghours import OpenNow
    # from flatten import FlattenPlacesResponse
    from shapely.geometry import MultiPoint
    from geopy.distance import geodesic

    app = create_app()

    with app.app_context():
        # Fetch from DB
        meeting = db.session.query(Meetings).get(meeting_id)
        member_addresses = db.session.query(Members.location_preference).filter_by(meeting_id=meeting_id).all()
        locations = [addr[0] for addr in member_addresses]
        member_payments = db.session.query(Members.uses_card).filter_by(meeting_id=meeting_id).all()
        card = meeting.uses_card ## calculte from member preferences
        db.session.query(Members.is_vegetarian).filter_by(meeting_id=meeting_id).all()
        vegetarian = meeting.is_vegetarian ## calculate from member preferences
        datetime = meeting.datetime.isoformat() 

        # --- rest of your pipeline logic using locations, card, vegetarian, datetime ---
        ### Fix imports/errors, write to restaurants db table (and fix names), check return statement 

        # --- DATA FETCHING PIPELINE ---

        # API endpoint
        url = "https://places.googleapis.com/v1/places:searchNearby"

        # Your API Key
        api_key = "AIzaSyAwNuqmopqXKbaH1VM-P5SgQRm4V4lQa0o"

        # Calculating centroid coordinates for API request
        geocoder = GoogleGeocodingAPI(api_key=api_key)

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

        # Print response
        if response.status_code == 200:
            print("Success! Response data:")
            print(json.dumps(response.json(), indent=2))
            df = pd.json_normalize(response.json(), record_path=["places"]) # here goes flattening the dataframe once we know the response fields we need.
        else:
            print(f"Error {response.status_code}: {response.text}")

        # --- FILTER PIPELINE ---

        # 1. Filter operational businesses
        df = df[df['businessStatus'] == 'OPERATIONAL']

        # 2. Filter vegetarian-friendly places if requested
        if vegetarian == 1 and 'servesVegetarianFood' in df.columns:
            df = df[df['servesVegetarianFood'] == True]

        # 3. Filter for debit card support if requested
        if card == 1 and 'paymentOptions.acceptsDebitCards' in df.columns:
            df = df[df['paymentOptions.acceptsDebitCards'] == True]

        # 4. Filter open places

        def check_open(row):
            try:
                return IsOpenNow(row['opening_hours'], datetime)
            except:
                return False

        if 'opening_hours' in df.columns:
            df['is_open'] = df.apply(check_open, axis=1)
            df = df[df['is_open'] == True]

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

        # df.to_csv("cleaned_data.csv")

        # At the end, return the DataFrame or result
        return {"status": "success", "meeting_id": meeting_id, "locations": df}




