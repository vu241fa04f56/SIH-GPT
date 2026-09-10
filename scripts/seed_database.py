"""
seed_database.py
────────────────
Seeds the database with:
  1. 40 major Indian cities (with lat/lon and PostGIS geometry)
  2. Optional: Load your 600K-row disaster CSV (set DISASTER_CSV_PATH)

Usage:
    python scripts/seed_database.py
    DISASTER_CSV_PATH=./data/disaster_events.csv python scripts/seed_database.py
"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from loguru import logger
import httpx
from sqlalchemy import func, select, text

from backend.core.config import settings
from data_pipeline.storage.db_connection import engine, get_async_session
from data_pipeline.storage.db_models import Base, City, DisasterRecord

# ── 126 Indian cities — all state capitals + major tier-2/district centres ────
CITIES = [
    # ── Maharashtra ──────────────────────────────────────────────────────────
    {"name": "Mumbai",       "state": "Maharashtra",     "lat": 19.0760,  "lon": 72.8777,  "coastal": True},
    {"name": "Pune",         "state": "Maharashtra",     "lat": 18.5204,  "lon": 73.8567,  "coastal": False},
    {"name": "Nagpur",       "state": "Maharashtra",     "lat": 21.1458,  "lon": 79.0882,  "coastal": False},
    {"name": "Nashik",       "state": "Maharashtra",     "lat": 19.9975,  "lon": 73.7898,  "coastal": False},
    {"name": "Aurangabad",   "state": "Maharashtra",     "lat": 19.8762,  "lon": 75.3433,  "coastal": False},
    {"name": "Kolhapur",     "state": "Maharashtra",     "lat": 16.7050,  "lon": 74.2433,  "coastal": False},
    {"name": "Solapur",      "state": "Maharashtra",     "lat": 17.6599,  "lon": 75.9064,  "coastal": False},
    {"name": "Amravati",     "state": "Maharashtra",     "lat": 20.9374,  "lon": 77.7796,  "coastal": False},
    {"name": "Nanded",       "state": "Maharashtra",     "lat": 19.1383,  "lon": 77.3210,  "coastal": False},
    # ── Delhi & NCR ──────────────────────────────────────────────────────────
    {"name": "Delhi",        "state": "Delhi",           "lat": 28.6139,  "lon": 77.2090,  "coastal": False},
    {"name": "Noida",        "state": "Uttar Pradesh",   "lat": 28.5355,  "lon": 77.3910,  "coastal": False},
    {"name": "Ghaziabad",    "state": "Uttar Pradesh",   "lat": 28.6692,  "lon": 77.4538,  "coastal": False},
    {"name": "Faridabad",    "state": "Haryana",         "lat": 28.4089,  "lon": 77.3178,  "coastal": False},
    {"name": "Gurugram",     "state": "Haryana",         "lat": 28.4595,  "lon": 77.0266,  "coastal": False},
    # ── Karnataka ─────────────────────────────────────────────────────────────
    {"name": "Bengaluru",    "state": "Karnataka",       "lat": 12.9716,  "lon": 77.5946,  "coastal": False},
    {"name": "Mysuru",       "state": "Karnataka",       "lat": 12.2958,  "lon": 76.6394,  "coastal": False},
    {"name": "Mangaluru",    "state": "Karnataka",       "lat": 12.9141,  "lon": 74.8560,  "coastal": True},
    {"name": "Hubli",        "state": "Karnataka",       "lat": 15.3647,  "lon": 75.1240,  "coastal": False},
    {"name": "Belagavi",     "state": "Karnataka",       "lat": 15.8497,  "lon": 74.4977,  "coastal": False},
    {"name": "Bellary",      "state": "Karnataka",       "lat": 15.1394,  "lon": 76.9214,  "coastal": False},
    # ── Tamil Nadu ────────────────────────────────────────────────────────────
    {"name": "Chennai",      "state": "Tamil Nadu",      "lat": 13.0827,  "lon": 80.2707,  "coastal": True},
    {"name": "Coimbatore",   "state": "Tamil Nadu",      "lat": 11.0168,  "lon": 76.9558,  "coastal": False},
    {"name": "Madurai",      "state": "Tamil Nadu",      "lat": 9.9252,   "lon": 78.1198,  "coastal": False},
    {"name": "Tiruchirappalli", "state": "Tamil Nadu",   "lat": 10.7905,  "lon": 78.7047,  "coastal": False},
    {"name": "Salem",        "state": "Tamil Nadu",      "lat": 11.6643,  "lon": 78.1460,  "coastal": False},
    {"name": "Tirunelveli",  "state": "Tamil Nadu",      "lat": 8.7139,   "lon": 77.7567,  "coastal": True},
    {"name": "Erode",        "state": "Tamil Nadu",      "lat": 11.3410,  "lon": 77.7172,  "coastal": False},
    {"name": "Vellore",      "state": "Tamil Nadu",      "lat": 12.9165,  "lon": 79.1325,  "coastal": False},
    {"name": "Thoothukudi",  "state": "Tamil Nadu",      "lat": 8.7642,   "lon": 78.1348,  "coastal": True},
    {"name": "Puducherry",   "state": "Puducherry",      "lat": 11.9416,  "lon": 79.8083,  "coastal": True},
    # ── Andhra Pradesh ────────────────────────────────────────────────────────
    {"name": "Visakhapatnam","state": "Andhra Pradesh",  "lat": 17.6868,  "lon": 83.2185,  "coastal": True},
    {"name": "Vijayawada",   "state": "Andhra Pradesh",  "lat": 16.5062,  "lon": 80.6480,  "coastal": False},
    {"name": "Guntur",       "state": "Andhra Pradesh",  "lat": 16.3067,  "lon": 80.4365,  "coastal": False},
    {"name": "Nellore",      "state": "Andhra Pradesh",  "lat": 14.4426,  "lon": 79.9865,  "coastal": True},
    {"name": "Tirupati",     "state": "Andhra Pradesh",  "lat": 13.6288,  "lon": 79.4192,  "coastal": False},
    {"name": "Kurnool",      "state": "Andhra Pradesh",  "lat": 15.8281,  "lon": 78.0373,  "coastal": False},
    {"name": "Amaravati",    "state": "Andhra Pradesh",  "lat": 16.5151,  "lon": 80.5158,  "coastal": False},
    # ── Telangana ─────────────────────────────────────────────────────────────
    {"name": "Hyderabad",    "state": "Telangana",       "lat": 17.3850,  "lon": 78.4867,  "coastal": False},
    {"name": "Warangal",     "state": "Telangana",       "lat": 17.9784,  "lon": 79.5941,  "coastal": False},
    {"name": "Nizamabad",    "state": "Telangana",       "lat": 18.6725,  "lon": 78.0941,  "coastal": False},
    {"name": "Karimnagar",   "state": "Telangana",       "lat": 18.4386,  "lon": 79.1288,  "coastal": False},
    # ── Kerala ────────────────────────────────────────────────────────────────
    {"name": "Thiruvananthapuram", "state": "Kerala",    "lat": 8.5241,   "lon": 76.9366,  "coastal": True},
    {"name": "Kochi",        "state": "Kerala",          "lat": 9.9312,   "lon": 76.2673,  "coastal": True},
    {"name": "Kozhikode",    "state": "Kerala",          "lat": 11.2588,  "lon": 75.7804,  "coastal": True},
    {"name": "Thrissur",     "state": "Kerala",          "lat": 10.5276,  "lon": 76.2144,  "coastal": False},
    {"name": "Kollam",       "state": "Kerala",          "lat": 8.8932,   "lon": 76.6141,  "coastal": True},
    {"name": "Kannur",       "state": "Kerala",          "lat": 11.8745,  "lon": 75.3704,  "coastal": True},
    {"name": "Malappuram",   "state": "Kerala",          "lat": 11.0510,  "lon": 76.0711,  "coastal": False},
    # ── Gujarat ───────────────────────────────────────────────────────────────
    {"name": "Ahmedabad",    "state": "Gujarat",         "lat": 23.0225,  "lon": 72.5714,  "coastal": False},
    {"name": "Surat",        "state": "Gujarat",         "lat": 21.1702,  "lon": 72.8311,  "coastal": True},
    {"name": "Vadodara",     "state": "Gujarat",         "lat": 22.3072,  "lon": 73.1812,  "coastal": False},
    {"name": "Rajkot",       "state": "Gujarat",         "lat": 22.3039,  "lon": 70.8022,  "coastal": False},
    {"name": "Bhavnagar",    "state": "Gujarat",         "lat": 21.7645,  "lon": 72.1519,  "coastal": True},
    {"name": "Jamnagar",     "state": "Gujarat",         "lat": 22.4707,  "lon": 70.0577,  "coastal": True},
    {"name": "Junagadh",     "state": "Gujarat",         "lat": 21.5222,  "lon": 70.4579,  "coastal": False},
    {"name": "Gandhinagar",  "state": "Gujarat",         "lat": 23.2156,  "lon": 72.6369,  "coastal": False},
    {"name": "Anand",        "state": "Gujarat",         "lat": 22.5645,  "lon": 72.9289,  "coastal": False},
    # ── Rajasthan ─────────────────────────────────────────────────────────────
    {"name": "Jaipur",       "state": "Rajasthan",       "lat": 26.9124,  "lon": 75.7873,  "coastal": False},
    {"name": "Jodhpur",      "state": "Rajasthan",       "lat": 26.2389,  "lon": 73.0243,  "coastal": False},
    {"name": "Kota",         "state": "Rajasthan",       "lat": 25.2138,  "lon": 75.8648,  "coastal": False},
    {"name": "Bikaner",      "state": "Rajasthan",       "lat": 28.0229,  "lon": 73.3119,  "coastal": False},
    {"name": "Udaipur",      "state": "Rajasthan",       "lat": 24.5854,  "lon": 73.7125,  "coastal": False},
    {"name": "Ajmer",        "state": "Rajasthan",       "lat": 26.4499,  "lon": 74.6399,  "coastal": False},
    {"name": "Alwar",        "state": "Rajasthan",       "lat": 27.5530,  "lon": 76.6346,  "coastal": False},
    # ── Uttar Pradesh ─────────────────────────────────────────────────────────
    {"name": "Lucknow",      "state": "Uttar Pradesh",   "lat": 26.8467,  "lon": 80.9462,  "coastal": False},
    {"name": "Kanpur",       "state": "Uttar Pradesh",   "lat": 26.4499,  "lon": 80.3319,  "coastal": False},
    {"name": "Agra",         "state": "Uttar Pradesh",   "lat": 27.1767,  "lon": 78.0081,  "coastal": False},
    {"name": "Varanasi",     "state": "Uttar Pradesh",   "lat": 25.3176,  "lon": 82.9739,  "coastal": False},
    {"name": "Meerut",       "state": "Uttar Pradesh",   "lat": 28.9845,  "lon": 77.7064,  "coastal": False},
    {"name": "Prayagraj",    "state": "Uttar Pradesh",   "lat": 25.4358,  "lon": 81.8463,  "coastal": False},
    {"name": "Gorakhpur",    "state": "Uttar Pradesh",   "lat": 26.7606,  "lon": 83.3732,  "coastal": False},
    {"name": "Bareilly",     "state": "Uttar Pradesh",   "lat": 28.3670,  "lon": 79.4304,  "coastal": False},
    {"name": "Aligarh",      "state": "Uttar Pradesh",   "lat": 27.8974,  "lon": 78.0880,  "coastal": False},
    {"name": "Moradabad",    "state": "Uttar Pradesh",   "lat": 28.8386,  "lon": 78.7733,  "coastal": False},
    # ── Madhya Pradesh ────────────────────────────────────────────────────────
    {"name": "Bhopal",       "state": "Madhya Pradesh",  "lat": 23.2599,  "lon": 77.4126,  "coastal": False},
    {"name": "Indore",       "state": "Madhya Pradesh",  "lat": 22.7196,  "lon": 75.8577,  "coastal": False},
    {"name": "Jabalpur",     "state": "Madhya Pradesh",  "lat": 23.1815,  "lon": 79.9864,  "coastal": False},
    {"name": "Gwalior",      "state": "Madhya Pradesh",  "lat": 26.2183,  "lon": 78.1828,  "coastal": False},
    {"name": "Ujjain",       "state": "Madhya Pradesh",  "lat": 23.1793,  "lon": 75.7849,  "coastal": False},
    {"name": "Sagar",        "state": "Madhya Pradesh",  "lat": 23.8388,  "lon": 78.7378,  "coastal": False},
    # ── Punjab & Haryana ──────────────────────────────────────────────────────
    {"name": "Ludhiana",     "state": "Punjab",          "lat": 30.9010,  "lon": 75.8573,  "coastal": False},
    {"name": "Amritsar",     "state": "Punjab",          "lat": 31.6340,  "lon": 74.8723,  "coastal": False},
    {"name": "Jalandhar",    "state": "Punjab",          "lat": 31.3260,  "lon": 75.5762,  "coastal": False},
    {"name": "Patiala",      "state": "Punjab",          "lat": 30.3398,  "lon": 76.3869,  "coastal": False},
    {"name": "Bathinda",     "state": "Punjab",          "lat": 30.2110,  "lon": 74.9455,  "coastal": False},
    {"name": "Chandigarh",   "state": "Chandigarh",      "lat": 30.7333,  "lon": 76.7794,  "coastal": False},
    {"name": "Ambala",       "state": "Haryana",         "lat": 30.3753,  "lon": 76.7821,  "coastal": False},
    # ── Himachal Pradesh & Uttarakhand ────────────────────────────────────────
    {"name": "Shimla",       "state": "Himachal Pradesh","lat": 31.1048,  "lon": 77.1734,  "coastal": False},
    {"name": "Dharamshala",  "state": "Himachal Pradesh","lat": 32.2190,  "lon": 76.3234,  "coastal": False},
    {"name": "Manali",       "state": "Himachal Pradesh","lat": 32.2432,  "lon": 77.1892,  "coastal": False},
    {"name": "Dehradun",     "state": "Uttarakhand",     "lat": 30.3165,  "lon": 78.0322,  "coastal": False},
    {"name": "Haridwar",     "state": "Uttarakhand",     "lat": 29.9457,  "lon": 78.1642,  "coastal": False},
    {"name": "Roorkee",      "state": "Uttarakhand",     "lat": 29.8543,  "lon": 77.8880,  "coastal": False},
    # ── J&K & Ladakh ──────────────────────────────────────────────────────────
    {"name": "Srinagar",     "state": "J&K",             "lat": 34.0837,  "lon": 74.7973,  "coastal": False},
    {"name": "Jammu",        "state": "J&K",             "lat": 32.7266,  "lon": 74.8570,  "coastal": False},
    {"name": "Leh",          "state": "Ladakh",          "lat": 34.1526,  "lon": 77.5771,  "coastal": False},
    # ── Bihar ─────────────────────────────────────────────────────────────────
    {"name": "Patna",        "state": "Bihar",           "lat": 25.5941,  "lon": 85.1376,  "coastal": False},
    {"name": "Gaya",         "state": "Bihar",           "lat": 24.7914,  "lon": 85.0002,  "coastal": False},
    {"name": "Muzaffarpur",  "state": "Bihar",           "lat": 26.1209,  "lon": 85.3647,  "coastal": False},
    {"name": "Bhagalpur",    "state": "Bihar",           "lat": 25.2425,  "lon": 86.9842,  "coastal": False},
    {"name": "Darbhanga",    "state": "Bihar",           "lat": 26.1542,  "lon": 85.8918,  "coastal": False},
    # ── Jharkhand ─────────────────────────────────────────────────────────────
    {"name": "Ranchi",       "state": "Jharkhand",       "lat": 23.3441,  "lon": 85.3096,  "coastal": False},
    {"name": "Jamshedpur",   "state": "Jharkhand",       "lat": 22.8046,  "lon": 86.2029,  "coastal": False},
    {"name": "Dhanbad",      "state": "Jharkhand",       "lat": 23.7957,  "lon": 86.4304,  "coastal": False},
    {"name": "Bokaro",       "state": "Jharkhand",       "lat": 23.6693,  "lon": 85.9609,  "coastal": False},
    # ── West Bengal ───────────────────────────────────────────────────────────
    {"name": "Kolkata",      "state": "West Bengal",     "lat": 22.5726,  "lon": 88.3639,  "coastal": True},
    {"name": "Howrah",       "state": "West Bengal",     "lat": 22.5958,  "lon": 88.2636,  "coastal": False},
    {"name": "Siliguri",     "state": "West Bengal",     "lat": 26.7271,  "lon": 88.3953,  "coastal": False},
    {"name": "Asansol",      "state": "West Bengal",     "lat": 23.6833,  "lon": 86.9833,  "coastal": False},
    {"name": "Durgapur",     "state": "West Bengal",     "lat": 23.5204,  "lon": 87.3119,  "coastal": False},
    # ── Odisha ────────────────────────────────────────────────────────────────
    {"name": "Bhubaneswar",  "state": "Odisha",          "lat": 20.2961,  "lon": 85.8245,  "coastal": False},
    {"name": "Cuttack",      "state": "Odisha",          "lat": 20.4625,  "lon": 85.8830,  "coastal": False},
    {"name": "Rourkela",     "state": "Odisha",          "lat": 22.2604,  "lon": 84.8536,  "coastal": False},
    {"name": "Sambalpur",    "state": "Odisha",          "lat": 21.4669,  "lon": 83.9756,  "coastal": False},
    {"name": "Puri",         "state": "Odisha",          "lat": 19.8106,  "lon": 85.8314,  "coastal": True},
    # ── Chhattisgarh ──────────────────────────────────────────────────────────
    {"name": "Raipur",       "state": "Chhattisgarh",    "lat": 21.2514,  "lon": 81.6296,  "coastal": False},
    {"name": "Bhilai",       "state": "Chhattisgarh",    "lat": 21.1938,  "lon": 81.3509,  "coastal": False},
    {"name": "Bilaspur",     "state": "Chhattisgarh",    "lat": 22.0796,  "lon": 82.1391,  "coastal": False},
    # ── Assam & North-East ────────────────────────────────────────────────────
    {"name": "Guwahati",     "state": "Assam",           "lat": 26.1445,  "lon": 91.7362,  "coastal": False},
    {"name": "Dibrugarh",    "state": "Assam",           "lat": 27.4728,  "lon": 94.9120,  "coastal": False},
    {"name": "Silchar",      "state": "Assam",           "lat": 24.8333,  "lon": 92.7789,  "coastal": False},
    {"name": "Shillong",     "state": "Meghalaya",       "lat": 25.5788,  "lon": 91.8933,  "coastal": False},
    {"name": "Agartala",     "state": "Tripura",         "lat": 23.8315,  "lon": 91.2868,  "coastal": False},
    {"name": "Imphal",       "state": "Manipur",         "lat": 24.8170,  "lon": 93.9368,  "coastal": False},
    {"name": "Aizawl",       "state": "Mizoram",         "lat": 23.7271,  "lon": 92.7176,  "coastal": False},
    {"name": "Kohima",       "state": "Nagaland",        "lat": 25.6701,  "lon": 94.1077,  "coastal": False},
    {"name": "Itanagar",     "state": "Arunachal Pradesh","lat": 27.0844,  "lon": 93.6053,  "coastal": False},
    {"name": "Gangtok",      "state": "Sikkim",          "lat": 27.3389,  "lon": 88.6065,  "coastal": False},
    # ── Goa ───────────────────────────────────────────────────────────────────
    {"name": "Panaji",       "state": "Goa",             "lat": 15.4909,  "lon": 73.8278,  "coastal": True},
    # ── Union Territories ─────────────────────────────────────────────────────
    {"name": "Port Blair",   "state": "Andaman & Nicobar","lat": 11.6234,  "lon": 92.7265,  "coastal": True},
]



async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.run_sync(Base.metadata.create_all)
    logger.success("Tables created.")


async def seed_cities() -> None:
    async with get_async_session() as session:
        for c in CITIES:
            existing = await session.execute(
                select(City).where(City.name == c["name"])
            )
            if existing.scalar_one_or_none():
                continue
            city = City(
                name=c["name"],
                state=c["state"],
                latitude=c["lat"],
                longitude=c["lon"],
                is_coastal=c.get("coastal", False),
                geom=f"SRID=4326;POINT({c['lon']} {c['lat']})",
            )
            session.add(city)
    logger.success(f"Seeded {len(CITIES)} cities.")


async def enrich_city_elevations(concurrency: int = 8) -> None:
    """Fill missing elevations with the free Open-Meteo elevation endpoint."""
    async with get_async_session() as session:
        result = await session.execute(select(City).where(City.elevation_m.is_(None)))
        cities = list(result.scalars().all())
    if not cities:
        return

    semaphore = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(timeout=30) as client:
        async def fetch(city: City) -> tuple[int, float | None]:
            async with semaphore:
                try:
                    response = await client.get(
                        settings.OPEN_METEO_ELEVATION_URL,
                        params={"latitude": city.latitude, "longitude": city.longitude},
                    )
                    response.raise_for_status()
                    values = response.json().get("elevation", [])
                    return city.id, float(values[0]) if values else None
                except Exception as exc:
                    logger.warning(f"Elevation fetch failed for {city.name}: {exc}")
                    return city.id, None
        elevations = await asyncio.gather(*(fetch(city) for city in cities))

    async with get_async_session() as session:
        for city_id, elevation in elevations:
            if elevation is not None:
                city = await session.get(City, city_id)
                city.elevation_m = elevation
    logger.success(f"Elevation enrichment complete for {sum(v is not None for _, v in elevations)} cities.")


async def seed_disaster_csv(csv_path: str) -> None:
    """Load the 600K-row historical disaster CSV into disaster_records."""
    import pandas as pd

    logger.info(f"Loading disaster CSV from {csv_path}...")
    df = pd.read_csv(csv_path)
    logger.info(f"  Rows: {len(df)}, Columns: {list(df.columns)}")

    # Map required columns — adjust column names to match your actual CSV schema
    col_map = {
        "city_id": "city_id",
        "timestamp": "timestamp",
        "disaster_type": "disaster_type",
        "severity": "severity",
    }
    for req in col_map:
        if req not in df.columns:
            logger.error(f"CSV missing required column '{req}'. Skipping disaster seed.")
            return

    async with get_async_session() as session:
        batch = []
        for _, row in df.iterrows():
            batch.append(DisasterRecord(
                city_id=int(row["city_id"]),
                timestamp=row["timestamp"],
                disaster_type=str(row["disaster_type"]),
                severity=str(row.get("severity", "medium")),
                risk_score=float(row.get("risk_score", 0.5)),
                source="seed_csv",
            ))
            if len(batch) >= 10_000:
                session.add_all(batch)
                await session.flush()
                batch = []
        if batch:
            session.add_all(batch)
    logger.success("Disaster CSV seeded.")


async def main() -> None:
    await create_tables()
    await seed_cities()
    await enrich_city_elevations()

    csv_path = os.getenv("DISASTER_CSV_PATH", "")
    if csv_path and os.path.exists(csv_path):
        await seed_disaster_csv(csv_path)
    else:
        logger.info("DISASTER_CSV_PATH not set — skipping disaster seed. Set it when you have the CSV.")


if __name__ == "__main__":
    asyncio.run(main())
