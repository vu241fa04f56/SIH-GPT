// CityPanel.jsx — Comprehensive Side Panel with ML Model Predictions & Current Observations

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { getWeather, getDisasterRisk, getAdvisory } from '../../services/apiClient'

const FEATURE_GROUPS = [
  {
    title: '🌡 Atmosphere',
    fields: [
      { key: 'temperature_2m',       label: 'Temperature',     unit: '°C' },
      { key: 'apparent_temperature', label: 'Feels Like',      unit: '°C' },
      { key: 'relative_humidity_2m', label: 'Humidity',        unit: '%' },
      { key: 'dew_point_2m',         label: 'Dew Point',       unit: '°C' },
      { key: 'pressure_msl',         label: 'Pressure (MSL)',  unit: 'hPa' },
      { key: 'surface_pressure',     label: 'Surface Press',   unit: 'hPa' },
    ],
  },
  {
    title: '🌧 Precipitation',
    fields: [
      { key: 'precipitation',  label: 'Precipitation', unit: 'mm' },
      { key: 'rain',           label: 'Rain',          unit: 'mm' },
      { key: 'snowfall',       label: 'Snowfall',      unit: 'cm' },
      { key: 'snow_depth',     label: 'Snow Depth',    unit: 'm' },
    ],
  },
  {
    title: '💨 Wind',
    fields: [
      { key: 'wind_speed_10m',     label: 'Wind (10m)',   unit: 'km/h' },
      { key: 'wind_speed_100m',    label: 'Wind (100m)',  unit: 'km/h' },
      { key: 'wind_gusts_10m',     label: 'Gusts',        unit: 'km/h' },
      { key: 'wind_direction_10m', label: 'Direction',   unit: '°' },
    ],
  },
  {
    title: '☀️ Radiation & UV',
    fields: [
      { key: 'uv_index',            label: 'UV Index',        unit: '' },
      { key: 'uv_index_clear_sky',  label: 'UV (Clear Sky)',  unit: '' },
      { key: 'shortwave_radiation', label: 'Solar Rad.',      unit: 'W/m²' },
      { key: 'cape',                label: 'CAPE',            unit: 'J/kg' },
      { key: 'cloud_cover',         label: 'Cloud Cover',     unit: '%' },
    ],
  },
  {
    title: '🌫 Air Quality',
    fields: [
      { key: 'pm10',             label: 'PM10',         unit: 'μg/m³' },
      { key: 'pm2_5',            label: 'PM2.5',        unit: 'μg/m³' },
      { key: 'ammonia',          label: 'NH₃',          unit: 'μg/m³' },
      { key: 'ozone',            label: 'O₃',           unit: 'μg/m³' },
      { key: 'nitrogen_dioxide', label: 'NO₂',          unit: 'μg/m³' },
      { key: 'carbon_monoxide',  label: 'CO',           unit: 'μg/m³' },
    ],
  },
  {
    title: '🌊 Marine',
    fields: [
      { key: 'wave_height',             label: 'Wave Height', unit: 'm' },
      { key: 'sea_surface_temperature', label: 'Sea Temp',    unit: '°C' },
    ],
  },
]

const CROPS = ['Rice', 'Wheat', 'Maize', 'Cotton', 'Sugarcane', 'Mustard']

const fmt = (val) => (val != null ? Number(val).toFixed(1) : '—')

