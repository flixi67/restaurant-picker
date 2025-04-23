import sqlite3

with open('app/templates/schema.sql') as f:
    sql_script = f.read()

try:
    conn = sqlite3.connect('restaurants.db')
    conn.executescript(sql_script)
    conn.close()
    print("✅ Database created successfully.")
except sqlite3.OperationalError as e:
    print("❌ SQLite Error:", e)
    print("❓ Failing SQL snippet:")
    for line in sql_script.splitlines():
        if '.' in line:
            print("👉", line)
