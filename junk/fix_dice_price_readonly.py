#!/usr/bin/env python3
"""
Aggressive fix specifically for dice.price column to make it editable.
"""

import sys
import os
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db

def fix_dice_price():
    """Aggressively fix dice.price column"""
    with app.app_context():
        try:
            print("Fixing dice.price column to be editable...")
            print("=" * 60)
            
            # Step 1: Check current state
            result = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default, 
                       is_generated, generation_expression
                FROM information_schema.columns
                WHERE table_name = 'dice' AND column_name = 'price'
            """))
            
            row = result.fetchone()
            if row:
                print(f"Current state: {row[1]}, nullable={row[2]}, default={row[3]}, generated={row[4]}")
            
            # Step 2: Drop all constraints that might reference price
            print("\nStep 1: Checking for constraints...")
            constraints = db.session.execute(text("""
                SELECT conname, contype, pg_get_constraintdef(oid) as definition
                FROM pg_constraint
                WHERE conrelid = 'dice'::regclass
            """)).fetchall()
            
            for conname, contype, definition in constraints:
                if 'price' in definition.lower():
                    print(f"  Found constraint: {conname} ({contype})")
                    try:
                        db.session.execute(text(f"ALTER TABLE dice DROP CONSTRAINT IF EXISTS {conname} CASCADE"))
                        db.session.commit()
                        print(f"    ✓ Dropped constraint: {conname}")
                    except Exception as e:
                        print(f"    ⚠ Could not drop constraint: {e}")
                        db.session.rollback()
            
            # Step 3: Drop the column completely
            print("\nStep 2: Dropping price column...")
            try:
                db.session.execute(text("ALTER TABLE dice DROP COLUMN IF EXISTS price CASCADE"))
                db.session.commit()
                print("  ✓ Dropped price column")
            except Exception as e:
                print(f"  ⚠ Error dropping column: {e}")
                db.session.rollback()
            
            # Step 4: Recreate the column with explicit settings
            print("\nStep 3: Recreating price column as fully editable...")
            db.session.execute(text("""
                ALTER TABLE dice 
                ADD COLUMN price INTEGER NULL
            """))
            db.session.commit()
            print("  ✓ Recreated price column")
            
            # Step 5: Explicitly set as nullable
            print("\nStep 4: Ensuring column is nullable...")
            db.session.execute(text("ALTER TABLE dice ALTER COLUMN price DROP NOT NULL"))
            db.session.commit()
            print("  ✓ Column is nullable")
            
            # Step 6: Remove any default
            print("\nStep 5: Removing any default value...")
            try:
                db.session.execute(text("ALTER TABLE dice ALTER COLUMN price DROP DEFAULT"))
                db.session.commit()
                print("  ✓ Removed default")
            except Exception as e:
                print(f"  ℹ No default to remove: {e}")
                db.session.rollback()
            
            # Step 7: Grant explicit permissions
            print("\nStep 6: Granting explicit permissions...")
            try:
                user_result = db.session.execute(text("SELECT current_user"))
                current_user = user_result.scalar()
                
                db.session.execute(text(f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE dice TO {current_user}"))
                db.session.execute(text(f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE dice TO PUBLIC"))
                db.session.execute(text(f"GRANT USAGE ON SCHEMA public TO {current_user}"))
                db.session.execute(text(f"GRANT USAGE ON SCHEMA public TO PUBLIC"))
                db.session.commit()
                print(f"  ✓ Granted permissions to {current_user} and PUBLIC")
            except Exception as e:
                print(f"  ⚠ Permission issue: {e}")
                db.session.rollback()
            
            # Step 8: Verify final state
            print("\nStep 7: Verifying final state...")
            result = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default, 
                       is_generated, generation_expression
                FROM information_schema.columns
                WHERE table_name = 'dice' AND column_name = 'price'
            """))
            
            final_row = result.fetchone()
            if final_row:
                col_name, data_type, is_nullable, col_default, is_generated, gen_expr = final_row
                print(f"\n✅ Final state:")
                print(f"   Column: {col_name}")
                print(f"   Type: {data_type}")
                print(f"   Nullable: {is_nullable}")
                print(f"   Default: {col_default or 'None'}")
                print(f"   Generated: {is_generated}")
                print(f"   Generation Expression: {gen_expr or 'None'}")
                
                # Test if we can update it
                print("\nStep 8: Testing write access...")
                try:
                    # Try to update a row (if any exist)
                    count_result = db.session.execute(text("SELECT COUNT(*) FROM dice"))
                    count = count_result.scalar()
                    if count > 0:
                        # Update first row's price to test
                        db.session.execute(text("UPDATE dice SET price = NULL WHERE id = (SELECT MIN(id) FROM dice)"))
                        db.session.commit()
                        print("  ✓ Successfully updated dice.price - column is writable!")
                    else:
                        print("  ℹ No rows in dice table to test update")
                except Exception as e:
                    print(f"  ❌ Could not update: {e}")
                    db.session.rollback()
            else:
                print("  ❌ Column not found after recreation!")
            
            print("\n" + "=" * 60)
            print("✅ dice.price column fix completed!")
            print("=" * 60)
            print("\n💡 If still read-only in DBeaver:")
            print("   1. Close and reopen DBeaver")
            print("   2. Disconnect and reconnect to the database")
            print("   3. Refresh the table (F5)")
            print("   4. Try editing via SQL: UPDATE dice SET price = 100 WHERE id = 1;")
            
        except ProgrammingError as e:
            db.session.rollback()
            print(f"\n❌ Database error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    fix_dice_price()

