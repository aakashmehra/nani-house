#!/usr/bin/env python3
"""
Fix price columns to be fully editable in DBeaver.
Ensures columns are nullable and have no constraints that prevent editing.
"""

import sys
import os
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db

def fix_price_columns():
    """Make price columns fully editable"""
    with app.app_context():
        try:
            print("Checking and fixing price columns...")
            print("=" * 50)
            
            # Check current state of price columns
            tables = ['characters', 'dice', 'chests']
            
            for table in tables:
                print(f"\nChecking '{table}' table...")
                
                # Check if price column exists and get its current definition
                result = db.session.execute(text(f"""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = '{table}' AND column_name = 'price'
                """))
                
                row = result.fetchone()
                if row:
                    col_name, data_type, is_nullable, col_default = row
                    print(f"  Current: {col_name} ({data_type}), nullable={is_nullable}, default={col_default}")
                    
                    # If column is NOT NULL, make it nullable
                    if is_nullable == 'NO':
                        print(f"  Making '{table}.price' nullable...")
                        db.session.execute(text(f"ALTER TABLE {table} ALTER COLUMN price DROP NOT NULL"))
                        print(f"  ✓ Made '{table}.price' nullable")
                    
                    # Remove any default value that might interfere
                    if col_default:
                        print(f"  Removing default value from '{table}.price'...")
                        db.session.execute(text(f"ALTER TABLE {table} ALTER COLUMN price DROP DEFAULT"))
                        print(f"  ✓ Removed default from '{table}.price'")
                    
                    # Ensure the column type is INTEGER (not constrained)
                    print(f"  Ensuring '{table}.price' is INTEGER type...")
                    db.session.execute(text(f"ALTER TABLE {table} ALTER COLUMN price TYPE INTEGER"))
                    print(f"  ✓ Verified '{table}.price' is INTEGER")
                    
                else:
                    print(f"  ⚠ 'price' column not found in '{table}' table")
            
            # Commit all changes
            db.session.commit()
            print("\n" + "=" * 50)
            print("✓ All price columns are now editable!")
            print("=" * 50)
            
            # Verify final state
            print("\nFinal verification:")
            for table in tables:
                result = db.session.execute(text(f"""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = '{table}' AND column_name = 'price'
                """))
                row = result.fetchone()
                if row:
                    col_name, data_type, is_nullable, col_default = row
                    print(f"  {table}.price: {data_type}, nullable={is_nullable}, default={col_default or 'None'}")
            
        except ProgrammingError as e:
            db.session.rollback()
            print(f"\n✗ Database error: {e}")
            print("Rolling back changes...")
            sys.exit(1)
        except Exception as e:
            db.session.rollback()
            print(f"\n✗ Unexpected error: {e}")
            print("Rolling back changes...")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    print("Fixing price columns to be editable in DBeaver...")
    fix_price_columns()

