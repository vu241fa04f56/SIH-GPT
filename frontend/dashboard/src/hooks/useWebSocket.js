// useWebSocket.js — React hook for WebSocket live updates

import { useEffect, useRef } from 'react'
import { connectWebSocket, disconnectWebSocket } from '../services/websocketClient'

export function useWebSocket(onMessage) {
  const cbRef = useRef(onMessage)
  cbRef.current = onMessage

  useEffect(() => {
    const handler = (data) => cbRef.current(data)
    connectWebSocket(handler)
    return () => disconnectWebSocket(handler)
  }, [])
}
