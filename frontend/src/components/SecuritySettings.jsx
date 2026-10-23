import React, { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Shield, Smartphone, History, CheckCircle, X } from 'lucide-react'
import api from '../utils/api'
import errorTracker from '../utils/errorTracker'
import { japanDateTime } from '../utils/japanTime'
import './SecuritySettings.css'

function SecuritySettings({ userId }) {
  const { t, i18n } = useTranslation()
  const [twoFAStatus, setTwoFAStatus] = useState(null)
  const [devices, setDevices] = useState([])
  const [loginHistory, setLoginHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [show2FASetup, setShow2FASetup] = useState(false)
  const [twoFASetupData, setTwoFASetupData] = useState(null)
  const [verificationToken, setVerificationToken] = useState('')
  const [backupCodesSaved, setBackupCodesSaved] = useState(false)
  const [copyStatus, setCopyStatus] = useState('')
  const [error, setError] = useState('')
  const generation = useRef(0)
  const activeOperation = useRef(null)

  useEffect(() => {
    generation.current += 1
    activeOperation.current = null
    clearSetup()
    setTwoFAStatus(null)
    setDevices([])
    setLoginHistory([])
    loadSecurityData()
    return () => {
      generation.current += 1
      activeOperation.current = null
    }
  }, [userId])

  const clearSetup = () => {
    setShow2FASetup(false)
    setTwoFASetupData(null)
    setVerificationToken('')
    setBackupCodesSaved(false)
    setCopyStatus('')
  }

  // A synchronous lock also covers clicks before React applies disabled state.
  const startOperation = () => {
    if (activeOperation.current) return null
    const operation = { generation: generation.current }
    activeOperation.current = operation
    setLoading(true)
    setError('')
    return operation
  }

  const isCurrentOperation = (operation) => activeOperation.current === operation && operation.generation === generation.current

  const finishOperation = (operation) => {
    if (!isCurrentOperation(operation)) return
    activeOperation.current = null
    setLoading(false)
  }

  const fetchSecurityData = async (operation) => {
    const [statusRes, devicesRes, historyRes] = await Promise.all([
      api.get2FAStatus(),
      api.getDevices(),
      api.getLoginHistory()
    ])
    if (!isCurrentOperation(operation)) return
    setTwoFAStatus(statusRes.status)
    setDevices(devicesRes.devices || [])
    setLoginHistory(historyRes.history || [])
  }

  const loadSecurityData = async () => {
    const operation = startOperation()
    if (!operation) return
    try {
      await fetchSecurityData(operation)
    } catch (error) {
      if (!isCurrentOperation(operation)) return
      errorTracker.trackError(error, { action: 'load_security_data' })
      setError(t('pilot.loadFailed'))
    } finally {
      finishOperation(operation)
    }
  }

  const handleSetup2FA = async () => {
    const operation = startOperation()
    if (!operation) return
    clearSetup()
    try {
      const data = await api.setup2FA()
      if (!isCurrentOperation(operation)) return
      const setup = data.setup
      if (typeof setup?.qr_code !== 'string' || !setup.qr_code.startsWith('data:image/png;base64,') ||
        !Array.isArray(setup.backup_codes) || !setup.backup_codes.length ||
        !setup.backup_codes.every(code => typeof code === 'string' && code.trim())) {
        throw new Error('Incomplete authenticator setup')
      }
      // Keep only the material displayed here, in component memory.
      setTwoFASetupData({ qr_code: setup.qr_code, backup_codes: setup.backup_codes })
      setShow2FASetup(true)
    } catch (error) {
      if (!isCurrentOperation(operation)) return
      errorTracker.trackError(error, { action: 'setup_2fa' })
      setError(t('security.actionFailed'))
    } finally {
      finishOperation(operation)
    }
  }

  const handleCopyBackupCodes = async () => {
    if (!twoFASetupData) return
    const operation = startOperation()
    if (!operation) return
    setCopyStatus('')
    try {
      await navigator.clipboard.writeText(twoFASetupData.backup_codes.join('\n'))
      if (isCurrentOperation(operation)) setCopyStatus(t('security.backupCodesCopied'))
    } catch {
      if (isCurrentOperation(operation)) setCopyStatus(t('security.backupCodesCopyFailed'))
    } finally {
      finishOperation(operation)
    }
  }

  const handleCancelSetup = () => {
    if (activeOperation.current) return
    clearSetup()
    setError('')
  }

  const handleEnable2FA = async () => {
    if (!twoFASetupData || !backupCodesSaved || !/^\d{6}$/.test(verificationToken)) return
    const operation = startOperation()
    if (!operation) return
    try {
      await api.enable2FA(verificationToken)
      // The API revokes the session and signs out; unmount also discards setup.
      if (isCurrentOperation(operation)) clearSetup()
    } catch (error) {
      if (!isCurrentOperation(operation)) return
      errorTracker.trackError(error, { action: 'enable_2fa' })
      setError(t('security.actionFailed'))
    } finally {
      finishOperation(operation)
    }
  }

  const handleDisable2FA = async () => {
    if (activeOperation.current) return
    if (!confirm(t('security.confirmDisable2FA', 'Are you sure you want to disable 2FA?'))) {
      return
    }
    
    const operation = startOperation()
    if (!operation) return
    try {
      await api.disable2FA()
    } catch (error) {
      if (!isCurrentOperation(operation)) return
      errorTracker.trackError(error, { action: 'disable_2fa' })
      setError(t('security.actionFailed'))
    } finally {
      finishOperation(operation)
    }
  }

  const handleRemoveDevice = async (deviceId) => {
    if (activeOperation.current) return
    if (!confirm(t('security.confirmRemoveDevice', 'Are you sure you want to remove this device?'))) {
      return
    }
    
    const operation = startOperation()
    if (!operation) return
    try {
      await api.removeDevice(deviceId)
      if (isCurrentOperation(operation)) await fetchSecurityData(operation)
    } catch (error) {
      if (!isCurrentOperation(operation)) return
      errorTracker.trackError(error, { action: 'remove_device' })
      setError(t('security.actionFailed'))
    } finally {
      finishOperation(operation)
    }
  }

  if (loading && !twoFAStatus) {
    return <div className="security-settings-loading">{t('common.loading')}</div>
  }

  return (
    <div className="security-settings">
      {error && <p role="alert">{error} <button disabled={loading} onClick={loadSecurityData}>{t('pilot.retry')}</button></p>}
      <div className="security-header">
        <h2>{t('security.title', 'Security Settings')}</h2>
        <p>{t('security.description', 'Manage your account security')}</p>
      </div>

      {/* Two-Factor Authentication */}
      <div className="security-section">
        <div className="section-header">
          <Shield size={24} />
          <div>
            <h3>{t('security.twoFactorAuth', 'Two-Factor Authentication')}</h3>
            <p>{t('security.twoFactorDesc', 'Add an extra layer of security to your account')}</p>
          </div>
        </div>
        
        {twoFAStatus && (
          <div className="security-status">
            <div className="status-indicator">
              {twoFAStatus.is_enabled ? (
                <CheckCircle size={20} className="status-enabled" />
              ) : (
                <X size={20} className="status-disabled" />
              )}
              <span>
                {twoFAStatus.is_enabled
                  ? t('security.2faEnabled', '2FA is enabled')
                  : t('security.2faDisabled', '2FA is disabled')}
              </span>
            </div>
            
            {show2FASetup && twoFASetupData && (
              <div className="two-fa-setup">
                <h4>{t('security.scanQRCode', 'Scan QR Code')}</h4>
                <img src={twoFASetupData.qr_code} alt={t('security.qrAlt')} className="qr-code" />
                <div className="backup-codes-panel">
                  <h4>{t('security.backupCodesTitle')}</h4>
                  <p>{t('security.backupCodesHelp')}</p>
                  <ul className="backup-codes-list" aria-label={t('security.backupCodesTitle')}>
                    {twoFASetupData.backup_codes.map((code, index) => <li key={index}><code>{code}</code></li>)}
                  </ul>
                  <button type="button" className="btn-secondary" disabled={loading} onClick={handleCopyBackupCodes}>
                    {t('security.copyBackupCodes')}
                  </button>
                  <p className="backup-codes-copy-status" role="status">{copyStatus}</p>
                  <label className="backup-codes-confirmation">
                    <input type="checkbox" checked={backupCodesSaved} disabled={loading} onChange={event => setBackupCodesSaved(event.target.checked)} />
                    <span>{t('security.backupCodesSaved')}</span>
                  </label>
                  <p className="backup-codes-notice">{t('security.backupCodesSignOut')}</p>
                </div>
                <p>{t('security.enterVerificationCode', 'Enter verification code from your authenticator app')}</p>
                <input
                  type="text"
                  value={verificationToken}
                  disabled={loading}
                  onChange={(e) => setVerificationToken(e.target.value)}
                  placeholder="000000"
                  aria-label={t('security.enterVerificationCode')}
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={6}
                  className="verification-input"
                />
                <button className="btn-primary" disabled={loading || !backupCodesSaved || !/^\d{6}$/.test(verificationToken)} onClick={handleEnable2FA}>
                  {t('security.enable', 'Enable 2FA')}
                </button>
                <button className="btn-secondary" disabled={loading} onClick={handleCancelSetup}>
                  {t('common.cancel', 'Cancel')}
                </button>
              </div>
            )}
            
            {!show2FASetup && (
              <div className="security-actions">
                {twoFAStatus.is_enabled ? (
                  <button className="btn-secondary" disabled={loading} onClick={handleDisable2FA}>
                    {t('security.disable2FA', 'Disable 2FA')}
                  </button>
                ) : (
                  <button className="btn-primary" disabled={loading} onClick={handleSetup2FA}>
                    {t('security.setup2FA', 'Setup 2FA')}
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Device Management */}
      <div className="security-section">
        <div className="section-header">
          <Smartphone size={24} />
          <div>
            <h3>{t('security.devices', 'Device Management')}</h3>
            <p>{t('security.devicesDesc', 'Manage devices that have access to your account')}</p>
          </div>
        </div>
        
        <div className="devices-list">
          {devices.length === 0 ? (
            <p className="empty-state">{t('security.noDevices', 'No devices registered')}</p>
          ) : (
            devices.map(device => (
              <div key={device.device_id} className="device-item">
                <div className="device-info">
                  <Smartphone size={20} />
                  <div>
                    <h4>{device.device_name}</h4>
                    <p className="device-meta">
                      {device.device_type} • {device.ip_address} • {japanDateTime(device.last_used, i18n.language)}
                    </p>
                  </div>
                </div>
                <div className="device-actions">
                  {device.is_trusted && (
                    <span className="trusted-badge">{t('security.trusted', 'Trusted')}</span>
                  )}
                  <button
                    className="btn-danger"
                    disabled={loading}
                    onClick={() => handleRemoveDevice(device.device_id)}
                  >
                    {t('security.remove', 'Remove')}
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Login History */}
      <div className="security-section">
        <div className="section-header">
          <History size={24} />
          <div>
            <h3>{t('security.loginHistory', 'Login History')}</h3>
            <p>{t('security.loginHistoryDesc', 'Recent login attempts')}</p>
          </div>
        </div>
        
        <div className="login-history-list">
          {loginHistory.length === 0 ? (
            <p className="empty-state">{t('security.noLoginHistory', 'No login history')}</p>
          ) : (
            loginHistory.map(entry => (
              <div key={entry.id} className={`login-entry ${entry.success ? 'success' : 'failed'}`}>
                <div className="login-info">
                  <div className="login-status">
                    {entry.success ? (
                      <CheckCircle size={16} className="status-success" />
                    ) : (
                      <X size={16} className="status-failed" />
                    )}
                    <span>{entry.success ? t('security.successful', 'Successful') : t('security.failed', 'Failed')}</span>
                  </div>
                  <p className="login-meta">
                    {entry.ip_address} • {entry.login_method} • {japanDateTime(entry.created_at, i18n.language)}
                  </p>
                  {entry.failure_reason && (
                    <p className="failure-reason">{entry.failure_reason}</p>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

export default SecuritySettings
