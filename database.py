from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from database import Base

class AirQuality(Base):
    __tablename__ = "air_quality"

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String, index=True)
    pm2_5 = Column(Float)
    pm10 = Column(Float)
    co = Column(Float)
    no2 = Column(Float)
    so2 = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    