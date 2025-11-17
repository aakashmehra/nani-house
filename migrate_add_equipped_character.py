#!/usr/bin/env python3
"""
Migration script to add equiped_character column to players table.
"""

import sys
import os
from sqlalchemy import text, inspect
from sqlalchemy.exc import ProgrammingError

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db


def migrate_database():
    """Add equiped_character column to players table with default value 1."""
    with app.app_context():
        inspector = inspect(db.engine)

        try:
            player_columns = [col['name'] for col in inspector.get_columns('players')]
            if 'equiped_character' not in player_columns:
                print("Adding 'equiped_character' column to 'players' table...")
                db.session.execute(text(
                    "ALTER TABLE players ADD COLUMN equiped_character INTEGER DEFAULT 1 NOT NULL"
                ))
                print("✓ Added 'equiped_character' column to 'players' table")
            else:
                print("✓ 'equiped_character' column already exists in 'players' table")

            # Ensure all existing rows have a value (in case the column was added without default)
            db.session.execute(text(
                "UPDATE players SET equiped_character = 1 WHERE equiped_character IS NULL"
            ))
            db.session.commit()
            print("✓ Updated existing rows with default equipped character (1)")

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

