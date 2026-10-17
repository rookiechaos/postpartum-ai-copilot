import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { quickChoices, defaultQuickKeys, saveQuickPreferences } from '../utils/quickPreferences'

export default function QuickActionSettings({ userId, value, onSaved, onClose }) {
  const { t } = useTranslation()
  const [keys, setKeys] = useState([...value])
  const [error, setError] = useState(false)
  const label = key => t(['sleep', 'feedingTimer'].includes(key) ? `interaction.shortcuts.${key}` : `polish.quick.${key}`)
  const move = (index, offset) => setKeys(previous => {
    const next = [...previous]; [next[index], next[index + offset]] = [next[index + offset], next[index]]; return next
  })
  return <section className="shortcut-settings"><h4>{t('interaction.shortcuts.title')}</h4><p>{t('interaction.shortcuts.notice')}</p>
    <fieldset><legend>{t('interaction.shortcuts.choose')}</legend>{quickChoices.map(choice => <label key={choice.key}>
      <input type="checkbox" checked={keys.includes(choice.key)} disabled={!keys.includes(choice.key) && keys.length >= 4}
        onChange={event => setKeys(previous => event.target.checked ? [...previous, choice.key] : previous.filter(key => key !== choice.key))} />{label(choice.key)}
    </label>)}</fieldset>
    <ol>{keys.map((key, index) => <li key={key}><span>{label(key)}</span><div className="pilot-actions">
      <button type="button" className="pilot-button secondary" disabled={index === 0} aria-label={t('interaction.shortcuts.moveUp', { name: label(key) })} onClick={() => move(index, -1)}>{t('interaction.shortcuts.up')}</button>
      <button type="button" className="pilot-button secondary" disabled={index === keys.length - 1} aria-label={t('interaction.shortcuts.moveDown', { name: label(key) })} onClick={() => move(index, 1)}>{t('interaction.shortcuts.down')}</button>
    </div></li>)}</ol>
    {error && <p role="alert">{t('interaction.shortcuts.storageError')}</p>}
    <div className="pilot-actions"><button type="button" className="pilot-button" disabled={keys.length === 0} onClick={() => {
      if (!saveQuickPreferences(userId, keys)) { setError(true); return }
      onSaved(keys)
    }}>{t('work.saveChanges')}</button>
      <button type="button" className="pilot-button secondary" onClick={() => setKeys([...defaultQuickKeys])}>{t('interaction.shortcuts.reset')}</button>
      <button type="button" className="pilot-button secondary" onClick={onClose}>{t('tracking.cancel')}</button>
    </div>
  </section>
}
