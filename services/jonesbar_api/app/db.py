import os
from dotenv import load_dotenv
import pymysql

# Load variables from .env in the current working directory
load_dotenv()

def get_connection():
    host = os.getenv("DB_HOST", "127.0.0.1")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASS")
    database = os.getenv("DB_NAME")

    if not user or not password or not database:
        raise RuntimeError("Missing DB_USER, DB_PASS, or DB_NAME in .env")

    return pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )
