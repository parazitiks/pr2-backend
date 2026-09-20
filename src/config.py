import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://app:app@db:5432/appdb")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
INSTANCE_ID = os.getenv("INSTANCE_ID", "unknown")