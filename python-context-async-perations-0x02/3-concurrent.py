import asyncio
import aiosqlite


async def async_fetch_users():
    """Fetch all users from the database"""
    async with aiosqlite.connect("example.db") as db:
        cursor = await db.execute("SELECT * FROM users")
        results = await cursor.fetchall()
        return results


async def async_fetch_older_users():
    """Fetch users older than 40 from the database"""
    async with aiosqlite.connect("example.db") as db:
        cursor = await db.execute("SELECT * FROM users WHERE age > ?", (40,))
        results = await cursor.fetchall()
        return results


async def fetch_concurrently():
    """Execute both queries concurrently using asyncio.gather"""
    all_users, older_users = await asyncio.gather(
        async_fetch_users(),
        async_fetch_older_users()
    )

    print("All users:")
    for user in all_users:
        print(f"ID: {user[0]}, Name: {user[1]}, Email: {user[2]}, Age: {user[3]}")

    print("\nUsers older than 40:")
    for user in older_users:
        print(f"ID: {user[0]}, Name: {user[1]}, Email: {user[2]}, Age: {user[3]}")


async def setup_database():
    """Create and populate sample database"""
    async with aiosqlite.connect("example.db") as db:
        await db.execute("""
                         CREATE TABLE IF NOT EXISTS users
                         (
                             id    INTEGER PRIMARY KEY,
                             name  TEXT NOT NULL,
                             email TEXT NOT NULL,
                             age   INTEGER
                         )
                         """)
        await db.execute(
            "INSERT OR IGNORE INTO users (id, name, email, age) VALUES (1, 'John Doe', 'john@example.com', 30)")
        await db.execute(
            "INSERT OR IGNORE INTO users (id, name, email, age) VALUES (2, 'Jane Smith', 'jane@example.com', 45)")
        await db.execute(
            "INSERT OR IGNORE INTO users (id, name, email, age) VALUES (3, 'Bob Johnson', 'bob@example.com', 50)")
        await db.execute(
            "INSERT OR IGNORE INTO users (id, name, email, age) VALUES (4, 'Alice Brown', 'alice@example.com', 35)")
        await db.commit()


if __name__ == "__main__":
    # Setup database first
    asyncio.run(setup_database())

    # Run concurrent fetch operations
    asyncio.run(fetch_concurrently())