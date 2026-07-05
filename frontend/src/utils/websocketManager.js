/**
 * WebSocket Manager - Real-time task updates
 */

import { getApiBase } from './api'

class WebSocketManager {
  constructor() {
    this.ws = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 1000
    this.listeners = new Map() // event -> Set[callback]
    this.subscribedTasks = new Set()
    this.isConnecting = false
  }

  /**
   * Connect to WebSocket server
   * @param {string} token - JWT authentication token
   * @param {string} baseUrl - WebSocket server URL (default: ws://localhost:8000)
   */
  connect(token, baseUrl = null) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return // Already connected
    }

    if (this.isConnecting) {
      return // Connection in progress
    }

    this.isConnecting = true

    try {
      // Determine WebSocket URL
      const wsUrl = baseUrl || this._getWebSocketUrl()
      const url = `${wsUrl}/ws?token=${encodeURIComponent(token)}`

      this.ws = new WebSocket(url)

      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.isConnecting = false
        this.reconnectAttempts = 0
        this._emit('connected')
        
        // Resubscribe to all tasks
        this.subscribedTasks.forEach(taskId => {
          this.subscribeToTask(taskId)
        })
        
        // Start heartbeat
        this._startHeartbeat()
      }

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          this._handleMessage(message)
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.isConnecting = false
        this._emit('error', error)
      }

      this.ws.onclose = () => {
        console.log('WebSocket disconnected')
        this.isConnecting = false
        this._emit('disconnected')
        this._stopHeartbeat()
        
        // Attempt to reconnect
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          setTimeout(() => {
            this.reconnectAttempts++
            this.connect(token, baseUrl)
          }, this.reconnectDelay * this.reconnectAttempts)
        }
      }
    } catch (error) {
      console.error('Error creating WebSocket:', error)
      this.isConnecting = false
      this._emit('error', error)
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this._stopHeartbeat()
    this.subscribedTasks.clear()
  }

  /**
   * Subscribe to task updates
   * @param {string} taskId - Task ID to subscribe to
   */
  subscribeToTask(taskId) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket not connected, cannot subscribe to task')
      return
    }

    this.subscribedTasks.add(taskId)
    this._send({
      type: 'subscribe_task',
      task_id: taskId
    })
  }

  /**
   * Unsubscribe from task updates
   * @param {string} taskId - Task ID to unsubscribe from
   */
  unsubscribeFromTask(taskId) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return
    }

    this.subscribedTasks.delete(taskId)
    this._send({
      type: 'unsubscribe_task',
      task_id: taskId
    })
  }

  /**
   * Add event listener
   * @param {string} event - Event name (connected, disconnected, task_update, error)
   * @param {Function} callback - Callback function
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set())
    }
    this.listeners.get(event).add(callback)
  }

  /**
   * Remove event listener
   * @param {string} event - Event name
   * @param {Function} callback - Callback function
   */
  off(event, callback) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).delete(callback)
    }
  }

  /**
   * Check if WebSocket is connected
   */
  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN
  }

  /**
   * Handle incoming WebSocket message
   * @private
   */
  _handleMessage(message) {
    const type = message.type

    if (type === 'task_update') {
      this._emit('task_update', message.data)
    } else if (type === 'connection') {
      this._emit('connected')
    } else if (type === 'subscription') {
      this._emit('subscription', message)
    } else if (type === 'pong') {
      // Heartbeat response
    } else if (type === 'error') {
      this._emit('error', new Error(message.message))
    }
  }

  /**
   * Send message to WebSocket server
   * @private
   */
  _send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    }
  }

  /**
   * Emit event to listeners
   * @private
   */
  _emit(event, data = null) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => {
        try {
          callback(data)
        } catch (error) {
          console.error(`Error in WebSocket event listener for ${event}:`, error)
        }
      })
    }
  }

  /**
   * Get WebSocket URL from environment or default
   * @private
   */
  _getWebSocketUrl() {
    const apiBase = getApiBase()
    return apiBase.replace('http://', 'ws://').replace('https://', 'wss://')
  }

  /**
   * Start heartbeat to keep connection alive
   * @private
   */
  _startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      if (this.isConnected()) {
        this._send({ type: 'ping' })
      }
    }, 30000) // Send ping every 30 seconds
  }

  /**
   * Stop heartbeat
   * @private
   */
  _stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }
}

// Export singleton instance
const websocketManager = new WebSocketManager()
export default websocketManager
