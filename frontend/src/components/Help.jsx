import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { HelpCircle, MessageCircle, BarChart3, Heart, Moon, Settings, ChevronRight } from 'lucide-react'
import './Help.css'

function Help() {
  const [activeSection, setActiveSection] = useState(null)

  const sections = [
    {
      id: 'getting-started',
      title: 'Getting Started',
      icon: <HelpCircle size={24} />,
      content: (
        <div>
          <h4>Welcome to Postpartum AI Copilot!</h4>
          <p>This app is designed to support you through your postpartum journey. Here's how to get started:</p>
          <ol>
            <li>Complete the welcome screen to set up your profile</li>
            <li>Start tracking your baby's activities (feeding, diapers, sleep)</li>
            <li>Use the chat feature to ask questions anytime</li>
            <li>Check in with your emotional wellbeing regularly</li>
          </ol>
        </div>
      )
    },
    {
      id: 'chat',
      title: 'AI Chat Assistant',
      icon: <MessageCircle size={24} />,
      content: (
        <div>
          <h4>How to Use the Chat</h4>
          <p>The AI chat assistant is trained specifically for postpartum and newborn care:</p>
          <ul>
            <li><strong>Ask questions:</strong> "Is it normal for my baby to...?"</li>
            <li><strong>Get reassurance:</strong> "Am I doing this right?"</li>
            <li><strong>Learn about patterns:</strong> "What should I expect at this age?"</li>
            <li><strong>Safety concerns:</strong> The AI will always flag red flags and recommend consulting healthcare providers</li>
          </ul>
          <p className="help-note">⚠️ Remember: This app provides general information, not medical diagnosis. Always consult healthcare professionals for medical concerns.</p>
        </div>
      )
    },
    {
      id: 'tracking',
      title: 'Tracking Features',
      icon: <BarChart3 size={24} />,
      content: (
        <div>
          <h4>What Can You Track?</h4>
          <ul>
            <li><strong>Feeding:</strong> Type, duration, amount</li>
            <li><strong>Diapers:</strong> Wet, dirty, or both</li>
            <li><strong>Sleep:</strong> Duration and quality</li>
            <li><strong>Mood:</strong> Your emotional state</li>
            <li><strong>Pumping:</strong> If applicable</li>
          </ul>
          <p>The AI analyzes your tracking data to identify patterns and provide insights about what's normal for your baby's age.</p>
        </div>
      )
    },
    {
      id: 'night-mode',
      title: 'Night Mode',
      icon: <Moon size={24} />,
      content: (
        <div>
          <h4>Crisis Support</h4>
          <p>Night Mode is designed for urgent situations when you need immediate help:</p>
          <ul>
            <li>One-tap access from anywhere in the app</li>
            <li>Quick action buttons for common concerns</li>
            <li>Minimal UI designed for low-light situations</li>
            <li>Concise, actionable responses</li>
          </ul>
          <p>Use Night Mode when you're overwhelmed, baby won't stop crying, or you need immediate guidance.</p>
        </div>
      )
    },
    {
      id: 'checkin',
      title: 'Emotional Check-in',
      icon: <Heart size={24} />,
      content: (
        <div>
          <h4>Mental Health Support</h4>
          <p>Regular emotional check-ins help monitor your wellbeing:</p>
          <ul>
            <li>Rate your overwhelmed, anxiety, and support levels</li>
            <li>Get personalized check-ins</li>
            <li>Receive resource recommendations</li>
            <li>Automatic escalation for high-risk situations</li>
          </ul>
          <p className="help-note">💚 Your mental health matters. If you're struggling, please reach out to healthcare providers or support resources.</p>
        </div>
      )
    },
    {
      id: 'settings',
      title: 'Settings & Privacy',
      icon: <Settings size={24} />,
      content: (
        <div>
          <h4>Managing Your Data</h4>
          <ul>
            <li>Update baby information as they grow</li>
            <li>Adjust preferences (notifications, dark mode)</li>
            <li>Export your data for backup or sharing</li>
            <li>All data is stored locally and securely</li>
          </ul>
          <p>Your privacy is important. We don't share your data with third parties.</p>
        </div>
      )
    }
  ]

  return (
    <div className="help-container">
      <div className="help-header">
        <h2>📚 Help & Support</h2>
        <p>Learn how to get the most out of Postpartum AI Copilot</p>
      </div>

      <div className="help-sections">
        {sections.map((section, index) => (
          <motion.div
            key={section.id}
            className="help-section"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <button
              className="help-section-header"
              onClick={() => setActiveSection(activeSection === section.id ? null : section.id)}
            >
              <div className="help-section-title">
                <div className="help-icon">{section.icon}</div>
                <span>{section.title}</span>
              </div>
              <ChevronRight
                size={20}
                className={`chevron ${activeSection === section.id ? 'open' : ''}`}
              />
            </button>
            {activeSection === section.id && (
              <motion.div
                className="help-section-content"
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
              >
                {section.content}
              </motion.div>
            )}
          </motion.div>
        ))}
      </div>

      <div className="help-footer">
        <div className="help-contact">
          <h4>Need More Help?</h4>
          <p>If you have questions or concerns, please:</p>
          <ul>
            <li>Consult your healthcare provider for medical questions</li>
            <li>Contact Postpartum Support International: 1-800-944-4773</li>
            <li>In case of emergency, call 911</li>
          </ul>
        </div>
      </div>
    </div>
  )
}

export default Help
