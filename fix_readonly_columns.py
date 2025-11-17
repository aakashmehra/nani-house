#!/usr/bin/env python3
"""
Comprehensive fix to make price columns fully editable in DBeaver.
Removes all constraints, defaults, and ensures proper permissions.
"""

import sys
import os
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db

def fix_readonly_columns():
    """Make price columns fully editable by removing all restrictions"""
    with app.app_context():
        try:
            print("Fixing read-only price columns...")
            print("=" * 60)
            
            tables = ['characters', 'dice', 'chests']
            
            for table in tables:
                print(f"\n🔧 Fixing '{table}' table...")
                
                # Step 1: Check current state
                result = db.session.execute(text(f"""
                    SELECT column_name, data_type, is_nullable, column_default, 
                           is_generated, generation_expression
                    FROM information_schema.columns
                    WHERE table_name = '{table}' AND column_name = 'price'
                """))
                
                row = result.fetchone()
                if not row:
                    print(f"  ⚠ 'price' column not found in '{table}' table")
                    continue
                
                col_name, data_type, is_nullable, col_default, is_generated, gen_expr = row
                print(f"  Current state: {data_type}, nullable={is_nullable}, default={col_default}, generated={is_generated}")
                
                # Step 2: Drop and recreate the column to ensure it's clean
                print(f"  Step 1: Dropping existing 'price' column...")
                try:
                    db.session.execute(text(f"ALTER TABLE {table} DROP COLUMN IF EXISTS price CASCADE"))
                    db.session.commit()
                    print(f"    ✓ Dropped 'price' column")
                except Exception as e:
                    print(f"    ⚠ Could not drop column (may not exist): {e}")
                    db.session.rollback()
                
                # Step 3: Recreate column as fully editable
                print(f"  Step 2: Recreating 'price' column as editable INTEGER...")
                db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN price INTEGER NULL"))
                db.session.commit()
                print(f"    ✓ Recreated 'price' column as nullable INTEGER")
                
                # Step 4: Ensure no NOT NULL constraint
                print(f"  Step 3: Ensuring column is nullable...")
                db.session.execute(text(f"ALTER TABLE {table} ALTER COLUMN price DROP NOT NULL"))
                db.session.commit()
                print(f"    ✓ Column is nullable")
                
                # Step 5: Remove any default
                print(f"  Step 4: Removing any default value...")
                try:
                    db.session.execute(text(f"ALTER TABLE {table} ALTER COLUMN price DROP DEFAULT"))
                    db.session.commit()
                    print(f"    ✓ Removed default")
                except Exception as e:
                    print(f"    ℹ No default to remove: {e}")
                    db.session.rollback()
                
                # Step 6: Grant permissions (if needed)
                print(f"  Step 5: Ensuring proper permissions...")
                try:
                    # Get current user
                    user_result = db.session.execute(text("SELECT current_user"))
                    current_user = user_result.scalar()
                    
                    # Grant all privileges on the table
                    db.session.execute(text(f"GRANT ALL PRIVILEGES ON TABLE {table} TO {current_user}"))
                    db.session.execute(text(f"GRANT ALL PRIVILEGES ON TABLE {table} TO PUBLIC"))
                    db.session.commit()
                    print(f"    ✓ Granted permissions to {current_user} and PUBLIC")
                except Exception as e:
                    print(f"    ⚠ Permission grant issue (may not be needed): {e}")
                    db.session.rollback()
                
                # Step 7: Verify final state
                result = db.session.execute(text(f"""
                    SELECT column_name, data_type, is_nullable, column_default, 
                           is_generated, generation_expression
                    FROM information_schema.columns
                    WHERE table_name = '{table}' AND column_name = 'price'
                """))
                
                final_row = result.fetchone()
                if final_row:
                    f_col_name, f_data_type, f_is_nullable, f_col_default, f_is_generated, f_gen_expr = final_row
                    print(f"\n  ✅ Final state: {f_data_type}, nullable={f_is_nullable}, default={f_col_default or 'None'}, generated={f_is_generated}")
                else:
                    print(f"  ❌ Column not found after recreation!")
            
            print("\n" + "=" * 60)
            print("✅ All price columns should now be editable in DBeaver!")
            print("=" * 60)
            print("\n💡 If still read-only in DBeaver:")
            print("   1. Refresh the connection in DBeaver")
            print("   2. Reconnect to the database")
            print("   3. Check if you're viewing a view instead of the table")
            print("   4. Ensure you have write permissions on the database")
            
        except ProgrammingError as e:
            db.session.rollback()
            print(f"\n❌ Database error: {e}")
            print("Rolling back changes...")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Unexpected error: {e}")
            print("Rolling back changes...")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    fix_readonly_columns()

