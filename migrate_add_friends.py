#!/usr/bin/env python3
"""
Migration script to add friends column to users table and create friend_requests table.
"""

import sys
import os
from sqlalchemy import text, inspect
from sqlalchemy.exc import ProgrammingError

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, FriendRequest

def migrate_database():
    """Add friends column to users table and create friend_requests table"""
    with app.app_context():
        inspector = inspect(db.engine)
        
        try:
            # Check if friends column exists in users table
            users_columns = [col['name'] for col in inspector.get_columns('users')]
            if 'friends' not in users_columns:
                print("Adding 'friends' column to 'users' table...")
                db.session.execute(text("ALTER TABLE users ADD COLUMN friends TEXT"))
                print("✓ Added 'friends' column to 'users' table")
            else:
                print("✓ 'friends' column already exists in 'users' table")
            
            # Check if friend_requests table exists
            tables = inspector.get_table_names()
            if 'friend_requests' not in tables:
                print("Creating 'friend_requests' table...")
                # Create the table using SQLAlchemy
                FriendRequest.__table__.create(db.engine, checkfirst=True)
                print("✓ Created 'friend_requests' table")
            else:
                print("✓ 'friend_requests' table already exists")
            
            # Commit all changes
            db.session.commit()
            print("\n✓ Migration completed successfully!")
            
        except ProgrammingError as e:
            db.session.rollback()
            print(f"\n✗ Database error: {e}")
            print("Rolling back changes...")
            sys.exit(1)
        except Exception as e:
            db.session.rollback()
            print(f"\n✗ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    migrate_database()

