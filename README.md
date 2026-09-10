# WeatherGPT 🌦️

> **AI-powered conversational weather, disaster early-warning, and agro-advisory platform for India.**

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Open-Meteo APIs  ──►  Data Pipeline  ──►  PostgreSQL+PostGIS   │
│                         (hourly cron)         (raw + processed) │
├─────────────────────────────────────────────────────────────────┤
│  ML Models  ──►  Inference Service  ──►  FastAPI Backend        │
│  (.pkl files)                             (REST + WebSocket)    │
├─────────────────────────────────────────────────────────────────┤
│  Gemini LLM  ──►  Chatbot Layer  ──►  Tool-calling into API     │
├─────────────────────────────────────────────────────────────────┤
│  React + Mapbox GL  ──►  3D Globe Dashboard                     │
│  (web)               (800 Indian cities, feature toggles)       │
└─────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + SQLAlchemy async + WebSockets |
| Database | PostgreSQL 16 + PostGIS |
| ML Models | XGBoost + LightGBM + scikit-learn (bundled pipelines) |
| LLM | Google Gemini (function-calling) |
| Frontend | React + Vite + Mapbox GL JS |
| Scheduling | APScheduler (hourly ingestion) |
| Push Alerts | Firebase Cloud Messaging |
| Container | Docker + Docker Compose |
| Orchestration | Kubernetes (production) |

## Quick Start

### Prerequisites
- Docker + Docker Compose
- Python 3.11+
- Node.js 20+

### 1. Clone and configure

```bash
git clone <repo-url>
cd weathergpt
cp .env.example .env
# Edit .env — add GEMINI_API_KEY and VITE_MAPBOX_TOKEN
```

### 2. Start all services

```bash
docker-compose up -d

# Create/migrate the PostGIS schema and seed 40 cities + elevation
docker-compose exec backend alembic upgrade head
docker-compose exec backend python scripts/seed_database.py

# Pull the first weather, air-quality, marine and derived-disaster batch
docker-compose exec backend python -m data_pipeline.ingestion.scheduler --once
```

The three supplied trained artifacts are already installed under each model
registry's `active/` directory. You do **not** need to retrain before the first
prediction. Check `GET http://localhost:8000/health`; all three entries under
`models` should report `loaded: true`.

## Integrated data sources

All four supplied Open-Meteo services are configured in `.env.example` and are
free/no-key endpoints:

| Data | Endpoint | NWP Backend | Use |
|---|---|---|---|
| Historical weather | `archive-api.open-meteo.com/v1/archive` | **GFS, ECMWF IFS, ERA5** | Atmospheric, soil and radiation observations |
| Air quality | `air-quality-api.open-meteo.com/v1/air-quality` | **CAMS / GFS** | US AQI, PM, gases, dust and pollen |
| Marine | `marine-api.open-meteo.com/v1/marine` | **GFS-Wave / ERA5** | Wave height and sea-surface temperature for coastal cities |
| Elevation | `api.open-meteo.com/v1/elevation` | SRTM | One-time city elevation enrichment while seeding |

> **NWP Integration note**: Open-Meteo acts as a unified interface over multiple
> Numerical Weather Prediction (NWP) models including **GFS** (NOAA), **ECMWF IFS**,
> **ERA5** reanalysis, **GFS-Wave**, and **CAMS** (Copernicus). WeatherGPT's ML models
> are trained on and continuously ingest real NWP model output — no mock data is used.

The scheduler limits concurrent requests, deduplicates city/timestamp rows and
runs weather/disaster ingestion hourly and agro aggregation every six hours.

## Bundled model adapters

| Artifact | Real saved interface | Backend integration |
|---|---|---|
| `WeatherGPT_39_Feature_Model.pickle` | 39 engineered inputs; 18 next-hour targets | Builds time/wind features and 1/2/3/24-hour lags; inverse-transforms skewed outputs |
| `disaster_prediction_pipeline.pkl` | 20 inputs + RobustScaler + 18-class encoder | Builds 24/48-hour rainfall and risk indices; decodes `nominal` as no active disaster |
| `farmer_advisory_pipeline (2).pkl` | 35 inputs + categorical encoders + five LightGBM classifiers | Builds 1/3/7/14-day aggregates and returns all five advisory outputs |

The weather artifact does not directly predict every stored API column: it
predicts its 18 trained targets. Other current fields are carried forward so
the API still returns a complete dashboard payload without inventing outputs.

### 3. Optional retraining

Only run these after ingesting enough new labelled data; the supplied models
are already active:

```bash
docker-compose exec backend python models/weather/train_weather_model.py
docker-compose exec backend python models/disaster/train_disaster_model.py
docker-compose exec backend python models/agro/train_agro_model.py
```

### 4. Access

| Service | URL |
|---|---|
| API docs | http://localhost:8000/docs |
| Frontend dashboard | http://localhost:5173 |
| WebSocket test | ws://localhost:8000/ws |

## Project Structure

```
weathergpt/
├── data_pipeline/      # Ingestion, preprocessing, retraining
├── models/             # Train scripts + .pkl registry
├── backend/            # FastAPI app (routes, services, schemas)
├── chatbot/            # Gemini LLM engine + tools + multilingual
├── frontend/           # React + Mapbox GL dashboard
├── geo_data/           # 800 Indian cities GeoJSON
├── infra/              # Docker, K8s, CI/CD
├── scripts/            # Seed, ingestion, retrain helpers
└── docs/               # Specifications
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/predict/weather/{city_id}` | Complete current payload + model-trained next-hour targets |
| GET | `/predict/disaster/{city_id}` | 3-hr advance disaster risk |
| GET | `/advisory/{city_id}` | Agro advisory |
| POST | `/alerts/subscribe` | Register device for FCM alerts |
| POST | `/chat` | Chatbot (Gemini + tool-calling) |
| WS | `/ws` | Live prediction broadcast |
| GET | `/history/{city_id}/records` | Raw hourly records for past N days |
| GET | `/history/{city_id}/stats` | Climate aggregate stats (mean/min/max/std) |
| GET | `/history/{city_id}/trend` | Daily anomaly trend for any variable |
| POST | `/voice/transcribe` | Audio → text (Google Cloud STT, 11 Indian languages) |
| POST | `/voice/respond` | Audio → STT → Chatbot → text reply |
| POST | `/voice/synthesize` | Text → MP3 audio (Google Cloud TTS, 11 Indian languages) |

## Data Sources

- **Weather + Air Quality**: [Open-Meteo](https://open-meteo.com/) (free, no key required)
- **Marine**: [Open-Meteo Marine](https://marine-api.open-meteo.com)
- **Disaster events**: Derived from extreme-weather variables + your 600K-row seed dataset

## Environment Variables

See [`.env.example`](./.env.example) for the full list. Critical ones:

```env
GEMINI_API_KEY=           # Google AI Studio → https://aistudio.google.com
VITE_MAPBOX_TOKEN=        # https://account.mapbox.com/
DATABASE_URL=             # auto-set by docker-compose
```

## Development

```bash
# Backend only (hot reload)
uvicorn backend.main:app --reload

# Frontend only
cd frontend/dashboard && npm install && npm run dev

# Run ingestion manually
python -m data_pipeline.ingestion.scheduler --once

# Run tests
pytest backend/tests/ -v
```

## License

MIT
