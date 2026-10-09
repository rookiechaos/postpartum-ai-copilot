/** Async tasks use bounded polling; WebSocket updates can finish them sooner. */
import api from './api.js'
import websocketManager from './websocketManager.js'

const POLL_INTERVAL = 1000
const MAX_POLL_ATTEMPTS = 300
const DEFAULT_TIMEOUT_MS = 300000
const POLL_BACKOFF_MULTIPLIER = 1.5

class TaskManager {
  constructor() {
    this.activeTasks = new Map()
    this.taskCache = new Map()
    this.pendingSubmissions = new Set()
    this.sessionGeneration = 0
    this.useWebSocket = false

    websocketManager.on('task_update', task => {
      if (task) this._applyUpdate(task.task_id, task)
    })
    websocketManager.on('connected', () => {
      this.useWebSocket = true
      this.activeTasks.forEach((info, taskId) => websocketManager.subscribeToTask(taskId))
    })
    websocketManager.on('disconnected', () => { this.useWebSocket = false })
    websocketManager.on('error', () => { this.useWebSocket = false })
    api.onAuthChange(change => this._setAuth(change))
    this._setAuth({ token: localStorage.getItem('access_token') })
  }

  _setAuth({ token, preserveTasks = false }) {
    if (!preserveTasks) {
      // Finish the old generation before invalidating it.
      this.pendingSubmissions.forEach(submission => {
        submission.reject(new Error('Authentication session changed'))
        submission.controller.abort()
        clearTimeout(submission.timer)
      })
      this.pendingSubmissions.clear()
      this.activeTasks.forEach((info, taskId) => {
        this._finishTask(taskId, info, new Error('Authentication session changed'))
      })
      this.sessionGeneration++
      this.taskCache.clear()
    }
    this.useWebSocket = false
    websocketManager.disconnect()
    if (token) websocketManager.connect(token)
  }

  _isCurrent(taskId, info) {
    return this.activeTasks.get(taskId) === info && info.generation === this.sessionGeneration
  }

  _finishTask(taskId, info, error = null, result = undefined) {
    if (!this._isCurrent(taskId, info)) return
    this.activeTasks.delete(taskId)
    clearTimeout(info.pollTimer)
    clearTimeout(info.deadlineTimer)
    info.controller.abort()
    websocketManager.unsubscribeFromTask(taskId)
    if (error) info.reject(error)
    else {
      this.taskCache.set(taskId, result)
      info.resolve(result)
    }
  }

  _applyUpdate(taskId, task) {
    const info = this.activeTasks.get(taskId)
    if (!info || !this._isCurrent(taskId, info)) return
    info.task = task
    if (task.status === 'completed') this._finishTask(taskId, info, null, task.result)
    else if (task.status === 'failed') this._finishTask(taskId, info, new Error(task.error || 'Task failed'))
    else if (task.status === 'cancelled') this._finishTask(taskId, info, new Error('Task was cancelled'))
  }

