/**
 * AgroScreen.js — Agricultural Weather Advisory & Crop Intelligence
 *
 * Features:
 *  • Multi-crop intelligence selector (Rice, Wheat, Maize, Cotton, etc.)
 *  • Growth stage & agro-meteorological season detection (Kharif/Rabi)
 *  • Machine Learning agro advisory label & natural-language guidance
 *  • 4 Core Field Decision Cards:
 *     1. 💧 Irrigation Advisory (IRRIGATE, DELAY, NO_IRRIGATION)
 *     2. 🌿 Chemical Spraying Window (SAFE, CAUTION, UNSAFE)
 *     3. ☀️ Heat Stress Index (LOW, MODERATE, HIGH)
 *     4. 🌊 Waterlogging & Drainage Risk (LOW, MODERATE, HIGH)
 *  • 7-Day farming calendar & pest outbreak prevention tips
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

import { fetchAgroAdvisory, fetchAllCities } from '../services/api';
import { COLORS, GRADIENTS } from '../constants/colors';
import { CROPS } from '../constants/languages';

const CROP_ICONS = {
  rice: 'leaf',
  wheat: 'nutrition',
  maize: 'flame',
  sugarcane: 'git-commit',
  cotton: 'cloud',
  soybean: 'radio-button-on',
  groundnut: 'ellipse',
  mustard: 'flower',
  tomato: 'color-palette',
  onion: 'disc',
};

const getStatusColor = (val) => {
  const v = (val || '').toUpperCase();
  if (v.includes('SAFE') || v.includes('LOW') || v.includes('NO_IRRIGATION')) return COLORS.success;
  if (v.includes('CAUTION') || v.includes('MODERATE') || v.includes('DELAY')) return COLORS.warning;
  if (v.includes('UNSAFE') || v.includes('HIGH') || v.includes('IRRIGATE')) return COLORS.accent;
  return COLORS.primary;
};

export default function AgroScreen({ selectedCity, setSelectedCity }) {
  const insets = useSafeAreaInsets();

  const [selectedCrop, setSelectedCrop] = useState('Rice');
  const [advisory, setAdvisory]         = useState(null);
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

  const loadAdvisory = useCallback(async () => {
    try {
      const data = await fetchAgroAdvisory(selectedCity.id, selectedCrop.toLowerCase());
      setAdvisory(data);
    } catch {
      Alert.alert('Network Error', 'Could not load agricultural advisory data.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [selectedCity.id, selectedCrop]);

  useEffect(() => {
    setLoading(true);
    loadAdvisory();
  }, [loadAdvisory]);

  const predictions = advisory?.predictions || {};
  const cropRisk = advisory?.advisory_label || predictions.crop_weather_risk || 'LOW';
  const riskColor = getStatusColor(cropRisk);

  const filteredCities = cities.filter(c =>
    (c.city_name || c.name || '').toLowerCase().includes(citySearch.toLowerCase())
  );

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      {/* ── Header ────────────────────────────────────────────────────────── */}
      <View style={styles.header}>
        <View>
          <Text style={styles.screenTag}>FARM INTELLIGENCE</Text>
          <Text style={styles.headerTitle}>Agro Weather Advisory</Text>
        </View>

        <TouchableOpacity style={styles.cityBadge} onPress={() => setCityModal(true)}>
          <Ionicons name="location-sharp" size={14} color={COLORS.primary} />
          <Text style={styles.cityName}>{selectedCity.name}</Text>
          <Ionicons name="chevron-down" size={12} color={COLORS.textMuted} />
        </TouchableOpacity>
      </View>

      {/* ── Crop Selector Horizontal Carousel ──────────────────────────────── */}
      <View style={styles.cropSelectorWrapper}>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.cropCarousel}
        >
          {CROPS.map((crop) => {
            const isSelected = selectedCrop.toLowerCase() === crop.toLowerCase();
            return (
              <TouchableOpacity
                key={crop}
                style={[styles.cropChip, isSelected && styles.cropChipSelected]}
                onPress={() => setSelectedCrop(crop)}
                activeOpacity={0.7}
              >
                <Ionicons
                  name={CROP_ICONS[crop.toLowerCase()] || 'leaf'}
                  size={14}
                  color={isSelected ? '#fff' : COLORS.textMuted}
                />
                <Text style={[styles.cropChipText, isSelected && styles.cropChipTextSelected]}>
                  {crop}
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
            onRefresh={() => { setRefreshing(true); loadAdvisory(); }}
            tintColor={COLORS.primary}
          />
        }
      >
        {loading ? (
          <View style={styles.loaderContainer}>
            <ActivityIndicator size="large" color={COLORS.primary} />
            <Text style={styles.loadingText}>Synthesizing crop phenology and weather...</Text>
          </View>
        ) : (
          <>
            {/* ── Main Crop Stage & Risk Banner ──────────────────────────────── */}
            <LinearGradient
              colors={[COLORS.bgElevated, 'rgba(20,184,166,0.12)']}
              style={styles.summaryCard}
            >
              <View style={styles.summaryTopRow}>
                <View>
                  <Text style={styles.cropNameTitle}>{selectedCrop}</Text>
                  <Text style={styles.growthStageText}>
                    Stage: <Text style={{ color: COLORS.primary, fontWeight: '700' }}>{advisory?.growth_stage || 'Active Vegetative'}</Text>
                  </Text>
                </View>

                <View style={[styles.riskBadge, { backgroundColor: `${riskColor}22`, borderColor: riskColor }]}>
                  <Text style={[styles.riskBadgeText, { color: riskColor }]}>
                    {cropRisk} RISK
                  </Text>
                </View>
              </View>

              <View style={styles.advisoryTextBox}>
                <Ionicons name="bulb-outline" size={20} color={COLORS.primary} style={{ marginTop: 2 }} />
                <Text style={styles.advisoryText}>
                  {advisory?.advisory_text ||
                    `Weather conditions in ${selectedCity.name} are optimal for ${selectedCrop}. Continue standard field monitoring.`}
                </Text>
              </View>
            </LinearGradient>

            {/* ── 4 Primary Field Decisions Grid ──────────────────────────────── */}
            <Text style={styles.sectionTitle}>Field Operations Guidance</Text>
            <View style={styles.decisionGrid}>
              {/* Irrigation Card */}
              <View style={styles.decisionCard}>
                <View style={styles.decisionHeader}>
                  <View style={[styles.iconWrap, { backgroundColor: 'rgba(59,130,246,0.15)' }]}>
                    <Ionicons name="water" size={18} color="#60a5fa" />
                  </View>
                  <View
                    style={[
                      styles.decisionTag,
                      { backgroundColor: `${getStatusColor(predictions.irrigation)}22` }
                    ]}
                  >
                    <Text style={[styles.decisionTagText, { color: getStatusColor(predictions.irrigation) }]}>
                      {predictions.irrigation || 'NORMAL'}
                    </Text>
                  </View>
                </View>
                <Text style={styles.cardTitle}>Irrigation Needs</Text>
                <Text style={styles.cardDesc}>
                  {predictions.irrigation === 'IRRIGATE'
                    ? 'Soil evapotranspiration high. Water crops during early morning or dusk.'
                    : predictions.irrigation === 'DELAY'
                    ? 'Rain expected within 24-48 hours. Postpone field irrigation.'
                    : 'Soil moisture adequate. No supplemental watering required.'}
                </Text>
              </View>

              {/* Spraying Suitability */}
              <View style={styles.decisionCard}>
                <View style={styles.decisionHeader}>
                  <View style={[styles.iconWrap, { backgroundColor: 'rgba(16,185,129,0.15)' }]}>
                    <Ionicons name="flask" size={18} color="#10b981" />
                  </View>
                  <View
                    style={[
                      styles.decisionTag,
                      { backgroundColor: `${getStatusColor(predictions.spraying_suitability)}22` }
                    ]}
                  >
                    <Text style={[styles.decisionTagText, { color: getStatusColor(predictions.spraying_suitability) }]}>
                      {predictions.spraying_suitability || 'SAFE'}
                    </Text>
                  </View>
                </View>
                <Text style={styles.cardTitle}>Spraying Window</Text>
                <Text style={styles.cardDesc}>
                  {predictions.spraying_suitability === 'UNSAFE'
                    ? 'High winds or rain probability will cause pesticide wash-off.'
                    : 'Winds below 15 km/h and dry conditions permit safe chemical application.'}
                </Text>
              </View>

              {/* Heat Stress Index */}
              <View style={styles.decisionCard}>
                <View style={styles.decisionHeader}>
                  <View style={[styles.iconWrap, { backgroundColor: 'rgba(245,158,11,0.15)' }]}>
                    <Ionicons name="thermometer" size={18} color="#f59e0b" />
                  </View>
                  <View
                    style={[
                      styles.decisionTag,
                      { backgroundColor: `${getStatusColor(predictions.heat_stress)}22` }
                    ]}
                  >
                    <Text style={[styles.decisionTagText, { color: getStatusColor(predictions.heat_stress) }]}>
                      {predictions.heat_stress || 'LOW'}
                    </Text>
                  </View>
                </View>
                <Text style={styles.cardTitle}>Heat Stress Index</Text>
                <Text style={styles.cardDesc}>
                  {predictions.heat_stress === 'HIGH'
                    ? 'Extreme heat may impair pollination. Consider mulching or light misting.'
                    : 'Thermal profile is within safe agronomic thresholds for vegetative health.'}
                </Text>
              </View>

              {/* Waterlogging Risk */}
              <View style={styles.decisionCard}>
                <View style={styles.decisionHeader}>
                  <View style={[styles.iconWrap, { backgroundColor: 'rgba(99,102,241,0.15)' }]}>
                    <Ionicons name="umbrella" size={18} color="#818cf8" />
                  </View>
                  <View
                    style={[
                      styles.decisionTag,
                      { backgroundColor: `${getStatusColor(predictions.waterlogging_risk)}22` }
                    ]}
                  >
                    <Text style={[styles.decisionTagText, { color: getStatusColor(predictions.waterlogging_risk) }]}>
                      {predictions.waterlogging_risk || 'LOW'}
                    </Text>
                  </View>
                </View>
                <Text style={styles.cardTitle}>Waterlogging Risk</Text>
                <Text style={styles.cardDesc}>
                  {predictions.waterlogging_risk === 'HIGH'
                    ? 'Ensure field drainage channels are clear to prevent root rot asphyxiation.'
                    : 'Soil drainage capacity is normal with low precipitation accumulation.'}
                </Text>
              </View>
            </View>

            {/* ── 7-Day Agricultural Checklist & Best Practices ────────────────── */}
            <Text style={[styles.sectionTitle, { marginTop: 24 }]}>Weekly Farming Checklist</Text>
            <View style={styles.checklistCard}>
              <View style={styles.checkItem}>
                <Ionicons name="checkmark-circle" size={20} color={COLORS.primary} />
                <View style={{ flex: 1, marginLeft: 10 }}>
                  <Text style={styles.checkTitle}>Pest & Fungal Surveillance</Text>
                  <Text style={styles.checkDesc}>High relative humidity may trigger blast or aphid infestation in {selectedCrop}. Inspect leaf undersides.</Text>
                </View>
              </View>

              <View style={styles.checkItem}>
                <Ionicons name="checkmark-circle" size={20} color={COLORS.primary} />
                <View style={{ flex: 1, marginLeft: 10 }}>
                  <Text style={styles.checkTitle}>Nutrient Application Window</Text>
                  <Text style={styles.checkDesc}>Apply top-dressing nitrogen fertilizers when soil is moist but no heavy downpours are forecasted.</Text>
                </View>
              </View>

              <View style={styles.checkItem}>
                <Ionicons name="checkmark-circle" size={20} color={COLORS.primary} />
                <View style={{ flex: 1, marginLeft: 10 }}>
                  <Text style={styles.checkTitle}>Storage & Harvesting Precautions</Text>
                  <Text style={styles.checkDesc}>Keep harvested grain stored in dry, moisture-sealed bins with ventilation.</Text>
                </View>
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
              <Text style={styles.modalTitle}>Select City for Agro Advisory</Text>
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

  cropSelectorWrapper: { borderBottomWidth: 1, borderBottomColor: COLORS.border, backgroundColor: COLORS.bgCard },
  cropCarousel: { paddingHorizontal: 16, paddingVertical: 10, gap: 8 },
  cropChip: {
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
  cropChipSelected: { backgroundColor: COLORS.primary, borderColor: COLORS.primary },
  cropChipText: { fontSize: 12, fontWeight: '600', color: COLORS.textSecondary },
  cropChipTextSelected: { color: '#fff', fontWeight: '700' },

  scrollContent: { padding: 16, paddingBottom: 40 },
  loaderContainer: { alignItems: 'center', justifyContent: 'center', paddingTop: 80 },
  loadingText: { marginTop: 12, color: COLORS.textSecondary, fontSize: 13 },

  // Summary Card
  summaryCard: {
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: 'rgba(20,184,166,0.25)',
    marginBottom: 20,
  },
  summaryTopRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  cropNameTitle: { fontSize: 22, fontWeight: '800', color: COLORS.textPrimary },
  growthStageText: { fontSize: 12, color: COLORS.textSecondary, marginTop: 2 },
  riskBadge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12, borderWidth: 1 },
  riskBadgeText: { fontSize: 11, fontWeight: '800', letterSpacing: 0.5 },
  advisoryTextBox: {
    flexDirection: 'row',
    backgroundColor: 'rgba(0,0,0,0.3)',
    borderRadius: 10,
    padding: 12,
    marginTop: 14,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.06)',
  },
  advisoryText: { flex: 1, fontSize: 13, color: COLORS.textPrimary, marginLeft: 10, lineHeight: 18 },

  sectionTitle: { fontSize: 14, fontWeight: '700', color: COLORS.textPrimary, marginBottom: 12 },

  // Decision Grid
  decisionGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 20 },
  decisionCard: {
    width: '48%',
    backgroundColor: COLORS.bgCard,
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  decisionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  iconWrap: { width: 32, height: 32, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  decisionTag: { paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6 },
  decisionTagText: { fontSize: 9, fontWeight: '800' },
  cardTitle: { fontSize: 13, fontWeight: '700', color: COLORS.textPrimary, marginBottom: 4 },
  cardDesc: { fontSize: 11, color: COLORS.textSecondary, lineHeight: 15 },

  // Checklist
  checklistCard: {
    backgroundColor: COLORS.bgCard,
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: COLORS.border,
    gap: 14,
  },
  checkItem: { flexDirection: 'row', alignItems: 'flex-start' },
  checkTitle: { fontSize: 13, fontWeight: '600', color: COLORS.textPrimary },
  checkDesc: { fontSize: 11, color: COLORS.textMuted, marginTop: 2, lineHeight: 15 },

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
