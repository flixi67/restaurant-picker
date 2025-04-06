import sqlite3

with open('app/templates/schema.sql') as f:
    conn = sqlite3.connect('restaurants.db')
    conn.executescript(f.read())
    conn.close()