import React, { useState, useEffect } from 'react'
import { CreditCard, Check, X, Crown, Zap, Building } from 'lucide-react'
import api from '../utils/api'
import './SubscriptionManager.css'

function SubscriptionManager({ userId }) {
  const [subscription, setSubscription] = useState(null)
  const [loading, setLoading] = useState(false)
  const [selectedPlan, setSelectedPlan] = useState(null)

  useEffect(() => {
    loadSubscription()
  }, [userId])

  const loadSubscription = async () => {
    setLoading(true)
    try {
      const data = await api.get('/api/payments/subscriptions/me')
      setSubscription(data)
    } catch (error) {
      console.error('Failed to load subscription:', error)
    } finally {
      setLoading(false)
    }
  }

  const createSubscription = async (plan, provider = 'stripe') => {
    setLoading(true)
    try {
      // In production, this would redirect to payment provider
      // For now, create subscription directly
      const data = await api.post('/api/payments/subscriptions', {
        plan,
        payment_provider: provider,
        payment_provider_id: `test_${Date.now()}`
      })
      setSubscription(data)
      setSelectedPlan(null)
    } catch (error) {
      console.error('Failed to create subscription:', error)
    } finally {
      setLoading(false)
    }
  }

  const cancelSubscription = async () => {
    if (!confirm('Are you sure you want to cancel your subscription?')) return

    setLoading(true)
    try {
      await api.post('/api/payments/subscriptions/cancel', {
        cancel_at_period_end: true
      })
      await loadSubscription()
    } catch (error) {
      console.error('Failed to cancel subscription:', error)
    } finally {
      setLoading(false)
    }
  }

  const plans = [
    {
      id: 'free',
      name: 'Free',
      price: '$0',
      icon: <Check size={24} />,
      features: [
        'Basic AI chat',
        'Tracking entries',
        'Basic notifications',
        'Limited analytics'
      ],
      color: '#48bb78'
    },
    {
      id: 'premium',
      name: 'Premium',
      price: '$9.99/month',
      icon: <Crown size={24} />,
      features: [
        'All Free features',
        'Data export (JSON/CSV/PDF)',
        'Advanced analytics',
        'Family sharing',
        'Voice interaction',
        'Priority support'
      ],
      color: '#667eea',
      popular: true
    },
    {
      id: 'enterprise',
      name: 'Enterprise',
      price: 'Custom',
      icon: <Building size={24} />,
      features: [
        'All Premium features',
        'Custom integrations',
        'Dedicated support',
        'SLA guarantee',
        'Custom branding'
      ],
      color: '#ed8936'
    }
  ]

  const currentPlan = subscription?.plan || 'free'

  return (
    <div className="subscription-manager">
      <div className="subscription-header">
        <h2><CreditCard size={24} /> Subscription & Billing</h2>
        {subscription && (
          <div className="current-subscription">
            <span className="plan-badge">{subscription.plan}</span>
            <span className="status-badge">{subscription.status}</span>
          </div>
        )}
      </div>

      {subscription && subscription.status === 'active' && (
        <div className="subscription-info">
          <div className="info-item">
            <strong>Current Plan:</strong> {subscription.plan}
          </div>
          {subscription.current_period_end && (
            <div className="info-item">
              <strong>Renews:</strong>{' '}
              {new Date(subscription.current_period_end).toLocaleDateString()}
            </div>
          )}
          {subscription.cancel_at_period_end && (
            <div className="info-item warning">
              <strong>⚠️ Cancels at period end</strong>
            </div>
          )}
          <button
            onClick={cancelSubscription}
            className="cancel-button"
            disabled={loading}
          >
            Cancel Subscription
          </button>
        </div>
      )}

      <div className="plans-grid">
        {plans.map(plan => (
          <div
            key={plan.id}
            className={`plan-card ${plan.popular ? 'popular' : ''} ${currentPlan === plan.id ? 'current' : ''}`}
          >
            {plan.popular && <div className="popular-badge">Most Popular</div>}
            {currentPlan === plan.id && (
              <div className="current-badge">Current Plan</div>
            )}
            
            <div className="plan-header">
              <div className="plan-icon" style={{ color: plan.color }}>
                {plan.icon}
              </div>
              <h3>{plan.name}</h3>
              <div className="plan-price">{plan.price}</div>
            </div>

            <ul className="plan-features">
              {plan.features.map((feature, idx) => (
                <li key={idx}>
                  <Check size={16} /> {feature}
                </li>
              ))}
            </ul>

            {currentPlan !== plan.id && (
              <button
                onClick={() => {
                  setSelectedPlan(plan.id)
                  createSubscription(plan.id)
                }}
                className="subscribe-button"
                disabled={loading || plan.id === 'enterprise'}
                style={{ backgroundColor: plan.color }}
              >
                {plan.id === 'enterprise' ? 'Contact Sales' : 'Subscribe'}
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export default SubscriptionManager
