"""
Shared MySQL connection configuration.

Reads credentials from environment variables with reasonable defaults so the
project can run locally without extra wiring:
    MYSQL_HOST (default: localhost)
    MYSQL_PORT (default: 3306)
    MYSQL_USER (default: root)
    MYSQL_PASSWORD (default: password)
    MYSQL_DB (default: taxi)
"""

import os
import mysql.connector


def get_connection():
    """
    Return a new MySQL connection using mysql-connector-python.

    Using dictionary=True so callers can treat rows like dicts, similar to the
    previous sqlite3.Row behaviour.
    """
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", "root@123"),
        database=os.getenv("MYSQL_DB", "taxiProduction"),
        autocommit=False,
    )


