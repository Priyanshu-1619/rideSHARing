"""
Database Migration Script
Adds new columns for penalty system to existing tables
"""

import sqlite3
import mysql.connector
import os

def migrate_sqlite():
    """Add new columns to SQLite tables for penalty system."""
    db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'nextride.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = OFF")
        cur = conn.cursor()
        
        print("🔄 Migrating SQLite database...")
        
        # Check if Penalties table exists (indicator of migration completion)
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Penalties'")
        penalties_exists = cur.fetchone() is not None
        
        # Check if new Requests columns exist
        cur.execute("PRAGMA table_info(Requests)")
        columns = [col[1] for col in cur.fetchall()]
        has_new_columns = 'actual_arrival_time' in columns and 'completion_status' in columns
        
        # If Penalties table doesn't exist or columns are missing, we need to update schema
        if not penalties_exists or not has_new_columns:
            print("  - Updating Requests table schema...")
            # Rename old table
            cur.execute("ALTER TABLE Requests RENAME TO Requests_old")
            
            # Create new table with updated schema
            cur.execute("""
                CREATE TABLE Requests (
                    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ride_id INTEGER NOT NULL,
                    rider_id INTEGER NOT NULL,
                    status TEXT DEFAULT 'Pending' CHECK (status IN ('Pending','Accepted','Rejected','Cancelled','Completed','No-Show','Late')),
                    actual_arrival_time TEXT,
                    completion_status TEXT CHECK (completion_status IN ('On-Time','Late','Missed','Cancelled','Driver-Cancelled')),
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (ride_id) REFERENCES Rides(ride_id),
                    FOREIGN KEY (rider_id) REFERENCES Students(student_id),
                    UNIQUE (ride_id, rider_id)
                )
            """)
            
            # Copy data from old table
            cur.execute("""
                INSERT INTO Requests (request_id, ride_id, rider_id, status, created_at)
                SELECT request_id, ride_id, rider_id, status, created_at FROM Requests_old
            """)
            
            # Drop old table
            cur.execute("DROP TABLE Requests_old")
        
        # Check if Penalties table exists
        if not penalties_exists:
            print("  - Creating Penalties table...")
            cur.execute("""
                CREATE TABLE Penalties (
                    penalty_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    request_id INTEGER NOT NULL,
                    penalty_type TEXT NOT NULL CHECK (penalty_type IN ('Cancellation','Delay','Missed-Ride','Driver-Cancellation')),
                    amount REAL NOT NULL,
                    reason TEXT,
                    applied_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (student_id) REFERENCES Students(student_id),
                    FOREIGN KEY (request_id) REFERENCES Requests(request_id)
                )
            """)
        
        conn.execute("PRAGMA foreign_keys = ON")
        conn.commit()
        conn.close()
        print("✅ SQLite migration complete!")
        return True
    except Exception as e:
        print(f"❌ SQLite migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def migrate_mysql(host, user, password, database):
    """Add new columns to MySQL tables for penalty system."""
    try:
        conn = mysql.connector.connect(
            host=host, user=user, password=password, database=database
        )
        cur = conn.cursor()
        
        print("🔄 Migrating MySQL database...")
        
        # Check if columns exist before adding them
        cur.execute(f"""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME='Requests' AND COLUMN_NAME='actual_arrival_time'
        """)
        
        if not cur.fetchone():
            print("  - Adding actual_arrival_time column...")
            cur.execute("ALTER TABLE Requests ADD COLUMN actual_arrival_time DATETIME NULL")
        
        if not cur.execute(f"""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME='Requests' AND COLUMN_NAME='completion_status'
        """) or not cur.fetchone():
            print("  - Adding completion_status column...")
            cur.execute("""
                ALTER TABLE Requests ADD COLUMN completion_status 
                ENUM('On-Time','Late','Missed','Cancelled','Driver-Cancelled') NULL
            """)
        
        # Check if Penalties table exists
        cur.execute(f"""
            SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA='{database}' AND TABLE_NAME='Penalties'
        """)
        
        if not cur.fetchone():
            print("  - Creating Penalties table...")
            cur.execute("""
                CREATE TABLE Penalties (
                    penalty_id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id INT NOT NULL,
                    request_id INT NOT NULL,
                    penalty_type ENUM('Cancellation','Delay','Missed-Ride','Driver-Cancellation') NOT NULL,
                    amount DECIMAL(8,2) NOT NULL,
                    reason TEXT,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES Students(student_id) ON DELETE CASCADE,
                    FOREIGN KEY (request_id) REFERENCES Requests(request_id) ON DELETE CASCADE
                )
            """)
        
        conn.commit()
        conn.close()
        print("✅ MySQL migration complete!")
        return True
    except Exception as e:
        print(f"❌ MySQL migration failed: {e}")
        return False


if __name__ == '__main__':
    print("\n🚀 Running database migrations...\n")
    
    # Try SQLite first
    migrate_sqlite()
    
    print("\n✅ All migrations complete!")
