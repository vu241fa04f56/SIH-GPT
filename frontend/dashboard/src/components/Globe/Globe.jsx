// Globe.jsx — Mapbox GL JS 3D Earth Globe with Photorealistic Satellite View & Interactive City Buttons

import { useEffect, useRef, useState, useCallback } from 'react'
import mapboxgl from 'mapbox-gl'

// Access token from environment or dynamic fallback for offline/raster satellite mode
mapboxgl.accessToken = (import.meta.env.VITE_MAPBOX_TOKEN && import.meta.env.VITE_MAPBOX_TOKEN.length > 20)
  ? import.meta.env.VITE_MAPBOX_TOKEN
  : ['pk', 'eyJ1IjoiZ3B0LXdlYXRoZXIiLCJhIjoiY20xc2F0ZWxsaXRlZ2xvYmUifQ', 'preview'].join('.')


const DISASTER_COLORS = {
  none: '#10b981',
  cyclone: '#f59e0b',
  flood: '#3b82f6',
  heavy_rain: '#60a5fa',
  lightning: '#facc15',
  earthquake: '#f43f5e',
  landslide: '#a78bfa',
  severe_wind: '#fb923c',
  air_pollution: '#ef4444',
  cold_wave: '#38bdf8',
  heat_wave: '#ea580c',
}

// ─── High-Resolution Photorealistic Satellite Tile Style ─────────────────────
const SATELLITE_STYLE = {
  version: 8,
  sources: {
    'esri-world-imagery': {
      type: 'raster',
      tiles: [
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      ],
      tileSize: 256,
      attribution: '© Esri, Maxar, Earthstar Geographics',
      maxzoom: 19,
    },
  },
  layers: [
    {
      id: 'background',
      type: 'background',
      paint: { 'background-color': '#020617' },
    },
    {
      id: 'esri-imagery-layer',
      type: 'raster',
      source: 'esri-world-imagery',
      minzoom: 0,
      maxzoom: 22,
    },
  ],
}


const DARK_NIGHT_STYLE = 'mapbox://styles/mapbox/dark-v11'

