/** WebSocket connections and reconnects belong to one authentication session. */
import { getApiBase } from './api'

class WebSocketManager {
  constructor() {
    this.ws = null
    this.token = null
    this.baseUrl = null
    this.connectionGeneration = 0
    this.reconnectTimer = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 1000
    this.listeners = new Map()
    this.subscribedTasks = new Set()
    this.isConnecting = false
  }

  connect(token, baseUrl = null) {
    if (!token) return
    if (this.token !== token || this.baseUrl !== baseUrl) this.disconnect()
    if (this.isConnected() || this.isConnecting) return
    clearTimeout(this.reconnectTimer)
    this.reconnectTimer = null
    this.token = token
    this.baseUrl = baseUrl
    this.isConnecting = true
    const generation = ++this.connectionGeneration
    try {
      const url = (baseUrl || this._getWebSocketUrl()) + '/ws?token=' + encodeURIComponent(token)
      const socket = new WebSocket(url)
      this.ws = socket
      const isCurrent = () => this.ws === socket && this.connectionGeneration === generation

      socket.onopen = () => {
        if (!isCurrent()) return
        this.isConnecting = false
        this.reconnectAttempts = 0
        this.subscribedTasks.forEach(taskId => {
          this._send({ type: 'subscribe_task', task_id: taskId })
        })
        this._startHeartbeat()
        this._emit('connected')
      }
      socket.onmessage = event => {
        if (!isCurrent()) return
        try { this._handleMessage(JSON.parse(event.data)) }
        catch (error) { console.error('Error parsing WebSocket message:', error) }
      }
      socket.onerror = error => {
        if (isCurrent()) this._emit('error', error)
      }
      socket.onclose = () => {
        if (!isCurrent()) return
        this.ws = null
        this.isConnecting = false
        this._stopHeartbeat()
        this._emit('disconnected')
        if (this.connectionGeneration === generation && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++
          this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null
            if (this.connectionGeneration === generation && this.token === token) this.connect(token, baseUrl)
          }, this.reconnectDelay * this.reconnectAttempts)
        }
      }
    } catch (error) {
      this.ws = null
      this.isConnecting = false
      this._emit('error', error)
    }
  }

  disconnect() {
    this.connectionGeneration++
    clearTimeout(this.reconnectTimer)
    this.reconnectTimer = null
    const socket = this.ws
    this.ws = null
    this.token = null
    this.baseUrl = null
    this.isConnecting = false
    this.reconnectAttempts = 0
    this._stopHeartbeat()
    this.subscribedTasks.clear()
    if (socket) {
      socket.onopen = socket.onmessage = socket.onerror = socket.onclose = null
      socket.close()
    }
  }

  subscribeToTask(taskId) {
    if (this.subscribedTasks.has(taskId)) return
    this.subscribedTasks.add(taskId)
    this._send({ type: 'subscribe_task', task_id: taskId })
  }

  unsubscribeFromTask(taskId) {
    this.subscribedTasks.delete(taskId)
    this._send({ type: 'unsubscribe_task', task_id: taskId })
  }

  on(event, callback) {
    if (!this.listeners.has(event)) this.listeners.set(event, new Set())
    this.listeners.get(event).add(callback)
  }

  off(event, callback) { this.listeners.get(event)?.delete(callback) }
  isConnected() { return !!this.ws && this.ws.readyState === WebSocket.OPEN }

  _handleMessage(message) {
    if (message.type === 'task_update') this._emit('task_update', message.data)
    else if (message.type === 'notification') this._emit('notification', message)
    else if (message.type === 'subscription') this._emit('subscription', message)
    else if (message.type === 'error') this._emit('error', new Error(message.message))
  }

  _send(message) {
    if (!this.isConnected()) return
    try { this.ws.send(JSON.stringify(message)) }
    catch (error) { this._emit('error', error) }
  }

  _emit(event, data = null) {
    this.listeners.get(event)?.forEach(callback => {
      try { callback(data) }
      catch (error) { console.error('WebSocket listener failed:', error) }
    })
  }

  _getWebSocketUrl() {
    return getApiBase().replace('http://', 'ws://').replace('https://', 'wss://')
  }

  _startHeartbeat() {
    this._stopHeartbeat()
    this.heartbeatInterval = setInterval(() => this._send({ type: 'ping' }), 30000)
  }

  _stopHeartbeat() {
    clearInterval(this.heartbeatInterval)
    this.heartbeatInterval = null
  }
}

const websocketManager = new WebSocketManager()
export default websocketManager
