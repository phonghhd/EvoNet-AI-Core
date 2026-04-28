import sqlite3

# Vulnerable code with SQL Injection
def get_user_data(username):
    conn = sqlite3.connect('example.db')
    cursor = conn.cursor()
    # This is vulnerable to SQL injection
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    result = cursor.fetchall()
    conn.close()
    return result

def authenticate_user(username, password):
    # Another vulnerable function
    user_data = get_user_data(username)
    # In a real scenario, we would check the password here
    return user_data