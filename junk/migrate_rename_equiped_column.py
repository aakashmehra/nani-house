#!/usr/bin/env python3
"""
Migration script to rename players.equiped_character -> players.equipped_character.
"""

import sys
import os
from sqlalchemy import text, inspect
from sqlalchemy.exc import ProgrammingError

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db


def migrate_database():
    """Rename equiped_character column and ensure default value."""
    with app.app_context():
        inspector = inspect(db.engine)
        try:
            player_columns = [col['name'] for col in inspector.get_columns('players')]

            if 'equiped_character' in player_columns and 'equipped_character' not in player_columns:
                print("Renaming column 'equiped_character' -> 'equipped_character'...")
                db.session.execute(text("ALTER TABLE players RENAME COLUMN equiped_character TO equipped_character"))
                print("✓ Column renamed.")
            elif 'equipped_character' in player_columns:
                print("✓ 'equipped_character' column already present.")
            else:
                print("⚠ Neither 'equiped_character' nor 'equipped_character' found. Nothing to do.")

            # Ensure default value and non-null constraint
            db.session.execute(text(
                "UPDATE players SET equipped_character = 1 WHERE equipped_character IS NULL"
            ))
            db.session.commit()
            print("✓ Ensured equipped_character defaults to 1 where missing.")

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

