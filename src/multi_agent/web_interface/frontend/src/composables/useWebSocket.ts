import { ref, onUnmounted, watch } from 'vue'
import type { WebSocketMessage } from '@/types/websocket'
import { useProject } from './useProject'

const MAX_RECONNECT_ATTEMPTS = 10

export function useWebSocket() {
  const isConnected = ref(false)
  const { currentProject } = useProject()

  let ws: WebSocket | null = null
  let reconnectAttempts = 0
  let pingInterval: ReturnType<typeof setInterval> | null = null
  const handlers: Array<(msg: WebSocketMessage) => void> = []

  function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const projectParam = encodeURIComponent(currentProject.value.project_dir)
    const wsUrl = `${protocol}//${window.location.host}/ws/updates?project=${projectParam}`

    try {
      ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        reconnectAttempts = 0
        isConnected.value = true

        // Periodic ping to keep alive
        if (pingInterval) clearInterval(pingInterval)
        pingInterval = setInterval(() => {
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send('ping')
          }
        }, 30000)
      }

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          handlers.forEach((handler) => handler(message))
        } catch {
          // Ignore parse errors (e.g. pong responses)
        }
      }

      ws.onerror = () => {
        isConnected.value = false
      }

      ws.onclose = () => {
        isConnected.value = false
        if (pingInterval) {
          clearInterval(pingInterval)
          pingInterval = null
        }

        // Exponential backoff reconnect
        if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts++
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000)
          setTimeout(() => connect(), delay)
        }
      }
    } catch {
      isConnected.value = false
    }
  }

  function disconnect() {
    if (pingInterval) {
      clearInterval(pingInterval)
      pingInterval = null
    }
    if (ws) {
      ws.close()
      ws = null
    }
    isConnected.value = false
  }

  function onMessage(handler: (msg: WebSocketMessage) => void) {
    handlers.push(handler)
  }

  // Watch for project changes and reconnect
  watch(
    () => currentProject.value.project_dir,
    () => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        disconnect()
        setTimeout(() => connect(), 100)
      }
    }
  )

  onUnmounted(() => {
    disconnect()
  })

  return { isConnected, connect, disconnect, onMessage }
}
