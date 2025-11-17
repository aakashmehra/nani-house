#!/usr/bin/env python3
"""Check current database schema"""

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

def check_schema():
    """Check database schema"""
    with app.app_context():
        # Check games table columns
        result = db.session.execute(db.text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name='games'
            ORDER BY ordinal_position
        """))
        print("Games table columns:")
        for row in result:
            print(f"  - {row[0]}: {row[1]}")
        
        # Check if game_rooms table exists
        result = db.session.execute(db.text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema='public' AND table_name IN ('game_rooms', 'houses')
        """))
        print("\nTables:")
        for row in result:
            print(f"  - {row[0]}")

if __name__ == '__main__':
    check_schema()

