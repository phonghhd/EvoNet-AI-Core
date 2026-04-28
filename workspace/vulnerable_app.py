import sqlite3
from flask import Flask, request

app = Flask(__name__)

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

@app.route('/user')
def user_route():
    username = request.args.get('username')
    user_data = get_user_data(username)
    return str(user_data)

if __name__ == '__main__':
    app.run()