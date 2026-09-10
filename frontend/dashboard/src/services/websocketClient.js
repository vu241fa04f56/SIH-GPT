// websocketClient.js — WebSocket client with auto-reconnect

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'

let ws = null
let listeners = []
let reconnectTimer = null

export function connectWebSocket(onMessage) {
  listeners.push(onMessage)
  if (ws && ws.readyState === WebSocket.OPEN) return

  _connect()
}

function _connect() {
  ws = new WebSocket(WS_URL)

  ws.onopen = () => {
    console.log('[WS] Connected to WeatherGPT live feed')
    if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      listeners.forEach((fn) => fn(data))
    } catch (e) {
      console.warn('[WS] Failed to parse message:', e)
    }
  }

  ws.onclose = () => {
    console.warn('[WS] Disconnected. Reconnecting in 3s...')
    reconnectTimer = setTimeout(_connect, 3000)
  }

  ws.onerror = (err) => {
    console.error('[WS] Error:', err)
    ws.close()
  }
}

export function disconnectWebSocket(onMessage) {
  listeners = listeners.filter((fn) => fn !== onMessage)
}
