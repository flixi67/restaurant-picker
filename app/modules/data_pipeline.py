import json
import pandas as pd
import requests
from shapely.geometry import MultiPoint
from geopy.distance import geodesic
from decimal import Decimal
from datetime import datetime

# Internal imports
from app.models import db, Meetings, Members, Restaurants, RestaurantsMeetings
from app.context import pipeline_context
from app.modules.geocode import GoogleGeocodingAPI
from app.modules.flatten import FlattenPlacesResponse
from app.modules.is_open import is_open
from app.matching_algorithm import Group, propose_restaurants

def run_pipeline_for_meeting(meeting_id):
    with pipeline_context():
        meeting = db.session.query(Meetings).get(meeting_id)
        if meeting is None:
            raise ValueError(f"❌ No meeting found with ID: {meeting_id}")

        member_addresses = db.session.query(Members.current_location).filter_by(meeting_id=meeting_id).all()
        locations = [addr[0] for addr in member_addresses]
        member_payments = db.session.query(Members.uses_card).filter_by(meeting_id=meeting_id).all()
        card = any(row[0] for row in member_payments)
        member_diets = db.session.query(Members.is_vegetarian).filter_by(meeting_id=meeting_id).all()
        vegetarian = any(row[0] for row in member_diets)
        meeting_time = datetime.fromisoformat(meeting.datetime)

        url = "https://places.googleapis.com/v1/places:searchNearby"
        api_key = "AIzaSyAwNuqmopqXKbaH1VM-P5SgQRm4V4lQa0o"
        geocoder = GoogleGeocodingAPI(api_key=api_key)

        points = []
        for address in locations:
            coord = geocoder.geocode_address(address)
            if coord:
                points.append([coord[k] for k in ["lat", "lng"]])
            else:
                print(f"For the address: {address} geocoding failed. It will not be included.")

        centroid = MultiPoint(points).centroid
        if centroid.is_empty:
            print("Error: Centroid coordinates are empty, cannot proceed.")
            return

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "*"
        }

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

        response = requests.post(url, headers=headers, data=json.dumps(payload))
        flattener = FlattenPlacesResponse(full_scope=True)

        if response.status_code == 200:
            print("Success! Response data:")
            df = flattener.flatten(response.json())
            df_original = df.copy(deep=True)
            # filter restaurants that are open at the meeting time
            print(f"Meeting time: {meeting_time}")
            open_restaurants = []

            for i, row in enumerate(df.to_dict('records')):
                try:
                    restaurant_name = row.get('displayName.text', f"Restaurant {i}")
                    
                    # Get weekday descriptions
                    weekday_descriptions = row.get('regularOpeningHours.weekdayDescriptions')
                    
                    # Skip if no descriptions available
                    if weekday_descriptions is None or not isinstance(weekday_descriptions, list):
                        continue
                        
                    # Check if restaurant is open
                    is_restaurant_open = is_open(
                        weekday_descriptions,
                        meeting_time.weekday(),
                        meeting_time.hour,
                        meeting_time.minute
                    )
                    
                    if is_restaurant_open:
                        open_restaurants.append(i)
                        print(f"Restaurant open: {restaurant_name}")
                        
                except Exception as e:
                    print(f"Error checking restaurant {i}: {e}")

            # Filter the DataFrame to only include open restaurants
            if open_restaurants:
                print(f"Found {len(open_restaurants)} open restaurants")
                df = df.iloc[open_restaurants].copy()
                print(f"Filtered to {len(df)} restaurants that are open at meeting time")
            else:
                print("No restaurants found open at meeting time. Keeping all restaurants.")                    
        else:
            print(f"Error {response.status_code}: {response.text}")
            return

        if vegetarian and 'servesVegetarianFood' in df.columns:
            df = df[df['servesVegetarianFood'] == True]

        if card == 1:
            credit_col = 'paymentOptions.acceptsCreditCards'
            debit_col = 'paymentOptions.acceptsDebitCards'
            
            if credit_col in df.columns or debit_col in df.columns:
                df = df[
                    ((credit_col in df.columns) & (df[credit_col] == True)) |
                    ((debit_col in df.columns) & (df[debit_col] == True))
                    ]
            else:
                print("⚠️ No card payment fields found in the data.")

        df[['lat', 'lng']] = df[['location.latitude', 'location.longitude']]
        centroid_latlng = (centroid.y, centroid.x)

        def calc_distance(row):
            if pd.notnull(row['lat']) and pd.notnull(row['lng']):
                return geodesic((row['lat'], row['lng']), centroid_latlng).meters
            return None

        df['distance_from_centroid'] = df.apply(calc_distance, axis=1)

        columns_to_keep = [
            col for col in [
                "id", "rating", "displayName.text", "editorialSummary.text", "googleMapsUri",
                "websiteUri", "formattedAddress", "internationalPhoneNumber",
                "primaryTypeDisplayName.text", "userRatingCount", "servesVegetarianFood",
                "paymentOptions.acceptsCashOnly", "priceRange.startPrice.units",
                "priceRange.endPrice.units", "priceLevel", "distance_from_centroid"
            ] if col in df.columns
        ]

        df_db = df[columns_to_keep].copy()

        df_db.rename(columns={
            "googleMapsUri": "google_maps_uri",
            "websiteUri": "website_uri",
            "formattedAddress": "formatted_address",
            "internationalPhoneNumber": "international_phone_number",
            "primaryTypeDisplayName.text": "primary_type",
            "displayName.text": "restaurant_name",
            "editorialSummary.text": "description",
            "userRatingCount": "user_rating_count",
            "servesVegetarianFood": "serves_vegetarian_food",
            "paymentOptions.acceptsCashOnly": "accepts_cash_only",
            "priceRange.startPrice.units": "start_price",
            "priceRange.endPrice.units": "end_price",
            "priceLevel": "price_level"
        }, inplace=True)

        restaurant_objects = []

        for _, row in df_db.iterrows():
            existing_restaurant = Restaurants.query.filter_by(id=row["id"]).first()
            if existing_restaurant is None:
                try:
                    start_price = Decimal(row["start_price"]) if pd.notna(row["start_price"]) else None
                except:
                    start_price = None

                try:
                    end_price = Decimal(row["end_price"]) if pd.notna(row["end_price"]) else None
                except:
                    end_price = None

                restaurant = Restaurants(
                    id=row["id"],
                    name=row.get("restaurant_name", ""),
                    description=row.get("description", ""),
                    rating=Decimal(row["rating"]) if pd.notna(row["rating"]) else None,
                    google_maps_uri=row.get("google_maps_uri", ""),
                    website_uri=row.get("website_uri", ""),
                    formatted_address=row.get("formatted_address", ""),
                    international_phone_number=row.get("international_phone_number", ""),
                    primary_type=row.get("primary_type", ""),
                    user_rating_count=int(row.get("user_rating_count", 0)) if pd.notna(row.get("user_rating_count", None)) else None,
                    serves_vegetarian_food=bool(row.get("serves_vegetarian_food", False)),
                    accepts_cash_only=bool(row.get("accepts_cash_only", False)),
                    start_price=start_price,
                    end_price=end_price,
                    price_level=row.get("price_level", None)
                )

                if restaurant.meeting_id_list is None:
                    restaurant.meeting_id_list = []
                meeting = db.session.query(Meetings).get(meeting_id)
                restaurant.meeting_id_list.append(meeting)
                restaurant_objects.append(restaurant)

                existing_association = db.session.query(RestaurantsMeetings).filter_by(
                    restaurant_id=row["id"],
                    meeting_id=meeting_id
                ).first()

                if existing_association is None:
                    db.session.execute(
                        RestaurantsMeetings.insert().values(
                            restaurant_id=row["id"],
                            meeting_id=meeting_id,
                            composite_score=0,
                            distance_from_centroid=row["distance_from_centroid"]
                        )
                    )
                db.session.flush()

        print(f"Number of restaurant objects created: {len(restaurant_objects)}")


