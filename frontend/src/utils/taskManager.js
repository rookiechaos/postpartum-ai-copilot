/**
 * Task Manager - Manages async task polling and state
 * Now supports WebSocket for real-time updates (fallback to polling if WebSocket unavailable)
 */

import api from './api.js'
import websocketManager from './websocketManager.js'

const POLL_INTERVAL = 1000 // 1 second
const MAX_POLL_ATTEMPTS = 300 // 5 minutes max
const POLL_BACKOFF_MULTIPLIER = 1.5 // Exponential backoff

class TaskManager {
  constructor() {
    this.activeTasks = new Map() // taskId -> { task, pollInterval, attempts, resolve, reject }
    this.taskCache = new Map() // taskId -> cached result
    this.useWebSocket = true // Try WebSocket first, fallback to polling
    this._setupWebSocket()
  }

  /**
   * Setup WebSocket connection and listeners
   * @private
   */
  _setupWebSocket() {
    // Get token for WebSocket connection
    const token = localStorage.getItem('access_token')
    if (token) {
      try {
        websocketManager.connect(token)
        
        // Listen for task updates
        websocketManager.on('task_update', (taskData) => {
          const taskId = taskData.task_id
          const taskInfo = this.activeTasks.get(taskId)
          
          if (taskInfo) {
            if (taskData.status === 'completed') {
              this.taskCache.set(taskId, taskData.result)
              this.activeTasks.delete(taskId)
              taskInfo.resolve(taskData.result)
            } else if (taskData.status === 'failed') {
              this.activeTasks.delete(taskId)
              taskInfo.reject(new Error(taskData.error || 'Task failed'))
            } else if (taskData.status === 'cancelled') {
              this.activeTasks.delete(taskId)
              taskInfo.reject(new Error('Task was cancelled'))
            } else {
              // Status update (pending -> processing, etc.)
              taskInfo.task = taskData
            }
          }
        })
        
        websocketManager.on('error', (error) => {
          console.warn('WebSocket error, falling back to polling:', error)
          this.useWebSocket = false
        })
        
        websocketManager.on('disconnected', () => {
          console.warn('WebSocket disconnected, falling back to polling')
          this.useWebSocket = false
        })
      } catch (error) {
        console.warn('WebSocket setup failed, using polling:', error)
        this.useWebSocket = false
      }
    } else {
      this.useWebSocket = false
    }
  }

  /**
   * Submit a task and poll for result
   * @param {string} taskType - Type of task
   * @param {object} taskData - Task data
   * @param {object} options - Options (priority, timeout, pollInterval)
   * @returns {Promise} Promise that resolves with task result
   */
  async submitTask(taskType, taskData, options = {}) {
    const {
      priority = 'medium',
      timeout = null,
      pollInterval = POLL_INTERVAL,
      maxAttempts = MAX_POLL_ATTEMPTS
    } = options

    try {
      // Create task
      const taskResponse = await api.createTask(taskType, taskData, priority, timeout)
      const taskId = taskResponse.task_id

      // Check if already completed (shouldn't happen, but handle it)
      if (taskResponse.status === 'completed' && taskResponse.result) {
        this.taskCache.set(taskId, taskResponse.result)
        return taskResponse.result
      }

      // Return promise that resolves when task completes
      return new Promise((resolve, reject) => {
        this.activeTasks.set(taskId, {
          task: taskResponse,
          pollInterval,
          attempts: 0,
          maxAttempts,
          resolve,
          reject,
          startTime: Date.now()
        })

        // Subscribe to WebSocket updates if available
        if (this.useWebSocket && websocketManager.isConnected()) {
          websocketManager.subscribeToTask(taskId)
        }

        // Start polling as fallback (or primary if WebSocket unavailable)
        if (!this.useWebSocket || !websocketManager.isConnected()) {
          this._pollTask(taskId)
        }
      })
    } catch (error) {
      console.error('Failed to submit task:', error)
      throw error
    }
  }

