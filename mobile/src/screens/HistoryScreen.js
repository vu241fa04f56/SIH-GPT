/**
 * HistoryScreen.js — Climate Trends & Historical Weather Analytics
 *
 * Features:
 *  • Multi-period historical analysis (7, 14, 30, 90 days)
 *  • Variable selector: Temperature, Precipitation, Wind Speed, Humidity, AQI
 *  • Statistical distribution: Mean, Min, Max, Std Dev, Total Accumulation
 *  • Climate trend detection (warming, cooling, wetter, drier, stable)
 *  • Interactive daily anomaly bar visualization
 *  • City selector modal
 *  • Pull-to-refresh
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  RefreshControl, ActivityIndicator, Alert, Modal, FlatList, TextInput,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { fetchHistoricalStats, fetchClimateTrend, fetchAllCities } from '../services/api';
import { COLORS, GRADIENTS } from '../constants/colors';

const PERIODS = [
  { label: '7D', days: 7 },
  { label: '14D', days: 14 },
  { label: '30D', days: 30 },
  { label: '90D', days: 90 },
];

const VARIABLES = [
  { key: 'temperature_2m', label: 'Temperature', unit: '°C', icon: 'thermometer', color: '#f59e0b' },
  { key: 'precipitation', label: 'Rainfall', unit: 'mm', icon: 'rainy', color: '#60a5fa' },
  { key: 'wind_speed_10m', label: 'Wind Speed', unit: 'km/h', icon: 'flag', color: '#34d399' },
  { key: 'relative_humidity_2m', label: 'Humidity', unit: '%', icon: 'water', color: '#818cf8' },
  { key: 'us_aqi', label: 'Air Quality', unit: 'AQI', icon: 'speedometer', color: '#ec4899' },
];

const TREND_META = {
  warming:   { label: 'Warming Trend', icon: 'trending-up', color: '#ef4444', desc: 'Temperatures are running higher than the period average.' },
  cooling:   { label: 'Cooling Trend', icon: 'trending-down', color: '#60a5fa', desc: 'Temperatures are trending cooler than normal.' },
  wetter:    { label: 'Wetter Trend', icon: 'rainy', color: '#3b82f6', desc: 'Increased precipitation intensity detected over recent cycles.' },
  drier:     { label: 'Drying Trend', icon: 'sunny', color: '#f59e0b', desc: 'Precipitation deficit observed compared to seasonal normals.' },
  increasing:{ label: 'Increasing Trend', icon: 'trending-up', color: '#a855f7', desc: 'Values showing an upward climb.' },
  decreasing:{ label: 'Decreasing Trend', icon: 'trending-down', color: '#10b981', desc: 'Values showing a downward trend.' },
  stable:    { label: 'Stable Pattern', icon: 'remove', color: '#10b981', desc: 'Atmospheric conditions within standard seasonal variations.' },
};

export default function HistoryScreen({ selectedCity, setSelectedCity }) {
  const insets = useSafeAreaInsets();

  const [days, setDays]                 = useState(30);
  const [selectedVar, setSelectedVar]   = useState(VARIABLES[0]);
  const [stats, setStats]               = useState(null);
  const [trend, setTrend]               = useState(null);
  const [cities, setCities]             = useState([]);
  const [loading, setLoading]           = useState(true);
  const [refreshing, setRefreshing]     = useState(false);
  const [cityModal, setCityModal]       = useState(false);
  const [citySearch, setCitySearch]     = useState('');

  useEffect(() => {
    fetchAllCities()
      .then(setCities)
      .catch(() => {});
  }, []);

  const loadData = useCallback(async () => {
    try {
      const [statsRes, trendRes] = await Promise.allSettled([
        fetchHistoricalStats(selectedCity.id, days),
        fetchClimateTrend(selectedCity.id, selectedVar.key, days),
      ]);

      if (statsRes.status === 'fulfilled') setStats(statsRes.value);
      if (trendRes.status === 'fulfilled') setTrend(trendRes.value);
    } catch {
      Alert.alert('Error', 'Unable to fetch historical climate statistics.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [selectedCity.id, days, selectedVar.key]);

  useEffect(() => {
    setLoading(true);
    loadData();
  }, [loadData]);

  const varStat = stats ? stats[selectedVar.key] : null;
  const trendDir = trend?.trend_direction || 'stable';
  const meta = TREND_META[trendDir] || TREND_META.stable;

  // Anomaly points calculation for custom bar chart
  const dailyPoints = trend?.daily_points || [];
  const maxVal = Math.max(...dailyPoints.map(p => Math.abs(p.value || 0)), 1);

  const filteredCities = cities.filter(c =>
    (c.city_name || c.name || '').toLowerCase().includes(citySearch.toLowerCase())
  );

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      {/* ── Header ────────────────────────────────────────────────────────── */}
      <View style={styles.header}>
        <View>
          <Text style={styles.screenTag}>CLIMATE OBSERVATORY</Text>
          <Text style={styles.headerTitle}>Historical Climate & Trends</Text>
        </View>

        <TouchableOpacity style={styles.cityBadge} onPress={() => setCityModal(true)}>
          <Ionicons name="location-sharp" size={14} color={COLORS.primary} />
          <Text style={styles.cityName}>{selectedCity.name}</Text>
          <Ionicons name="chevron-down" size={12} color={COLORS.textMuted} />
        </TouchableOpacity>
      </View>

      {/* ── Variable Selector Horizontal Chips ─────────────────────────────── */}
      <View style={styles.varChipsWrap}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.varCarousel}>
          {VARIABLES.map((v) => {
            const isSelected = selectedVar.key === v.key;
            return (
              <TouchableOpacity
                key={v.key}
                style={[styles.varChip, isSelected && { backgroundColor: v.color, borderColor: v.color }]}
                onPress={() => setSelectedVar(v)}
                activeOpacity={0.7}
              >
                <Ionicons name={v.icon} size={14} color={isSelected ? '#fff' : v.color} />
                <Text style={[styles.varChipText, isSelected && styles.varChipTextSelected]}>
                  {v.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      </View>

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => { setRefreshing(true); loadData(); }}
            tintColor={COLORS.primary}
          />
        }
      >
        {/* ── Period Selector Segmented Control ────────────────────────────── */}
        <View style={styles.periodRow}>
          <Text style={styles.periodLabel}>Observation Window:</Text>
          <View style={styles.periodSegment}>
            {PERIODS.map((p) => (
              <TouchableOpacity
                key={p.days}
                style={[styles.periodBtn, days === p.days && styles.periodBtnActive]}
                onPress={() => setDays(p.days)}
              >
                <Text style={[styles.periodBtnText, days === p.days && styles.periodBtnTextActive]}>
                  {p.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {loading ? (
          <View style={styles.loaderContainer}>
            <ActivityIndicator size="large" color={COLORS.primary} />
            <Text style={styles.loadingText}>Computing historical aggregate anomalies...</Text>
          </View>
        ) : (
          <>
            {/* ── Trend Direction Banner ────────────────────────────────────── */}
            <LinearGradient
              colors={[COLORS.bgElevated, `${meta.color}22`]}
              style={[styles.trendBanner, { borderColor: meta.color }]}
            >
              <View style={styles.trendBannerTop}>
                <View style={[styles.trendIconWrap, { backgroundColor: `${meta.color}33` }]}>
                  <Ionicons name={meta.icon} size={20} color={meta.color} />
                </View>
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <Text style={[styles.trendTitle, { color: meta.color }]}>{meta.label}</Text>
                  <Text style={styles.trendSubtitle}>{meta.desc}</Text>
                </View>
              </View>

              <View style={styles.trendStatsRow}>
                <View style={styles.trendStatBox}>
                  <Text style={styles.trendStatVal}>
                    {trend?.mean !== null && trend?.mean !== undefined
                      ? `${trend.mean.toFixed(1)}${selectedVar.unit}`
                      : '—'}
                  </Text>
                  <Text style={styles.trendStatKey}>{days}D Mean</Text>
                </View>

                <View style={styles.trendStatBox}>
                  <Text style={styles.trendStatVal}>
                    {stats?.record_count ?? '—'}
                  </Text>
                  <Text style={styles.trendStatKey}>Records Analyzed</Text>
                </View>

                <View style={styles.trendStatBox}>
                  <Text style={styles.trendStatVal}>
                    {selectedCity.name}
                  </Text>
                  <Text style={styles.trendStatKey}>Station</Text>
                </View>
              </View>
            </LinearGradient>

            {/* ── Daily Timeline & Anomaly Visualization ─────────────────────── */}
            <Text style={styles.sectionTitle}>Daily Trend & Anomaly Profile</Text>
            <View style={styles.chartCard}>
              <View style={styles.chartHeader}>
                <Text style={styles.chartVarTitle}>{selectedVar.label} ({selectedVar.unit})</Text>
                <Text style={styles.chartSub}>Last {dailyPoints.length} Daily Observations</Text>
              </View>

              {dailyPoints.length > 0 ? (
                <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.barsContainer}>
                  {dailyPoints.map((point, idx) => {
                    const val = point.value ?? 0;
                    const heightPct = Math.min(Math.max((val / maxVal) * 100, 8), 100);
                    const isPositive = (point.anomaly ?? 0) >= 0;

                    return (
                      <View key={point.date || idx} style={styles.barColumn}>
                        <Text style={styles.barValText}>{val.toFixed(0)}</Text>
                        <View style={styles.barTrack}>
                          <View
                            style={[
                              styles.barFill,
                              {
                                height: `${heightPct}%`,
                                backgroundColor: isPositive ? selectedVar.color : COLORS.info,
                              },
                            ]}
                          />
                        </View>
                        <Text style={styles.barDateText}>
                          {point.date ? point.date.slice(5) : ''}
                        </Text>
                      </View>
                    );
                  })}
                </ScrollView>
              ) : (
                <Text style={styles.emptyText}>No daily points recorded for this range.</Text>
              )}
            </View>

            {/* ── Summary Statistics Grid ───────────────────────────────────── */}
            <Text style={[styles.sectionTitle, { marginTop: 24 }]}>Aggregate Statistics ({days} Days)</Text>
            <View style={styles.statsGrid}>
              <View style={styles.statCard}>
                <Text style={styles.statKey}>Average (Mean)</Text>
                <Text style={[styles.statVal, { color: selectedVar.color }]}>
                  {varStat?.mean !== null && varStat?.mean !== undefined
                    ? `${varStat.mean.toFixed(1)} ${selectedVar.unit}`
                    : '—'}
                </Text>
              </View>

              <View style={styles.statCard}>
                <Text style={styles.statKey}>Minimum Observed</Text>
                <Text style={styles.statVal}>
                  {varStat?.min !== null && varStat?.min !== undefined
                    ? `${varStat.min.toFixed(1)} ${selectedVar.unit}`
                    : '—'}
                </Text>
              </View>

              <View style={styles.statCard}>
                <Text style={styles.statKey}>Maximum Observed</Text>
                <Text style={styles.statVal}>
                  {varStat?.max !== null && varStat?.max !== undefined
                    ? `${varStat.max.toFixed(1)} ${selectedVar.unit}`
                    : '—'}
                </Text>
              </View>

              <View style={styles.statCard}>
                <Text style={styles.statKey}>
                  {selectedVar.key === 'precipitation' ? 'Total Accumulation' : 'Std Deviation (σ)'}
                </Text>
                <Text style={styles.statVal}>
                  {selectedVar.key === 'precipitation'
                    ? (varStat?.total !== null && varStat?.total !== undefined ? `${varStat.total.toFixed(1)} mm` : '—')
                    : (varStat?.std_dev !== null && varStat?.std_dev !== undefined ? `±${varStat.std_dev.toFixed(2)}` : '—')}
                </Text>
              </View>
            </View>
          </>
        )}
      </ScrollView>

      {/* ── City Selector Modal ─────────────────────────────────────────────── */}
      <Modal visible={cityModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={[styles.modalSheet, { paddingBottom: insets.bottom + 16 }]}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Select City for Historical Trends</Text>
              <TouchableOpacity onPress={() => setCityModal(false)}>
                <Ionicons name="close-circle" size={26} color={COLORS.textMuted} />
              </TouchableOpacity>
            </View>

            <View style={styles.searchBar}>
              <Ionicons name="search" size={16} color={COLORS.textMuted} />
              <TextInput
                style={styles.searchInput}
                placeholder="Search city across India..."
                placeholderTextColor={COLORS.textMuted}
                value={citySearch}
                onChangeText={setCitySearch}
              />
            </View>

            <FlatList
              data={filteredCities}
              keyExtractor={(item) => String(item.id || item.city_id)}
              renderItem={({ item }) => {
                const name = item.city_name || item.name;
                const isSelected = selectedCity.name === name;
                return (
                  <TouchableOpacity
                    style={[styles.cityRow, isSelected && styles.cityRowSelected]}
                    onPress={() => {
                      setSelectedCity({
                        id: item.id || item.city_id,
                        name,
                        lat: item.latitude || item.lat,
                        lon: item.longitude || item.lon,
                      });
                      setCityModal(false);
                      setCitySearch('');
                    }}
                  >
                    <Ionicons
                      name="location-outline"
                      size={18}
                      color={isSelected ? COLORS.primary : COLORS.textMuted}
                    />
                    <Text style={[styles.cityRowText, isSelected && { color: COLORS.primary, fontWeight: '700' }]}>
                      {name}
                    </Text>
                    {isSelected && <Ionicons name="checkmark-sharp" size={16} color={COLORS.primary} />}
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
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
  },
  screenTag: { fontSize: 10, fontWeight: '700', color: COLORS.primary, letterSpacing: 1 },
  headerTitle: { fontSize: 18, fontWeight: '700', color: COLORS.textPrimary },
  cityBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: COLORS.bgElevated,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 20,
    gap: 4,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  cityName: { fontSize: 12, fontWeight: '600', color: COLORS.textPrimary },

  varChipsWrap: { backgroundColor: COLORS.bgCard, borderBottomWidth: 1, borderBottomColor: COLORS.border },
  varCarousel: { paddingHorizontal: 16, paddingVertical: 10, gap: 8 },
  varChip: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    backgroundColor: COLORS.bgElevated,
    gap: 6,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  varChipText: { fontSize: 12, fontWeight: '600', color: COLORS.textSecondary },
  varChipTextSelected: { color: '#fff', fontWeight: '700' },

  scrollContent: { padding: 16, paddingBottom: 40 },
  loaderContainer: { alignItems: 'center', justifyContent: 'center', paddingTop: 80 },
  loadingText: { marginTop: 12, color: COLORS.textSecondary, fontSize: 13 },

  periodRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  periodLabel: { fontSize: 12, color: COLORS.textSecondary, fontWeight: '600' },
  periodSegment: { flexDirection: 'row', backgroundColor: COLORS.bgElevated, borderRadius: 10, padding: 3 },
  periodBtn: { paddingHorizontal: 10, paddingVertical: 5, borderRadius: 8 },
  periodBtnActive: { backgroundColor: COLORS.primary },
  periodBtnText: { fontSize: 11, fontWeight: '700', color: COLORS.textMuted },
  periodBtnTextActive: { color: '#fff' },

  // Trend Banner
  trendBanner: {
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    marginBottom: 20,
  },
  trendBannerTop: { flexDirection: 'row', alignItems: 'center' },
  trendIconWrap: { width: 38, height: 38, borderRadius: 19, alignItems: 'center', justifyContent: 'center' },
  trendTitle: { fontSize: 16, fontWeight: '800' },
  trendSubtitle: { fontSize: 11, color: COLORS.textSecondary, marginTop: 2, lineHeight: 15 },
  trendStatsRow: { flexDirection: 'row', justifyContent: 'space-around', marginTop: 16, paddingTop: 14, borderTopWidth: 1, borderTopColor: 'rgba(255,255,255,0.08)' },
  trendStatBox: { alignItems: 'center' },
  trendStatVal: { fontSize: 15, fontWeight: '700', color: COLORS.textPrimary },
  trendStatKey: { fontSize: 10, color: COLORS.textMuted, marginTop: 2 },

  sectionTitle: { fontSize: 14, fontWeight: '700', color: COLORS.textPrimary, marginBottom: 12 },

  // Chart
  chartCard: {
    backgroundColor: COLORS.bgCard,
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: COLORS.border,
    marginBottom: 20,
  },
  chartHeader: { marginBottom: 14 },
  chartVarTitle: { fontSize: 14, fontWeight: '700', color: COLORS.textPrimary },
  chartSub: { fontSize: 11, color: COLORS.textMuted, marginTop: 2 },
  barsContainer: { flexDirection: 'row', alignItems: 'flex-end', height: 140, paddingTop: 20, gap: 10 },
  barColumn: { alignItems: 'center', width: 34 },
  barValText: { fontSize: 9, color: COLORS.textMuted, marginBottom: 4 },
  barTrack: { width: 12, height: 90, backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: 6, justifyContent: 'flex-end', overflow: 'hidden' },
  barFill: { width: '100%', borderRadius: 6 },
  barDateText: { fontSize: 9, color: COLORS.textMuted, marginTop: 6 },
  emptyText: { color: COLORS.textMuted, fontSize: 12, textAlign: 'center', paddingVertical: 20 },

  // Stats Grid
  statsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  statCard: {
    width: '48%',
    backgroundColor: COLORS.bgCard,
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  statKey: { fontSize: 11, color: COLORS.textMuted, marginBottom: 6 },
  statVal: { fontSize: 16, fontWeight: '700', color: COLORS.textPrimary },

  // Modal
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'flex-end' },
  modalSheet: { backgroundColor: COLORS.bgElevated, borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 16, maxHeight: '75%' },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  modalTitle: { fontSize: 16, fontWeight: '700', color: COLORS.textPrimary },
  searchBar: { flexDirection: 'row', alignItems: 'center', backgroundColor: COLORS.bgCard, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 8, marginBottom: 12, gap: 8 },
  searchInput: { flex: 1, color: COLORS.textPrimary, fontSize: 13 },
  cityRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: COLORS.border, gap: 10 },
  cityRowSelected: { backgroundColor: 'rgba(20,184,166,0.08)' },
  cityRowText: { fontSize: 14, color: COLORS.textPrimary, flex: 1 },
});