  /** options.timeout is milliseconds; the server's timeout is seconds. */
  async submitTask(taskType, taskData, options = {}) {
    const priority = options.priority ?? 'medium'
    const timeout = options.timeout ?? DEFAULT_TIMEOUT_MS
    const pollInterval = options.pollInterval ?? POLL_INTERVAL
    const maxAttempts = options.maxAttempts ?? MAX_POLL_ATTEMPTS
    if (![timeout, pollInterval, maxAttempts].every(value => Number.isFinite(value) && value > 0)) {
      throw new Error('Task timeout, poll interval and max attempts must be positive numbers')
    }
    const generation = this.sessionGeneration
    const startTime = Date.now()
    const deadlineAt = startTime + timeout
    const submission = { controller: new AbortController() }
    let response
    try {
      response = await new Promise((resolve, reject) => {
        submission.reject = reject
        submission.timer = setTimeout(() => {
          reject(new Error('Task polling timeout'))
          submission.controller.abort()
        }, timeout)
        this.pendingSubmissions.add(submission)
        api.createTask(taskType, taskData, priority, Math.ceil(timeout / 1000), {
          signal: submission.controller.signal
        }).then(resolve, reject)
      })
    } finally {
      clearTimeout(submission.timer)
      this.pendingSubmissions.delete(submission)
    }
    if (generation !== this.sessionGeneration) throw new Error('Authentication session changed')
    if (Date.now() >= deadlineAt) throw new Error('Task polling timeout')
    const taskId = response.task_id

    return new Promise((resolve, reject) => {
      const info = {
        task: response, generation, pollInterval, maxAttempts, attempts: 0,
        resolve, reject, startTime, deadlineAt, controller: new AbortController(), inFlight: false
      }
      this.activeTasks.set(taskId, info)
      info.deadlineTimer = setTimeout(() => {
        this._finishTask(taskId, info, new Error('Task polling timeout'))
      }, deadlineAt - Date.now())
      this._applyUpdate(taskId, response)
      if (!this._isCurrent(taskId, info)) return
      websocketManager.subscribeToTask(taskId)
      // API and worker may run in separate processes without a shared socket bus.
      this._pollTask(taskId)
    })
  }

  async _pollTask(taskId) {
    const info = this.activeTasks.get(taskId)
    if (!info || !this._isCurrent(taskId, info) || info.inFlight) return
    if (Date.now() >= info.deadlineAt || info.attempts >= info.maxAttempts) {
      this._finishTask(taskId, info, new Error('Task polling timeout'))
      return
    }
    info.inFlight = true
    info.attempts++
    let delay = info.pollInterval
    try {
      const task = await api.getTask(taskId, { signal: info.controller.signal })
      if (!this._isCurrent(taskId, info)) return
      this._applyUpdate(taskId, task)
      if (task.status === 'pending') {
        delay *= Math.pow(POLL_BACKOFF_MULTIPLIER, Math.min(info.attempts / 10, 3))
      }
    } catch (error) {
      if (!this._isCurrent(taskId, info)) return
      if ([401, 403, 404].includes(error.status)) {
        this._finishTask(taskId, info, error)
        return
      }
      delay *= 2
    } finally {
      info.inFlight = false
    }
    if (!this._isCurrent(taskId, info)) return
    if (info.attempts >= info.maxAttempts || Date.now() >= info.deadlineAt) {
      this._finishTask(taskId, info, new Error('Task polling timeout'))
      return
    }
    info.pollTimer = setTimeout(() => this._pollTask(taskId), Math.min(delay, info.deadlineAt - Date.now()))
  }

  async getTaskStatus(taskId) {
    const generation = this.sessionGeneration
    const task = await api.getTask(taskId)
    if (generation !== this.sessionGeneration) throw new Error('Authentication session changed')
    return { status: task.status, result: task.result, error: task.error, progress: this._calculateProgress(task) }
  }

  async cancelTask(taskId) {
    const info = this.activeTasks.get(taskId)
    await api.cancelTask(taskId)
    if (info) this._finishTask(taskId, info, new Error('Task cancelled by user'))
  }

  getCachedResult(taskId) { return this.taskCache.get(taskId) }
  clearCache() { this.taskCache.clear() }
  getActiveTasks() { return Array.from(this.activeTasks.keys()) }
  cleanupCache() { this.clearCache() }

  _calculateProgress(task) {
    if (task.status === 'completed') return 100
    if (task.status === 'failed' || task.status === 'cancelled') return 0
    if (task.status === 'processing') {
      if (task.started_at && task.timeout_seconds) {
        const elapsed = Date.now() - new Date(task.started_at).getTime()
        return Math.round(Math.min(90, (elapsed / (task.timeout_seconds * 1000)) * 90))
      }
      return 50
    }
    return 0
  }
}

const taskManager = new TaskManager()
export default taskManager
