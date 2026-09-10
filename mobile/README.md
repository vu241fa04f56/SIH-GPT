# WeatherGPT Mobile Application (React Native / Expo)

A cross-platform (iOS, Android, and Web) mobile application providing real-time weather intelligence, 3-hour lead disaster early warnings, agricultural advisory, conversational AI assistance with multilingual speech recognition, and historical climate analytics for 130 Indian cities.

---

## 📱 Features & Screens

| Screen | Tab | Description |
|---|---|---|
| **Live Weather** | `🌤 Weather` | Real-time weather dashboard with 1-hour NWP model predictions, GPS auto-detect, 130 Indian cities, and live WebSocket updates. |
| **Conversational AI** | `💬 Chat` | Gemini LLM-driven meteorological assistant with function-calling, voice input (STT), and support for 11 Indian languages. |
| **Disaster Early Warning** | `🚨 Alerts` | 3-hour lead early warnings, hazard probability meter (Flood, Cyclone, Heat Wave, Severe Storm, Drought), official NDMA/IMD action protocols, push alert subscription, and 1-tap SOS emergency dialing (112, NDRF 1070, Ambulance 108, Fire 101). |
| **Agro Intelligence** | `🌾 Farm` | Multi-crop intelligence (Rice, Wheat, Maize, Cotton, Sugarcane, etc.), growth stage tracking, ML risk scores, and 4 core field decisions (Irrigation, Chemical Spraying Window, Heat Stress, Waterlogging). |
| **Climate Trends** | `📈 History` | Historical climate analytics over 7, 14, 30, and 90 days. Visual anomaly bars, trend detection (warming, cooling, wetter, drier), and aggregate distribution (mean, min, max, std dev, total rain). |

---

## 🏗 Architecture & Tech Stack

- **Framework**: React Native 0.74 + Expo SDK 51
- **Navigation**: React Navigation (Bottom Tabs + Stacks)
- **Styling**: Tailored Dark Glassmorphism Design System (`src/constants/colors.js`)
- **Backend API Layer**: Axios with auto-host switching (`localhost` for web/iOS, `10.0.2.2` for Android emulator)
- **Sensors & Hardware**:
  - `expo-location`: High-accuracy GPS city matching
  - `expo-av`: Audio recording for voice queries
  - `expo-notifications`: Push alerts for disaster broadcasts
  - `expo-haptics`: Tactile feedback for actions

---

## 🚀 Quick Start

### 1. Prerequisites
- Node.js >= 18
- WeatherGPT backend running (e.g. via Docker Compose on port 8000 & 8001)

### 2. Install Dependencies
```bash
cd weathergpt/mobile
npm install
```

### 3. Start Development Server
```bash
# Start Expo bundler
npm start

# Or directly run on Web
npm run web

# Or run on Android Emulator
npm run android

# Or run on iOS Simulator
npm run ios
```

### 4. Testing on Physical Mobile Device (Expo Go)
1. Install the **Expo Go** app from the App Store (iOS) or Google Play (Android).
2. Ensure your computer and smartphone are connected to the same Wi-Fi network.
3. In `src/constants/api.js`, set your local LAN IP:
   ```javascript
   export const API_BASE_URL = "http://192.168.1.XX:8000";
   export const CHATBOT_URL  = "http://192.168.1.XX:8001";
   export const WS_URL       = "ws://192.168.1.XX:8000/ws";
   ```
4. Scan the QR code displayed in your terminal using the Expo Go camera (Android) or default Camera app (iOS).
