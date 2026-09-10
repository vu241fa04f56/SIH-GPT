// useGeolocation.js — React hook to get the user's GPS location

import { useState, useEffect } from 'react'

export function useGeolocation() {
  const [location, setLocation] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!navigator.geolocation) {
      setError('Geolocation not supported by this browser.')
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocation({
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
        })
      },
      (err) => {
        setError(err.message)
        // Fall back to Mumbai
        setLocation({ lat: 19.076, lon: 72.877, accuracy: null })
      },
      { timeout: 8000, enableHighAccuracy: false }
    )
  }, [])

  return { location, error }
}
