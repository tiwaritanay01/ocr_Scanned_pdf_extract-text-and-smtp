import mysql.connector
import os
import json

def get_schema():
    conn = mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="root123",
        database="student_results"
    )
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = [t[0] for t in cursor.fetchall()]
    
    schema = {}
    for t in tables:
        cursor.execute(f"DESCRIBE {t}")
        schema[t] = cursor.fetchall()
    
    cursor.close()
    conn.close()
    print(json.dumps(schema, indent=2))

if __name__ == "__main__":
    get_schema()
