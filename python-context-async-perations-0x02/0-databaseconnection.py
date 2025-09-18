import sqlite3
import uuid

"""
A context manager to handle opening and closing database connections automatically.
"""
class DatabaseConnection:
    def __init__(self, db_name):
        self.db_name = db_name
        self.connection = None

    def __enter__(self):
        self.connection = sqlite3.connect(self.db_name)
        return self.connection

    def __exit__(self, exc_type, exc_value, traceback):
        if self.connection:
            self.connection.close()

# Example usage:
if __name__ == "__main__":
    with DatabaseConnection('example.db') as conn:
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS users (
                       id VARCHAR PRIMARY KEY,
                       name TEXT,
                       age INTEGER,
                       email TEXT
                       )
                """)

        # Insert new users
        cursor.execute(("INSERT INTO users (id, name, age, email) VALUES (?, ?, ?, ?)"),
                       (str(uuid.uuid4()), 'Maxwell', 29, 'Max@gmail.com.com')
                       )

        conn.commit()

    with DatabaseConnection('example.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()

        print("Users in the database:")
        for row in users:
            print(f"ID: {row[0]}, Name: {row[1]}, Age: {row[2]}, Email: {row[3]}")