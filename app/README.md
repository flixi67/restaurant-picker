
# FIDN : Find in the Nahe  
Repository for the Flask Webapp — Course: *Data Structures and Algorithms* @ Hertie School

This repository documents the project structure for a web application built using Flask. The app is designed as a simple and functional interface for a group of friends to find and match on restaurants in Berlin.

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
