import React from 'react'
import { useTranslation } from 'react-i18next'
import { Inbox, Plus, TrendingUp } from 'lucide-react'
import Button from './ui/Button'
import './EmptyState.css'

/**
 * EmptyState Component - Displays friendly empty state messages
 */
function EmptyState({ 
  type = 'default',
  title,
  description,
  actionLabel,
  onAction,
  icon,
  suggestions,
  compact = false,
  headingLevel = 3
}) {
  const { t } = useTranslation()

  // Default configurations for different types
  const configs = {
    dashboard: {
      icon: <Inbox size={48} />,
      title: t('emptyState.dashboard.title', 'Welcome to Your Dashboard!'),
      description: t('emptyState.dashboard.description', 'Start tracking your baby\'s activities to see insights here.'),
      actionLabel: t('emptyState.dashboard.action', 'Start Tracking'),
      suggestions: [
        t('emptyState.dashboard.suggestion1', 'Log your first feeding'),
        t('emptyState.dashboard.suggestion2', 'Record a diaper change'),
        t('emptyState.dashboard.suggestion3', 'Track sleep duration')
      ]
    },
    tracking: {
      icon: <Plus size={48} />,
      title: t('emptyState.tracking.title', 'No Tracking Data Yet'),
      description: t('emptyState.tracking.description', 'Start tracking your baby\'s activities to see patterns and insights.'),
      actionLabel: t('emptyState.tracking.action', 'Add First Entry'),
      suggestions: [
        t('emptyState.tracking.suggestion1', 'Track feeding times and amounts'),
        t('emptyState.tracking.suggestion2', 'Record diaper changes'),
        t('emptyState.tracking.suggestion3', 'Monitor sleep patterns')
      ]
    },
    charts: {
      icon: <TrendingUp size={48} />,
      title: t('emptyState.charts.title', 'No Data to Display'),
      description: t('emptyState.charts.description', 'Start tracking activities to see beautiful charts and trends.'),
      actionLabel: t('emptyState.charts.action', 'Start Tracking'),
      suggestions: [
        t('emptyState.charts.suggestion1', 'Track at least 3-4 entries'),
        t('emptyState.charts.suggestion2', 'Data will appear automatically'),
        t('emptyState.charts.suggestion3', 'View trends over time')
      ]
    },
    chat: {
      icon: <Inbox size={48} />,
      title: t('emptyState.chat.title', 'Start a Conversation'),
      description: t('emptyState.chat.description', 'Ask me anything about postpartum care, baby care, or your wellbeing.'),
      actionLabel: t('emptyState.chat.action', 'Ask a Question'),
      suggestions: [
        t('emptyState.chat.suggestion1', 'How often should I feed my baby?'),
        t('emptyState.chat.suggestion2', 'What are signs of postpartum depression?'),
        t('emptyState.chat.suggestion3', 'How to improve sleep quality?')
      ]
    },
    notifications: {
      icon: <Inbox size={48} />,
      title: t('emptyState.notifications.title', 'No Notifications'),
      description: t('emptyState.notifications.description', 'You don\'t have any notifications yet.'),
      actionLabel: t('emptyState.notifications.action', 'Create Reminder'),
      suggestions: [
        t('emptyState.notifications.suggestion1', 'Set up feeding reminders'),
        t('emptyState.notifications.suggestion2', 'Schedule mood check-ins'),
        t('emptyState.notifications.suggestion3', 'Create custom reminders')
      ]
    },
    default: {
      icon: <Inbox size={48} />,
      title: t('emptyState.default.title', 'Nothing Here Yet'),
      description: t('emptyState.default.description', 'Get started to see content here.'),
      actionLabel: t('emptyState.default.action', 'Get Started')
    }
  }

  const config = configs[type] || configs.default
  const displayIcon = icon === undefined ? config.icon : icon
  const displayTitle = title ?? config.title
  const displayDescription = description ?? config.description
  const displayActionLabel = actionLabel ?? config.actionLabel
  const displaySuggestions = suggestions ?? config.suggestions ?? []
  const Heading = `h${headingLevel}`

  return (
    <div className={`empty-state${compact ? ' empty-state--compact' : ''}`}>
      {displayIcon && <div className="empty-state-icon" aria-hidden="true">
        {displayIcon}
      </div>}
      <Heading className="empty-state-title">{displayTitle}</Heading>
      {displayDescription && <p className="empty-state-description">{displayDescription}</p>}
      
      {displaySuggestions.length > 0 && (
        <div className="empty-state-suggestions">
          <h4>{t('emptyState.suggestionsTitle', 'Quick Start Suggestions:')}</h4>
          <ul>
            {displaySuggestions.map((suggestion, index) => (
              <li key={index}>{suggestion}</li>
            ))}
          </ul>
        </div>
      )}

      {onAction && (
        <Button
          className="empty-state-action"
          onClick={onAction}
        >
          {displayActionLabel}
        </Button>
      )}
    </div>
  )
}

export default EmptyState
