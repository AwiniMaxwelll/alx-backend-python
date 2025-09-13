import mysql.connector
from mysql.connector import Error
import csv, uuid
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


DB_NAME = os.getenv('DB_NAME', 'ALX_prodev')
TABLE_NAME = os.getenv('TABLE_NAME', 'user_data')
CSV_FILE_PATH = 'user_data.csv'

def connect_db():
    """
    connects to the mysql database server
    """
    try:
        db = mysql.connector.connect(
            host="localhost",
            user='root',
            passwd='',
            database='ALX_prodev'
        )
        if db.is_connected:
            print("connection is successful")
            return db
    except Error as e:
        print(f"Failed to connect to ALX_prodev: {e}")
        return None


def create_database(connection):
    """
    Create  the database
    """
    if connection == None:
        print('an error')
        return None
    try:
        db = connection
        mycursor = db.cursor()
        mycursor.execute("CREATE DATABASE IF NOT EXISTS ALX_prodev")
        print("Database ALX_prodev created successfully")
    except Error as e:
        print(f"Error creating database: {e}")
    finally:
        mycursor.close()
        print("database closed successfully")


def create_table(connection):
    """
    create a database table
    """
    try:
        dbcursor =connection.cursor()
        create_table = """
    CREATE TABLE IF NOT EXISTS `user_data` (
            `user_id` CHAR(36) PRIMARY KEY,
            `name` VARCHAR(255) NOT NULL,
            `email` VARCHAR(255) NOT NULL,
            `age` DECIMAL(5,2) NOT NULL
        ) 
        """
        dbcursor.execute(create_table)
        connection.commit()
    except Error as e:
        print(f"Error creating table: {e}")
    finally:
        dbcursor.close()
    

def insert_data(connection, data):
    """Insert data into a database table"""
    if not connection:
        print("There is no connection to the database for insertion")
        return None

    verify_email_does_not_exist = f"""
    SELECT email FROM {TABLE_NAME} WHERE email=%s
    """
    insert_data = f"""
    INSERT INTO {TABLE_NAME} (`user_id`, `name`, `email`, `age`) VALUES (%s, %s, %s, %s)
    """
    try:
        dbcursor = connection.cursor()
        inserted_count = 0
        with open(data, mode='r', encoding='utf-8') as csv_file:
            data_reader = csv.reader(csv_file)  
            next(data_reader)  # Skip header
            for row in data_reader:
                user_id = str(uuid.uuid4()) # generate unique ID convert it string to be inserted into the database 
                name, email, age = row
                dbcursor.execute(verify_email_does_not_exist, (email,))
                if dbcursor.fetchall():  # Use fetchall() to consume all results
                    print(f"The email: {email} already exists. Skipping it")
                    continue
                dbcursor.execute(insert_data, (user_id, name, email, age))
                inserted_count += 1
            connection.commit()  # Commit once after all inserts
        dbcursor.close()
        print(f"Inserted {inserted_count} new records into {TABLE_NAME}.")
    except mysql.connector.Error as err:
        print(f"Error inserting data: {err}")
        exit(1)


