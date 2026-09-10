/**
 * HomeScreen.js — Live Weather Dashboard & AI Model Predictions
 *
 * Features:
 *  • 130 Indian cities selector with search
 *  • Live weather conditions (39 meteorological parameters)
 *  • 1-Hour Weather ML Model Forecast (temperature, rain, wind, humidity, pressure, feels-like)
 *  • 3-Hour Disaster Risk ML Model Prediction (risk score, severity, hazard type, action advice)
 *  • Agro Crop Advisory ML Model Prediction (crop risk, irrigation, spraying safety)
 *  • GPS-based auto-detect nearest station
 *  • Real-time WebSocket updates
 *  • Pull-to-refresh
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  RefreshControl, ActivityIndicator, Alert,
  Modal, FlatList, TextInput,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import * as Location from 'expo-location';

import { fetchWeather, fetchAllCities, fetchDisasterRisk, fetchAgroAdvisory } from '../services/api';
import { COLORS, GRADIENTS } from '../constants/colors';
import { WEATHER_CODE_MAP } from '../constants/languages';
import { WS_URL } from '../constants/api';

// ─── Metric Card ──────────────────────────────────────────────────────────────
const MetricCard = ({ icon, label, value, unit, color = COLORS.primary }) => (
  <View style={styles.metricCard}>
    <Ionicons name={icon} size={22} color={color} />
    <Text style={styles.metricValue}>
      {value !== null && value !== undefined ? `${typeof value === 'number' ? value.toFixed(1) : value}${unit}` : '—'}
    </Text>
    <Text style={styles.metricLabel}>{label}</Text>
  </View>
);

export default function HomeScreen({ selectedCity, setSelectedCity, navigation }) {
  const insets = useSafeAreaInsets();
  const [weather, setWeather]       = useState(null);
  const [disaster, setDisaster]     = useState(null);
  const [advisory, setAdvisory]     = useState(null);
  const [cities, setCities]         = useState([]);
  const [loading, setLoading]       = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [cityModal, setCityModal]   = useState(false);
  const [citySearch, setCitySearch] = useState('');
  const [wsStatus, setWsStatus]     = useState('disconnected');
  const wsRef = useRef(null);

  // ── Load cities list once ─────────────────────────────────────────────────
  useEffect(() => {
    fetchAllCities()
      .then(setCities)
      .catch(() => {});
  }, []);

  // ── Load complete prediction bundle for selected city ────────────────────
  const loadAllData = useCallback(async () => {
    try {
      const [wxRes, disRes, advRes] = await Promise.allSettled([
        fetchWeather(selectedCity.id),
        fetchDisasterRisk(selectedCity.id),
        fetchAgroAdvisory(selectedCity.id, 'rice'),
      ]);
      if (wxRes.status === 'fulfilled') setWeather(wxRes.value);
      if (disRes.status === 'fulfilled') setDisaster(disRes.value);
      if (advRes.status === 'fulfilled') setAdvisory(advRes.value);
    } catch {
      // Handled gracefully
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [selectedCity.id]);

  useEffect(() => {
    setLoading(true);
    loadAllData();
  }, [loadAllData]);

  // ── WebSocket live updates ─────────────────────────────────────────────────
  useEffect(() => {
    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;
      ws.onopen  = () => setWsStatus('connected');
      ws.onclose = () => setWsStatus('disconnected');
      ws.onerror = () => setWsStatus('error');
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          if (msg.type === 'weather_update' && msg.city_id === selectedCity.id) {
            loadAllData();
          }
        } catch {}
      };
      return () => ws.close();
    } catch {}
  }, [selectedCity.id]);

  // ── GPS auto-detect ───────────────────────────────────────────────────────
  const detectLocation = async () => {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission Denied', 'Location permission is required for auto-detection.');
        return;
      }
      const loc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
      if (!cities.length) return;

      let nearest = cities[0];
      let minDist = Infinity;
      for (const c of cities) {
        const lat = c.latitude || c.lat;
        const lon = c.longitude || c.lon;
        if (lat && lon) {
          const d = Math.hypot(lat - loc.coords.latitude, lon - loc.coords.longitude);
          if (d < minDist) { minDist = d; nearest = c; }
        }
      }
      setSelectedCity({ id: nearest.city_id || nearest.id, name: nearest.city_name || nearest.name });
    } catch {}
  };

  const current = weather?.current || {};
  const forecast = weather?.forecast_1h || {};
  const agroPreds = advisory?.predictions || {};

  const weatherInfo = weather
    ? WEATHER_CODE_MAP[current.weather_code ?? forecast.weather_code] || { label: 'Mainly Clear', icon: '🌤️' }
    : null;

  const filteredCities = cities.filter(c =>
    (c.city_name || c.name || '').toLowerCase().includes(citySearch.toLowerCase())
  );

  const riskScore = disaster?.risk_score ?? 0;
  const severity = disaster?.severity || (riskScore > 0.8 ? 'extreme' : riskScore > 0.6 ? 'high' : riskScore > 0.3 ? 'moderate' : 'low');
  const severityColor =
    severity === 'extreme' ? COLORS.danger :
    severity === 'high' ? COLORS.high :
    severity === 'moderate' ? COLORS.moderate : COLORS.low;

  const tempDiff = forecast.temperature_2m != null && current.temperature_2m != null
    ? (forecast.temperature_2m - current.temperature_2m)
    : null;

  const aqiColor = (aqi) => {
    if (!aqi) return COLORS.textSecondary;
    if (aqi <= 50) return COLORS.success;
    if (aqi <= 100) return COLORS.warning;
    if (aqi <= 200) return COLORS.high;
    return COLORS.danger;
  };

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      {/* ── Top Bar ────────────────────────────────────────────────────────── */}
      <View style={styles.topBar}>
        <View style={styles.brandRow}>
          <Text style={styles.appTitle}>⛅ WeatherGPT</Text>
          <View style={[styles.wsDot, { backgroundColor: wsStatus === 'connected' ? COLORS.success : COLORS.textMuted }]} />
        </View>
        <View style={styles.headerRight}>
          <TouchableOpacity onPress={detectLocation} style={styles.iconBtn}>
            <Ionicons name="locate" size={18} color={COLORS.primary} />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => setCityModal(true)} style={styles.cityBtn}>
            <Ionicons name="location-sharp" size={14} color={COLORS.primary} />
            <Text style={styles.cityBtnText}>{selectedCity.name}</Text>
            <Ionicons name="chevron-down" size={13} color={COLORS.textSecondary} />
          </TouchableOpacity>
        </View>
      </View>

      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={COLORS.primary} />
          <Text style={styles.loadingText}>Synthesizing ML model forecasts...</Text>
        </View>
      ) : (
        <ScrollView
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => { setRefreshing(true); loadAllData(); }}
              tintColor={COLORS.primary}
            />
          }
          contentContainerStyle={{ padding: 16, paddingBottom: 40 }}
        >
          {/* ── Hero Weather Card ──────────────────────────────────────────── */}
          <LinearGradient colors={['#0d2040', '#0f3460']} style={styles.heroCard}>
            <View style={styles.heroTop}>
              <Text style={styles.weatherEmoji}>{weatherInfo?.icon || '🌡️'}</Text>
              <View style={styles.heroRight}>
                <Text style={styles.tempText}>
                  {current.temperature_2m != null ? `${current.temperature_2m.toFixed(1)}°C` : '—'}
                </Text>
                <Text style={styles.weatherLabel}>{weatherInfo?.label || 'Clear'}</Text>
                <Text style={styles.feelsLike}>
                  Feels like {current.apparent_temperature != null ? `${current.apparent_temperature.toFixed(1)}°C` : '—'}
                </Text>
              </View>
            </View>
            <View style={styles.heroBottom}>
              <Text style={styles.cityName}>{selectedCity.name}, India</Text>
              <Text style={styles.timestamp}>
                {weather?.timestamp ? new Date(weather.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Live'}
              </Text>
            </View>
          </LinearGradient>

          {/* ═════════════════════════════════════════════════════════════════ */}
          {/* ── 1. WEATHER MODEL PREDICTION (1-HOUR AHEAD) ────────────────── */}
          {/* ═════════════════════════════════════════════════════════════════ */}
          <View style={styles.sectionHeaderRow}>
            <Text style={styles.sectionTitle}>1-Hour Model Forecast</Text>
            <View style={styles.modelTag}>
              <Ionicons name="flash" size={11} color={COLORS.primary} />
              <Text style={styles.modelTagText}>XGBoost Model</Text>
            </View>
          </View>

          <View style={styles.forecastCard}>
            <View style={styles.forecastGrid}>
              <View style={styles.forecastTile}>
                <Text style={styles.forecastTileLabel}>Predicted Temp</Text>
                <Text style={[styles.forecastTileVal, { color: COLORS.sunny }]}>
                  {forecast.temperature_2m != null ? `${forecast.temperature_2m.toFixed(1)}°C` : '—'}
                </Text>
                {tempDiff != null && (
                  <Text style={[styles.forecastDiff, { color: tempDiff >= 0 ? COLORS.danger : COLORS.info }]}>
                    {tempDiff >= 0 ? '▲ +' : '▼ '}{tempDiff.toFixed(1)}°C vs now
                  </Text>
                )}
              </View>

              <View style={styles.forecastTile}>
                <Text style={styles.forecastTileLabel}>Predicted Rain</Text>
                <Text style={[styles.forecastTileVal, { color: COLORS.rainy }]}>
                  {forecast.precipitation != null ? `${forecast.precipitation.toFixed(2)} mm` : '0.00 mm'}
                </Text>
                <Text style={styles.forecastSub}>1h accumulation</Text>
              </View>

              <View style={styles.forecastTile}>
                <Text style={styles.forecastTileLabel}>Predicted Wind</Text>
                <Text style={[styles.forecastTileVal, { color: COLORS.success }]}>
                  {forecast.wind_speed_10m != null ? `${forecast.wind_speed_10m.toFixed(1)} km/h` : '—'}
                </Text>
                <Text style={styles.forecastSub}>Surface gusts</Text>
              </View>

              <View style={styles.forecastTile}>
                <Text style={styles.forecastTileLabel}>Humidity</Text>
                <Text style={styles.forecastTileVal}>
                  {forecast.relative_humidity_2m != null ? `${forecast.relative_humidity_2m.toFixed(0)}%` : '—'}
                </Text>
                <Text style={styles.forecastSub}>Relative air</Text>
              </View>

              <View style={styles.forecastTile}>
                <Text style={styles.forecastTileLabel}>Feels Like</Text>
                <Text style={styles.forecastTileVal}>
                  {forecast.apparent_temperature != null ? `${forecast.apparent_temperature.toFixed(1)}°C` : '—'}
                </Text>
                <Text style={styles.forecastSub}>Thermal index</Text>
              </View>

              <View style={styles.forecastTile}>
                <Text style={styles.forecastTileLabel}>Surface Press</Text>
                <Text style={styles.forecastTileVal}>
                  {forecast.surface_pressure != null ? `${forecast.surface_pressure.toFixed(1)} hPa` : '—'}
                </Text>
                <Text style={styles.forecastSub}>Barometer</Text>
              </View>
            </View>
          </View>

          {/* ═════════════════════════════════════════════════════════════════ */}
          {/* ── 2. DISASTER EARLY WARNING PREDICTION ──────────────────────── */}
          {/* ═════════════════════════════════════════════════════════════════ */}
          {disaster && (
            <>
              <View style={[styles.sectionHeaderRow, { marginTop: 20 }]}>
                <Text style={styles.sectionTitle}>3-Hour Disaster Risk Prediction</Text>
                <View style={[styles.modelTag, { backgroundColor: `${severityColor}22` }]}>
                  <Text style={[styles.modelTagText, { color: severityColor }]}>
                    {severity.toUpperCase()} RISK
                  </Text>
                </View>
              </View>

              <View style={[styles.disasterCard, { borderColor: `${severityColor}66` }]}>
                <View style={styles.disasterTopRow}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.disasterTypeTitle}>
                      {disaster.disaster_type && disaster.disaster_type !== 'none'
                        ? disaster.disaster_type.replace(/_/g, ' ').toUpperCase()
                        : 'Normal / Stable Atmospheric Conditions'}
                    </Text>
                    <Text style={styles.disasterLeadText}>
                      ⏱ Lead Time: +{disaster.lead_hours || 3.0} Hours Early Warning
                    </Text>
                  </View>
                  <View style={styles.disasterScoreWrap}>
                    <Text style={[styles.disasterScoreVal, { color: severityColor }]}>
                      {(riskScore * 100).toFixed(1)}%
                    </Text>
                    <Text style={styles.disasterScoreLabel}>Probability</Text>
                  </View>
                </View>

                {/* Progress bar */}
                <View style={styles.riskBarBg}>
                  <View style={[styles.riskBarFill, { width: `${Math.min(Math.max(riskScore * 100, 5), 100)}%`, backgroundColor: severityColor }]} />
                </View>

                <View style={styles.disasterActionBox}>
                  <Ionicons name="shield-checkmark" size={16} color={COLORS.primary} />
                  <Text style={styles.disasterActionText}>
                    {disaster.recommended_action || 'No extreme weather threat detected. Standard monitoring active.'}
                  </Text>
                </View>
              </View>
            </>
          )}

          {/* ═════════════════════════════════════════════════════════════════ */}
          {/* ── 3. AGRO ADVISORY PREDICTION ───────────────────────────────── */}
          {/* ═════════════════════════════════════════════════════════════════ */}
          {advisory && (
            <>
              <View style={[styles.sectionHeaderRow, { marginTop: 20 }]}>
                <Text style={styles.sectionTitle}>Agro Crop Intelligence (Model)</Text>
                <View style={styles.modelTag}>
                  <Ionicons name="leaf" size={11} color={COLORS.success} />
                  <Text style={[styles.modelTagText, { color: COLORS.success }]}>Crop: {advisory.crop_type?.toUpperCase()}</Text>
                </View>
              </View>

              <View style={styles.agroCard}>
                <View style={styles.agroGrid}>
                  <View style={styles.agroTile}>
                    <Text style={styles.agroTileLabel}>Weather Risk</Text>
                    <Text style={[styles.agroTileVal, { color: agroPreds.crop_weather_risk === 'HIGH' ? COLORS.danger : COLORS.success }]}>
                      {agroPreds.crop_weather_risk || advisory.advisory_label || 'LOW'}
                    </Text>
                  </View>

                  <View style={styles.agroTile}>
                    <Text style={styles.agroTileLabel}>Irrigation</Text>
                    <Text style={[styles.agroTileVal, { color: agroPreds.irrigation === 'IRRIGATE' ? COLORS.warning : COLORS.primary }]}>
                      {agroPreds.irrigation || 'NORMAL'}
                    </Text>
                  </View>

                  <View style={styles.agroTile}>
                    <Text style={styles.agroTileLabel}>Spraying Safe</Text>
                    <Text style={[styles.agroTileVal, { color: agroPreds.spraying_suitability === 'UNSAFE' ? COLORS.danger : COLORS.success }]}>
                      {agroPreds.spraying_suitability || 'SAFE'}
                    </Text>
                  </View>
                </View>

                <View style={styles.agroTextBox}>
                  <Text style={styles.agroText}>
                    {advisory.advisory_text || 'Optimal agronomic conditions. Proceed with routine field management.'}
                  </Text>
                </View>
              </View>
            </>
          )}

          {/* ── Current Atmospheric Sensor Metrics ─────────────────────────── */}
          <Text style={[styles.sectionTitle, { marginTop: 22, marginBottom: 12 }]}>Current Station Observations</Text>
          <View style={styles.metricsGrid}>
            <MetricCard icon="water"            label="Humidity"    value={current.relative_humidity_2m} unit="%" color={COLORS.info} />
            <MetricCard icon="speedometer"       label="Wind Speed"  value={current.wind_speed_10m}       unit=" km/h" color={COLORS.secondary} />
            <MetricCard icon="rainy"             label="Precipitation" value={current.precipitation}     unit=" mm" color={COLORS.rainy} />
            <MetricCard icon="sunny"             label="UV Index"   value={current.uv_index}             unit="" color={COLORS.sunny} />
            <MetricCard icon="pulse"             label="Pressure"   value={current.pressure_msl}         unit=" hPa" color={COLORS.textSecondary} />
            <MetricCard icon="cloud"             label="Cloud Cover" value={current.cloud_cover}         unit="%" color={COLORS.cloudy} />
          </View>

          {/* Air Quality */}
          {current.us_aqi != null && (
            <View style={styles.aqiCard}>
              <View style={styles.aqiLeft}>
                <Ionicons name="leaf" size={20} color={aqiColor(current.us_aqi)} />
                <View style={{ marginLeft: 10 }}>
                  <Text style={styles.aqiTitle}>Air Quality Index</Text>
                  <Text style={styles.aqiSub}>US-AQI scale standard</Text>
                </View>
              </View>
              <View style={[styles.aqiBadge, { backgroundColor: aqiColor(current.us_aqi) + '22', borderColor: aqiColor(current.us_aqi) }]}>
                <Text style={[styles.aqiValue, { color: aqiColor(current.us_aqi) }]}>{Math.round(current.us_aqi)} AQI</Text>
              </View>
            </View>
          )}
        </ScrollView>
      )}

      {/* ── City Selector Modal ─────────────────────────────────────────────── */}
      <Modal visible={cityModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContainer, { paddingBottom: insets.bottom + 16 }]}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Select City</Text>
              <TouchableOpacity onPress={() => { setCityModal(false); setCitySearch(''); }}>
                <Ionicons name="close" size={24} color={COLORS.textPrimary} />
              </TouchableOpacity>
            </View>
            <TextInput
              style={styles.searchInput}
              placeholder="Search 130 Indian cities..."
              placeholderTextColor={COLORS.textMuted}
              value={citySearch}
              onChangeText={setCitySearch}
              autoFocus
            />
            <FlatList
              data={filteredCities}
              keyExtractor={(c) => String(c.city_id || c.id)}
              renderItem={({ item }) => {
                const name = item.city_name || item.name;
                const id = item.city_id || item.id;
                const isActive = id === selectedCity.id;
                return (
                  <TouchableOpacity
                    style={[styles.cityRow, isActive && styles.cityRowActive]}
                    onPress={() => {
                      setSelectedCity({ id, name, lat: item.latitude || item.lat, lon: item.longitude || item.lon });
                      setCityModal(false);
                      setCitySearch('');
                    }}
                  >
                    <Ionicons name="location-outline" size={16} color={isActive ? COLORS.primary : COLORS.textMuted} />
                    <Text style={[styles.cityRowText, isActive && { color: COLORS.primary, fontWeight: '700' }]}>
                      {name}
                    </Text>
                    {isActive && <Ionicons name="checkmark" size={16} color={COLORS.primary} />}
                  </TouchableOpacity>
                );
              }}
            />
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg },
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
  },
  brandRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  appTitle: { fontSize: 18, fontWeight: '800', color: COLORS.textPrimary },
  wsDot: { width: 7, height: 7, borderRadius: 4 },
  headerRight: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  iconBtn: {
    padding: 7,
    backgroundColor: COLORS.bgElevated,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  cityBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: COLORS.bgElevated,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 18,
    gap: 4,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  cityBtnText: { fontSize: 12, fontWeight: '600', color: COLORS.textPrimary },
  loadingContainer: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  loadingText: { marginTop: 12, color: COLORS.textSecondary, fontSize: 13 },

  // Hero Card
  heroCard: { borderRadius: 16, padding: 18, marginBottom: 16 },
  heroTop: { flexDirection: 'row', alignItems: 'center' },
  weatherEmoji: { fontSize: 44, marginRight: 16 },
  heroRight: { flex: 1 },
  tempText: { fontSize: 36, fontWeight: '800', color: '#fff' },
  weatherLabel: { fontSize: 15, fontWeight: '600', color: '#93c5fd' },
  feelsLike: { fontSize: 12, color: 'rgba(255,255,255,0.7)', marginTop: 2 },
  heroBottom: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 14, paddingTop: 12, borderTopWidth: 1, borderTopColor: 'rgba(255,255,255,0.1)' },
  cityName: { fontSize: 13, fontWeight: '700', color: '#fff' },
  timestamp: { fontSize: 11, color: 'rgba(255,255,255,0.6)' },

  // Section Headers
  sectionHeaderRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  sectionTitle: { fontSize: 13, fontWeight: '800', color: COLORS.textPrimary, letterSpacing: 0.3 },
  modelTag: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(20,184,166,0.12)', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 10, gap: 4 },
  modelTagText: { fontSize: 10, fontWeight: '700', color: COLORS.primary },

  // Forecast Card
  forecastCard: {
    backgroundColor: COLORS.bgCard,
    borderRadius: 14,
    padding: 12,
    borderWidth: 1,
    borderColor: 'rgba(20,184,166,0.25)',
  },
  forecastGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  forecastTile: {
    width: '31%',
    backgroundColor: COLORS.bgElevated,
    borderRadius: 10,
    padding: 10,
  },
  forecastTileLabel: { fontSize: 9, color: COLORS.textMuted, fontWeight: '600' },
  forecastTileVal: { fontSize: 14, fontWeight: '800', color: COLORS.textPrimary, marginTop: 3 },
  forecastDiff: { fontSize: 9, fontWeight: '700', marginTop: 2 },
  forecastSub: { fontSize: 8, color: COLORS.textMuted, marginTop: 2 },

  // Disaster Card
  disasterCard: {
    backgroundColor: COLORS.bgCard,
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
  },
  disasterTopRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  disasterTypeTitle: { fontSize: 13, fontWeight: '800', color: COLORS.textPrimary },
  disasterLeadText: { fontSize: 10, color: COLORS.textMuted, marginTop: 3 },
  disasterScoreWrap: { alignItems: 'flex-end' },
  disasterScoreVal: { fontSize: 18, fontWeight: '800' },
  disasterScoreLabel: { fontSize: 9, color: COLORS.textMuted },
  riskBarBg: { height: 4, backgroundColor: 'rgba(255,255,255,0.08)', borderRadius: 2, marginVertical: 10, overflow: 'hidden' },
  riskBarFill: { height: '100%', borderRadius: 2 },
  disasterActionBox: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.25)', padding: 8, borderRadius: 8, gap: 8 },
  disasterActionText: { flex: 1, fontSize: 11, color: COLORS.textPrimary, lineHeight: 15 },

  // Agro Card
  agroCard: {
    backgroundColor: COLORS.bgCard,
    borderRadius: 14,
    padding: 12,
    borderWidth: 1,
    borderColor: 'rgba(16,185,129,0.25)',
  },
  agroGrid: { flexDirection: 'row', gap: 8, marginBottom: 10 },
  agroTile: { flex: 1, backgroundColor: COLORS.bgElevated, padding: 8, borderRadius: 8 },
  agroTileLabel: { fontSize: 9, color: COLORS.textMuted },
  agroTileVal: { fontSize: 12, fontWeight: '800', marginTop: 2 },
  agroTextBox: { backgroundColor: 'rgba(0,0,0,0.25)', padding: 10, borderRadius: 8 },
  agroText: { fontSize: 11, color: COLORS.textPrimary, lineHeight: 16 },

  // Metrics Grid
  metricsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  metricCard: {
    width: '31%',
    backgroundColor: COLORS.bgCard,
    borderRadius: 12,
    padding: 12,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  metricValue: { fontSize: 14, fontWeight: '700', color: COLORS.textPrimary, marginTop: 6 },
  metricLabel: { fontSize: 10, color: COLORS.textMuted, marginTop: 2 },

  // AQI Card
  aqiCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: COLORS.bgCard,
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: COLORS.border,
    marginTop: 12,
  },
  aqiLeft: { flexDirection: 'row', alignItems: 'center' },
  aqiTitle: { fontSize: 13, fontWeight: '700', color: COLORS.textPrimary },
  aqiSub: { fontSize: 10, color: COLORS.textMuted },
  aqiBadge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 10, borderWidth: 1 },
  aqiValue: { fontSize: 12, fontWeight: '800' },

  // City Picker Modal
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'flex-end' },
  modalContainer: { backgroundColor: COLORS.bgElevated, borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 16, maxHeight: '75%' },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  modalTitle: { fontSize: 16, fontWeight: '700', color: COLORS.textPrimary },
  searchInput: { backgroundColor: COLORS.bgCard, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10, color: COLORS.textPrimary, fontSize: 13, marginBottom: 12, borderWidth: 1, borderColor: COLORS.border },
  cityRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: COLORS.border, gap: 10 },
  cityRowActive: { backgroundColor: 'rgba(20,184,166,0.08)' },
  cityRowText: { flex: 1, fontSize: 14, color: COLORS.textPrimary },
});