# --- CHLOE'S EDIT: REMOVING THE FOLLOWING CHUNK AVOIDS EMPTY RESULTS UPON PAGE REFRESH (VER 1 OF THIS CODE) ---
        # Delete previous cached results
        # if db.session.query(Restaurants).filter_by(meeting_id=meeting_id).count() > 0: # Change to check if meeting_id_list includes the meeting_id
        #     db.session.query(Restaurants).filter_by(meeting_id=meeting_id).delete() # Change to check if meeting_id_list includes the meeting_id
        #     db.session.commit()
        #     print(f"Deleted previous cached results for meeting ID: {meeting_id}")
        # Query restaurants linked to this meeting_id
        # # Delete Restaurants where meeting_id is in their meeting_id_list
        # restaurants_to_delete = ( #ATTEMPTED CHANGE
        #     db.session.query(Restaurants).join(RestaurantsMeetings)  # Join the association table (RestaurantsMeetings)
        #     .filter(RestaurantsMeetings.c.meeting_id == meeting_id)  # Filter by the meeting_id in the association table
        #     .all()
        # )

        # if restaurants_to_delete:
        #     for restaurant in restaurants_to_delete:
        #         db.session.delete(restaurant)
        #     db.session.commit()
        #     print(f"Deleted previous cached results for meeting ID: {meeting_id}")

        # Delete Restaurants where meeting_id is in their meeting_id_list (attending a specific meeting)


