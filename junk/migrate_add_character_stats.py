#!/usr/bin/env python3
"""
Migration script to add total_matches_played column to characters table and fill image_path.
"""

import sys
import os
from sqlalchemy import text, inspect
from sqlalchemy.exc import ProgrammingError

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, Character

# Character name to image path mapping
CHARACTER_IMAGES = {
    'Ditte': 'img/characters/ditte.webp',
    'Tontar': 'img/characters/tontar.webp',
    'Makdi': 'img/characters/makdi.webp',
    'Mishu': 'img/characters/mishu.webp',
    'Dholky': 'img/characters/dholky.webp',
    'Beaster': 'img/characters/beaster.webp',
    'Prepto': 'img/characters/prepto.webp',
    'Ishada': 'img/characters/Ishada.webp',
    'Padupie': 'img/characters/padupie.webp',
}

def migrate_database():
    """Add total_matches_played column and fill image_path"""
    with app.app_context():
        inspector = inspect(db.engine)
        
        try:
            # Check if total_matches_played column exists in characters table
            characters_columns = [col['name'] for col in inspector.get_columns('characters')]
            if 'total_matches_played' not in characters_columns:
                print("Adding 'total_matches_played' column to 'characters' table...")
                db.session.execute(text("ALTER TABLE characters ADD COLUMN total_matches_played INTEGER DEFAULT 0 NOT NULL"))
                print("✓ Added 'total_matches_played' column to 'characters' table")
            else:
                print("✓ 'total_matches_played' column already exists in 'characters' table")
            
            # Fill image_path for characters
            print("\nUpdating character image paths...")
            for char_name, image_path in CHARACTER_IMAGES.items():
                char = Character.query.filter_by(name=char_name).first()
                if char:
                    if not char.image_path or char.image_path != image_path:
                        char.image_path = image_path
                        print(f"✓ Updated {char_name} image_path to {image_path}")
                    else:
                        print(f"✓ {char_name} already has correct image_path")
                else:
                    print(f"⚠ Character '{char_name}' not found in database")
            
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