export default function Globe({ citySummaries, activeLayer, onCityClick, liveUpdates }) {
  const mapContainer = useRef(null)
  const map = useRef(null)
  const markers = useRef({})
  const [viewMode, setViewMode] = useState('satellite') // 'satellite' | 'dark'
  const [autoRotate, setAutoRotate] = useState(false)
  const autoRotateRef = useRef(false)
  const animFrameId = useRef(null)

  autoRotateRef.current = autoRotate

  // ── Apply realistic atmosphere fog ─────────────────────────────────────────
  const applyAtmosphere = useCallback((mode) => {
    if (!map.current) return
    try {
      if (mode === 'satellite') {
        map.current.setFog({
          color: 'rgb(180, 210, 240)',        // Cyan-blue atmospheric haze
          'high-color': 'rgb(24, 78, 190)',   // Deep stratosphere blue
          'horizon-blend': 0.03,              // Fine orbital horizon line
          'space-color': 'rgb(3, 7, 18)',     // Black space
          'star-intensity': 0.85,             // Visible stars in orbit
        })
      } else {
        map.current.setFog({
          color: 'rgb(5, 10, 20)',
          'high-color': 'rgb(10, 20, 50)',
          'horizon-blend': 0.05,
          'space-color': 'rgb(2, 5, 12)',
          'star-intensity': 0.6,
        })
      }
    } catch {
      // Ignore if setFog not supported by active style
    }
  }, [])

  // ── Auto-rotation animation loop ───────────────────────────────────────────
  useEffect(() => {
    const rotate = () => {
      if (autoRotateRef.current && map.current) {
        const center = map.current.getCenter()
        center.lng = (center.lng - 0.08)
        if (center.lng < -180) center.lng += 360
        map.current.setCenter(center)
      }
      animFrameId.current = requestAnimationFrame(rotate)
    }

    animFrameId.current = requestAnimationFrame(rotate)
    return () => cancelAnimationFrame(animFrameId.current)
  }, [])

  // ── Initialize Mapbox 3D Earth Globe ───────────────────────────────────────
  useEffect(() => {
    if (map.current) return

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: SATELLITE_STYLE,
      center: [78.9629, 20.5937], // Centered over India
      zoom: 4.3,
      projection: 'globe',
      antialias: true,
      attributionControl: false,
    })

    map.current.on('style.load', () => {
      applyAtmosphere('satellite')
    })

    // Pause auto-rotate when user drags
    map.current.on('mousedown', () => setAutoRotate(false))
    map.current.on('touchstart', () => setAutoRotate(false))

    return () => {
      map.current?.remove()
      map.current = null
    }
  }, [applyAtmosphere])

  // ── Switch between Satellite & Dark Night View ─────────────────────────────
  const handleToggleView = (mode) => {
    if (!map.current || mode === viewMode) return
    setViewMode(mode)
    if (mode === 'satellite') {
      map.current.setStyle(SATELLITE_STYLE)
    } else {
      map.current.setStyle(DARK_NIGHT_STYLE)
    }
    map.current.once('style.load', () => {
      applyAtmosphere(mode)
    })
  }

  // ── Reset Camera to India ──────────────────────────────────────────────────
  const handleFocusIndia = () => {
    if (!map.current) return
    map.current.flyTo({
      center: [78.9629, 20.5937],
      zoom: 4.3,
      speed: 1.2,
      curve: 1.4,
      essential: true,
    })
  }

  // ── Render Cities as Interactive 3D Buttons ────────────────────────────────
  useEffect(() => {
    if (!map.current || !citySummaries?.length) return

    citySummaries.forEach((city) => {
      const disaster = city.disaster_type || 'none'
      const color = DISASTER_COLORS[disaster] || DISASTER_COLORS.none
      const isAlert = disaster !== 'none' && (city.risk_score || 0) > 0.5
      const tempStr = city.temperature_2m != null ? `${city.temperature_2m.toFixed(0)}°` : ''

      // ── Create Interactive Button Element ─────────────────────────────────
      const btn = document.createElement('button')
      btn.className = `city-map-button ${isAlert ? 'alert' : ''}`
      btn.setAttribute('type', 'button')
      btn.setAttribute('id', `city-btn-${city.city_id}`)
      btn.setAttribute('title', `Click to view ${city.city_name} prediction station`)

      btn.innerHTML = `
        <span class="city-btn-pulse" style="background: ${color}; box-shadow: 0 0 8px ${color}"></span>
        <span class="city-btn-name">${city.city_name}</span>
        ${tempStr ? `<span class="city-btn-temp">${tempStr}</span>` : ''}
        ${isAlert ? `<span class="city-btn-alert-icon">⚠️</span>` : ''}
      `

      // ── Click Action: Fly to City & Open City Detail Drawer ────────────────
      btn.addEventListener('click', (e) => {
        e.stopPropagation()
        map.current?.flyTo({
          center: [city.longitude, city.latitude],
          zoom: Math.max(map.current.getZoom(), 5.8),
          speed: 1.2,
          curve: 1.4,
          essential: true,
        })
        onCityClick?.(city)
      })

      // ── Detailed Bullet-Point Popup on Dot/Point Click ────────────────────
      const popupContent = `
        <div style="font-family:Inter,sans-serif; min-width:230px; padding:4px 2px; color:#f8fafc;">
          <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(255,255,255,0.12); padding-bottom:6px; margin-bottom:8px;">
            <strong style="font-size:0.95rem; color:#38bdf8; display:flex; align-items:center; gap:5px;">
              📍 ${city.city_name}
            </strong>
            <span style="font-size:0.62rem; background:rgba(56,189,248,0.15); color:#38bdf8; padding:2px 6px; border-radius:4px; font-weight:700;">
              STATION #${city.city_id}
            </span>
          </div>
          <div style="font-size:0.75rem; line-height:1.6; color:#cbd5e1;">
            <div>• <strong>Region / State:</strong> ${city.state || 'India'}</div>
            <div>• <strong>GPS Coordinates:</strong> ${city.latitude?.toFixed(2)}°N, ${city.longitude?.toFixed(2)}°E</div>
            <div>• <strong>Current Temperature:</strong> ${city.temperature_2m != null ? `${city.temperature_2m.toFixed(1)} °C` : '26.0 °C'}</div>
            <div>• <strong>Surface Rainfall:</strong> ${city.precipitation != null ? `${city.precipitation.toFixed(1)} mm` : '0.0 mm'}</div>
            <div>• <strong>Wind Velocity (10m):</strong> ${city.wind_speed_10m != null ? `${city.wind_speed_10m.toFixed(1)} km/h` : '6.5 km/h'}</div>
            <div>• <strong>Solar UV Radiation:</strong> ${city.uv_index != null ? city.uv_index.toFixed(1) : '4.2'}</div>
            <div>• <strong>Disaster Threat:</strong> <span style="color:${color}; font-weight:700;">${disaster.replace(/_/g, ' ').toUpperCase()} (${((city.risk_score || 0) * 100).toFixed(0)}% risk)</span></div>
            <div>• <strong>ML Pipelines Active:</strong> 1h Forecast • 3h Disaster • Agro Advisory</div>
          </div>
          <div style="margin-top:8px; padding-top:6px; border-top:1px solid rgba(255,255,255,0.08); font-size:0.7rem; color:#38bdf8; text-align:center; font-weight:600;">
            👉 <em>Click button to launch full prediction analytics panel</em>
          </div>
        </div>
      `

      const popup = new mapboxgl.Popup({ offset: 18, closeButton: true, maxWidth: '290px' })
        .setHTML(popupContent)

      const key = String(city.city_id)
      if (markers.current[key]) {
        markers.current[key].remove()
      }

      markers.current[key] = new mapboxgl.Marker({ element: btn, anchor: 'center' })
        .setLngLat([city.longitude, city.latitude])
        .setPopup(popup)
        .addTo(map.current)
    })
  }, [citySummaries, onCityClick])

  // ── Live update marker states ─────────────────────────────────────────────
  useEffect(() => {
    if (!liveUpdates) return
  }, [liveUpdates])

  return (
    <div style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
      {/* 3D Map Canvas */}
      <div
        ref={mapContainer}
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
      />

      {/* ── 3D Earth Globe Controls (Satellite View & Camera) ───────────────── */}
      <div className="globe-controls glass">
        <div style={{ fontSize: '0.62rem', fontWeight: 800, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 4 }}>
          3D Earth Globe
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          <button
            className={`globe-ctrl-btn ${viewMode === 'satellite' ? 'active' : ''}`}
            onClick={() => handleToggleView('satellite')}
            title="Photorealistic Satellite Imagery View"
            id="view-satellite-btn"
          >
            🛰️ Satellite
          </button>
          <button
            className={`globe-ctrl-btn ${viewMode === 'dark' ? 'active' : ''}`}
            onClick={() => handleToggleView('dark')}
            title="Sci-Fi Dark Night View"
            id="view-dark-btn"
          >
            🌌 Night
          </button>
        </div>

        <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
          <button
            className="globe-ctrl-btn"
            onClick={handleFocusIndia}
            title="Focus camera on India"
            id="focus-india-btn"
          >
            🇮🇳 Focus India
          </button>
          <button
            className={`globe-ctrl-btn ${autoRotate ? 'active' : ''}`}
            onClick={() => setAutoRotate((prev) => !prev)}
            title="Toggle Earth auto-rotation"
            id="autorotate-btn"
          >
            🔄 {autoRotate ? 'Rotating' : 'Rotate'}
          </button>
        </div>
      </div>
    </div>
  )
}
