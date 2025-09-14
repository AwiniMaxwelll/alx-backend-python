import sqlite3
import functools
import time

# Decorator to open & close DB connection
def with_db_connection(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        connection = sqlite3.connect('users.db')
        try:
            result = func(connection, *args, **kwargs)
            return result
        finally:
            connection.close()
    return wrapper


# Decorator to retry a function on failure
def retry_on_failure(retries=3, delay=2):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            any_exception = None
            for attempt in range(0, retries):
                try:
                   result = func(*args, **kwargs)
                   return result
                except Exception as e:
                    any_exception = e
                    print(f"[Retry {attempt}/{retries}] Failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
            # If all retries failed, re-raise the last exception
            raise any_exception
        return wrapper
    return decorator


@with_db_connection
@retry_on_failure(retries=3, delay=1)
def fetch_users_with_retry(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    return cursor.fetchall()


# Attempt to fetch users with automatic retry
users = fetch_users_with_retry()
print(users)