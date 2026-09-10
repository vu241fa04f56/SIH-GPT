// App.jsx — Root application component

import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'

import Globe from './components/Globe/Globe'
import FeatureToggles from './components/FeatureToggles/FeatureToggles'
import CityPanel from './components/CityPanel/CityPanel'
import ChatInterface from './components/ChatInterface/ChatInterface'
import AlertBanner from './components/AlertBanner/AlertBanner'

import { useGeolocation } from './hooks/useGeolocation'
import { useWebSocket } from './hooks/useWebSocket'
import { getWeatherSummary, getDisasterOverlay } from './services/apiClient'

export default function App() {
  const { location } = useGeolocation()
  const [citySummaries, setCitySummaries] = useState([])
  const [activeLayer, setActiveLayer] = useState('temperature')
  const [selectedCity, setSelectedCity] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [liveUpdates, setLiveUpdates] = useState(null)
  const [dataLoading, setDataLoading] = useState(true)

  // ── Load initial city data ────────────────────────────────────────────────
  useEffect(() => {
    Promise.all([
      getWeatherSummary().catch(() => []),
      getDisasterOverlay().catch(() => ({ cities: [] })),
    ]).then(([summaries, disasterData]) => {
      const disasterMap = {}
      ;(disasterData?.cities || []).forEach((d) => {
        disasterMap[d.city_id] = d
      })

      const merged = summaries.map((s) => ({
        ...s,
        disaster_type: disasterMap[s.city_id]?.disaster_type || 'none',
        risk_score: disasterMap[s.city_id]?.risk_score || 0,
      }))

      setCitySummaries(merged)

      // Surface high-risk cities as alerts
      const highRisk = merged.filter((c) => c.risk_score > 0.6 && c.disaster_type !== 'none')
      if (highRisk.length) setAlerts(highRisk)

      setDataLoading(false)
    })
  }, [])

  // ── WebSocket live updates ─────────────────────────────────────────────────
  useWebSocket(useCallback((data) => {
    setLiveUpdates(data)
    if (data.type === 'weather_update') {
      setCitySummaries((prev) =>
        prev.map((c) =>
          c.city_id === data.city_id
            ? { ...c, temperature_2m: data.temperature_2m, precipitation: data.precipitation }
            : c
        )
      )
    }
    if (data.type === 'disaster_alert') {
      setAlerts((prev) => [...prev, data])
    }
  }, []))

  const handleLayerToggle = (layer) => {
    setActiveLayer((prev) => (prev === layer ? null : layer))
  }

  return (
    <div className="app-wrapper">
      {/* 3D Globe */}
      <Globe
        citySummaries={citySummaries}
        activeLayer={activeLayer}
        onCityClick={setSelectedCity}
        liveUpdates={liveUpdates}
      />

      {/* Header */}
      <motion.div
        className="header glass"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <span className="header-logo">⛈ WeatherGPT</span>
        <span className="header-badge">LIVE</span>
        {dataLoading && (
          <div className="spinner" style={{ marginLeft: 8 }} />
        )}
        {location && (
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            📍 {location.lat.toFixed(3)}°N {location.lon.toFixed(3)}°E
          </span>
        )}
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
          {citySummaries.length} cities
        </span>
      </motion.div>

      {/* Feature Toggles */}
      <FeatureToggles activeLayer={activeLayer} onToggle={handleLayerToggle} />

      {/* Alert Banner */}
      <AlertBanner alerts={alerts} />

      {/* City Detail Panel */}
      <CityPanel city={selectedCity} onClose={() => setSelectedCity(null)} />

      {/* Chatbot */}
      <ChatInterface userLocation={location} />
    </div>
  )
}
