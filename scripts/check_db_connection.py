"""One-off check: can our Python code actually reach Postgres?

Run from the project root:   python scripts/check_db_connection.py
"""

from sqlalchemy import text

from app.db.session import engine

with engine.connect() as connection:
    database = connection.execute(text("SELECT current_database()")).scalar_one()
    user = connection.execute(text("SELECT current_user")).scalar_one()
    version = connection.execute(text("SELECT version()")).scalar_one()

print("Connected successfully.")
print(f"  database : {database}")
print(f"  user     : {user}")
print(f"  server   : {version.split(',')[0]}")
