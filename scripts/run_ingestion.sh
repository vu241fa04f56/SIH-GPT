#!/usr/bin/env bash
# run_ingestion.sh — Run a single ingestion cycle (all datasets, all cities)

set -e
echo "⏩ Starting WeatherGPT data ingestion..."

python -m data_pipeline.ingestion.fetch_weather_api
python -m data_pipeline.ingestion.fetch_disaster_api
python -m data_pipeline.ingestion.fetch_agro_api

echo "✅ Ingestion complete."
