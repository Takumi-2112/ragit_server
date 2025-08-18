import psycopg2
import psycopg2.extras
import os 
from dotenv import load_dotenv
from config import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT

load_dotenv()

# Global connection variable
connection = None
cursor = None

def get_db_connection():
    """Get database connection with error handling"""
    global connection, cursor
    
    try:
        if connection is None or connection.closed:
            # Option 1: Using individual parameters
            connection = psycopg2.connect(
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT,
                cursor_factory=psycopg2.extras.RealDictCursor,
                sslmode='require'  # Required for Supabase
            )
            
            # Option 2: Using connection string (alternative)
            # connection = psycopg2.connect(
            #     DATABASE_URL,
            #     cursor_factory=psycopg2.extras.RealDictCursor,
            #     sslmode='require'
            # )
            
            connection.autocommit = True
            cursor = connection.cursor()
            print(f"⚡ Connected to Supabase DB: {connection.get_dsn_parameters()['dbname']}")
            
        return connection, cursor
        
    except psycopg2.Error as e:
        print(f"❌ Database connection error: {e}")
        return None, None

def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    """Execute a query with error handling and return results"""
    try:
        conn, cur = get_db_connection()
        if not conn or not cur:
            return None
            
        cur.execute(query, params)
        
        if fetch_one:
            return cur.fetchone()
        elif fetch_all:
            return cur.fetchall()
        else:
            return cur.rowcount  # For INSERT/UPDATE/DELETE
            
    except psycopg2.Error as e:
        print(f"❌ Query execution error: {e}")
        return None

def close_connection():
    """Close database connection"""
    global connection, cursor
    try:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
        print("🔌 Database connection closed")
    except psycopg2.Error as e:
        print(f"❌ Error closing connection: {e}")

# Test connection on import
if __name__ == "__main__":
    conn, cur = get_db_connection()
    if conn:
        print("✅ Successfully connected to Supabase!")
        # Test query
        result = execute_query("SELECT current_database(), current_user", fetch_one=True)
        print(f"Connected to database: {result}")
        close_connection()
    else:
        print("❌ Failed to connect to Supabase")