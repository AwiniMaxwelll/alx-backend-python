from mysql.connector import Error
from seed import connect_db
import sys

"""
Create a generator to fetch and process data in batches from the users database

Write a function stream_users_in_batches(batch_size) that fetches rows in batches

Write a function batch_processing() that processes each batch to filter users over the age of25`
"""

def stream_users_in_batches(batch_size):
    """Generator that streams rows from the user_data table in batches."""
    connection = connect_db()
    if not connection:
        print("No connection available to stream users.")
        return

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(f"SELECT * FROM user_data")

        while True:
            batch = cursor.fetchmany(batch_size)
            if not batch:
                break
            yield batch
        cursor.close()
    except Error as err:
        print(f"Error fetching data: {err}")
    finally:
        connection.close()

def batch_processing(batch_size):
    """Process each batch to filter users over the age of 25."""
    for batch in stream_users_in_batches(batch_size):
        filtered_users = [user for user in batch if user.get('age', 0) > 25]
        for user in filtered_users:
            print(user)
try:
    batch_processing(50)
except BrokenPipeError:
    sys.stderr.close()