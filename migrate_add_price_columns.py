#!/usr/bin/env python3
"""
Migration script to add price columns to characters and dice tables,
and replace cost with price in chests table.
"""

import sys
import os
from sqlalchemy import text, inspect
from sqlalchemy.exc import ProgrammingError

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db

def migrate_database():
    """Add price columns and migrate cost to price in chests"""
    with app.app_context():
        inspector = inspect(db.engine)
        
        try:
            # Check if price column exists in characters table
            characters_columns = [col['name'] for col in inspector.get_columns('characters')]
            if 'price' not in characters_columns:
                print("Adding 'price' column to 'characters' table...")
                db.session.execute(text("ALTER TABLE characters ADD COLUMN price INTEGER"))
                print("✓ Added 'price' column to 'characters' table")
            else:
                print("✓ 'price' column already exists in 'characters' table")
            
            # Check if price column exists in dice table
            dice_columns = [col['name'] for col in inspector.get_columns('dice')]
            if 'price' not in dice_columns:
                print("Adding 'price' column to 'dice' table...")
                db.session.execute(text("ALTER TABLE dice ADD COLUMN price INTEGER"))
                print("✓ Added 'price' column to 'dice' table")
            else:
                print("✓ 'price' column already exists in 'dice' table")
            
            # Handle chests table: migrate cost to price
            chests_columns = [col['name'] for col in inspector.get_columns('chests')]
            
            if 'cost' in chests_columns and 'price' not in chests_columns:
                print("Migrating 'cost' to 'price' in 'chests' table...")
                # Add price column
                db.session.execute(text("ALTER TABLE chests ADD COLUMN price INTEGER"))
                # Copy cost values to price
                db.session.execute(text("UPDATE chests SET price = cost WHERE cost IS NOT NULL"))
                # Drop cost column
                db.session.execute(text("ALTER TABLE chests DROP COLUMN cost"))
                print("✓ Migrated 'cost' to 'price' in 'chests' table")
            elif 'cost' in chests_columns and 'price' in chests_columns:
                print("Both 'cost' and 'price' exist in 'chests' table...")
                # Copy cost values to price where price is NULL
                db.session.execute(text("UPDATE chests SET price = cost WHERE price IS NULL AND cost IS NOT NULL"))
                # Drop cost column
                db.session.execute(text("ALTER TABLE chests DROP COLUMN cost"))
                print("✓ Migrated remaining 'cost' values to 'price' and dropped 'cost' column")
            elif 'price' in chests_columns:
                print("✓ 'price' column already exists in 'chests' table (no 'cost' column found)")
            else:
                print("⚠ Neither 'cost' nor 'price' found in 'chests' table - adding 'price' column")
                db.session.execute(text("ALTER TABLE chests ADD COLUMN price INTEGER"))
                print("✓ Added 'price' column to 'chests' table")
            
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
            print("Rolling back changes...")
            sys.exit(1)

if __name__ == '__main__':
    print("Starting database migration...")
    print("=" * 50)
    migrate_database()
    print("=" * 50)

