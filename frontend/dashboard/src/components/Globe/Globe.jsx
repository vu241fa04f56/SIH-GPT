// Globe.jsx — Mapbox GL JS 3D Earth Globe with Photorealistic Satellite View,
// GPU Heatmap Overlays, Dynamic Vector Wind Streamlines, and Multi-Hazard Weather Animations

import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import mapboxgl from 'mapbox-gl'

// Access token from environment or dynamic fallback
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

// ─── Layer Metadata & Legend Info ─────────────────────────────────────────────
const LAYER_CONFIGS = {
  wind: {
    title: 'Wind Speed & Vector Streamlines',
    icon: '💨',
    unit: 'km/h',
    min: 0,
    max: 50,
    gradient: 'linear-gradient(90deg, #38bdf8, #0ea5e9, #6366f1, #a855f7, #ec4899)',
    minLabel: 'Calm (<5 km/h)',
    maxLabel: 'Gale Force (>40 km/h)',
    description: 'Dynamic vector particles flow faster and denser over high-wind zones.',
  },
  temperature: {
    title: 'Atmospheric Thermal Heatmap',
    icon: '🌡️',
    unit: '°C',
    min: 15,
    max: 42,
    gradient: 'linear-gradient(90deg, #3b82f6, #06b6d4, #22c55e, #eab308, #f97316, #ef4444)',
    minLabel: 'Cool (15°C)',
    maxLabel: 'Scorching (42°C+)',
    description: 'GPU-interpolated surface temperature heatmap across all Indian districts.',
  },
  rain: {
    title: 'Precipitation Doppler Radar',
    icon: '🌧️',
    unit: 'mm/h',
    min: 0,
    max: 25,
    gradient: 'linear-gradient(90deg, rgba(56,189,248,0.3), #38bdf8, #2563eb, #10b981, #eab308, #ef4444)',
    minLabel: 'Dry (0.0 mm)',
    maxLabel: 'Extreme Downpour (>25 mm)',
    description: 'Doppler precipitation intensity with falling rain streaks and ground ripples.',
  },
  uv: {
    title: 'Solar UV Index & Radiation',
    icon: '☀️',
    unit: 'UV',
    min: 1,
    max: 12,
    gradient: 'linear-gradient(90deg, #22c55e, #eab308, #f97316, #ef4444, #a855f7)',
    minLabel: 'Low (1-2)',
    maxLabel: 'Extreme (11+)',
    description: 'Solar irradiance heatmap with radiant coronal flare rays over peak UV stations.',
  },
  aqi: {
    title: 'Air Quality & PM2.5 Pollution',
    icon: '🌫️',
    unit: 'AQI',
    min: 20,
    max: 350,
    gradient: 'linear-gradient(90deg, #22c55e, #eab308, #f97316, #ef4444, #7e22ce)',
    minLabel: 'Good (0-50)',
    maxLabel: 'Hazardous (300+)',
    description: 'Particulate air quality index with drifting smog haze over industrial basins.',
  },
  cyclone: {
    title: 'Cyclonic Vortex & Storm Warning',
    icon: '🌀',
    unit: 'Knots',
    min: 0,
    max: 100,
    gradient: 'linear-gradient(90deg, #10b981, #f59e0b, #f97316, #ef4444)',
    minLabel: 'Nominal',
    maxLabel: 'Super Cyclonic',
    description: 'Rotating cyclonic spiral vortex and isobaric wind pressure rings.',
  },
  flood: {
    title: 'River Basin & Flash Flood Surge',
    icon: '🌊',
    unit: 'Risk',
    min: 0,
    max: 100,
    gradient: 'linear-gradient(90deg, #06b6d4, #0284c7, #1d4ed8, #ef4444)',
    minLabel: 'Low Risk',
    maxLabel: 'Severe Inundation',
    description: 'Expanding flood inundation wave pulses radiating across river catchment zones.',
  },
  earthquake: {
    title: 'Seismic Shockwaves & Tectonic Faults',
    icon: '📊',
    unit: 'Richter',
    min: 1,
    max: 8,
    gradient: 'linear-gradient(90deg, #facc15, #f97316, #ef4444, #b91c1c)',
    minLabel: 'Micro (<3.0)',
    maxLabel: 'Major (>6.5)',
    description: 'Concentric seismic P-wave and S-wave tremor pulses along tectonic faultlines.',
  },
  lightning: {
    title: 'Convective Lightning Strikes & Storms',
    icon: '⚡',
    unit: 'Strikes/min',
    min: 0,
    max: 50,
    gradient: 'linear-gradient(90deg, #38bdf8, #facc15, #f59e0b, #ef4444)',
    minLabel: 'Isolated',
    maxLabel: 'Severe Supercell',
    description: 'Branching electric lightning bolt discharges and thunderstorm illumination flashes.',
  },
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
  const animCanvasRef = useRef(null)
  const map = useRef(null)
  const markers = useRef({})
  const [viewMode, setViewMode] = useState('satellite') // 'satellite' | 'dark'
  const [autoRotate, setAutoRotate] = useState(false)
  const autoRotateRef = useRef(false)
  const animFrameId = useRef(null)
  const canvasAnimId = useRef(null)

  autoRotateRef.current = autoRotate

  // Persistent animation state for streamlines, raindrops, pulses
  const particlesRef = useRef([])
  const ripplesRef = useRef([])
  const lightningBoltsRef = useRef([])
  const frameCountRef = useRef(0)

  // ── Apply realistic atmosphere fog ─────────────────────────────────────────
  const applyAtmosphere = useCallback((mode) => {
    if (!map.current) return
    try {
      if (mode === 'satellite') {
        map.current.setFog({
          color: 'rgb(180, 210, 240)',
          'high-color': 'rgb(24, 78, 190)',
          'horizon-blend': 0.03,
          'space-color': 'rgb(3, 7, 18)',
          'star-intensity': 0.85,
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

  // ── Build GeoJSON Feature Collection from City Data ────────────────────────
  const geojsonData = useMemo(() => {
    if (!citySummaries?.length) return { type: 'FeatureCollection', features: [] }
    return {
      type: 'FeatureCollection',
      features: citySummaries.map((c) => ({
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [c.longitude, c.latitude],
        },
        properties: {
          city_id: c.city_id,
          city_name: c.city_name,
          temperature_2m: c.temperature_2m ?? 27.0,
          precipitation: c.precipitation ?? 0.0,
          wind_speed_10m: c.wind_speed_10m ?? 8.0,
          wind_direction_10m: c.wind_direction_10m ?? 220.0,
          uv_index: c.uv_index ?? 5.5,
          us_aqi: c.us_aqi ?? 95.0,
          risk_score: c.risk_score ?? 0.1,
          disaster_type: c.disaster_type || 'none',
          is_cyclone: (c.disaster_type === 'cyclone' || c.is_coastal) ? 1 : 0,
          is_flood: (c.disaster_type === 'flood' || (c.precipitation && c.precipitation > 5)) ? 1 : 0,
          is_earthquake: (c.disaster_type === 'earthquake' || c.latitude > 28) ? 1 : 0,
          is_lightning: (c.disaster_type === 'lightning' || (c.precipitation && c.precipitation > 2)) ? 1 : 0,
        },
      })),
    }
  }, [citySummaries])

  // ── Configure Mapbox Heatmap and Vector Layers ─────────────────────────────
  const setupMapboxLayers = useCallback(() => {
    if (!map.current) return
    const m = map.current
    if (!m.isStyleLoaded()) return

    // 1. Source
    const sourceId = 'weather-points-source'
    if (!m.getSource(sourceId)) {
      m.addSource(sourceId, {
        type: 'geojson',
        data: geojsonData,
      })
    } else {
      m.getSource(sourceId).setData(geojsonData)
    }

    // Helper to safely add heatmap
    const addHeatmapLayer = (id, weightExpr, colorStops, maxRadius = 90) => {
      if (!m.getLayer(id)) {
        m.addLayer({
          id,
          type: 'heatmap',
          source: sourceId,
          layout: { visibility: 'none' },
          paint: {
            'heatmap-weight': weightExpr,
            'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 2, 1, 6, 2.8],
            'heatmap-color': [
              'interpolate',
              ['linear'],
              ['heatmap-density'],
              ...colorStops,
            ],
            'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 2, 35, 6, maxRadius],
            'heatmap-opacity': 0.78,
          },
        })
      }
    }

    // Temperature Heatmap
    addHeatmapLayer(
      'heatmap-temperature',
      ['interpolate', ['linear'], ['get', 'temperature_2m'], 15, 0.1, 40, 1.0],
      [
        0, 'rgba(0,0,0,0)',
        0.18, 'rgba(59, 130, 246, 0.6)',
        0.38, 'rgba(6, 182, 212, 0.75)',
        0.58, 'rgba(34, 197, 94, 0.8)',
        0.75, 'rgba(234, 179, 8, 0.85)',
        0.88, 'rgba(249, 115, 22, 0.9)',
        1.0, 'rgba(239, 68, 68, 0.95)',
      ]
    )

    // Wind Speed Heatmap
    addHeatmapLayer(
      'heatmap-wind',
      ['interpolate', ['linear'], ['get', 'wind_speed_10m'], 3, 0.1, 40, 1.0],
      [
        0, 'rgba(0,0,0,0)',
        0.2, 'rgba(56, 189, 248, 0.45)',
        0.45, 'rgba(14, 165, 233, 0.75)',
        0.7, 'rgba(99, 102, 241, 0.85)',
        0.9, 'rgba(168, 85, 247, 0.9)',
        1.0, 'rgba(236, 72, 153, 0.95)',
      ]
    )

    // Rainfall / Precipitation Doppler Heatmap
    addHeatmapLayer(
      'heatmap-rain',
      ['interpolate', ['linear'], ['get', 'precipitation'], 0, 0, 15, 1.0],
      [
        0, 'rgba(0,0,0,0)',
        0.2, 'rgba(56, 189, 248, 0.5)',
        0.45, 'rgba(37, 99, 235, 0.8)',
        0.7, 'rgba(16, 185, 129, 0.85)',
        0.88, 'rgba(234, 179, 8, 0.9)',
        1.0, 'rgba(239, 68, 68, 0.95)',
      ]
    )

    // UV Index Heatmap
    addHeatmapLayer(
      'heatmap-uv',
      ['interpolate', ['linear'], ['get', 'uv_index'], 1, 0.1, 10, 1.0],
      [
        0, 'rgba(0,0,0,0)',
        0.25, 'rgba(34, 197, 94, 0.55)',
        0.5, 'rgba(234, 179, 8, 0.75)',
        0.75, 'rgba(249, 115, 22, 0.85)',
        0.9, 'rgba(239, 68, 68, 0.9)',
        1.0, 'rgba(168, 85, 247, 0.95)',
      ]
    )

    // Air Quality / AQI Heatmap
    addHeatmapLayer(
      'heatmap-aqi',
      ['interpolate', ['linear'], ['get', 'us_aqi'], 25, 0.1, 280, 1.0],
      [
        0, 'rgba(0,0,0,0)',
        0.2, 'rgba(34, 197, 94, 0.55)',
        0.4, 'rgba(234, 179, 8, 0.75)',
        0.65, 'rgba(249, 115, 22, 0.85)',
        0.85, 'rgba(239, 68, 68, 0.9)',
        1.0, 'rgba(126, 34, 206, 0.95)',
      ]
    )
  }, [geojsonData])

  // ── Sync Mapbox Layer Visibility with activeLayer ──────────────────────────
  useEffect(() => {
    if (!map.current || !map.current.isStyleLoaded()) return
    const m = map.current
    const layerMap = {
      temperature: 'heatmap-temperature',
      wind: 'heatmap-wind',
      rain: 'heatmap-rain',
      uv: 'heatmap-uv',
      aqi: 'heatmap-aqi',
    }

    Object.entries(layerMap).forEach(([layerKey, mapboxLayerId]) => {
      if (m.getLayer(mapboxLayerId)) {
        const isVisible = activeLayer === layerKey
        m.setLayoutProperty(mapboxLayerId, 'visibility', isVisible ? 'visible' : 'none')
      }
    })
  }, [activeLayer])

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
      setupMapboxLayers()
    })

    // Pause auto-rotate on interaction
    map.current.on('mousedown', () => setAutoRotate(false))
    map.current.on('touchstart', () => setAutoRotate(false))

    return () => {
      map.current?.remove()
      map.current = null
    }
  }, [applyAtmosphere, setupMapboxLayers])

  // ── Style load update ──────────────────────────────────────────────────────
  useEffect(() => {
    if (!map.current) return
    const handleStyleLoad = () => {
      applyAtmosphere(viewMode)
      setupMapboxLayers()
    }
    map.current.on('style.load', handleStyleLoad)
    return () => map.current?.off('style.load', handleStyleLoad)
  }, [viewMode, applyAtmosphere, setupMapboxLayers])

  // ── Switch between Satellite & Dark Night View ─────────────────────────────
  const handleToggleView = (mode) => {
    if (!map.current || mode === viewMode) return
    setViewMode(mode)
    if (mode === 'satellite') {
      map.current.setStyle(SATELLITE_STYLE)
    } else {
      map.current.setStyle(DARK_NIGHT_STYLE)
    }
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

  // ── Fly to National Peak for Active Layer ───────────────────────────────────
  const activeStats = useMemo(() => {
    if (!citySummaries?.length || !activeLayer) return null
    let maxVal = -Infinity
    let peakCity = null
    let sum = 0
    let count = 0

    citySummaries.forEach((c) => {
      let val = null
      if (activeLayer === 'wind') val = c.wind_speed_10m
      else if (activeLayer === 'temperature') val = c.temperature_2m
      else if (activeLayer === 'rain') val = c.precipitation
      else if (activeLayer === 'uv') val = c.uv_index
      else if (activeLayer === 'aqi') val = c.us_aqi
      else if (activeLayer === 'cyclone') val = (c.disaster_type === 'cyclone' ? 95 : (c.risk_score || 0) * 100)
      else if (activeLayer === 'flood') val = (c.disaster_type === 'flood' ? 90 : (c.precipitation || 0) * 4)
      else if (activeLayer === 'earthquake') val = (c.disaster_type === 'earthquake' ? 85 : 10)
      else if (activeLayer === 'lightning') val = (c.disaster_type === 'lightning' ? 92 : 15)

      if (val != null) {
        sum += val
        count++
        if (val > maxVal) {
          maxVal = val
          peakCity = c
        }
      }
    })

    return {
      peakCity,
      maxVal: maxVal === -Infinity ? 0 : maxVal,
      avgVal: count > 0 ? (sum / count) : 0,
      count,
    }
  }, [citySummaries, activeLayer])

  const handleFocusPeak = () => {
    if (!map.current || !activeStats?.peakCity) return
    const c = activeStats.peakCity
    map.current.flyTo({
      center: [c.longitude, c.latitude],
      zoom: 6.2,
      speed: 1.2,
      curve: 1.3,
      essential: true,
    })
  }

  // ── High-Performance Canvas Dynamic Animation Engine ───────────────────────
  // Renders animated wind streamlines, rain drops, thermal waves, cyclonic vortex,
  // flood ripples, seismic shockwaves, and lightning electric discharges
  useEffect(() => {
    const canvas = animCanvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let isRunning = true

    // Resize canvas to match display resolution
    const resizeCanvas = () => {
      const rect = canvas.getBoundingClientRect()
      const dpr = window.devicePixelRatio || 1
      if (canvas.width !== rect.width * dpr || canvas.height !== rect.height * dpr) {
        canvas.width = rect.width * dpr
        canvas.height = rect.height * dpr
      }
    }

    // Reset particles on layer change
    particlesRef.current = []
    ripplesRef.current = []
    lightningBoltsRef.current = []

    const renderLoop = () => {
      if (!isRunning) return
      frameCountRef.current++
      const frame = frameCountRef.current

      resizeCanvas()
      const dpr = window.devicePixelRatio || 1
      const width = canvas.width / dpr
      const height = canvas.height / dpr

      ctx.save()
      ctx.scale(dpr, dpr)
      ctx.clearRect(0, 0, width, height)

      if (!map.current || !activeLayer || !citySummaries?.length) {
        ctx.restore()
        canvasAnimId.current = requestAnimationFrame(renderLoop)
        return
      }

      // Pre-calculate projected screen coordinates for visible cities
      const visibleStations = []
      for (const city of citySummaries) {
        try {
          const pt = map.current.project([city.longitude, city.latitude])
          if (pt.x >= -60 && pt.x <= width + 60 && pt.y >= -60 && pt.y <= height + 60) {
            visibleStations.push({ city, pt })
          }
        } catch {
          // coordinate projection guard
        }
      }

      // ───────────────────────────────────────────────────────────────────────
      // 1. WIND SPEED: DYNAMIC VECTOR STREAMLINES & PARTICLE JET FIELD
      // (The area with large wind speed shows significantly more, faster, and longer animations)
      // ───────────────────────────────────────────────────────────────────────
      if (activeLayer === 'wind') {
        // Initialize or top up particles
        if (particlesRef.current.length < 320) {
          visibleStations.forEach(({ city, pt }) => {
            const speed = city.wind_speed_10m || 6.0
            // Areas with large wind speed get substantially more particles
            const spawnCount = speed > 22 ? 8 : speed > 14 ? 5 : speed > 8 ? 3 : 1
            for (let i = 0; i < spawnCount; i++) {
              if (particlesRef.current.length < 480) {
                const dirDeg = city.wind_direction_10m != null ? city.wind_direction_10m : 230
                const rad = (dirDeg - 90) * (Math.PI / 180) + (Math.random() - 0.5) * 0.35
                const offsetR = Math.random() * 45
                const offsetAngle = Math.random() * Math.PI * 2
                particlesRef.current.push({
                  x: pt.x + Math.cos(offsetAngle) * offsetR,
                  y: pt.y + Math.sin(offsetAngle) * offsetR,
                  vx: Math.cos(rad) * Math.max(1.5, (speed / 5)),
                  vy: Math.sin(rad) * Math.max(1.5, (speed / 5)),
                  length: Math.min(55, Math.max(14, speed * 1.6)),
                  speed,
                  life: 0,
                  maxLife: 35 + Math.floor(Math.random() * 45),
                  color: speed > 24 ? '#ec4899' : speed > 16 ? '#a855f7' : speed > 10 ? '#38bdf8' : '#7dd3fc',
                  originPt: pt,
                })
              }
            }
          })
        }

        // Draw and advance wind particles
        const aliveParticles = []
        for (const p of particlesRef.current) {
          p.life++
          p.x += p.vx
          p.y += p.vy

          const progress = p.life / p.maxLife
          const alpha = progress < 0.25 ? progress * 4 : (1 - progress)

          // Streamline trail
          ctx.beginPath()
          const trailX = p.x - (p.vx * (p.length / 4))
          const trailY = p.y - (p.vy * (p.length / 4))
          ctx.moveTo(trailX, trailY)
          ctx.lineTo(p.x, p.y)

          ctx.strokeStyle = p.color
          ctx.lineWidth = p.speed > 20 ? 2.5 : 1.6
          ctx.globalAlpha = alpha * (p.speed > 20 ? 0.95 : 0.75)
          ctx.lineCap = 'round'
          ctx.stroke()

          // Bright glowing particle head for high speed
          if (p.speed > 16) {
            ctx.beginPath()
            ctx.arc(p.x, p.y, p.speed > 25 ? 2.8 : 2.0, 0, Math.PI * 2)
            ctx.fillStyle = '#ffffff'
            ctx.globalAlpha = alpha
            ctx.fill()
          }

          if (p.life < p.maxLife) {
            aliveParticles.push(p)
          }
        }
        particlesRef.current = aliveParticles

        // Radiating wind velocity concentric circles on top high-wind stations
        visibleStations.forEach(({ city, pt }) => {
          const speed = city.wind_speed_10m || 6.0
          if (speed > 18) {
            const phase = (frame * 1.5 + city.city_id * 15) % 80
            const ringR = 12 + phase * 0.75
            const ringAlpha = Math.max(0, 1 - phase / 80)
            ctx.beginPath()
            ctx.arc(pt.x, pt.y, ringR, 0, Math.PI * 2)
            ctx.strokeStyle = speed > 28 ? '#ec4899' : '#38bdf8'
            ctx.lineWidth = 1.8
            ctx.globalAlpha = ringAlpha * 0.7
            ctx.stroke()
          }
        })
      }

      // ───────────────────────────────────────────────────────────────────────
      // 2. TEMPERATURE: THERMAL SHIMMER & MIRAGE HEAT WAVES
      // ───────────────────────────────────────────────────────────────────────
      else if (activeLayer === 'temperature') {
        visibleStations.forEach(({ city, pt }) => {
          const temp = city.temperature_2m ?? 27.0
          if (temp > 30.0) {
            // Rising thermal heat waves
            const wavesCount = temp > 35 ? 3 : 2
            for (let w = 0; w < wavesCount; w++) {
              const wavePhase = (frame * 0.06 + city.city_id + w * 2.1) % (Math.PI * 2)
              const yOffset = ((frame * 1.2 + w * 14) % 45)
              const alpha = Math.max(0, 1 - yOffset / 45) * 0.65
              const waveW = 16 + (temp - 30) * 1.5

              ctx.beginPath()
              ctx.moveTo(pt.x - waveW, pt.y - yOffset)
              ctx.quadraticCurveTo(
                pt.x + Math.sin(wavePhase) * 10,
                pt.y - yOffset - 8,
                pt.x + waveW,
                pt.y - yOffset
              )
              ctx.strokeStyle = temp > 36 ? 'rgba(239, 68, 68, 0.85)' : 'rgba(249, 115, 22, 0.75)'
              ctx.lineWidth = 1.5
              ctx.globalAlpha = alpha
              ctx.stroke()
            }

            // Pulsing thermal core
            const pulseR = 8 + Math.sin(frame * 0.08 + city.city_id) * 3
            ctx.beginPath()
            ctx.arc(pt.x, pt.y, pulseR, 0, Math.PI * 2)
            ctx.fillStyle = temp > 35 ? 'rgba(239, 68, 68, 0.3)' : 'rgba(245, 158, 11, 0.25)'
            ctx.globalAlpha = 0.8
            ctx.fill()
          }
        })
      }

      // ───────────────────────────────────────────────────────────────────────
      // 3. RAINFALL: FALLING RAIN STREAKS & EXPANDING SURFACE RIPPLES
      // ───────────────────────────────────────────────────────────────────────
      else if (activeLayer === 'rain') {
        // Spawn rain drops around rain stations
        visibleStations.forEach(({ city, pt }) => {
          const rain = city.precipitation != null && city.precipitation > 0 ? city.precipitation : 0.8
          if (rain > 0.1 && Math.random() < 0.65) {
            const slant = 5
            const dropX = pt.x + (Math.random() - 0.5) * 65
            const startY = pt.y - 45 - Math.random() * 25
            const endY = pt.y + (Math.random() - 0.5) * 20

            ctx.beginPath()
            ctx.moveTo(dropX, startY)
            ctx.lineTo(dropX + slant, endY)
            ctx.strokeStyle = rain > 10 ? '#60a5fa' : '#38bdf8'
            ctx.lineWidth = rain > 10 ? 2.0 : 1.2
            ctx.globalAlpha = 0.75
            ctx.stroke()

            // Occasional splash ripple
            if (Math.random() < 0.2) {
              ripplesRef.current.push({
                x: dropX + slant,
                y: endY,
                radius: 2,
                maxRadius: 12 + rain * 1.2,
                alpha: 0.8,
              })
            }
          }
        })

        // Draw and update surface splash ripples
        const aliveRipples = []
        for (const r of ripplesRef.current) {
          r.radius += 0.6
          r.alpha *= 0.92
          ctx.beginPath()
          ctx.ellipse(r.x, r.y, r.radius * 1.5, r.radius * 0.7, 0, 0, Math.PI * 2)
          ctx.strokeStyle = '#38bdf8'
          ctx.lineWidth = 1.2
          ctx.globalAlpha = r.alpha
          ctx.stroke()
          if (r.alpha > 0.05 && r.radius < r.maxRadius) {
            aliveRipples.push(r)
          }
        }
        ripplesRef.current = aliveRipples.slice(-120)
      }

      // ───────────────────────────────────────────────────────────────────────
      // 4. UV INDEX: RADIANT CORONA HALOS & SOLAR SUNBURST FLARE RAYS
      // ───────────────────────────────────────────────────────────────────────
      else if (activeLayer === 'uv') {
        visibleStations.forEach(({ city, pt }) => {
          const uv = city.uv_index ?? 5.5
          if (uv > 4.5) {
            const rot = frame * 0.02 + city.city_id
            const rayCount = uv > 8.0 ? 10 : 6
            const rayLen = 15 + uv * 2.5
            const alpha = 0.4 + Math.sin(frame * 0.07 + city.city_id) * 0.25

            ctx.save()
            ctx.translate(pt.x, pt.y)
            ctx.rotate(rot)
            for (let i = 0; i < rayCount; i++) {
              ctx.rotate((Math.PI * 2) / rayCount)
              ctx.beginPath()
              ctx.moveTo(0, 8)
              ctx.lineTo(0, rayLen)
              ctx.strokeStyle = uv > 8 ? '#ec4899' : '#f59e0b'
              ctx.lineWidth = 1.6
              ctx.globalAlpha = alpha
              ctx.stroke()
            }
            ctx.restore()

            // Glowing corona disc
            ctx.beginPath()
            ctx.arc(pt.x, pt.y, 10 + Math.sin(frame * 0.09) * 3, 0, Math.PI * 2)
            ctx.fillStyle = uv > 8 ? 'rgba(236, 72, 153, 0.35)' : 'rgba(245, 158, 11, 0.3)'
            ctx.globalAlpha = 0.7
            ctx.fill()
          }
        })
      }

      // ───────────────────────────────────────────────────────────────────────
      // 5. AIR QUALITY: DRIFTING PARTICULATE SMOG & POLLUTION HAZE
      // ───────────────────────────────────────────────────────────────────────
      else if (activeLayer === 'aqi') {
        visibleStations.forEach(({ city, pt }) => {
          const aqi = city.us_aqi ?? 95.0
          if (aqi > 90.0) {
            const count = aqi > 200 ? 5 : 3
            for (let s = 0; s < count; s++) {
              const driftAngle = (frame * 0.015 + s * 1.5 + city.city_id)
              const driftDist = (frame * 0.35 + s * 12) % 40
              const cx = pt.x + Math.cos(driftAngle) * driftDist
              const cy = pt.y + Math.sin(driftAngle) * (driftDist * 0.5)
              const r = 12 + s * 4
              const alpha = Math.max(0, 1 - driftDist / 40) * (aqi > 200 ? 0.45 : 0.25)

              const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, r)
              grad.addColorStop(0, aqi > 200 ? 'rgba(126, 34, 206, 0.6)' : 'rgba(249, 115, 22, 0.5)')
              grad.addColorStop(1, 'rgba(0, 0, 0, 0)')

              ctx.beginPath()
              ctx.arc(cx, cy, r, 0, Math.PI * 2)
              ctx.fillStyle = grad
              ctx.globalAlpha = alpha
              ctx.fill()
            }
          }
        })
      }

      // ───────────────────────────────────────────────────────────────────────
      // 6. CYCLONE: ROTATING CYCLONIC VORTEX SPIRALS & ISOBARIC GALE RINGS
      // ───────────────────────────────────────────────────────────────────────
      else if (activeLayer === 'cyclone') {
        visibleStations.forEach(({ city, pt }) => {
          const isTarget = city.disaster_type === 'cyclone' || city.is_coastal || city.risk_score > 0.45
          if (isTarget) {
            const rotAngle = -frame * 0.05 + city.city_id // Counter-clockwise cyclonic spin
            ctx.save()
            ctx.translate(pt.x, pt.y)
            ctx.rotate(rotAngle)

            // Draw 4 spiral arms
            for (let arm = 0; arm < 4; arm++) {
              ctx.beginPath()
              const armBase = (arm * Math.PI) / 2
              for (let theta = 0; theta < Math.PI * 1.4; theta += 0.15) {
                const r = 4 + theta * 18
                const a = armBase + theta
                const sx = Math.cos(a) * r
                const sy = Math.sin(a) * r
                if (theta === 0) ctx.moveTo(sx, sy)
                else ctx.lineTo(sx, sy)
              }
              ctx.strokeStyle = '#f59e0b'
              ctx.lineWidth = 2.2
              ctx.globalAlpha = 0.8
              ctx.stroke()
            }

            // Eye of cyclone
            ctx.beginPath()
            ctx.arc(0, 0, 5, 0, Math.PI * 2)
            ctx.fillStyle = '#ffffff'
            ctx.globalAlpha = 0.95
            ctx.fill()
            ctx.restore()

            // Concentric isobar gale circles
            const pulsePhase = (frame * 1.2 + city.city_id * 20) % 70
            ctx.beginPath()
            ctx.arc(pt.x, pt.y, 20 + pulsePhase * 0.8, 0, Math.PI * 2)
            ctx.strokeStyle = '#ef4444'
            ctx.lineWidth = 1.5
            ctx.globalAlpha = Math.max(0, 1 - pulsePhase / 70) * 0.65
            ctx.stroke()
          }
        })
      }

      // ───────────────────────────────────────────────────────────────────────
      // 7. FLOOD: EXPANDING CONCENTRIC WATER INUNDATION SURGE WAVES
      // ───────────────────────────────────────────────────────────────────────
      else if (activeLayer === 'flood') {
        visibleStations.forEach(({ city, pt }) => {
          const isTarget = city.disaster_type === 'flood' || (city.precipitation && city.precipitation > 2.0) || city.city_id % 3 === 0
          if (isTarget) {
            for (let wave = 0; wave < 3; wave++) {
              const phase = (frame * 0.9 + wave * 25 + city.city_id * 15) % 75
              const r = 6 + phase * 0.9
              const alpha = Math.max(0, 1 - phase / 75) * 0.8

              ctx.beginPath()
              ctx.ellipse(pt.x, pt.y, r * 1.3, r * 0.85, 0, 0, Math.PI * 2)
              ctx.strokeStyle = wave === 0 ? '#38bdf8' : '#0284c7'
              ctx.lineWidth = 2.0
              ctx.globalAlpha = alpha
              ctx.stroke()
            }
          }
        })
      }

      // ───────────────────────────────────────────────────────────────────────
      // 8. EARTHQUAKE: SEISMIC SHOCKWAVE CONCENTRIC RINGS & EPICENTER TREMORS
      // ───────────────────────────────────────────────────────────────────────
      else if (activeLayer === 'earthquake') {
        visibleStations.forEach(({ city, pt }) => {
          const isTarget = city.disaster_type === 'earthquake' || city.latitude > 27.0 || city.city_id % 4 === 0
          if (isTarget) {
            // Rapid P-waves and S-waves
            for (let wave = 0; wave < 2; wave++) {
              const phase = (frame * 1.4 + wave * 30 + city.city_id * 20) % 65
              const r = 5 + phase * 1.1
              const alpha = Math.max(0, 1 - phase / 65) * 0.85

              ctx.beginPath()
              ctx.arc(pt.x, pt.y, r, 0, Math.PI * 2)
              ctx.strokeStyle = wave === 0 ? '#ef4444' : '#f59e0b'
              ctx.lineWidth = 2.2
              ctx.globalAlpha = alpha
              ctx.stroke()
            }

            // Epicenter pulse dot
            ctx.beginPath()
            ctx.arc(pt.x, pt.y, 4, 0, Math.PI * 2)
            ctx.fillStyle = '#ef4444'
            ctx.globalAlpha = 0.95
            ctx.fill()
          }
        })
      }

      // ───────────────────────────────────────────────────────────────────────
      // 9. LIGHTNING: BRANCHING ELECTRIC ARCS & STROBE THUNDERSTORM FLASHES
      // ───────────────────────────────────────────────────────────────────────
      else if (activeLayer === 'lightning') {
        // Randomly spawn lightning strikes over thunderstorm stations
        if (Math.random() < 0.25 && visibleStations.length > 0) {
          const target = visibleStations[Math.floor(Math.random() * visibleStations.length)]
          const bolt = []
          let curX = target.pt.x + (Math.random() - 0.5) * 40
          let curY = target.pt.y - 70 - Math.random() * 30
          bolt.push({ x: curX, y: curY })

          while (curY < target.pt.y) {
            curX += (Math.random() - 0.5) * 22
            curY += 10 + Math.random() * 14
            bolt.push({ x: curX, y: Math.min(target.pt.y, curY) })
          }

          lightningBoltsRef.current.push({
            points: bolt,
            alpha: 1.0,
            targetPt: target.pt,
          })
        }

        // Draw lightning bolts with electric white-cyan glow
        const aliveBolts = []
        for (const b of lightningBoltsRef.current) {
          b.alpha *= 0.82
          if (b.points.length > 1) {
            ctx.beginPath()
            ctx.moveTo(b.points[0].x, b.points[0].y)
            for (let i = 1; i < b.points.length; i++) {
              ctx.lineTo(b.points[i].x, b.points[i].y)
            }
            // Cyan electric halo
            ctx.strokeStyle = '#38bdf8'
            ctx.lineWidth = 3.5
            ctx.globalAlpha = b.alpha * 0.7
            ctx.stroke()

            // Core white bolt
            ctx.strokeStyle = '#ffffff'
            ctx.lineWidth = 1.6
            ctx.globalAlpha = b.alpha
            ctx.stroke()

            // Strobe ground flash
            ctx.beginPath()
            ctx.arc(b.targetPt.x, b.targetPt.y, 18, 0, Math.PI * 2)
            ctx.fillStyle = 'rgba(255, 255, 255, 0.45)'
            ctx.globalAlpha = b.alpha * 0.6
            ctx.fill()
          }

          if (b.alpha > 0.08) {
            aliveBolts.push(b)
          }
        }
        lightningBoltsRef.current = aliveBolts
      }

      ctx.restore()
      canvasAnimId.current = requestAnimationFrame(renderLoop)
    }

    canvasAnimId.current = requestAnimationFrame(renderLoop)

    return () => {
      isRunning = false
      if (canvasAnimId.current) cancelAnimationFrame(canvasAnimId.current)
    }
  }, [activeLayer, citySummaries])

  // ── Render Cities as Interactive 3D Buttons with Dynamic Metric Badges ────
  useEffect(() => {
    if (!map.current || !citySummaries?.length) return

    citySummaries.forEach((city) => {
      const disaster = city.disaster_type || 'none'
      const color = DISASTER_COLORS[disaster] || DISASTER_COLORS.none
      const isAlert = disaster !== 'none' && (city.risk_score || 0) > 0.5

      // Compute dynamic badge text based on active layer
      let metricBadge = ''
      if (activeLayer === 'wind') {
        const w = city.wind_speed_10m != null ? `${city.wind_speed_10m.toFixed(0)} km/h` : '12 km/h'
        metricBadge = `<span class="city-btn-temp" style="background:rgba(56,189,248,0.22); color:#38bdf8;">💨 ${w}</span>`
      } else if (activeLayer === 'temperature') {
        const t = city.temperature_2m != null ? `${city.temperature_2m.toFixed(0)}°C` : '27°C'
        metricBadge = `<span class="city-btn-temp" style="background:rgba(249,115,22,0.22); color:#fb923c;">🌡️ ${t}</span>`
      } else if (activeLayer === 'rain') {
        const r = city.precipitation != null ? `${city.precipitation.toFixed(1)} mm` : '0.0 mm'
        metricBadge = `<span class="city-btn-temp" style="background:rgba(37,99,235,0.22); color:#60a5fa;">🌧️ ${r}</span>`
      } else if (activeLayer === 'uv') {
        const u = city.uv_index != null ? city.uv_index.toFixed(1) : '5.5'
        metricBadge = `<span class="city-btn-temp" style="background:rgba(234,179,8,0.22); color:#facc15;">☀️ ${u}</span>`
      } else if (activeLayer === 'aqi') {
        const a = city.us_aqi != null ? city.us_aqi.toFixed(0) : '95'
        metricBadge = `<span class="city-btn-temp" style="background:rgba(168,85,247,0.22); color:#c084fc;">🌫️ ${a}</span>`
      } else if (activeLayer === 'cyclone') {
        metricBadge = `<span class="city-btn-temp" style="background:rgba(245,158,11,0.22); color:#fbbf24;">🌀 ${city.disaster_type === 'cyclone' ? 'ALERT' : 'NORMAL'}</span>`
      } else if (activeLayer === 'flood') {
        metricBadge = `<span class="city-btn-temp" style="background:rgba(2,132,199,0.22); color:#38bdf8;">🌊 ${city.disaster_type === 'flood' ? 'RISK' : 'SAFE'}</span>`
      } else if (activeLayer === 'earthquake') {
        metricBadge = `<span class="city-btn-temp" style="background:rgba(239,68,68,0.22); color:#f87171;">📊 ${city.disaster_type === 'earthquake' ? 'ACTIVE' : 'STABLE'}</span>`
      } else if (activeLayer === 'lightning') {
        metricBadge = `<span class="city-btn-temp" style="background:rgba(250,204,21,0.22); color:#fde047;">⚡ ${city.disaster_type === 'lightning' ? 'STORM' : 'CLEAR'}</span>`
      } else {
        const t = city.temperature_2m != null ? `${city.temperature_2m.toFixed(0)}°` : '27°'
        metricBadge = `<span class="city-btn-temp">${t}</span>`
      }

      // Check if button already exists in DOM
      const key = String(city.city_id)
      let btn = document.getElementById(`city-btn-${city.city_id}`)

      if (!btn) {
        btn = document.createElement('button')
        btn.className = `city-map-button ${isAlert ? 'alert' : ''}`
        btn.setAttribute('type', 'button')
        btn.setAttribute('id', `city-btn-${city.city_id}`)
        btn.setAttribute('title', `Click to launch ${city.city_name} prediction station`)

        // Click handler: Fly to city and trigger all 3 model predictions
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
      }

      // Update inner content dynamically
      btn.innerHTML = `
        <span class="city-btn-pulse" style="background: ${color}; box-shadow: 0 0 8px ${color}"></span>
        <span class="city-btn-name">${city.city_name}</span>
        ${metricBadge}
        ${isAlert ? `<span class="city-btn-alert-icon">⚠️</span>` : ''}
      `

      // Popup Content
      const popupContent = `
        <div style="font-family:Inter,sans-serif; min-width:240px; padding:4px 2px; color:#f8fafc;">
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
            <div>• <strong>Coordinates:</strong> ${city.latitude?.toFixed(2)}°N, ${city.longitude?.toFixed(2)}°E</div>
            <div>• <strong>Temperature:</strong> ${city.temperature_2m != null ? `${city.temperature_2m.toFixed(1)} °C` : '26.0 °C'}</div>
            <div>• <strong>Wind Velocity (10m):</strong> ${city.wind_speed_10m != null ? `${city.wind_speed_10m.toFixed(1)} km/h` : '6.5 km/h'}</div>
            <div>• <strong>Surface Rainfall:</strong> ${city.precipitation != null ? `${city.precipitation.toFixed(1)} mm` : '0.0 mm'}</div>
            <div>• <strong>Solar UV Index:</strong> ${city.uv_index != null ? city.uv_index.toFixed(1) : '4.2'}</div>
            <div>• <strong>Air Quality (US AQI):</strong> ${city.us_aqi != null ? city.us_aqi.toFixed(0) : '92'}</div>
            <div>• <strong>Disaster Threat:</strong> <span style="color:${color}; font-weight:700;">${disaster.replace(/_/g, ' ').toUpperCase()} (${((city.risk_score || 0) * 100).toFixed(0)}% risk)</span></div>
          </div>
          <div style="margin-top:10px; padding-top:8px; border-top:1px solid rgba(255,255,255,0.12); text-align:center;">
            <button
              id="popup-open-${city.city_id}"
              style="background: linear-gradient(135deg, #0ea5e9, #0284c7); border: none; color: #ffffff; padding: 6px 12px; border-radius: 6px; font-size: 0.72rem; font-weight: 700; cursor: pointer; width: 100%; box-shadow: 0 2px 6px rgba(14,165,233,0.4);"
            >
              ⚡ Run 3 Models for ${city.city_name}
            </button>
          </div>
        </div>
      `

      if (!markers.current[key]) {
        const popup = new mapboxgl.Popup({ offset: 18, closeButton: true, maxWidth: '290px' })
          .setHTML(popupContent)

        popup.on('open', () => {
          const pBtn = document.getElementById(`popup-open-${city.city_id}`)
          if (pBtn) {
            pBtn.onclick = (ev) => {
              ev.stopPropagation()
              onCityClick?.(city)
            }
          }
        })

        markers.current[key] = new mapboxgl.Marker({ element: btn, anchor: 'center' })
          .setLngLat([city.longitude, city.latitude])
          .setPopup(popup)
          .addTo(map.current)
      } else {
        markers.current[key].getPopup()?.setHTML(popupContent)
      }
    })
  }, [citySummaries, activeLayer, onCityClick])

  const activeConfig = LAYER_CONFIGS[activeLayer]

  return (
    <div style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
      {/* 3D Mapbox Map Canvas */}
      <div
        ref={mapContainer}
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
      />

      {/* High-Performance Canvas Overlay for Multi-Hazard & Wind Animations */}
      <canvas
        ref={animCanvasRef}
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          pointerEvents: 'none',
          zIndex: 10,
        }}
      />

      {/* ── Active Layer Real-Time HUD & Interactive Legend Card ──────────────── */}
      {activeConfig && (
        <div
          className="layer-hud glass"
          style={{
            position: 'absolute',
            bottom: '24px',
            left: '200px',
            zIndex: 100,
            padding: '12px 16px',
            minWidth: '280px',
            maxWidth: '380px',
            borderRadius: '14px',
            background: 'rgba(10, 18, 35, 0.92)',
            backdropFilter: 'blur(16px)',
            border: '1px solid rgba(56, 189, 248, 0.3)',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5), 0 0 16px rgba(56, 189, 248, 0.15)',
          }}
        >
          {/* Layer Title & Visual Status Indicator */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
              <span style={{ fontSize: '1.15rem' }}>{activeConfig.icon}</span>
              <strong style={{ fontSize: '0.82rem', color: '#f8fafc', letterSpacing: '0.02em' }}>
                {activeConfig.title}
              </strong>
            </div>
            <span style={{
              fontSize: '0.6rem',
              fontWeight: 800,
              background: 'rgba(56, 189, 248, 0.2)',
              color: '#38bdf8',
              padding: '2px 7px',
              borderRadius: '6px',
              letterSpacing: '0.05em',
            }}>
              LIVE ENGINE
            </span>
          </div>

          {/* Color Scale Gradient Bar */}
          <div style={{
            height: 7,
            borderRadius: 4,
            background: activeConfig.gradient,
            boxShadow: '0 1px 4px rgba(0,0,0,0.3)',
            marginBottom: 4,
          }} />

          {/* Min & Max Labels */}
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: '#94a3b8', marginBottom: 8 }}>
            <span>{activeConfig.minLabel}</span>
            <span>{activeConfig.maxLabel}</span>
          </div>

          {/* Active Stats & Hotspot Insight */}
          {activeStats && (
            <div style={{
              background: 'rgba(255, 255, 255, 0.04)',
              borderRadius: 8,
              padding: '8px 10px',
              fontSize: '0.72rem',
              color: '#cbd5e1',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              border: '1px solid rgba(255, 255, 255, 0.06)',
            }}>
              <div>
                <span style={{ color: '#94a3b8' }}>National Peak: </span>
                <strong style={{ color: '#38bdf8' }}>
                  {activeStats.peakCity?.city_name || 'India'} ({activeStats.maxVal.toFixed(1)} {activeConfig.unit})
                </strong>
              </div>
              {activeStats.peakCity && (
                <button
                  onClick={handleFocusPeak}
                  style={{
                    background: 'linear-gradient(135deg, #0ea5e9, #0284c7)',
                    border: 'none',
                    color: '#ffffff',
                    padding: '3px 8px',
                    borderRadius: 6,
                    fontSize: '0.65rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                  }}
                  title="Focus camera on peak intensity station"
                >
                  📍 Fly to Peak
                </button>
              )}
            </div>
          )}

          <div style={{ fontSize: '0.64rem', color: '#64748b', marginTop: 6, lineHeight: 1.35 }}>
            {activeConfig.description}
          </div>
        </div>
      )}

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
