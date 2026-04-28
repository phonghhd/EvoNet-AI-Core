import sqlite3

def get_user_data(user_id):
    # Vulnerable code with SQL Injection
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # This is vulnerable to SQL injection
    query = "SELECT * FROM users WHERE id = " + user_id
    cursor.execute(query)
    
    return cursor.fetchall()

def login_user(username, password):
    # Another vulnerable function
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Vulnerable to SQL injection
    query = "SELECT * FROM users WHERE username = '" + username + "' AND password = '" + password + "'"
    cursor.execute(query)
    
    return cursor.fetchone()

# Example usage
if __name__ == "__main__":
    user_data = get_user_data("1 OR 1=1")
    print(user_data)