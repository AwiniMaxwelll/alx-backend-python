import sqlite3
import functools
from datetime import datetime


# Decorator to log SQL queries
def log_queries(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if args:
            query = args[0]
        else:
            query = kwargs.get("query")
        print(f"[{datetime.now()}] Executing SQL query: {query}")
        return func(*args, **kwargs)
    return wrapper


@log_queries
def fetch_all_users(query):
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
    return results


# Fetch users while logging the query
users = fetch_all_users(query="SELECT * FROM users")