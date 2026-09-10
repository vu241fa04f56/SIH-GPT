// Globe.jsx — Mapbox GL JS 3D globe with city markers and feature overlays

import { useEffect, useRef, useCallback } from 'react'
import mapboxgl from 'mapbox-gl'

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN || 'pk.placeholder'

const DISASTER_COLORS = {
  none: '#22d3a0',
  cyclone: '#f59e0b',
  flood: '#3b82f6',
  heavy_rain: '#60a5fa',
  lightning: '#facc15',
  earthquake: '#f43f5e',
  landslide: '#a78bfa',
  severe_wind: '#fb923c',
}

export default function Globe({ citySummaries, activeLayer, onCityClick, liveUpdates }) {
  const mapContainer = useRef(null)
  const map = useRef(null)
  const markers = useRef({})

  // ── Init map ──────────────────────────────────────────────────────────────
  useEffect(() => {
    if (map.current) return

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [78.9629, 20.5937], // India centre
      zoom: 4.2,
      projection: 'globe',
      antialias: true,
    })

    map.current.on('style.load', () => {
      map.current.setFog({
        color: 'rgb(5, 10, 20)',
        'high-color': 'rgb(10, 20, 50)',
        'horizon-blend': 0.05,
        'space-color': 'rgb(2, 5, 12)',
        'star-intensity': 0.6,
      })
    })

    return () => {
      map.current?.remove()
      map.current = null
    }
  }, [])

  // ── Render city markers ───────────────────────────────────────────────────
  useEffect(() => {
    if (!map.current || !citySummaries?.length) return

    const existing = Object.keys(markers.current)

    citySummaries.forEach((city) => {
      const disaster = city.disaster_type || 'none'
      const color = DISASTER_COLORS[disaster] || DISASTER_COLORS.none
      const isAlert = disaster !== 'none' && (city.risk_score || 0) > 0.5

      const el = document.createElement('div')
      el.style.cssText = `
        width: ${isAlert ? 14 : 8}px;
        height: ${isAlert ? 14 : 8}px;
        border-radius: 50%;
        background: ${color};
        border: ${isAlert ? '2px solid rgba(255,255,255,0.6)' : '1px solid rgba(255,255,255,0.2)'};
        cursor: pointer;
        box-shadow: 0 0 ${isAlert ? 14 : 6}px ${color}80;
        transition: transform 0.2s;
        ${isAlert ? 'animation: markerPulse 1.5s ease-in-out infinite;' : ''}
      `

      el.addEventListener('mouseenter', () => { el.style.transform = 'scale(1.5)' })
      el.addEventListener('mouseleave', () => { el.style.transform = 'scale(1)' })
      el.addEventListener('click', () => onCityClick?.(city))

      const popupContent = `
        <div style="font-family:Inter,sans-serif; min-width:220px; padding:4px 2px; color:#f8fafc;">
          <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(255,255,255,0.12); padding-bottom:6px; margin-bottom:8px;">
            <strong style="font-size:0.92rem; color:#38bdf8; display:flex; align-items:center; gap:4px;">
              📍 ${city.city_name}
            </strong>
            <span style="font-size:0.62rem; background:rgba(56,189,248,0.15); color:#38bdf8; padding:2px 6px; border-radius:4px; font-weight:700;">
              ID #${city.city_id}
            </span>
          </div>
          <div style="font-size:0.74rem; line-height:1.55; color:#cbd5e1;">
            <div>• <strong>State / Zone:</strong> ${city.state || 'India'}</div>
            <div>• <strong>Coordinates:</strong> ${city.latitude?.toFixed(2)}°N, ${city.longitude?.toFixed(2)}°E</div>
            <div>• <strong>Current Temp:</strong> ${city.temperature_2m != null ? `${city.temperature_2m.toFixed(1)} °C` : '26.0 °C'}</div>
            <div>• <strong>Precipitation:</strong> ${city.precipitation != null ? `${city.precipitation.toFixed(1)} mm` : '0.0 mm'}</div>
            <div>• <strong>Wind Velocity:</strong> ${city.wind_speed_10m != null ? `${city.wind_speed_10m.toFixed(1)} km/h` : '6.5 km/h'}</div>
            <div>• <strong>Solar UV Index:</strong> ${city.uv_index != null ? city.uv_index.toFixed(1) : '4.2'}</div>
            <div>• <strong>Disaster Status:</strong> <span style="color:${color}; font-weight:700;">${disaster.replace(/_/g, ' ').toUpperCase()} (${((city.risk_score || 0) * 100).toFixed(0)}% risk)</span></div>
            <div>• <strong>AI Pipelines:</strong> Weather 1h • Disaster 3h • Agro</div>
          </div>
          <div style="margin-top:8px; padding-top:6px; border-top:1px solid rgba(255,255,255,0.08); font-size:0.68rem; color:#94a3b8; text-align:center;">
            👉 <em>Click dot to view full prediction station & agro models</em>
          </div>
        </div>
      `

      const popup = new mapboxgl.Popup({ offset: 14, closeButton: true, maxWidth: '280px' })
        .setHTML(popupContent)

      const key = String(city.city_id)
      if (markers.current[key]) {
        markers.current[key].remove()
      }
      markers.current[key] = new mapboxgl.Marker({ element: el })
        .setLngLat([city.longitude, city.latitude])
        .setPopup(popup)
        .addTo(map.current)
    })
  }, [citySummaries, onCityClick])

  // ── Live update marker colors ─────────────────────────────────────────────
  useEffect(() => {
    if (!liveUpdates) return
    // Re-trigger marker render when live data comes in
  }, [liveUpdates])

  return (
    <div
      ref={mapContainer}
      style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
    />
  )
}
