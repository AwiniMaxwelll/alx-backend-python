import sqlite3
import functools



#decorator to open & close DB connection
def with_db_connection(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        connection = sqlite3.connect('users.db')
        try:
            result=func(connection, *args, **kwargs)
            return result
        except Exception as e:
            raise e
        finally:
            connection.close()
    return wrapper

#decorator to manage transactions
def transactional(func):
    @functools.wraps(func)
    def wrapper(conn,*args, **kwargs):
        try:
            result = func(conn, *args, **kwargs)
            conn.commit()   #commit to the database table if no error
            return result
        except Exception as e:
            conn.rollback() #rollback if error occurs
            raise e
    return wrapper

@with_db_connection
@transactional
def update_user_email(conn, user_id, new_email):
    cursor=conn.cursor()
    cursor.execute("UPDATE users SET email=? WHERE id =? ", (new_email, user_id))
    print(f'Updated user {user_id} email to {new_email}')


update_user_email(user_id=1, new_email="awinimaxwell428@gmail.com")