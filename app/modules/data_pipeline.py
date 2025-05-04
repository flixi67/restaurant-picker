import json
import pandas as pd
import requests
from shapely.geometry import MultiPoint
from geopy.distance import geodesic
from decimal import Decimal
from datetime import datetime

# Internal imports
from app.models import db, Meetings, Members, Restaurants
from app.context import pipeline_context
from app.modules.geocode import GoogleGeocodingAPI
from app.modules.flatten import FlattenPlacesResponse
from app.modules.is_open import is_open_at_time
from app.matching_algorithm import Group, propose_restaurants

def run_pipeline_for_meeting(meeting_id):
    with pipeline_context():
        # Fetch from DB
        meeting = db.session.query(Meetings).get(meeting_id)
        if meeting is None:
            raise ValueError(f"❌ No meeting found with ID: {meeting_id}")
        member_addresses = db.session.query(Members.current_location).filter_by(meeting_id=meeting_id).all()
        locations = [addr[0] for addr in member_addresses]
        member_payments = db.session.query(Members.uses_card).filter_by(meeting_id=meeting_id).all()
        card = any(row[0] for row in member_payments) ## calculte from member preferences
        member_diets = db.session.query(Members.is_vegetarian).filter_by(meeting_id=meeting_id).all()
        vegetarian = any(row[0] for row in member_diets) ## calculate from member preferences
        meeting_time = datetime.fromisoformat(meeting.datetime) # take datetime from the meeting row we queried above and make sure it is date time format

        # --- rest of your pipeline logic using locations, card, vegetarian, datetime ---
        ### write to restaurants db table (and fix names), check return statement 

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
        
        # Create centroid
        centroid = MultiPoint(points).centroid

        # Check if centroid is valid
        
        # Check if centroid is empty before accessing coordinates
        if centroid.is_empty:
            print("Error: Centroid coordinates are empty, cannot proceed.")
        else:
            print("Centroid Latitude:", centroid.x)
            print("Centroid Longitude:", centroid.y)

        # Request headers
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "*"
        }

        # Request body
        if centroid.is_empty:
            print("Error: Centroid coordinates are None.")
        else:
            payload = {
                "includedTypes": ["restaurant"],
                "maxResultCount": 20,
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

        # Ininiate flattener
        flattener = FlattenPlacesResponse(full_scope=True)

        print("Actual status code from response:", response.status_code)
        # Print response
        if response.status_code == 200:
            print("Success! Response data:")
            print(json.dumps(response.json(), indent=2))
            try:
                df = flattener.flatten(response.json())   
                print(df)
            except Exception as e:
                print("⚠️ Error flattening response:", e)
                return {"status": "error", "message": "Flattening failed."}
        else:
            print(f"Error {response.status_code}: {response.response_text}")
            df = pd.DataFrame()
        
        print(df)

        # --- FILTER PIPELINE ---

        # 1. Filter operational businesses
        # df = df[df['businessStatus'] == 'OPERATIONAL']

        # 2. Filter vegetarian-friendly places if requested
        if vegetarian == 1 and 'servesVegetarianFood' in df.columns:
            try:
                df = df[df['servesVegetarianFood'] == True]
            except:
                raise NameError("No information on vegetarian options in database. Not filtering for dietary restrictions, please manually check.")

        # 3. Filter for debit card support if requested
        if card == 1 and 'paymentOptions.acceptsDebitCards' in df.columns:
            df = df[df['paymentOptions.acceptsDebitCards'] == True]
        else:
            raise NameError("No information on payment options in database. Not filtering for card payments, please manually check.")
        # 4. Filter open places

        # print([col for col in df.columns if "regularOpeningHours.periods" in col])
        # open_day_cols = [col for col in df.columns if ".open.day" in col]
        # print(df[open_day_cols].notnull().sum())
        # df = df[df.apply(lambda row: is_open_at_time(row, meeting_time), axis=1)]
        # print(list(df.columns))

        # --- TRANSFORM PIPELINE ---

        # Calculating distance from centroid
        # def get_lat_lng(address):
        #     result = geocoder.geocode_address(address)
        #     if result:
        #         return result['lat'], result['lng']
        #     return None, None

        df[['lat', 'lng']] = df[['location.latitude','location.longitude']]

        centroid_latlng = (centroid.y, centroid.x)  # geopy expects (lat, lon)

        def calc_distance(row):
            if pd.notnull(row['lat']) and pd.notnull(row['lng']):
                return geodesic((row['lat'], row['lng']), centroid_latlng).meters
            return None

        df['distance_from_centroid'] = df.apply(calc_distance, axis=1)

        # --- WRITE TO DB ---

        # Only select the columns that map to your Restaurants model attributes
        columns_to_keep = [
            "id",
            "rating",
            "googleMapsUri",
            "websiteUri",
            "formattedAddress",
            "internationalPhoneNumber",
            "primaryType",
            "userRatingCount",
            "servesVegetarianFood",
            "paymentOptions.acceptsCashOnly",
            "priceRange.startPrice.units",
            "priceRange.endPrice.units",
            "priceLevel",
            "distance_from_centroid"
        ]

        # Filter the dataframe
        df_db = df[columns_to_keep].copy()

        print(df_db["distance_from_centroid"])

        # Optional: rename to match your SQLAlchemy model field names
        df_db.rename(columns={
            "googleMapsUri": "google_maps_uri",
            "websiteUri": "website_uri",
            "formattedAddress": "formatted_address",
            "internationalPhoneNumber": "international_phone_number",
            "primaryType": "primary_type",
            "userRatingCount": "user_rating_count",
            "servesVegetarianFood": "serves_vegetarian_food",
            "paymentOptions.acceptsCashOnly": "accepts_cash_only",
            "priceRange.startPrice.units": "start_price",
            "priceRange.endPrice.units": "end_price",
            "priceLevel": "price_level"
        }, inplace=True)

        # Convert DataFrame rows into ORM objects
        restaurant_objects = []

        for _, row in df_db.iterrows():
            restaurant = Restaurants(
                id=row["id"],
                meeting_id=meeting.id, # this line is different because it uses the id from "meeting" ovject we fetched before
                rating=Decimal(row["rating"]) if not pd.isna(row["rating"]) else None,
                google_maps_uri=row["google_maps_uri"],
                website_uri=row["website_uri"],
                formatted_address=row["formatted_address"],
                international_phone_number=row["international_phone_number"],
                primary_type=row["primary_type"],
                user_rating_count=int(row["user_rating_count"]) if not pd.isna(row["user_rating_count"]) else None,
                serves_vegetarian_food=bool(row["serves_vegetarian_food"]),
                accepts_cash_only=bool(row["accepts_cash_only"]),
                start_price=Decimal(row["start_price"]) if not pd.isna(row["start_price"]) else None,
                end_price=Decimal(row["end_price"]) if not pd.isna(row["end_price"]) else None,
                price_level=row["price_level"],
                distance_from_centroid=float(row["distance_from_centroid"]) if not pd.isna(row["distance_from_centroid"]) else None
            )
            restaurant_objects.append(restaurant)

        print(f"Number of restaurant objects created: {len(restaurant_objects)}")

        # Bulk insert
        db.session.bulk_save_objects(restaurant_objects)
        db.session.commit()

# --- NEW CODE --- #

        # Create a Group object for the meeting
        group = Group(meeting_id)

        # Calculate group preferences based on the group object
        group_preferences = group.calculate_group_preferences()

        # Fetch restaurant candidates
        # Fetch restaurant candidates for the current meeting
        candidates = db.session.query(Restaurants).filter_by(meeting_id=meeting.id).all()

        # Pass the candidates and group preferences to the propose_restaurants function
        recommended_restaurants = propose_restaurants(candidates, group_preferences, meeting_id)

        # Optionally: Do something with the recommended restaurants, like saving them to the DB or logging
        print(f"Recommended restaurants for meeting {meeting_id}:")

        for restaurant in recommended_restaurants:
            print(f"Restaurant ID: {restaurant.id}, Composite Score: {restaurant.composite_score}")

        return {"status": "success", "meeting_id": meeting_id, "recommended_restaurants": recommended_restaurants}

        # At the end, return the DataFrame or result
        #return {"status": "success", "meeting_id": meeting_id, "locations": df_db}
