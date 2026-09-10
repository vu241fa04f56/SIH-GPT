/**
 * api.js — WeatherGPT backend API service layer
 *
 * All API calls go through this module. Handles errors gracefully
 * so screens never crash on network failure.
 */

import axios from 'axios';
import { API_BASE_URL, CHATBOT_URL } from '../constants/api';

const backend = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
  headers: { 'Content-Type': 'application/json' },
});

const chatbot = axios.create({
  baseURL: CHATBOT_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// ─── Weather ──────────────────────────────────────────────────────────────────

export const fetchWeather = async (cityId) => {
  const res = await backend.get(`/predict/weather/${encodeURIComponent(cityId)}`);
  return res.data;
};

export const fetchAllCities = async () => {
  const res = await backend.get('/predict/weather/summary/all');
  return res.data;
};

// ─── Disaster ─────────────────────────────────────────────────────────────────

export const fetchDisasterRisk = async (cityId) => {
  const res = await backend.get(`/predict/disaster/${encodeURIComponent(cityId)}`);
  return res.data;
};

export const fetchDisasterOverlay = async () => {
  try {
    const res = await backend.get('/predict/disaster/overlay/all');
    return res.data;
  } catch (err) {
    const res = await backend.get('/predict/disaster/overlay');
    return res.data;
  }
};

// ─── Agro Advisory ────────────────────────────────────────────────────────────

export const fetchAgroAdvisory = async (cityId, crop = 'rice') => {
  const res = await backend.get(`/advisory/${encodeURIComponent(cityId)}`, { params: { crop } });
  return res.data;
};

// ─── Historical / Climate ─────────────────────────────────────────────────────

export const fetchHistoricalStats = async (cityId, days = 30) => {
  const res = await backend.get(`/history/${cityId}/stats`, { params: { days } });
  return res.data;
};

export const fetchClimateTrend = async (cityId, variable = 'temperature_2m', days = 30) => {
  const res = await backend.get(`/history/${cityId}/trend`, {
    params: { variable, days },
  });
  return res.data;
};

// ─── Chatbot ──────────────────────────────────────────────────────────────────

export const sendChatMessage = async ({ message, language = 'en', lat, lon }) => {
  const res = await chatbot.post('/chat', {
    message,
    language,
    user_lat: lat,
    user_lon: lon,
  });
  return res.data;
};

// ─── Voice ────────────────────────────────────────────────────────────────────

export const transcribeAudio = async (audioUri, language = 'en') => {
  const formData = new FormData();
  formData.append('audio', {
    uri: audioUri,
    type: 'audio/mp4',
    name: 'voice_query.m4a',
  });
  formData.append('language', language);

  const res = await axios.post(`${API_BASE_URL}/voice/transcribe`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 30000,
  });
  return res.data;
};

export const voiceRespond = async (audioUri, language = 'en', lat, lon) => {
  const formData = new FormData();
  formData.append('audio', {
    uri: audioUri,
    type: 'audio/mp4',
    name: 'voice_query.m4a',
  });
  formData.append('language', language);
  if (lat) formData.append('latitude', String(lat));
  if (lon) formData.append('longitude', String(lon));

  const res = await axios.post(`${API_BASE_URL}/voice/respond`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 30000,
  });
  return res.data;
};

// ─── FCM Alerts ───────────────────────────────────────────────────────────────

export const subscribeAlerts = async ({ fcmToken, latitude, longitude, language = 'en' }) => {
  const res = await backend.post('/alerts/subscribe', {
    fcm_token: fcmToken,
    latitude,
    longitude,
    language,
    disaster_types: ['flood', 'cyclone', 'heat_wave', 'earthquake', 'thunderstorm'],
  });
  return res.data;
};

// ─── Health ───────────────────────────────────────────────────────────────────

export const fetchHealth = async () => {
  const res = await backend.get('/health');
  return res.data;
};
