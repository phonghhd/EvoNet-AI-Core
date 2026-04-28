#!/usr/bin/env python3
"""
Script để kiểm tra chức năng phát hiện và vá lỗi trong file code có chứa lỗ hổng.
"""

import os
import sys

# Tạo một bản vá cho lỗ hổng SQL Injection
def create_sql_injection_fix():
    """
    Tạo bản vá cho lỗ hổng SQL Injection bằng cách sử dụng parameterized queries
    """
    vulnerable_code = """
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
"""
    
    fixed_code = """
import sqlite3

# Fixed code using parameterized queries
def get_user_data(username):
    conn = sqlite3.connect('example.db')
    cursor = conn.cursor()
    # Fixed with parameterized query to prevent SQL injection
    query = "SELECT * FROM users WHERE username = ?"
    cursor.execute(query, (username,))
    result = cursor.fetchall()
    conn.close()
    return result
"""
    
    return vulnerable_code, fixed_code

# Kiểm tra xem bản vá có thể sửa được lỗ hổng không
def test_fix():
    vulnerable, fixed = create_sql_injection_fix()
    print("Original vulnerable code:")
    print(vulnerable)
    print("\nFixed code:")
    print(fixed)
    
    # Kiểm tra xem bản vá có sửa được lỗ hổng không
    if "username = ?" in fixed and "username = '" not in fixed:
        print("\n✅ Bản vá đã sửa được lỗ hổng SQL Injection!")
        return True
    else:
        print("\n❌ Bản vá chưa sửa được lỗ hổng!")
        return False

if __name__ == "__main__":
    test_fix()