# --- CHLOE'S EDIT: REMOVING THE FOLLOWING CHUNK AVOIDS EMPTY RESULTS UPON PAGE REFRESH (VER 2 OF THIS CODE) ---
        # restaurants_to_delete = (
        #     db.session.query(Restaurants).filter(RestaurantsMeetings.c.meeting_id == meeting_id).all()
        # )

        # print(f"Restaurants to delete: {restaurants_to_delete}")

        # if restaurants_to_delete:
        #     for restaurant in restaurants_to_delete:
        #         # Delete the association from the RestaurantsMeetings table first to avoid orphaned relationships
        #         associations_to_delete = db.session.query(RestaurantsMeetings).filter_by(restaurant_id=restaurant.id, meeting_id=meeting_id).all()
        #         if associations_to_delete:
        #             print(f"Number of associations to delete: {len(associations_to_delete)}")
        #             for association in associations_to_delete:
        #                 db.session.execute(
        #                     RestaurantsMeetings.delete().where(
        #                         (RestaurantsMeetings.c.restaurant_id == restaurant.id) &
        #                         (RestaurantsMeetings.c.meeting_id == meeting_id)
        #                     )
        #                 )
        #             print(f"Deleted associations for restaurant {restaurant.id} and meeting {meeting_id}")
        #         else:
        #             print(f"No associations found for restaurant {restaurant.id} and meeting {meeting_id}")
        #         # Now delete the actual restaurant entity
        #         db.session.delete(restaurant)
        #         print(f"Deleted restaurant {restaurant.id}")

        #     db.session.commit()
        #     print(f"Deleted previous cached restaurant results and associations for meeting ID: {meeting_id}")
        # else:
        #     print(f"No previous RestaurantsMeetings associations found for meeting ID: {meeting_id}")

 # --- END: REMOVING THE ABOVE CHUNK AVOIDS EMPTY RESULTS UPON PAGE REFRESH  ---

        # Bulk insert
        print(f"Number of restaurant objects to insert: {len(restaurant_objects)}")
        print(f"Restaurant objects: {restaurant_objects}, {type(restaurant_objects)}")

        db.session.bulk_save_objects(restaurant_objects)
        db.session.commit()
        print(f"Inserted {len(restaurant_objects)} restaurant objects into the database.")

        # Create a Group object for the meeting
        group = Group(meeting_id)

        # Calculate group preferences based on the group object
        group_preferences = group.calculate_group_preferences()

        # Fetch restaurant candidates for the current meeting
        candidates = db.session.query(Restaurants).join(RestaurantsMeetings, Restaurants.id == RestaurantsMeetings.c.restaurant_id).filter(RestaurantsMeetings.c.meeting_id == meeting.id).all()

        # Pass the candidates and group preferences to the propose_restaurants function
        recommended_restaurants = propose_restaurants(candidates, group_preferences, meeting_id)

        return {"status": "success", "meeting_id": meeting_id, "recommended_restaurants": recommended_restaurants}
