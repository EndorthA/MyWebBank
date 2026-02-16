# Backend/create_test_db.py
"""
Create the test database if it doesn't exist.
Run this once before running tests: python create_test_db.py
"""

import psycopg2
from psycopg2 import sql

# Connection parameters
DB_HOST = "localhost"
DB_PORT = 5432
DB_USER = "webbank"
DB_PASSWORD = "webbank"
DB_NAME = "webbank_test"

def create_test_database():
    """Create the test database if it doesn't exist."""
    try:
        # Connect to default postgres database
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database="postgres"  # Default database
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(
            sql.SQL("SELECT 1 FROM pg_database WHERE datname = %s"),
            [DB_NAME]
        )
        exists = cursor.fetchone()
        
        if exists:
            print(f"✓ Database '{DB_NAME}' already exists")
        else:
            # Create database
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(
                sql.Identifier(DB_NAME)
            ))
            print(f"✓ Created database '{DB_NAME}'")
        
        cursor.close()
        conn.close()
        
    except psycopg2.OperationalError as e:
        print(f"✗ Error: Could not connect to PostgreSQL")
        print(f"  Make sure PostgreSQL is running and credentials are correct:")
        print(f"  Host: {DB_HOST}")
        print(f"  Port: {DB_PORT}")
        print(f"  User: {DB_USER}")
        raise
    except Exception as e:
        print(f"✗ Error: {e}")
        raise

if __name__ == "__main__":
    create_test_database()
