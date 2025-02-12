import os

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")  # Mặc định dùng localhost nếu không có biến môi trường
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "fastapi_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "fastapi_password")
DB_NAME = os.getenv("DB_NAME", "fastapi_db")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
