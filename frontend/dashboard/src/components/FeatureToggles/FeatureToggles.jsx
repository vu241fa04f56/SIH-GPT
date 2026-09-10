// FeatureToggles.jsx — Layer toggle sidebar buttons

import { motion } from 'framer-motion'

const FEATURES = [
  { id: 'wind',         label: 'Wind Speed',   icon: '💨' },
  { id: 'rain',         label: 'Rainfall',      icon: '🌧' },
  { id: 'temperature',  label: 'Temperature',   icon: '🌡' },
  { id: 'uv',           label: 'UV Index',      icon: '☀️' },
  { id: 'aqi',          label: 'Air Quality',   icon: '🌫' },
  { id: 'cyclone',      label: 'Cyclone',       icon: '🌀' },
  { id: 'flood',        label: 'Flood',         icon: '🌊' },
  { id: 'earthquake',   label: 'Earthquake',    icon: '📊' },
  { id: 'lightning',    label: 'Lightning',     icon: '⚡' },
]

export default function FeatureToggles({ activeLayer, onToggle }) {
  return (
    <motion.div
      className="toggle-sidebar glass"
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay: 0.2 }}
    >
      <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: 6, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
        Layers
      </div>
      {FEATURES.map((feat) => (
        <button
          key={feat.id}
          className={`toggle-btn ${activeLayer === feat.id ? 'active' : ''}`}
          onClick={() => onToggle(feat.id)}
          id={`toggle-${feat.id}`}
        >
          <span className="toggle-icon">{feat.icon}</span>
          {feat.label}
        </button>
      ))}
    </motion.div>
  )
}
