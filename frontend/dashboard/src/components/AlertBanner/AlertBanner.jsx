// AlertBanner.jsx — Realtime disaster alert toast banner

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

export default function AlertBanner({ alerts }) {
  const [visible, setVisible] = useState([])

  useEffect(() => {
    if (!alerts?.length) return
    const newAlerts = alerts.map((a, i) => ({ ...a, id: Date.now() + i }))
    setVisible((prev) => [...prev, ...newAlerts])
  }, [alerts])

  const dismiss = (id) => setVisible((prev) => prev.filter((a) => a.id !== id))

  // Auto-dismiss after 8 seconds
  useEffect(() => {
    if (!visible.length) return
    const timer = setTimeout(() => {
      setVisible((prev) => prev.slice(1))
    }, 8000)
    return () => clearTimeout(timer)
  }, [visible])

  return (
    <div style={{ position: 'absolute', top: 80, left: '50%', transform: 'translateX(-50%)', zIndex: 200, display: 'flex', flexDirection: 'column', gap: 8 }}>
      <AnimatePresence>
        {visible.slice(0, 3).map((alert) => (
          <motion.div
            key={alert.id}
            className="alert-banner glass"
            initial={{ opacity: 0, y: -20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          >
            <span className="alert-icon">⚠️</span>
            <span className="alert-text">
              <strong>{alert.city_name}</strong> — {alert.disaster_type?.replace(/_/g, ' ')} alert
              {alert.severity ? ` (${alert.severity})` : ''}
              {alert.risk_score ? ` · ${(alert.risk_score * 100).toFixed(0)}% risk` : ''}
            </span>
            <button className="alert-close" onClick={() => dismiss(alert.id)}>✕</button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
