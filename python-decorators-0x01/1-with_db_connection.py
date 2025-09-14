import functools
import sqlite3


def with_db_connection(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        connection =sqlite3.connect("users.db")
        try:
            result = func(connection, *args, **kwargs)
            return result
        except Exception as e:
            raise e
        finally:
            connection.close()
    return wrapper

@with_db_connection
def get_user_by_id(conn, user_id):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cursor.fetchone()

# Fetch user by ID with automatic connection handling
user = get_user_by_id(user_id=1)
print(user)