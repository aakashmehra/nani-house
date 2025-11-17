#!/usr/bin/env python3
"""Cleanup old game_rooms table if it exists and is empty"""

import os
from dotenv import load_dotenv
from flask import Flask
from models import db

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/battle_lanes')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def cleanup():
    """Drop old game_rooms table if it exists"""
    with app.app_context():
        try:
            # Check if game_rooms table exists
            result = db.session.execute(db.text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema='public' AND table_name='game_rooms'
            """))
            
            if result.fetchone():
                # Check if it has any data
                count_result = db.session.execute(db.text("SELECT COUNT(*) FROM game_rooms"))
                count = count_result.fetchone()[0]
                
                if count == 0:
                    print(f"game_rooms table exists and is empty ({count} rows). Dropping it...")
                    db.session.execute(db.text("DROP TABLE IF EXISTS game_rooms CASCADE"))
                    db.session.commit()
                    print("✅ Dropped old game_rooms table")
                else:
                    print(f"⚠️  game_rooms table has {count} rows. Not dropping (data may need migration).")
            else:
                print("ℹ️ game_rooms table doesn't exist")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            db.session.rollback()

if __name__ == '__main__':
    cleanup()

