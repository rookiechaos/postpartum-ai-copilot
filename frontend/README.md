# Postpartum AI Copilot - Frontend

Modern React application for postpartum support and newborn care.

## Features

- 🎨 Modern, responsive UI with smooth animations
- 📱 Mobile-first design
- 🎯 Dashboard with quick stats and insights
- 💬 AI-powered chat interface
- 📊 Smart tracking system
- 🌙 Night mode for crisis support
- 💚 Emotional check-ins
- ⚙️ Settings and personalization

## Tech Stack

- React 18
- Vite
- Framer Motion (animations)
- Lucide React (icons)
- Axios (API calls)
- Recharts (data visualization)

## Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Environment Variables

Create a `.env` file:

```
VITE_API_BASE_URL=http://localhost:8000
```

## Project Structure

```
src/
  components/
    ChatInterface.jsx      # Main chat component
    Dashboard.jsx          # Home dashboard
    EmotionalCheckIn.jsx   # Mental health check-in
    NightMode.jsx          # Crisis mode
    Settings.jsx           # User settings
    TrackingPanel.jsx       # Tracking interface
    WelcomeScreen.jsx      # Onboarding
  App.jsx                  # Main app component
  main.jsx                 # Entry point
  utils/
    api.js                 # API utilities
```

## Features in Detail

### Dashboard
- Quick stats overview
- Today's activity summary
- Quick action buttons
- AI-generated insights

### Chat Interface
- Real-time AI conversations
- Context-aware responses
- Suggestion cards
- Red flag warnings

### Tracking
- Feeding logs
- Diaper changes
- Sleep tracking
- Mood entries
- AI pattern analysis

### Night Mode
- One-tap crisis support
- Quick action buttons
- Minimal UI for low-light
- Immediate help

### Emotional Check-in
- Daily wellness assessment
- Risk level detection
- Resource recommendations
- Escalation support

## Responsive Design

The app is fully responsive and optimized for:
- Mobile phones (320px+)
- Tablets (768px+)
- Desktops (1024px+)

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)
