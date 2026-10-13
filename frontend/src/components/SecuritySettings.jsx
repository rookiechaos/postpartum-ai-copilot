import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Lock, Shield, Smartphone, History, CheckCircle, X, QrCode } from 'lucide-react'
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
  const [error, setError] = useState('')

  useEffect(() => {
    loadSecurityData()
  }, [userId])

  const loadSecurityData = async () => {
    setLoading(true)
    setError('')
    try {
      const [statusRes, devicesRes, historyRes] = await Promise.all([
        api.get2FAStatus(),
        api.getDevices(),
        api.getLoginHistory()
      ])
      
      setTwoFAStatus(statusRes.status)
      setDevices(devicesRes.devices || [])
      setLoginHistory(historyRes.history || [])
    } catch (error) {
      errorTracker.trackError(error, { action: 'load_security_data' })
      setError(t('pilot.loadFailed'))
    } finally {
      setLoading(false)
    }
  }

  const handleSetup2FA = async () => {
    setLoading(true)
    try {
      const data = await api.setup2FA()
      setTwoFASetupData(data.setup)
      setShow2FASetup(true)
    } catch (error) {
      errorTracker.trackError(error, { action: 'setup_2fa' })
      setError(t('security.actionFailed'))
    } finally {
      setLoading(false)
    }
  }

  const handleEnable2FA = async () => {
    if (!verificationToken) return
    
    setLoading(true)
    try {
      await api.enable2FA(verificationToken)
      setShow2FASetup(false)
      setVerificationToken('')
    } catch (error) {
      errorTracker.trackError(error, { action: 'enable_2fa' })
      setError(t('security.actionFailed'))
    } finally {
      setLoading(false)
    }
  }

  const handleDisable2FA = async () => {
    if (!confirm(t('security.confirmDisable2FA', 'Are you sure you want to disable 2FA?'))) {
      return
    }
    
    setLoading(true)
    try {
      await api.disable2FA()
    } catch (error) {
      errorTracker.trackError(error, { action: 'disable_2fa' })
      setError(t('security.actionFailed'))
    } finally {
      setLoading(false)
    }
  }

  const handleRemoveDevice = async (deviceId) => {
    if (!confirm(t('security.confirmRemoveDevice', 'Are you sure you want to remove this device?'))) {
      return
    }
    
    try {
      await api.removeDevice(deviceId)
      await loadSecurityData()
    } catch (error) {
      errorTracker.trackError(error, { action: 'remove_device' })
      setError(t('security.actionFailed'))
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
                <p>{t('security.enterVerificationCode', 'Enter verification code from your authenticator app')}</p>
                <input
                  type="text"
                  value={verificationToken}
                  onChange={(e) => setVerificationToken(e.target.value)}
                  placeholder="000000"
                  aria-label={t('security.enterVerificationCode')}
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={6}
                  className="verification-input"
                />
                <button className="btn-primary" disabled={loading || !/^\d{6}$/.test(verificationToken)} onClick={handleEnable2FA}>
                  {t('security.enable', 'Enable 2FA')}
                </button>
                <button className="btn-secondary" onClick={() => setShow2FASetup(false)}>
                  {t('common.cancel', 'Cancel')}
                </button>
              </div>
            )}
            
            {!show2FASetup && (
              <div className="security-actions">
                {twoFAStatus.is_enabled ? (
                  <button className="btn-secondary" onClick={handleDisable2FA}>
                    {t('security.disable2FA', 'Disable 2FA')}
                  </button>
                ) : (
                  <button className="btn-primary" onClick={handleSetup2FA}>
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
