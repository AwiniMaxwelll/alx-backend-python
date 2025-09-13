from seed import connect_db
from itertools import islice

def stream_users():
    """Generator that streams rows from user_data 
    table one by one."""

    connection = connect_db()
    try:
        cursor = connection.cursor(dictionary=True)  # Use dictionary for easier row access
        cursor.execute("SELECT * FROM user_data")
        # Yield each row one by one        
        for row in cursor:
            yield row 
    finally:
        cursor.fetchall()  # Consume any remaining results when fetching part of the data
        cursor.close()
        connection.close()
for user in islice(stream_users(), 100):
    print(user)