  /**
   * Poll a task for status updates
   * @private
   */
  async _pollTask(taskId) {
    const taskInfo = this.activeTasks.get(taskId)
    if (!taskInfo) {
      return // Task was cancelled or removed
    }

    try {
      const task = await api.getTask(taskId)
      taskInfo.attempts++

      if (task.status === 'completed') {
        // Task completed successfully
        this.taskCache.set(taskId, task.result)
        this.activeTasks.delete(taskId)
        taskInfo.resolve(task.result)
        return
      }

      if (task.status === 'failed') {
        // Task failed
        this.activeTasks.delete(taskId)
        taskInfo.reject(new Error(task.error || 'Task failed'))
        return
      }

      if (task.status === 'cancelled') {
        // Task was cancelled
        this.activeTasks.delete(taskId)
        taskInfo.reject(new Error('Task was cancelled'))
        return
      }

      // Check if max attempts reached
      if (taskInfo.attempts >= taskInfo.maxAttempts) {
        this.activeTasks.delete(taskId)
        taskInfo.reject(new Error('Task polling timeout'))
        return
      }

      // Task still pending or processing, continue polling
      // Use exponential backoff for pending tasks
      const backoff = task.status === 'pending' 
        ? taskInfo.pollInterval * Math.pow(POLL_BACKOFF_MULTIPLIER, Math.min(taskInfo.attempts / 10, 3))
        : taskInfo.pollInterval

      setTimeout(() => {
        this._pollTask(taskId)
      }, backoff)

    } catch (error) {
      console.error(`Error polling task ${taskId}:`, error)
      
      // Retry on error (network issues, etc.)
      if (taskInfo.attempts < taskInfo.maxAttempts) {
        setTimeout(() => {
          this._pollTask(taskId)
        }, taskInfo.pollInterval * 2)
      } else {
        this.activeTasks.delete(taskId)
        taskInfo.reject(error)
      }
    }
  }

  /**
   * Get task status (without polling)
   */
  async getTaskStatus(taskId) {
    try {
      const task = await api.getTask(taskId)
      return {
        status: task.status,
        result: task.result,
        error: task.error,
        progress: this._calculateProgress(task)
      }
    } catch (error) {
      console.error('Failed to get task status:', error)
      throw error
    }
  }

  /**
   * Cancel a task
   */
  async cancelTask(taskId) {
    try {
      await api.cancelTask(taskId)
      const taskInfo = this.activeTasks.get(taskId)
      if (taskInfo) {
        this.activeTasks.delete(taskId)
        taskInfo.reject(new Error('Task cancelled by user'))
      }
    } catch (error) {
      console.error('Failed to cancel task:', error)
      throw error
    }
  }

  /**
   * Get cached task result
   */
  getCachedResult(taskId) {
    return this.taskCache.get(taskId)
  }

  /**
   * Clear task cache
   */
  clearCache() {
    this.taskCache.clear()
  }

  /**
   * Calculate progress based on task status and timing
   * @private
   */
  _calculateProgress(task) {
    if (task.status === 'completed') return 100
    if (task.status === 'failed' || task.status === 'cancelled') return 0
    if (task.status === 'processing') {
      // Estimate progress based on elapsed time vs timeout
      if (task.started_at && task.timeout_seconds) {
        const started = new Date(task.started_at).getTime()
        const elapsed = Date.now() - started
        const progress = Math.min(90, (elapsed / (task.timeout_seconds * 1000)) * 90)
        return Math.round(progress)
      }
      return 50 // Unknown progress, assume halfway
    }
    return 0 // Pending
  }

  /**
   * Get all active tasks
   */
  getActiveTasks() {
    return Array.from(this.activeTasks.keys())
  }

  /**
   * Clean up old cached results (older than 1 hour)
   */
  cleanupCache() {
    // For now, just clear all cache
    // Could implement time-based cleanup if needed
    this.clearCache()
  }
}

// Export singleton instance
const taskManager = new TaskManager()
export default taskManager
