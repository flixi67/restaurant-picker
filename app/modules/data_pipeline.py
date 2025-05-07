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
from app.modules.is_open import is_open_at_time
from app.matching_algorithm import Group, propose_restaurants

def run_pipeline_for_meeting(meeting_id):
    with pipeline_context():
        # Fetch the meeting from the database
        meeting = db.session.query(Meetings).get(meeting_id)
        # If there is no meeting, raise an error
        if meeting is None:
            raise ValueError(f"❌ No meeting found with ID: {meeting_id}")
        # Fetch members' preferences
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

        # Print response and check for errors
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
        if card == 1 and 'paymentOptions.acceptsCreditCards' in df.columns:
            df = df[df['paymentOptions.acceptsCreditCards'] == True]
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
            col for col in [
            "id",
            "rating",
            "displayName.text",
            "editorialSummary.text",
            "googleMapsUri",
            "websiteUri",
            "formattedAddress",
            "internationalPhoneNumber",
            "primaryTypeDisplayName.text", # Changed the type from primaryType to primaryTypeDisplayName.text
            "userRatingCount",
            "servesVegetarianFood",
            "paymentOptions.acceptsCashOnly",
            "priceRange.startPrice.units",
            "priceRange.endPrice.units",
            "priceLevel",
            "distance_from_centroid"
        ] if col in df.columns
        ]

        # Filter the dataframe
        df_db = df[columns_to_keep].copy()
        
        print(df_db["distance_from_centroid"])

        if "editorialSummary.text" not in df.columns:
            df["editorialSummary.text"] = ""  # Create empty column if missing

        # Optional: rename to match your SQLAlchemy model field names
        df_db.rename(columns={
            "googleMapsUri": "google_maps_uri",
            "websiteUri": "website_uri",
            "formattedAddress": "formatted_address",
            "internationalPhoneNumber": "international_phone_number",
            "primaryTypeDisplayName.text": "primary_type", # Changed the type from primaryType to primaryTypeDisplayName.text
            "displayName.text": "restaurant_name",  # New column to save
            "editorialSummary.text": "description",  # New column to save
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

            # Check if the restaurant already exists in the database -- NEW CODE
            existing_restaurant = Restaurants.query.filter_by(id=row["id"]).first()

            # If the restaurant does not exist, create a new one
            if existing_restaurant is None:

                # Convert start_price to Decimal, handling NaN values
                try:
                    start_price = Decimal(row["start_price"]) if pd.notna(row["start_price"]) else None
                except:
                    print(f"⚠️ Could not convert start_price for restaurant {row['id']}: {row['start_price']}")
                    start_price = None

                # Convert end_price to Decimal, handling NaN values
                try:
                    end_price = Decimal(row["end_price"]) if pd.notna(row["end_price"]) else None
                except:
                    print(f"⚠️ Could not convert end_price for restaurant {row['id']}: {row['end_price']}")
                    end_price = None

                # Create a new Restaurants object
                restaurant = Restaurants(
                id=row["id"],
                name=row["restaurant_name"], # New column to save
                description = row.get("description", ""), # New column to save
                # meeting_id=meeting.id, # Change into a list of meeting IDs # ATTEMPTED CHANGE
                rating=Decimal(row["rating"]) if not pd.isna(row["rating"]) else None,
                google_maps_uri=row["google_maps_uri"],
                website_uri=row["website_uri"],
                formatted_address=row["formatted_address"],
                international_phone_number=row["international_phone_number"],
                primary_type=row["primary_type"],
                user_rating_count=int(row["user_rating_count"]) if not pd.isna(row["user_rating_count"]) else None,
                serves_vegetarian_food = bool(row.get("serves_vegetarian_food", False)),
                accepts_cash_only=bool(row["accepts_cash_only"]),
                start_price=start_price,
                end_price=end_price,
                price_level = row.get("price_level", None),
                #distance_from_centroid=float(row["distance_from_centroid"]) if not pd.isna(row["distance_from_centroid"]) else None
                )
                # Ensure meeting_id_list is initialized (if it's None)
                if restaurant.meeting_id_list is None:
                    restaurant.meeting_id_list = []  # Initialize as empty list

                # Now append the meeting_id to the list of meeting IDs per restaurant
                # restaurant.meeting_id_list.append(meeting_id)# ATTEMPTED CHANGE
                meeting = db.session.query(Meetings).get(meeting_id)
                restaurant.meeting_id_list.append(meeting)

                # Add the object to the list
                restaurant_objects.append(restaurant)

                print(f"These are the restaurant objects made: {restaurant_objects}. There are {len(restaurant_objects)} restaurant objects in total.")

                # ------ RestaurantsMeetings table ------

                # Check if the combination already exists in the RestaurantsMeetings table
                existing_associated_entry = db.session.query(RestaurantsMeetings).filter_by(
                    restaurant_id=row["id"],
                    meeting_id=meeting_id
                ).first()

                # Only insert if the combination does not exist
                if existing_associated_entry is None:
                    db.session.execute(
                        RestaurantsMeetings.insert().values(
                            restaurant_id=row["id"],
                            meeting_id=meeting_id,
                            composite_score=0,  # Placeholder for composite score
                            distance_from_centroid=row["distance_from_centroid"]  # Store distance here
                        )
                    )
                    print(f"Inserted new entry for restaurant {row['id']} and meeting {meeting_id} into RestaurantsMeetings.")
                else:
                    print(f"Entry for restaurant {row['id']} and meeting {meeting_id} already exists.")

                db.session.flush()

        # Check the number of restaurant objects created
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
