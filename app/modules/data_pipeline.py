import json
import pandas as pd
import requests
from shapely.geometry import MultiPoint
from geopy.distance import geodesic
from decimal import Decimal

# Internal imports
from app.models import db, Meetings, Members, Restaurants
from app.context import pipeline_context
from app.modules.geocode import GoogleGeocodingAPI

def run_pipeline_for_meeting(meeting_id):
    with pipeline_context():
        # Fetch from DB
        meeting = db.session.query(Meetings).get(meeting_id)
        if meeting is None:
            raise ValueError(f"❌ No meeting found with ID: {meeting_id}")
        member_addresses = db.session.query(Members.location_preference).filter_by(meeting_id=meeting_id).all()
        locations = [addr[0] for addr in member_addresses]
        member_payments = db.session.query(Members.uses_card).filter_by(meeting_id=meeting_id).all()
        card = any(row[0] for row in member_payments) ## calculte from member preferences
        member_diets = db.session.query(Members.is_vegetarian).filter_by(meeting_id=meeting_id).all()
        vegetarian = any(row[0] for row in member_diets) ## calculate from member preferences
        datetime = meeting.datetime # take datetime from the meeting row we queried above

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

        # --- WRITE TO DB ---

        # Only select the columns that map to your Restaurants model attributes
        columns_to_keep = [
            "id",
            "meeting_id",
            "rating",
            "googleMapsUri",
            "websiteUri",
            "formattedAddress",
            "internationalPhoneNumber",
            "primaryType",
            "userRatingCount",
            "servesVegetarianFood",
            "acceptsCashOnly",
            "startPrice",
            "endPrice",
            "priceLevel"
        ]

        # Filter the dataframe
        df_db = df[columns_to_keep].copy()

        # Optional: rename to match your SQLAlchemy model field names
        df_db.rename(columns={
            "googleMapsUri": "google_maps_uri",
            "websiteUri": "website_uri",
            "formattedAddress": "formatted_address",
            "internationalPhoneNumber": "international_phone_number",
            "primaryType": "primary_type",
            "userRatingCount": "user_rating_count",
            "servesVegetarianFood": "serves_vegetarian_food",
            "acceptsCashOnly": "accepts_cash_only",
            "startPrice": "start_price",
            "endPrice": "end_price",
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
                price_level=row["price_level"]
            )
            restaurant_objects.append(restaurant)

        # Bulk insert
        db.session.bulk_save_objects(restaurant_objects)
        db.session.commit()

        # At the end, return the DataFrame or result
        return {"status": "success", "meeting_id": meeting_id, "locations": df_db}
