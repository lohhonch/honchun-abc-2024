import os
import sqlite3

from helper.utility import get_secret_value

DATABASE_FOLDER = os.path.join(os.getcwd(), "database")
DATABASE_NAME = get_secret_value("DATABASE_NAME")
DATABASE_PATH = os.path.join(DATABASE_FOLDER, DATABASE_NAME)

if not os.path.exists(DATABASE_FOLDER):
  os.makedirs(DATABASE_FOLDER)


# Get connection
def get_connection():
  conn = sqlite3.connect(DATABASE_PATH)
  return conn


# Execute Non Query
def execute_non_query(query, parameters=None):
  conn = get_connection()

  with conn:
    cursor = conn.cursor()
    if parameters is None:
      cursor.execute(query)
    else:
      cursor.execute(query, parameters)

    last_id = cursor.lastrowid

  return last_id


# Fetch one
def fetch_one(query, parameters=None):
  conn = get_connection()

  with conn:
    cursor = conn.cursor()
    if parameters is None:
      cursor.execute(query)
    else:
      cursor.execute(query, parameters)
    data = cursor.fetchone()

  return data


# Fetch all
def fetch_all(query, parameters=None):
  conn = get_connection()

  with conn:
    cursor = conn.cursor()
    if parameters is None:
      cursor.execute(query)
    else:
      cursor.execute(query, parameters)
    rows = cursor.fetchall()

  return rows


# Create database if does not exist
def create_db():
  conn = get_connection()

  with conn:
    cursor = conn.cursor()

    # Create Configuration table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Configuration (
            configuration_id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL,
            creation_date TIMESTAMP DEFAULT (DATETIME(CURRENT_TIMESTAMP, '+8 hours')) NOT NULL
        )
    """)
    cursor.execute("""
        INSERT INTO Configuration (key)
          SELECT 'setup_on'
          WHERE NOT EXISTS (SELECT 1 FROM Configuration WHERE key = 'setup_on')
    """)

    # Create Repository table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Repository (
            repository_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            creation_date TIMESTAMP DEFAULT (DATETIME(CURRENT_TIMESTAMP, '+8 hours')) NOT NULL,
            modification_date TIMESTAMP DEFAULT (DATETIME(CURRENT_TIMESTAMP, '+8 hours')) NOT NULL
        )
    """)

    # Create Files table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Files (
            file_id INTEGER PRIMARY KEY AUTOINCREMENT,
            repository_id TEXT NOT NULL,
            file_name TEXT NOT NULL,
            type TEXT NOT NULL,
            size INTEGER NOT NULL,
            data BLOB NOT NULL,
            FOREIGN KEY (repository_id) REFERENCES Repository(repository_id) ON DELETE CASCADE
        )
    """)

    conn.commit()

  # End of create_db()
