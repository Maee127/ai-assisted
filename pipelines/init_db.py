#!/usr/bin/env python3
"""Initialize the local SQLite database."""

from .src.db import DB_PATH, init_db

if __name__ == "__main__":
    print(f"Initializing database at {DB_PATH}")
    init_db()
    print("Database initialized successfully!")
