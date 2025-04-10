from app import create_app
from faker import Faker
from uuid import uuid4
import datetime as dt
import random

# Internal imports
from app.models import db, Meetings, Members

fake = Faker()

### --- Create fake data in database on initiation

def seed_data(n_meetings=5, members_per_meeting=4):
    db.drop_all()
    db.create_all()

    for _ in range(n_meetings):
        # Create a fake meeting
        meeting_id = fake.bothify(text='MEET####')
        meeting = Meetings(
            id=meeting_id,
            name=fake.catch_phrase(),
            datetime=(dt.datetime.utcnow() + dt.timedelta(days=random.randint(1, 30))).isoformat(),
            group_size=members_per_meeting,
            created_at=dt.datetime.utcnow().isoformat()
        )
        db.session.add(meeting)

        # Create fake members for this meeting
        for _ in range(members_per_meeting):
            member = Members(
                id=str(uuid4()),
                meeting_id=meeting_id,
                budget=random.randint(1, 4),
                uses_cash=random.choice([True, False]),
                uses_card=random.choice([True, False]),
                is_vegetarian=random.choice([True, False]),
                location_preference=fake.city()
            )
            # Enforce at least one payment method
            if not (member.uses_cash or member.uses_card):
                member.uses_cash = True  # default one to true

            db.session.add(member)

    db.session.commit()
    print(f"Seeded {n_meetings} meetings and {n_meetings * members_per_meeting} members!")

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        seed_data()
