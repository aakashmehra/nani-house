from dotenv import load_dotenv
import os
import psycopg2
import urllib.parse

load_dotenv()

# Use DATABASE_URL directly
url = os.getenv("DATABASE_URL")

if not url:
    raise Exception("❌ DATABASE_URL not set in environment")

# Optional: parse DATABASE_URL for clarity (not required)
parsed = urllib.parse.urlparse(url)
print(f"🔌 Connecting to: {parsed.hostname}:{parsed.port} as {parsed.username} → {parsed.path[1:]}")

# Connect using the full URL
conn = psycopg2.connect(url)
print("✅ Connected to PostgreSQL!")
conn.close()
