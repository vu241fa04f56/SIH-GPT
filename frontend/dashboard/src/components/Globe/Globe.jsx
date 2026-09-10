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

      const key = String(city.city_id)
      if (markers.current[key]) {
        markers.current[key].remove()
      }
      markers.current[key] = new mapboxgl.Marker({ element: el })
        .setLngLat([city.longitude, city.latitude])
        .setPopup(
          new mapboxgl.Popup({ offset: 12, closeButton: false }).setHTML(`
            <div style="font-family:Inter,sans-serif">
              <strong style="font-size:0.85rem">${city.city_name}</strong><br/>
              <span style="color:#64748b;font-size:0.72rem">
                ${city.temperature_2m != null ? `🌡 ${city.temperature_2m.toFixed(1)}°C` : ''}
                ${city.precipitation != null ? `  🌧 ${city.precipitation.toFixed(1)}mm` : ''}
              </span>
              ${isAlert ? `<br/><span style="color:#f43f5e;font-size:0.72rem;font-weight:600">⚠ ${disaster.replace('_',' ')}</span>` : ''}
            </div>
          `)
        )
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
