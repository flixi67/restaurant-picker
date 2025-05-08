from app.models import db, Meetings, Members, Restaurants, RestaurantsMeetings
from app.context import pipeline_context

import pandas as pd
import numpy as np
import random
from sqlalchemy import update

# Debugging: Print the columns of RestaurantsMeetings
print(RestaurantsMeetings.columns.keys())

def create_group_code():
    while True:
        code = random.randint(100000, 999999)
        existing_codes = db.session.query(Meetings.id).all()
        existing_codes = [code[0] for code in existing_codes]
        if code not in existing_codes:
            return code

class Group:
    def __init__(self, meeting_id):
        self.meeting_id = meeting_id
        self.members = self.get_members_for_group()

    def get_members_for_group(self):
        members_data = db.session.query(Members).filter_by(meeting_id=self.meeting_id).all()
        members_preferences = []
        for member in members_data:
            preferences = {
                'rating_preference': (member.min_rating, member.rating_preference),
                'max_budget': (member.budget, member.budget_preference),
                'dist_from_centroid': member.location_preference,
                'uses_cash': member.uses_cash,
                'uses_card': member.uses_card,
                'is_vegetarian': member.is_vegetarian,
                'current_location': member.current_location
            }
            members_preferences.append(preferences)
        return members_preferences

    def calculate_group_preferences(self):
        group_min_rating = float('inf')
        group_rating_weight = 0
        group_max_budget = 0
        group_budget_weight = 0
        group_dist_weight = 0

        for member in self.members:
            rating_pref = member['rating_preference'][0]
            rating_weight = member['rating_preference'][1]
            budget_max = member['max_budget'][0]
            budget_weight = member['max_budget'][1]
            dist_weight = member['dist_from_centroid']

            if rating_pref < group_min_rating:
                group_min_rating = rating_pref
            group_rating_weight += rating_weight
            if budget_max > group_max_budget:
                group_max_budget = budget_max
            group_budget_weight += budget_weight
            group_dist_weight += dist_weight

        num_members = len(self.members)
        group_rating_weight /= num_members
        group_budget_weight /= num_members
        group_dist_weight /= num_members

        return {
            'dist': group_dist_weight,
            'rating': (group_min_rating, group_rating_weight),
            'max_budget_per_person': (group_max_budget, group_budget_weight)
        }

def score_rating(restaurant, group_preferences):
    if restaurant.rating < group_preferences['rating'][0]:
        return 0
    else:
        return float(group_preferences['rating'][1]) * float(restaurant.rating / 5)

def score_distance(distance_from_centroid, group_preferences):
    return float(group_preferences['dist'] * (1 / (1 + distance_from_centroid)))

def propose_restaurants(candidates, group_preferences, meeting_id):
    with pipeline_context():
        raw_candidates = db.session.query(
            Restaurants.id,
            Restaurants.name,
            Restaurants.rating,
            Restaurants.start_price,
            Restaurants.end_price,
            Restaurants.description,
            RestaurantsMeetings.c.distance_from_centroid
        ).join(
            RestaurantsMeetings, Restaurants.id == RestaurantsMeetings.c.restaurant_id
        ).filter(
            RestaurantsMeetings.c.meeting_id == meeting_id
        ).order_by(Restaurants.id).all()

        if not raw_candidates:
            return []

        topsis_matrix = []
        valid_restaurants = []

        for row in raw_candidates:
            rid, name, rating, start_price, end_price, description, distance = row
            score_components = {}

            if end_price is None:
                if start_price is None:
                    if len(raw_candidates) == 1:
                        price = 50
                    else:
                        continue
                else:
                    price = start_price
            else:
                price = end_price

            if price > group_preferences['max_budget_per_person'][0]:
                continue

            score_components['norm_budget'] = 1 - (price / group_preferences['max_budget_per_person'][0])
            score_components['norm_rating'] = (rating or 0) / 5
            score_components['norm_dist'] = 1 / (1 + distance)

            topsis_matrix.append([
                float(score_components['norm_rating']),
                float(score_components['norm_budget']),
                float(score_components['norm_dist'])
            ])

            valid_restaurants.append({
                'id': rid,
                'name': name,
                'rating': rating,
                'description': description
            })

        if not topsis_matrix:
            return []

        matrix = np.array(topsis_matrix)
        weights = np.array([
            group_preferences['rating'][1],
            group_preferences['max_budget_per_person'][1],
            group_preferences['dist']
        ])

        norm = np.linalg.norm(matrix, axis=0)
        norm_matrix = matrix / norm
        weighted_matrix = norm_matrix * weights

        ideal = np.max(weighted_matrix, axis=0)
        anti_ideal = np.min(weighted_matrix, axis=0)

        dist_to_ideal = np.linalg.norm(weighted_matrix - ideal, axis=1)
        dist_to_anti_ideal = np.linalg.norm(weighted_matrix - anti_ideal, axis=1)

        closeness = dist_to_anti_ideal / (dist_to_ideal + dist_to_anti_ideal)

        ranked = list(zip(valid_restaurants, closeness))

        for (restaurant, score) in ranked:
            db.session.execute(update(RestaurantsMeetings).where(
                RestaurantsMeetings.c.restaurant_id == restaurant['id'],
                RestaurantsMeetings.c.meeting_id == meeting_id
            ).values(composite_score=score))

        db.session.commit()

        sorted_restaurants = [r for (r, _) in sorted(ranked, key=lambda x: x[1], reverse=True)]
        return sorted_restaurants
