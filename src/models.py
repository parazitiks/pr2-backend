from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from .db import Base

class Visit(Base):
    __tablename__ = "visits"
    id = Column(Integer, primary_key=True, index=True)
    instance_id = Column(String, nullable=False)
    path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)