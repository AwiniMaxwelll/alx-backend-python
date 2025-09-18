import sqlite3
import uuid

class ExecuteQuery:
    def __init__(self, database_name, query, params=None):
        self.database_name = database_name
        self.query = query
        self.params = params or ()
        self.connection = None
        self.results = None

    def __enter__(self):
        self.connection = sqlite3.connect(self.database_name)
        cursor = self.connection.cursor()
        cursor.execute(self.query, self.params)
        self.results = cursor.fetchall()
        return self.results

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.connection.close()

# Example usage
if __name__ == "__main__":
    # Create sample database with users table
    with sqlite3.connect("example.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                age INTEGER
            )
        """)
        user_id = str(uuid.uuid4())
        cursor.execute("INSERT OR IGNORE INTO users (id, name, email, age) VALUES (1, 'Maxwell Awini', 'max@example.com', 30)")
        cursor.execute("INSERT OR IGNORE INTO users (id, name, email, age) VALUES (2, 'LordLinker, 'Lord@example.com', 22)")
        cursor.execute("INSERT OR IGNORE INTO users (id, name, email, age) VALUES (3, 'Bob Kofi', 'Kofi@example.com', 28)")
        conn.commit()

    # Use the ExecuteQuery context manager
    with ExecuteQuery("example.db", "SELECT * FROM users WHERE age > ?", (25,)) as results:
        print("Users older than 25:")
        for row in results:
            print(f"ID: {row[0]}, Name: {row[1]}, Email: {row[2]}, Age: {row[3]}")