import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.matching_algorithm import Group, propose_restaurants
from app.models import db


def test_propose_restaurants_basic():
    app = create_app()
    with app.app_context():
        meeting_id = 652234
        group = Group(meeting_id)
        group_preferences = group.calculate_group_preferences()
        raw_results = propose_restaurants([], group_preferences, meeting_id)

        assert isinstance(raw_results, list)

        if raw_results:
            print("\n✅ Recommended Restaurants:")
            for r in raw_results:
                rid = r.get('id')
                rname = r.get('name')
                rrating = r.get('rating')

                print(f"- {rname} (Rating: {rrating})")
                assert rid is not None
                assert rname is not None
        else:
            print("\n❌ No restaurants found for the given preferences.")

def test_propose_restaurants_no_candidates():
    app = create_app()
    with app.app_context():
        meeting_id = 0  # Non-existent or invalid meeting
        group = Group(meeting_id)
        group_preferences = group.calculate_group_preferences()

        raw_results = propose_restaurants([], group_preferences, meeting_id)

        assert isinstance(raw_results, list)
        print("\nℹ️ No candidates were passed in; expecting fallback behavior.")
        assert raw_results == [], "Expected empty list when no candidates provided"
