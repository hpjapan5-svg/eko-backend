from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import httpx

import database
import models

# 1. Shaharlar koordinatalari
CITIES = {
    "Toshkent": {"lat": 41.2995, "lon": 69.2401},
    "Samarqand": {"lat": 39.6542, "lon": 66.9597},
    "Farg'ona": {"lat": 40.3842, "lon": 71.7843}
}

# 2. Open-Meteo API'dan ma'lumot tortib bazaga yozuvchi background funksiya
async def fetch_air_quality_job():
    db: Session = database.SessionLocal()
    try:
        async with httpx.AsyncClient() as client:
            for city_name, coords in CITIES.items():
                url = (
                    f"https://air-quality-api.open-meteo.com/v1/air-quality?"
                    f"latitude={coords['lat']}&longitude={coords['lon']}"
                    f"&current=pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide"
                )
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json().get("current", {})
                    
                    air_data = models.AirQuality(
                        city=city_name,
                        pm2_5=data.get("pm2_5"),
                        pm10=data.get("pm10"),
                        co=data.get("carbon_monoxide"),
                        no2=data.get("nitrogen_dioxide"),
                        so2=data.get("sulphur_dioxide")
                    )
                    db.add(air_data)
            db.commit()
            print("✅ Open-Meteo ma'lumotlari muvaffaqiyatli saqlandi!")
    except Exception as e:
        print(f"❌ Ma'lumot yig'ishda xatolik: {e}")
    finally:
        db.close()

# 3. Server ishga tushganda taymerni yoqish
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(fetch_air_quality_job, 'interval', hours=1)
    scheduler.start()
    
    # Server yonishi bilan birinchi marta ma'lumotlarni tortadi
    await fetch_air_quality_job()
    
    yield
    scheduler.shutdown()

# 4. FastAPI ilovasi
app = FastAPI(title="Eco Monitoring Uz API", lifespan=lifespan)

# 🌐 CORS MIDDLEWARE (Frontend va Vercel/Netlify uchun ruxsat)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Istalgan frontend domenidan kelgan so'rovlarga ruxsat beradi
    allow_credentials=True,
    allow_methods=["*"],  # GET, POST va boshqa barcha metodlarga ruxsat
    allow_headers=["*"],
)

# Base jadvallarini yaratish
models.Base.metadata.create_all(bind=database.engine)

@app.get("/")
def home():
    return {"message": "Eco Monitoring Uz API muvaffaqiyatli ishlayapti!"}

@app.get("/air-quality")
@app.get("/air-quality/")
def get_air_quality(db: Session = Depends(database.get_db)):
    return db.query(models.AirQuality).order_by(models.AirQuality.id.desc()).all()