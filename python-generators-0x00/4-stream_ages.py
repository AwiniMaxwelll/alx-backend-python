from mysql.connector import Error
from  seed import create_db

def stream_user_ages():
    """Generator that streams user ages from the user_data table one by one."""
    connection = create_db()
    if not connection:
        print("No connection available to stream users.")
        return

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(f"SELECT age FROM user_data")

        for row in cursor:
            yield row.get('age', 0)
        cursor.close()
    except Error as err:
        print(f"Error fetching data: {err}")
    finally:
        connection.close()

def calculate_average_age():
    """Calculate the average age of users using the stream_user_ages generator."""
    total_age = 0
    count = 0

    for age in stream_user_ages():
        total_age += age
        count += 1

    average_age = total_age / count if count > 0 else 0
    print(f"Average age of users: {average_age}")

