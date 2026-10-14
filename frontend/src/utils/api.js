/**
 * API utility functions
 * Handles API calls with error handling and fallbacks
 * Includes authentication token management
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const DEFAULT_REQUEST_TIMEOUT_MS = 30000

// Token management
const getToken = () => {
  return localStorage.getItem('access_token')
}

const setToken = (token) => {
  if (token) {
    localStorage.setItem('access_token', token)
  } else {
    localStorage.removeItem('access_token')
  }
}

const getAuthHeaders = () => {
  const token = getToken()
  return token ? { 'Authorization': `Bearer ${token}` } : {}
}

const getStoredUserId = () => localStorage.getItem('userId')
const setStoredUserId = (id) => {
  if (id) localStorage.setItem('userId', id)
  else localStorage.removeItem('userId')
}

const getRefreshToken = () => localStorage.getItem('refresh_token')
const AUTH_SESSION_KEY = 'auth_session_id'
const AUTH_STORAGE_KEYS = new Set([AUTH_SESSION_KEY, 'access_token', 'refresh_token', 'userId'])
const authListeners = new Set()
let authSession = 0
const readAuthState = () => ({
  sessionId: localStorage.getItem(AUTH_SESSION_KEY),
  userId: getStoredUserId(),
  token: getToken(),
})
let observedAuthState = readAuthState()

function notifyAuthChange(preserveTasks = false, reason = 'session-change') {
  observedAuthState = readAuthState()
  const change = { token: getToken(), preserveTasks, reason }
  authListeners.forEach(callback => {
    try { callback(change) } catch (error) { console.error('Auth listener failed:', error) }
  })
}

function synchronizeAuthStorage() {
  const current = readAuthState()
  const changed = current.sessionId !== observedAuthState.sessionId ||
    (observedAuthState.userId !== null && current.userId !== observedAuthState.userId) ||
    Boolean(current.token) !== Boolean(observedAuthState.token)
  const tokenChanged = current.token !== observedAuthState.token
  observedAuthState = current
  if (changed) {
    authSession++
    notifyAuthChange(false, 'storage')
    clearPrivateCaches().catch(() => {})
  } else if (tokenChanged) {
    // A refresh within the same login keeps private state and active tasks.
    notifyAuthChange(true)
  }
}

if (typeof window !== 'undefined') {
  window.addEventListener('storage', event => {
    if (event.storageArea && event.storageArea !== localStorage) return
    if (event.key === null || AUTH_STORAGE_KEYS.has(event.key)) synchronizeAuthStorage()
  })
}

function isCurrentSession(session) {
  // Storage events are queued: check shared state before accepting any response.
  synchronizeAuthStorage()
  return session === authSession
}

function assertSession(session) {
  if (!isCurrentSession(session)) throw new Error('Authentication session changed')
}

function getAuthSession() {
  const session = authSession
  assertSession(session)
  return session
}

async function responseError(response, session) {
  const data = await response.json().catch(() => ({}))
  assertSession(session)
  const message = data?.error?.message ?? data?.detail
  const error = new Error(typeof message === 'string' ? message : `API error: ${response.status}`)
  error.status = response.status
  const validation = data?.error?.details?.errors
  if (response.status === 422 && Array.isArray(validation)) {
    error.validation = validation.filter(item => Array.isArray(item?.loc)).map(item => ({
      loc: item.loc.filter(part => typeof part === 'string' || Number.isInteger(part)),
      type: typeof item.type === 'string' ? item.type : '',
    }))
  }
  return error
}

function clearLegacyOfflineStorage() {
  if (typeof indexedDB === 'undefined') return Promise.resolve(true)
  return new Promise(resolve => {
    try {
      const request = indexedDB.deleteDatabase('postpartum-offline')
      request.onsuccess = () => resolve(true)
      request.onerror = () => resolve(false)
      request.onblocked = () => resolve(false)
    } catch { resolve(false) }
  })
}

async function clearPrivateCaches() {
  const cleanup = [clearLegacyOfflineStorage()]
  if (typeof caches !== 'undefined') cleanup.push(caches.keys().then(names => Promise.all(
    names.filter(name => name.startsWith('postpartum-runtime')).map(name => caches.delete(name)),
  )))
  await Promise.all(cleanup)
}

let onUnauthorizedCallback = null

function triggerUnauthorized() {
  if (typeof onUnauthorizedCallback === 'function') {
    onUnauthorizedCallback()
  }
}

/** Build fetch options with optional timeout (AbortController). Returns { signal, timeoutId }. */
function withTimeout(options, defaultTimeoutMs = DEFAULT_REQUEST_TIMEOUT_MS) {
  const timeoutMs = options.timeout ?? defaultTimeoutMs
  if (options.signal) {
    return { signal: options.signal, timeoutId: null }
  }
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)
  return { signal: controller.signal, timeoutId }
}

