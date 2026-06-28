"""Store POS - Vercel serverless entry point"""
import sys
import os

# Ensure /tmp is used for the database (Vercel's writable directory)
os.environ.setdefault('DB_PATH', '/tmp/store.db')

# Import and init the Flask app
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import app

# Export as Vercel serverless handler
handler = app
