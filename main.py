from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import List
from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy.orm import Session
from database import engine, Base, get_db

# Bazada jadval yaratish
Base.metadata.create_all(bind=engine)

# --- SQLALCHEMY DATABASE MODELI ---
class AirQualityDB(Base):
    __tablename__ = "air_quality_logs"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(String, index=True)
    pm25 = Column(Float)
    pm10 = Column(Float)
    aqi_status = Column(String)
    timestamp = Column(DateTime, default=datetime.now)

# --- PYDANTIC SCHEMAS ---
class SensorData(BaseModel):
    sensor_id: str
    pm25: float
    pm10: float

class AirQualityResponse(SensorData):
    id: int 
    timestamp: datetime
    aqi_status: str

    class Config:
        from_attributes = True

app = FastAPI(title="O'zbekistonda Havo Sifati API (Database bilan)")

def calculate_aqi_status(pm25: float) -> str:
    if pm25 <= 12.0:
        return "Yaxshi (Good) 😊"
    elif pm25 <= 35.4:
        return "Qoniqarli (Moderate) 😐"
    elif pm25 <= 55.4:
        return "Nozik guruhlar uchun zararli 😷"
    else: 
        return "Xavfli / Nosog'lom 🚨"

# --- API ENDPOINT'LAR ---

# A. Datchikdan kelgan ma'lumotni BAZAGA SAQLASH
@app.post("/api/v1/telemetry", response_model=AirQualityResponse)
def receive_sensor_data(data: SensorData, db: Session = Depends(get_db)):
    status = calculate_aqi_status(data.pm25)

    # Bazaga yangi qator qo'shamiz
    db_entry = AirQualityDB(
        sensor_id=data.sensor_id,
        pm25=data.pm25,
        pm10=data.pm10,
        aqi_status=status
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)

    return db_entry

# B. BAZADAN eng oxirgi ko'rsatkichni olish
@app.get("/api/v1/air-quality/latest", response_model=AirQualityResponse)
def get_latest_data(db: Session = Depends(get_db)):
    latest = db.query(AirQualityDB).order_by(AirQualityDB.id.desc()).first()
    if not latest:
        raise HTTPException(status_code=404, detail="Bazada hali ma'lumot yo'q.")
    return latest

# C. Bazadagi barcha tarixlarni olish (Grafiklar uchun)
@app.get("/api/v1/air-quality/history", response_model=List[AirQualityResponse])
def get_history(db: Session = Depends(get_db)):
    return db.query(AirQualityDB).all()
