// apiClient.js — Axios API client for WeatherGPT backend

import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

export const getWeather = (cityIdentifier) =>
  api.get(`/predict/weather/${encodeURIComponent(cityIdentifier)}`).then((r) => r.data)

export const getWeatherSummary = () =>
  api.get('/predict/weather/summary/all').then((r) => r.data)

export const getDisasterRisk = (cityIdentifier) =>
  api.get(`/predict/disaster/${encodeURIComponent(cityIdentifier)}`).then((r) => r.data)

export const getDisasterOverlay = () =>
  api.get('/predict/disaster/overlay/all').then((r) => r.data)

export const getAdvisory = (cityIdentifier, crop = 'rice') =>
  api.get(`/advisory/${encodeURIComponent(cityIdentifier)}`, { params: { crop } }).then((r) => r.data)

export const sendChat = (message, language = 'en', latitude = null, longitude = null) =>
  api.post('/chat', { message, language, latitude, longitude }).then((r) => r.data)

export const subscribeAlerts = (fcmToken, latitude, longitude, language = 'en') =>
  api.post('/alerts/subscribe', { fcm_token: fcmToken, latitude, longitude, language }).then((r) => r.data)

export default api
