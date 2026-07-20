from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import httpx

import database
import models

# 14 ta hudud koordinatalari
CITIES = {
    "Toshkent shahri": {"lat": 41.2995, "lon": 69.2401},
    "Andijon": {"lat": 40.7821, "lon": 72.3442},
    "Buxoro": {"lat": 39.7747, "lon": 64.4286},
    "Farg'ona": {"lat": 40.3842, "lon": 71.7843},
    "Jizzax": {"lat": 40.1158, "lon": 67.8422},
    "Namangan": {"lat": 41.0011, "lon": 71.6683},
    "Navoiy": {"lat": 40.0844, "lon": 65.3792},
    "Qarshi": {"lat": 38.8605, "lon": 65.7890},
    "Samarqand": {"lat": 39.6542, "lon": 66.9597},
    "Guliston": {"lat": 40.4897, "lon": 68.7842},
    "Termiz": {"lat": 37.2242, "lon": 67.2783},
    "Nurafshon": {"lat": 41.0422, "lon": 69.3583},
    "Urganch": {"lat": 41.5503, "lon": 60.6314},
    "Nukus": {"lat": 42.4602, "lon": 59.6180}
}

async def fetch_air_quality_job():
    db: Session = database.SessionLocal()
    try:
        lats = ",".join([str(coords["lat"]) for coords in CITIES.values()])
        lons = ",".join([str(coords["lon"]) for coords in CITIES.values()])
        
        url = (
            f"https://air-quality-api.open-meteo.com/v1/air-quality?"
            f"latitude={lats}&longitude={lons}"
            f"&current=pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide"
        )

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code == 200:
                res_data = response.json()
                
                if isinstance(res_data, list):
                    for idx, city_name in enumerate(CITIES.keys()):
                        data = res_data[idx].get("current", {})
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
                print("✅ MVP: Open-Meteo ma'lumotlari muvaffaqiyatli yangilandi!")
    except Exception as e:
        print(f"❌ Ma'lumot yig'ishda xatolik: {e}")
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(fetch_air_quality_job, 'interval', hours=1)
    scheduler.start()
    await fetch_air_quality_job()
    yield
    scheduler.shutdown()

app = FastAPI(title="Eco Monitoring Uz - MVP API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

models.Base.metadata.create_all(bind=database.engine)

@app.get("/")
def home():
    return {
        "status": "online",
        "project": "Eco Monitoring Uz MVP",
        "coverage": "O'zbekistonning 14 ta asosiy hududi"
    }

@app.get("/air-quality")
@app.get("/air-quality/")
def get_air_quality(db: Session = Depends(database.get_db)):
    return db.query(models.AirQuality).order_by(models.AirQuality.id.desc()).all()