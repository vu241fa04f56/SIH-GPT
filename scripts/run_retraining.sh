#!/usr/bin/env bash
# run_retraining.sh — Retrain all three models

set -e
echo "⏩ Retraining WeatherGPT models..."

python models/weather/train_weather_model.py
python models/disaster/train_disaster_model.py
python models/agro/train_agro_model.py

echo "✅ All models retrained."
