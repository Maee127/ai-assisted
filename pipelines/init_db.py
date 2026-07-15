#!/usr/bin/env python3
"""
Initialize the database - equivalent to npm run init-db
"""
import os
from src.database import Database
from src.config import DB_PATH

if __name__ == "__main__":
    print(f"Initializing database at {DB_PATH}")
    db = Database(DB_PATH)
    print("Database initialized successfully!")