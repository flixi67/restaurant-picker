
# FIDN : Find in the Nahe  
Repository for the Flask Webapp — Course: *Data Structures and Algorithms* @ Hertie School

This repository documents the project structure for a web application built using Flask. The app is designed as a simple and functional interface for a group of friends to find and match on restaurants in Berlin.

## Flow of the Application

The application pulls data from a Google API where we query restaurant information based on user locations and preferences. This data includes details like name, address, coordinates, opening hours, and type of cuisine.

Once fetched, the data is cleaned and stored in a **relational database**, which links key components:
- Users and their preferences  
- Restaurants and their attributes  
- Meeting confirmations between users

The web interface then lets users:
1. Submit their name, availability, and cuisine preferences  
2. Get matched with others who have overlapping preferences  
3. View recommended restaurants near the group’s geometric center  
4. Confirm or decline the suggested plan via the dashboard

## Restaurant Ranking Algorithm: TOPSIS

We use the **TOPSIS** method (Technique for Order Preference by Similarity to Ideal Solution) to recommend the most suitable restaurant for the group.

TOPSIS is a multi-criteria decision-making algorithm that compares alternatives based on how close they are to an "ideal" solution, and how far they are from the "worst" case. In this context, we use it to balance user preferences on **rating**, **budget-friendliness**, and **proximity**.

### How it works:
1. **Filter**: Remove restaurants that exceed the group's maximum budget.  
2. **Normalize**: Scale the selected features — rating (higher is better), budget-friendliness (lower is better), and proximity to center (closer is better).  
3. **Rank**: Apply the TOPSIS formula to assign a score to each restaurant.  
4. **Sort**: Return a DataFrame sorted by TOPSIS score, along with a `rank` column.

The top-ranked restaurant is the one that best satisfies the group’s combined preferences

## Contributors

Chloe Fung
Farhan Shaikh
Sattiki Ganguly
Felix Kube

## Features  
- Add and manage user preferences  
- Match restaurants based on mutual availability and cuisine type  
- Confirm and view meetings via the dashboard  
- Lightweight frontend with clean UX

## Structure  
- `app.py`: Main Flask application  
- `templates/`: HTML templates for rendering frontend pages  
- `static/`: CSS and assets  
- `forms.py`: WTForms for handling user input  
- `models.py`: (If applicable) defines data models or structures  
- `db/`: SQLite or other backend support

## Packages Used  
- **requests**: For API integration  
- **geopy**: For geocoding addresses (e.g., using Google Maps) — converts addresses into latitude and longitude  
- **geopandas**: Used for spatial operations like calculating the geometric center of multiple user locations  
- **numpy**: Numerical operations  
- **pandas**: Data manipulation and handling tabular inputs  
- **datetime**: Manage and compare restaurant opening hours  
- **WTForms**: For validating and handling user inputs ([video explainer](https://www.youtube.com/watch?v=j5IQI4aW9ZU))  
- **Flask-WTF**: WTForms + CSRF protection for Flask  
- **SQLAlchemy**: For working with relational databases in Python

## Setup  
1. Clone the repo  
2. Set up a virtual environment  
3. Install dependencies:  
   ```bash
   pip install -r requirements.txt
