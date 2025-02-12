from sqlalchemy import create_engine

from database import engine, Base
import models  # Import your models to ensure they are registered with Base

# Tạo bảng nếu chưa có
Base.metadata.create_all(bind=engine)

print("✅ Tables created successfully!")
