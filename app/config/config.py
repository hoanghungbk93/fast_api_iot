import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DATABASE_TYPE = os.getenv("DATABASE_TYPE")

if DATABASE_TYPE == "sqlite":
    SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH")
    DATABASE_URL = f"sqlite:///{SQLITE_DB_PATH}"
elif DATABASE_TYPE == "postgres":
    POSTGRES_USER = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_DB = os.getenv("POSTGRES_DB")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT")
    DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
elif DATABASE_TYPE == "mysql":
    MYSQL_USER = os.getenv("MYSQL_USER")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
    MYSQL_DB = os.getenv("MYSQL_DB")
    MYSQL_HOST = os.getenv("MYSQL_HOST")
    MYSQL_PORT = os.getenv("MYSQL_PORT")
    DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
else:
    raise ValueError("Unsupported database type")