export default function CityPanel({ city, onClose }) {
  const [weather, setWeather]       = useState(null)
  const [disaster, setDisaster]     = useState(null)
  const [advisory, setAdvisory]     = useState(null)
  const [selectedCrop, setSelectedCrop] = useState('rice')
  const [loading, setLoading]       = useState(false)
  const [agroLoading, setAgroLoading] = useState(false)

  // ── Load full prediction bundle for selected city ─────────────────────────
  useEffect(() => {
    if (!city?.city_id) return
    setLoading(true)
    Promise.all([
      getWeather(city.city_id).catch(() => null),
      getDisasterRisk(city.city_id).catch(() => null),
      getAdvisory(city.city_id, selectedCrop).catch(() => null),
    ]).then(([wx, dis, adv]) => {
      setWeather(wx)
      setDisaster(dis)
      setAdvisory(adv)
      setLoading(false)
    })
  }, [city?.city_id])

  // ── Reload agro advisory on crop switch ───────────────────────────────────
  const handleCropChange = (crop) => {
    const c = crop.toLowerCase()
    setSelectedCrop(c)
    if (!city?.city_id) return
    setAgroLoading(true)
    getAdvisory(city.city_id, c)
      .then((adv) => setAdvisory(adv))
      .catch(() => {})
      .finally(() => setAgroLoading(false))
  }

  const current = weather?.current || {}
  const forecast = weather?.forecast_1h || {}
  const agroPreds = advisory?.predictions || {}

  const riskScore = disaster?.risk_score ?? 0
  const severity = disaster?.severity || (riskScore > 0.8 ? 'extreme' : riskScore > 0.6 ? 'high' : riskScore > 0.3 ? 'moderate' : 'low')
  const severityColor =
    severity === 'extreme' ? '#ef4444' :
    severity === 'high' ? '#f97316' :
    severity === 'moderate' ? '#f59e0b' : '#10b981'

  const tempDiff = forecast.temperature_2m != null && current.temperature_2m != null
    ? (forecast.temperature_2m - current.temperature_2m)
    : null

  return (
    <AnimatePresence>
      {city && (
        <motion.div
          className="city-panel glass"
          style={{ width: '420px', maxWidth: '92vw', overflowY: 'auto', maxHeight: 'calc(100vh - 40px)' }}
          initial={{ opacity: 0, x: 40 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 40 }}
          transition={{ type: 'spring', stiffness: 280, damping: 28 }}
        >
          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                <span style={{ fontSize: '0.65rem', fontWeight: 800, color: 'var(--accent-teal)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                  AI / ML METEOROLOGICAL STATION
                </span>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#10b981', display: 'inline-block' }} />
              </div>
              <h2 style={{ margin: 0, fontSize: '1.4rem', fontWeight: 800 }}>{city.city_name}</h2>
              <div className="city-state" style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                {city.state || 'India'} • {city.latitude?.toFixed(2)}°N, {city.longitude?.toFixed(2)}°E
              </div>
            </div>
            <button
              onClick={onClose}
              style={{ background: 'rgba(255,255,255,0.06)', border: 'none', borderRadius: '50%', width: 28, height: 28, color: 'var(--text-muted)', cursor: 'pointer', fontSize: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            >✕</button>
          </div>

          {loading ? (
            <div style={{ textAlign: 'center', padding: '30px 0' }}>
              <div className="spinner" />
              <div style={{ marginTop: 8, fontSize: '0.78rem', color: 'var(--text-muted)' }}>Executing model inference engines...</div>
            </div>
          ) : (
            <>
              {/* ═══════════════════════════════════════════════════════════════ */}
              {/* ── 1. WEATHER MODEL PREDICTION (1-HOUR AHEAD) ──────────────── */}
              {/* ═══════════════════════════════════════════════════════════════ */}
              <div style={{
                marginTop: 14,
                padding: '12px 14px',
                borderRadius: 12,
                background: 'linear-gradient(135deg, rgba(20, 184, 166, 0.12), rgba(99, 102, 241, 0.08))',
                border: '1px solid rgba(20, 184, 166, 0.3)',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span style={{ fontSize: '0.68rem', fontWeight: 800, color: '#14b8a6', letterSpacing: '0.06em', display: 'flex', alignItems: 'center', gap: 4 }}>
                    🌦 1-HOUR WEATHER FORECAST (MODEL)
                  </span>
                  <span style={{ fontSize: '0.62rem', background: 'rgba(20,184,166,0.2)', color: '#14b8a6', padding: '2px 6px', borderRadius: 6, fontWeight: 700 }}>
                    ⚡ XGBOOST INFERENCE
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
                  <div className="feature-card" style={{ background: 'rgba(0,0,0,0.25)' }}>
                    <div className="f-label">Predicted Temp</div>
                    <div className="f-value" style={{ color: '#fbbf24', fontWeight: 800 }}>
                      {fmt(forecast.temperature_2m)}
                      <span className="f-unit"> °C</span>
                    </div>
                    {tempDiff != null && (
                      <div style={{ fontSize: '0.62rem', color: tempDiff >= 0 ? '#f87171' : '#60a5fa', marginTop: 2 }}>
                        {tempDiff >= 0 ? '▲ +' : '▼ '}{tempDiff.toFixed(1)}° vs now
                      </div>
                    )}
                  </div>

                  <div className="feature-card" style={{ background: 'rgba(0,0,0,0.25)' }}>
                    <div className="f-label">Predicted Rain</div>
                    <div className="f-value" style={{ color: '#60a5fa', fontWeight: 800 }}>
                      {fmt(forecast.precipitation)}
                      <span className="f-unit"> mm</span>
                    </div>
                    <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', marginTop: 2 }}>1h accumulation</div>
                  </div>

                  <div className="feature-card" style={{ background: 'rgba(0,0,0,0.25)' }}>
                    <div className="f-label">Predicted Wind</div>
                    <div className="f-value" style={{ color: '#34d399', fontWeight: 800 }}>
                      {fmt(forecast.wind_speed_10m)}
                      <span className="f-unit"> km/h</span>
                    </div>
                    <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', marginTop: 2 }}>10m altitude</div>
                  </div>

                  <div className="feature-card" style={{ background: 'rgba(0,0,0,0.25)' }}>
                    <div className="f-label">Humidity</div>
                    <div className="f-value">
                      {fmt(forecast.relative_humidity_2m)}
                      <span className="f-unit"> %</span>
                    </div>
                  </div>

                  <div className="feature-card" style={{ background: 'rgba(0,0,0,0.25)' }}>
                    <div className="f-label">Feels Like</div>
                    <div className="f-value">
                      {fmt(forecast.apparent_temperature)}
                      <span className="f-unit"> °C</span>
                    </div>
                  </div>

                  <div className="feature-card" style={{ background: 'rgba(0,0,0,0.25)' }}>
                    <div className="f-label">Surface Press</div>
                    <div className="f-value">
                      {fmt(forecast.surface_pressure)}
                      <span className="f-unit"> hPa</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* ═══════════════════════════════════════════════════════════════ */}
              {/* ── 2. DISASTER RISK PREDICTION (3-HOUR LEAD) ───────────────── */}
              {/* ═══════════════════════════════════════════════════════════════ */}
              {disaster && (
                <div style={{
                  marginTop: 12,
                  padding: '12px 14px',
                  borderRadius: 12,
                  background: severity === 'extreme' || severity === 'high'
                    ? 'linear-gradient(135deg, rgba(239,68,68,0.15), rgba(249,115,22,0.1))'
                    : 'rgba(16, 185, 129, 0.08)',
                  border: `1px solid ${severityColor}44`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.68rem', fontWeight: 800, color: severityColor, letterSpacing: '0.06em' }}>
                      🚨 3-HOUR DISASTER RISK PREDICTION
                    </span>
                    <span style={{
                      fontSize: '0.62rem',
                      fontWeight: 800,
                      background: `${severityColor}22`,
                      color: severityColor,
                      border: `1px solid ${severityColor}`,
                      padding: '2px 8px',
                      borderRadius: 10,
                      letterSpacing: '0.05em',
                    }}>
                      {severity.toUpperCase()} RISK
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 8 }}>
                    <div>
                      <div style={{ fontSize: '0.92rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                        {disaster.disaster_type && disaster.disaster_type !== 'none'
                          ? disaster.disaster_type.replace(/_/g, ' ').toUpperCase()
                          : 'Nominal (No Extreme Threat)'}
                      </div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        Lead Time: +{disaster.lead_hours || 3.0} Hours • Classifier Confidence
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: '1.2rem', fontWeight: 800, color: severityColor }}>
                        {(riskScore * 100).toFixed(1)}%
                      </div>
                      <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)' }}>Risk Probability</div>
                    </div>
                  </div>

                  {/* Progress bar */}
                  <div style={{ width: '100%', height: 4, background: 'rgba(255,255,255,0.08)', borderRadius: 2, marginTop: 8, overflow: 'hidden' }}>
                    <div style={{ width: `${Math.min(Math.max(riskScore * 100, 4), 100)}%`, height: '100%', background: severityColor }} />
                  </div>

                  <div style={{ marginTop: 8, fontSize: '0.75rem', color: 'var(--text-primary)', lineHeight: 1.4, background: 'rgba(0,0,0,0.2)', padding: '6px 8px', borderRadius: 6 }}>
                    🛡 {disaster.recommended_action || 'Atmospheric conditions stable. Standard observation active.'}
                  </div>
                </div>
              )}

              {/* ═══════════════════════════════════════════════════════════════ */}
              {/* ── 3. AGRO CROP WEATHER ADVISORY (MODEL) ───────────────────── */}
              {/* ═══════════════════════════════════════════════════════════════ */}
              <div style={{
                marginTop: 12,
                padding: '12px 14px',
                borderRadius: 12,
                background: 'rgba(34,211,160,0.06)',
                border: '1px solid rgba(34,211,160,0.25)',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span style={{ fontSize: '0.68rem', color: 'var(--accent-green)', fontWeight: 800, letterSpacing: '0.06em' }}>
                    🌾 CROP INTELLIGENCE & ADVISORY (MODEL)
                  </span>
                  <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)' }}>
                    Stage: <strong style={{ color: 'var(--text-primary)' }}>{advisory?.growth_stage || 'Vegetative'}</strong>
                  </span>
                </div>

                {/* Crop selector chips */}
                <div style={{ display: 'flex', gap: 5, overflowX: 'auto', paddingBottom: 6, marginBottom: 8 }}>
                  {CROPS.map((c) => {
                    const active = selectedCrop === c.toLowerCase()
                    return (
                      <button
                        key={c}
                        onClick={() => handleCropChange(c)}
                        style={{
                          background: active ? 'var(--accent-green)' : 'rgba(255,255,255,0.06)',
                          color: active ? '#0a0f1e' : 'var(--text-muted)',
                          border: 'none',
                          borderRadius: 12,
                          padding: '3px 9px',
                          fontSize: '0.68rem',
                          fontWeight: active ? 700 : 500,
                          cursor: 'pointer',
                          whiteSpace: 'nowrap',
                          transition: 'all 0.15s',
                        }}
                      >
                        {c}
                      </button>
                    )
                  })}
                </div>

                {agroLoading ? (
                  <div style={{ textAlign: 'center', padding: '10px 0' }}><div className="spinner" style={{ width: 18, height: 18 }} /></div>
                ) : advisory ? (
                  <>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6, marginBottom: 8 }}>
                      <div style={{ background: 'rgba(0,0,0,0.25)', padding: '6px 8px', borderRadius: 8 }}>
                        <div style={{ fontSize: '0.58rem', color: 'var(--text-muted)' }}>Weather Risk</div>
                        <div style={{ fontSize: '0.75rem', fontWeight: 800, color: agroPreds.crop_weather_risk === 'HIGH' ? '#ef4444' : '#10b981' }}>
                          {agroPreds.crop_weather_risk || advisory.advisory_label || 'LOW'}
                        </div>
                      </div>

                      <div style={{ background: 'rgba(0,0,0,0.25)', padding: '6px 8px', borderRadius: 8 }}>
                        <div style={{ fontSize: '0.58rem', color: 'var(--text-muted)' }}>Irrigation</div>
                        <div style={{ fontSize: '0.75rem', fontWeight: 800, color: agroPreds.irrigation === 'IRRIGATE' ? '#f59e0b' : '#34d399' }}>
                          {agroPreds.irrigation || 'NORMAL'}
                        </div>
                      </div>

                      <div style={{ background: 'rgba(0,0,0,0.25)', padding: '6px 8px', borderRadius: 8 }}>
                        <div style={{ fontSize: '0.58rem', color: 'var(--text-muted)' }}>Spraying Safe</div>
                        <div style={{ fontSize: '0.75rem', fontWeight: 800, color: agroPreds.spraying_suitability === 'UNSAFE' ? '#f87171' : '#10b981' }}>
                          {agroPreds.spraying_suitability || 'SAFE'}
                        </div>
                      </div>
                    </div>

                    <div style={{ fontSize: '0.74rem', color: 'var(--text-primary)', lineHeight: 1.45, background: 'rgba(0,0,0,0.2)', padding: '8px 10px', borderRadius: 8 }}>
                      {advisory.advisory_text}
                    </div>
                  </>
                ) : null}
              </div>

              {/* ═══════════════════════════════════════════════════════════════ */}
              {/* ── 4. DETAILED 39-FEATURE SENSOR OBSERVATIONS ───────────────── */}
              {/* ═══════════════════════════════════════════════════════════════ */}
              <div style={{ marginTop: 18, borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: 14 }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 10 }}>
                  📡 Current Observations (39 Meteorological Sensors)
                </div>

                {FEATURE_GROUPS.map((group) => {
                  const hasData = group.fields.some(f => current[f.key] != null)
                  if (!hasData) return null
                  return (
                    <div key={group.title} style={{ marginBottom: 12 }}>
                      <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: 6, fontWeight: 600, letterSpacing: '0.06em' }}>
                        {group.title}
                      </div>
                      <div className="feature-grid">
                        {group.fields.map((f) => (
                          current[f.key] != null && (
                            <div key={f.key} className="feature-card">
                              <div className="f-label">{f.label}</div>
                              <div className="f-value">
                                {fmt(current[f.key])}
                                <span className="f-unit"> {f.unit}</span>
                              </div>
                            </div>
                          )
                        ))}
                      </div>
                    </div>
                  )
                })}
              </div>
            </>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  )
}