function communicationError(error, write = false) {
  if (write && error.status >= 500) error.resultUnconfirmed = true
  if (['AbortError', 'TypeError', 'SyntaxError'].includes(error.name) && !error.status) {
    const failure = new Error(error.name === 'AbortError' ? 'Request timed out' : 'Connection unavailable')
    failure.communication = navigator.onLine === false ? 'offline' : error.name === 'AbortError' ? 'timeout' : 'connection'
    failure.resultUnconfirmed = write
    return failure
  }
  return error
}

/** Call /api/auth/refresh with refresh_token; does NOT retry on 401 (avoids loop). */
async function refreshAccessToken() {
  const session = getAuthSession()
  const refreshToken = getRefreshToken()
  if (!refreshToken) return null
  const response = await fetch(`${API_BASE}/api/auth/refresh`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${refreshToken}`
    },
    body: JSON.stringify({ refresh_token: refreshToken })
  })
  if (!isCurrentSession(session)) return null
  if (refreshToken !== getRefreshToken()) return getToken()
  if (!response.ok) return null
  const data = await response.json().catch(() => null)
  if (!isCurrentSession(session)) return null
  if (refreshToken !== getRefreshToken()) return getToken()
  if (data?.access_token) {
    setToken(data.access_token)
    if (data.refresh_token) {
      localStorage.setItem('refresh_token', data.refresh_token)
    }
    notifyAuthChange(true)
    return data.access_token
  }
  return null
}

export const api = {
  clearLegacyOfflineStorage,
  async get(endpoint, options = {}, isRetry = false) {
    const session = getAuthSession()
    const { signal, timeoutId } = withTimeout(options)
    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        signal,
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(),
          ...options.headers
        }
      })
      assertSession(session)
      if (response.status === 401 && !isRetry) {
        const newToken = await refreshAccessToken()
        assertSession(session)
        if (newToken) {
          return await this.get(endpoint, options, true)
        }
        this.logout({ reason: 'expired' })
        triggerUnauthorized()
        const error = new Error('Authentication required')
        error.status = 401
        throw error
      }
      if (response.status === 401 && isRetry) {
        const error = await responseError(response, session)
        this.logout({ reason: 'expired' })
        triggerUnauthorized()
        throw error
      }
      if (!response.ok) {
        throw await responseError(response, session)
      }
      const data = await response.json()
      assertSession(session)
      return data
    } catch (error) {
      console.error('API GET error:', error)
      throw communicationError(error)
    } finally {
      if (timeoutId) clearTimeout(timeoutId)
    }
  },

  async post(endpoint, data, options = {}, isRetry = false) {
    const session = getAuthSession()
    const { signal, timeoutId } = withTimeout(options)
    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        ...options,
        signal,
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(),
          ...options.headers
        },
        body: JSON.stringify(data)
      })
      assertSession(session)
      if (response.status === 401 && !isRetry && !endpoint.startsWith('/api/auth/')) {
        const newToken = await refreshAccessToken()
        assertSession(session)
        if (newToken) {
          return await this.post(endpoint, data, options, true)
        }
        this.logout({ reason: 'expired' })
        triggerUnauthorized()
        const error = new Error('Authentication required')
        error.status = 401
        throw error
      }
      if (response.status === 401 && isRetry) {
        const error = await responseError(response, session)
        this.logout({ reason: 'expired' })
        triggerUnauthorized()
        throw error
      }
      if (!response.ok) {
        throw await responseError(response, session)
      }
      const result = await response.json()
      assertSession(session)
      return result
    } catch (error) {
      console.error('API POST error:', error)
      throw communicationError(error, true)
    } finally {
      if (timeoutId) clearTimeout(timeoutId)
    }
  },

  async delete(endpoint, options = {}, isRetry = false) {
    const session = getAuthSession()
    const { signal, timeoutId } = withTimeout(options)
    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'DELETE',
        ...options,
        signal,
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(),
          ...options.headers
        }
      })
      assertSession(session)
      if (response.status === 401 && !isRetry) {
        const newToken = await refreshAccessToken()
        assertSession(session)
        if (newToken) {
          return await this.delete(endpoint, options, true)
        }
        this.logout({ reason: 'expired' })
        triggerUnauthorized()
        const error = new Error('Authentication required')
        error.status = 401
        throw error
      }
      if (response.status === 401 && isRetry) {
        const error = await responseError(response, session)
        this.logout({ reason: 'expired' })
        triggerUnauthorized()
        throw error
      }
      if (response.status === 204) {
        return null
      }
      if (!response.ok) {
        throw await responseError(response, session)
      }
      const data = await response.json().catch(() => null)
      assertSession(session)
      return data
    } catch (error) {
      console.error('API DELETE error:', error)
      throw communicationError(error, true)
    } finally {
      if (timeoutId) clearTimeout(timeoutId)
    }
  },

  setOnUnauthorized(callback) {
    onUnauthorizedCallback = callback
  },

  onAuthChange(callback) {
    authListeners.add(callback)
    return () => authListeners.delete(callback)
  },

  // Authentication methods
  async login(email, password, verificationToken = null) {
    const clearing = this.logout({ reason: 'sign-in' })
    const session = getAuthSession()
    await clearing
    assertSession(session)
    const response = await this.post('/api/auth/login', {
      email, password, verification_token: verificationToken
    })
    assertSession(session)
    if (response.access_token) {
      // A login marker stays stable through token refreshes and changes on sign-in.
      localStorage.setItem(AUTH_SESSION_KEY, globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`)
      setToken(response.access_token)
      if (response.refresh_token) {
        localStorage.setItem('refresh_token', response.refresh_token)
      }
      notifyAuthChange(false, 'sign-in')
    }
    return response
  },

  async register(email, password, user_id = null) {
    const response = await this.post('/api/auth/register', { email, password, user_id })
    return response
  },

  async getCurrentUser() {
    return await this.get('/api/auth/me')
  },

  logout({ reason = 'logout' } = {}) {
    authSession++
    setToken(null)
    setStoredUserId(null)
    localStorage.removeItem('refresh_token')
    localStorage.removeItem(AUTH_SESSION_KEY)
    notifyAuthChange(false, reason)
    return clearPrivateCaches().catch(() => {})
  },

  isAuthenticated() {
    return !!getToken()
  },

  getUserId() {
    return getStoredUserId()
  },
  setUserId(uid) {
    getAuthSession()
    setStoredUserId(uid)
    observedAuthState = readAuthState()
  },

  // User context (settings)
  getUserContext(userId) {
    return this.get(`/api/user/${userId}/context`)
  },
  updateUserContext(userId, context) {
    return this.post('/api/user/context', { user_id: userId, context })
  },

  // Tracking
  getTracking(userId, days = 7) {
    return this.get(`/api/tracking/${userId}?days=${days}`)
  },
  getTrackingSummary(userId, days = 7, scope = {}) {
    const params = new URLSearchParams({ days, ...scope })
    return this.get(`/api/tracking/${userId}/summary?${params}`)
  },
  addTrackingEntry(data) {
    return this.post('/api/tracking', data)
  },
  updateTrackingEntry(entryId, data) {
    return this.post(`/api/tracking/entries/${entryId}/update`, data)
  },
  deleteTrackingEntry(entryId, { record_key, revision }) {
    const query = new URLSearchParams({ record_key, revision })
    return this.delete(`/api/tracking/entries/${entryId}?${query}`)
  },
  requestAccountAccess(email, language) {
    return this.post('/api/pilot/account-help', { email, language })
  },
  getAccountRequestStatus(reference) {
    return this.get(`/api/pilot/account-help/${encodeURIComponent(reference)}`)
  },
  getAccountRequests() {
    return this.get('/api/account/requests')
  },
  createAccountRequest(kind, language) {
    return this.post('/api/account/requests', { kind, language })
  },
  getDailySummary(userId) {
    return this.get(`/api/tracking/${userId}/daily-summary`)
  },
  getWeeklySummary(userId) {
    return this.get(`/api/tracking/${userId}/weekly-summary`)
  },

  // Crisis / night mode
  postCrisis(data) {
    return this.post('/api/crisis', data)
  },
  getNightModeRelaxation(language = 'en') {
    return this.post(`/api/night-mode/relaxation?language=${language}`, {})
  },
  getNightModeBreathing(language = 'en') {
    return this.post(`/api/night-mode/breathing?language=${language}`, {})
  },
  getNightModeSafetyTips(language = 'en') {
    return this.get(`/api/night-mode/safety-tips?language=${language}`)
  },

  // Emotional check-in
  postEmotionalCheckin(data) {
    return this.post('/api/emotional-checkin', data)
  },

  // Task management methods
  async createTask(taskType, taskData, priority = 'medium', timeout = null, options = {}) {
    return await this.post('/api/tasks', {
      task_type: taskType,
      task_data: taskData,
      priority,
      timeout
    }, options)
  },

  async getTask(taskId, options = {}) {
    return await this.get(`/api/tasks/${taskId}`, options)
  },

  async getUserTasks(status = null, limit = 50) {
    const params = new URLSearchParams({ limit: limit.toString() })
    if (status) {
      params.append('status', status)
    }
    return await this.get(`/api/tasks?${params.toString()}`)
  },

  async cancelTask(taskId) {
    return await this.delete(`/api/tasks/${taskId}`)
  },

  // Voice methods
  async speechToText(audioFile, language = 'en') {
    const session = getAuthSession()
    const formData = new FormData()
    formData.append('audio', audioFile)
    formData.append('language', language)
    
    const response = await fetch(`${API_BASE}/api/voice/speech-to-text`, {
      method: 'POST',
      headers: {
        ...getAuthHeaders()
      },
      body: formData
    })
    assertSession(session)
    
    if (!response.ok) {
      throw new Error(`Speech-to-text failed: ${response.status}`)
    }
    
    const data = await response.json()
    assertSession(session)
    return data
  },

  async textToSpeech(text, language = 'en', voice = null, speed = 1.0) {
    const session = getAuthSession()
    const response = await fetch(`${API_BASE}/api/voice/text-to-speech`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      },
      body: JSON.stringify({ text, language, voice, speed })
    })
    assertSession(session)
    
    if (!response.ok) {
      throw new Error(`Text-to-speech failed: ${response.status}`)
    }
    
    const audio = await response.blob()
    assertSession(session)
    return audio
  },

  // Family methods
  async createFamily(name) {
    return await this.post('/api/families', { name })
  },

  async getFamilies() {
    return await this.get('/api/families')
  },

  async inviteFamilyMember(familyId, inviteeUserId, role = 'member') {
    return await this.post(`/api/families/${familyId}/invite`, {
      invitee_user_id: inviteeUserId,
      role
    })
  },

  async getFamilyMembers(familyId) {
    return await this.get(`/api/families/${familyId}/members`)
  },

  async getSharedData(familyId, days = 7) {
    return await this.get(`/api/families/${familyId}/shared-data?days=${days}`)
  },

  // Payment methods
  async getSubscription() {
    return await this.get('/api/payments/subscriptions/me')
  },

  async createSubscription(plan, paymentProvider = 'stripe', paymentProviderId = null) {
    return await this.post('/api/payments/subscriptions', {
      plan,
      payment_provider: paymentProvider,
      payment_provider_id: paymentProviderId
    })
  },

  async cancelSubscription(cancelAtPeriodEnd = true) {
    return await this.post('/api/payments/subscriptions/cancel', {
      cancel_at_period_end: cancelAtPeriodEnd
    })
  },

  async checkFeatureAccess(feature) {
    return await this.get(`/api/payments/subscriptions/check-access?feature=${feature}`)
  },

  // Help methods
  async getHelpArticles(category = null, language = 'en', search = null) {
    const params = new URLSearchParams({ language })
    if (category) params.append('category', category)
    if (search) params.append('search', search)
    return await this.get(`/api/help/articles?${params}`)
  },

  async getHelpArticle(articleId) {
    return await this.get(`/api/help/articles/${articleId}`)
  },

  async getFAQs(category = null, language = 'en', search = null) {
    const params = new URLSearchParams({ language })
    if (category) params.append('category', category)
    if (search) params.append('search', search)
    return await this.get(`/api/help/faqs?${params}`)
  },

  async searchHelp(query, language = 'en') {
    return await this.get(`/api/help/search?q=${encodeURIComponent(query)}&language=${language}`)
  },

  async getHelpCategories(language = 'en') {
    return await this.get(`/api/help/categories?language=${language}`)
  },

  async submitHelpFeedback(articleId, faqId, isHelpful, comment = null) {
    return await this.post('/api/help/feedback', {
      article_id: articleId,
      faq_id: faqId,
      is_helpful: isHelpful,
      comment
    })
  },

  // Onboarding methods
  async getOnboardingProgress() {
    return this.get('/api/onboarding/progress')
  },

  async updateOnboardingProgress(data) {
    return this.post('/api/onboarding/progress', data)
  },

  async markStepCompleted(stepId) {
    return this.post('/api/onboarding/step-completed', { step_id: stepId })
  },

  async savePersonalizationData(data) {
    return this.post('/api/onboarding/personalization', { personalization_data: data })
  },

  // Analytics methods
  async trackEvent(eventType, eventName, eventCategory = null, eventData = null, properties = null, sessionId = null, pageUrl = null) {
    return await this.post('/api/analytics/product/events', {
      event_type: eventType,
      event_name: eventName,
      event_category: eventCategory,
      event_data: eventData,
      properties: properties,
      session_id: sessionId,
      page_url: pageUrl
    })
  },

  async getProductDashboard(days = 30) {
    return await this.get(`/api/analytics/product/dashboard?days=${days}`)
  },

  // NPS Survey methods
  async submitNPSSurvey(score, comment = null, context = null) {
    return this.post('/api/feedback/nps', {
      score,
      comment,
      context
    })
  },

  async getNPSStats(days = 30) {
    return this.get(`/api/feedback/nps/stats?days=${days}`)
  },

  // Feature Request methods
  async createFeatureRequest(featureName, description = null, category = null) {
    return this.post('/api/feedback/features', {
      feature_name: featureName,
      description,
      category
    })
  },

  async voteFeatureRequest(featureRequestId) {
    return this.post(`/api/feedback/features/${featureRequestId}/vote`)
  },

  async getFeatureRequests(status = null, category = null, limit = 50) {
    const params = new URLSearchParams({ limit })
    if (status) params.append('status', status)
    if (category) params.append('category', category)
    return this.get(`/api/feedback/features?${params}`)
  },

  // Auto-classify feedback
  async createFeedbackAutoClassify(title, message, category = null, priority = 'medium', metadata = null) {
    return this.post('/api/feedback/auto-classify', {
      category,
      title,
      message,
      priority,
      metadata
    })
  },

  // Recommendation methods
  async getSmartReminders() {
    return this.get('/api/recommendations/smart-reminders')
  },

  async getContentRecommendations(limit = 5) {
    return this.get(`/api/recommendations/content?limit=${limit}`)
  },

  async getMilestones() {
    return this.get('/api/recommendations/milestones')
  },

  // Milestone methods
  async checkMilestones() {
    return this.get('/api/milestones/check')
  },

  async getUserStats() {
    return this.get('/api/milestones/stats')
  },

  // Achievement methods
  async checkAchievements() {
    return this.get('/api/achievements/check')
  },

  async getAchievements() {
    return this.get('/api/achievements')
  },

  async createGoal(goalType, targetValue = null, period = 'daily') {
    return this.post('/api/achievements/goals', {
      goal_type: goalType,
      target_value: targetValue,
      period
    })
  },

  async getGoals(activeOnly = true) {
    return this.get(`/api/achievements/goals?active_only=${activeOnly}`)
  },

  async updateGoalProgress(goalId, increment = 1) {
    return this.post(`/api/achievements/goals/${goalId}/progress?increment=${increment}`)
  },

  // Data Analysis methods
  async predictTrends(entryType, days = 30) {
    return this.get(`/api/analysis/predict/${entryType}?days=${days}`)
  },

  async comparePeriods(entryType, period1Days = 7, period2Days = 7) {
    return this.get(`/api/analysis/compare/${entryType}?period1_days=${period1Days}&period2_days=${period2Days}`)
  },

  async detectAnomalies(entryType, days = 30) {
    return this.get(`/api/analysis/anomalies/${entryType}?days=${days}`)
  },

  async generateReport(days = 30) {
    return this.get(`/api/analysis/report?days=${days}`)
  },

  // Referral methods
  async getReferralCode() {
    return this.get('/api/referrals/code')
  },

  async trackReferral(referredUserId, referralCode = null) {
    return this.post('/api/referrals/track', {
      referred_user_id: referredUserId,
      referral_code: referralCode
    })
  },

  async getReferralStats(days = 30) {
    return this.get(`/api/referrals/stats?days=${days}`)
  },

  async validateReferralCode(referralCode) {
    return this.get(`/api/referrals/validate/${referralCode}`)
  },

  // User Health methods
  async getHealthScore() {
    return this.get('/api/health/score')
  },

  async getInterventions() {
    return this.get('/api/health/interventions')
  },

  // Security methods
  async setup2FA() {
    return this.post('/api/security/2fa/setup')
  },

  async enable2FA(verificationToken) {
    const response = await this.post('/api/security/2fa/enable', {
      verification_token: verificationToken
    })
    const clearing = this.logout()
    triggerUnauthorized()
    await clearing
    return response
  },

  async disable2FA() {
    const response = await this.post('/api/security/2fa/disable')
    const clearing = this.logout()
    triggerUnauthorized()
    await clearing
    return response
  },

  async get2FAStatus() {
    return this.get('/api/security/2fa/status')
  },

  async verify2FA(token) {
    return this.post('/api/security/2fa/verify', { token })
  },

  async getDevices(activeOnly = true) {
    return this.get(`/api/security/devices?active_only=${activeOnly}`)
  },

  async registerDevice(deviceName = null) {
    return this.post(`/api/security/devices/register${deviceName ? `?device_name=${deviceName}` : ''}`)
  },

  async removeDevice(deviceId) {
    return this.delete(`/api/security/devices/${deviceId}`)
  },

  async trustDevice(deviceId, isTrusted = true) {
    return this.post(`/api/security/devices/${deviceId}/trust?is_trusted=${isTrusted}`)
  },

  async getLoginHistory(limit = 50) {
    return this.get(`/api/security/login-history?limit=${limit}`)
  }
}

export const getApiBase = () => API_BASE
export default api
