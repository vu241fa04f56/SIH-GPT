/**
 * ChatScreen.js — AI Chatbot with Voice Support
 *
 * Features:
 *  • Text chat with Gemini LLM (function-calling)
 *  • Voice recording → STT → auto-send
 *  • Language selector (11 Indian languages)
 *  • Message history with typing indicator
 *  • Location context for city-aware responses
 *  • Suggested quick questions
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, FlatList, TextInput, TouchableOpacity,
  KeyboardAvoidingView, Platform, ActivityIndicator, Alert, Modal,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Audio } from 'expo-av';
import * as Haptics from 'expo-haptics';

import { sendChatMessage, voiceRespond } from '../services/api';
import { COLORS, GRADIENTS } from '../constants/colors';
import { LANGUAGES } from '../constants/languages';

const QUICK_PROMPTS = [
  "What's the weather in Delhi today?",
  "Is it safe to travel to Mumbai now?",
  "Flood risk for Chennai this week?",
  "Best time to water crops in Pune?",
  "Air quality forecast for Kolkata?",
  "Will it rain in Hyderabad tomorrow?",
];

const TypingIndicator = () => (
  <View style={styles.typingRow}>
    <View style={styles.botAvatar}><Text style={{ fontSize: 14 }}>🤖</Text></View>
    <View style={styles.typingBubble}>
      <Text style={styles.typingDots}>● ● ●</Text>
    </View>
  </View>
);

export default function ChatScreen({ selectedCity, language, setLanguage }) {
  const insets = useSafeAreaInsets();
  const flatRef = useRef(null);

  const [messages, setMessages]     = useState([
    {
      id: '0',
      role: 'assistant',
      text: `Hello! I'm WeatherGPT 🌤️\n\nAsk me about weather, disaster risks, crop advisories, or climate trends for any Indian city.\n\nCurrently showing: **${selectedCity.name}**`,
      ts: new Date(),
    },
  ]);
  const [input, setInput]           = useState('');
  const [loading, setLoading]       = useState(false);
  const [recording, setRecording]   = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [langModal, setLangModal]   = useState(false);

  const selectedLang = LANGUAGES.find(l => l.code === language) || LANGUAGES[0];

  const scrollToBottom = () => {
    setTimeout(() => flatRef.current?.scrollToEnd({ animated: true }), 100);
  };

  const addMessage = useCallback((role, text) => {
    const msg = { id: Date.now().toString(), role, text, ts: new Date() };
    setMessages(prev => [...prev, msg]);
    scrollToBottom();
    return msg;
  }, []);

  const handleSend = useCallback(async (text = input) => {
    const msg = text.trim();
    if (!msg || loading) return;
    setInput('');
    addMessage('user', msg);
    setLoading(true);

    try {
      const res = await sendChatMessage({ message: msg, language });
      addMessage('assistant', res.reply || res.message || 'Sorry, no response received.');
    } catch (e) {
      addMessage('assistant', '⚠️ Network error. Make sure the WeatherGPT server is running.');
    } finally {
      setLoading(false);
    }
  }, [input, loading, language, addMessage]);

  // ── Voice Recording ─────────────────────────────────────────────────────
  const startRecording = async () => {
    try {
      await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
      const { status } = await Audio.requestPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission Required', 'Microphone access is needed for voice queries.');
        return;
      }
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
      const rec = new Audio.Recording();
      await rec.prepareToRecordAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
      await rec.startAsync();
      setRecording(rec);
      setIsRecording(true);
    } catch (e) {
      Alert.alert('Recording Error', e.message);
    }
  };

  const stopRecording = async () => {
    if (!recording) return;
    try {
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      setIsRecording(false);
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      setRecording(null);
      setLoading(true);

      addMessage('user', '🎙️ Voice message sent…');

      try {
        const res = await voiceRespond(uri, language);
        if (res.transcript && res.transcript !== '(no speech detected)') {
          setMessages(prev => {
            const updated = [...prev];
            updated[updated.length - 1] = { ...updated[updated.length - 1], text: `🎙️ "${res.transcript}"` };
            return updated;
          });
        }
        addMessage('assistant', res.reply || 'Sorry, could not process voice input.');
      } catch (e) {
        addMessage('assistant', '⚠️ Voice processing failed. Try typing your question.');
      } finally {
        setLoading(false);
      }
    } catch (e) {
      Alert.alert('Error', e.message);
      setLoading(false);
    }
  };

  // ── Render Message ──────────────────────────────────────────────────────
  const renderMessage = ({ item }) => {
    const isUser = item.role === 'user';
    return (
      <View style={[styles.msgRow, isUser && styles.msgRowUser]}>
        {!isUser && <View style={styles.botAvatar}><Text style={{ fontSize: 14 }}>🤖</Text></View>}
        <View style={[styles.bubble, isUser ? styles.userBubble : styles.botBubble]}>
          <Text style={[styles.bubbleText, isUser && { color: '#fff' }]}>{item.text}</Text>
          <Text style={styles.msgTime}>
            {item.ts.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </Text>
        </View>
      </View>
    );
  };

  return (
    <LinearGradient colors={GRADIENTS.bg} style={[styles.container, { paddingTop: insets.top }]}>
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>💬 WeatherGPT Chat</Text>
          <Text style={styles.headerSub}>Gemini AI • {selectedCity.name}</Text>
        </View>
        <TouchableOpacity onPress={() => setLangModal(true)} style={styles.langBtn}>
          <Text style={{ fontSize: 16 }}>{selectedLang.flag}</Text>
          <Text style={styles.langCode}>{selectedLang.code.toUpperCase()}</Text>
          <Ionicons name="chevron-down" size={12} color={COLORS.textMuted} />
        </TouchableOpacity>
      </View>

      {/* Quick Prompts */}
      <FlatList
        horizontal
        data={QUICK_PROMPTS}
        keyExtractor={(_, i) => String(i)}
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={{ paddingHorizontal: 14, paddingVertical: 8, gap: 8 }}
        renderItem={({ item }) => (
          <TouchableOpacity style={styles.quickChip} onPress={() => handleSend(item)}>
            <Text style={styles.quickChipText}>{item}</Text>
          </TouchableOpacity>
        )}
      />

      {/* Messages */}
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={90}
      >
        <FlatList
          ref={flatRef}
          data={messages}
          keyExtractor={(m) => m.id}
          renderItem={renderMessage}
          contentContainerStyle={{ padding: 14, gap: 10 }}
          onContentSizeChange={scrollToBottom}
          ListFooterComponent={loading ? <TypingIndicator /> : null}
        />

        {/* Input Row */}
        <View style={styles.inputRow}>
          <TextInput
            style={styles.input}
            placeholder={`Ask about weather in ${selectedCity.name}…`}
            placeholderTextColor={COLORS.textMuted}
            value={input}
            onChangeText={setInput}
            multiline
            maxLength={500}
            onSubmitEditing={() => handleSend()}
          />
          <TouchableOpacity
            style={[styles.voiceBtn, isRecording && styles.voiceBtnActive]}
            onPressIn={startRecording}
            onPressOut={stopRecording}
          >
            <Ionicons name={isRecording ? 'radio' : 'mic'} size={22} color={isRecording ? '#fff' : COLORS.primary} />
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.sendBtn, (!input.trim() || loading) && { opacity: 0.4 }]}
            onPress={() => handleSend()}
            disabled={!input.trim() || loading}
          >
            <Ionicons name="send" size={20} color="#fff" />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>

      {/* Language Modal */}
      <Modal visible={langModal} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalBox}>
            <Text style={styles.modalTitle}>Select Language</Text>
            {LANGUAGES.map(lang => (
              <TouchableOpacity
                key={lang.code}
                style={[styles.langRow, lang.code === language && styles.langRowActive]}
                onPress={() => { setLanguage(lang.code); setLangModal(false); }}
              >
                <Text style={{ fontSize: 20 }}>{lang.flag}</Text>
                <View style={{ flex: 1 }}>
                  <Text style={styles.langName}>{lang.name}</Text>
                  <Text style={styles.langNative}>{lang.nativeName}</Text>
                </View>
                {lang.code === language && <Ionicons name="checkmark-circle" size={20} color={COLORS.primary} />}
              </TouchableOpacity>
            ))}
          </View>
        </View>
      </Modal>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container:        { flex: 1 },
  header:           { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 12 },
  headerTitle:      { fontSize: 17, fontWeight: '700', color: COLORS.textPrimary },
  headerSub:        { fontSize: 12, color: COLORS.textMuted, marginTop: 2 },
  langBtn:          { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: COLORS.bgCard, borderRadius: 20, paddingHorizontal: 10, paddingVertical: 6, borderWidth: 1, borderColor: COLORS.border },
  langCode:         { color: COLORS.textSecondary, fontSize: 12, fontWeight: '600' },
  quickChip:        { backgroundColor: COLORS.bgCard, borderRadius: 20, paddingHorizontal: 12, paddingVertical: 6, borderWidth: 1, borderColor: COLORS.border },
  quickChipText:    { color: COLORS.textSecondary, fontSize: 12 },
  msgRow:           { flexDirection: 'row', alignItems: 'flex-end', gap: 8 },
  msgRowUser:       { justifyContent: 'flex-end' },
  botAvatar:        { width: 32, height: 32, borderRadius: 16, backgroundColor: COLORS.bgElevated, justifyContent: 'center', alignItems: 'center' },
  bubble:           { maxWidth: '78%', borderRadius: 18, padding: 12 },
  botBubble:        { backgroundColor: COLORS.bgCard, borderWidth: 1, borderColor: COLORS.border, borderBottomLeftRadius: 4 },
  userBubble:       { backgroundColor: COLORS.primary, borderBottomRightRadius: 4 },
  bubbleText:       { color: COLORS.textPrimary, fontSize: 14, lineHeight: 20 },
  msgTime:          { fontSize: 10, color: COLORS.textMuted, marginTop: 4, textAlign: 'right' },
  typingRow:        { flexDirection: 'row', alignItems: 'flex-end', gap: 8 },
  typingBubble:     { backgroundColor: COLORS.bgCard, borderRadius: 18, paddingHorizontal: 14, paddingVertical: 10, borderWidth: 1, borderColor: COLORS.border },
  typingDots:       { color: COLORS.textMuted, fontSize: 12, letterSpacing: 4 },
  inputRow:         { flexDirection: 'row', alignItems: 'flex-end', paddingHorizontal: 12, paddingVertical: 10, gap: 8, borderTopWidth: 1, borderTopColor: COLORS.border, backgroundColor: COLORS.bgCard },
  input:            { flex: 1, backgroundColor: COLORS.bgElevated, borderRadius: 20, paddingHorizontal: 14, paddingVertical: 10, color: COLORS.textPrimary, fontSize: 14, maxHeight: 100 },
  voiceBtn:         { width: 42, height: 42, borderRadius: 21, backgroundColor: COLORS.bgElevated, justifyContent: 'center', alignItems: 'center', borderWidth: 1, borderColor: COLORS.primary },
  voiceBtnActive:   { backgroundColor: COLORS.danger },
  sendBtn:          { width: 42, height: 42, borderRadius: 21, backgroundColor: COLORS.primary, justifyContent: 'center', alignItems: 'center' },
  // Modal
  modalOverlay:     { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'flex-end' },
  modalBox:         { backgroundColor: COLORS.bgCard, borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 20, paddingBottom: 40 },
  modalTitle:       { fontSize: 17, fontWeight: '700', color: COLORS.textPrimary, marginBottom: 16 },
  langRow:          { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, gap: 12, borderBottomWidth: 1, borderBottomColor: COLORS.border },
  langRowActive:    { backgroundColor: COLORS.bgGlass },
  langName:         { color: COLORS.textPrimary, fontSize: 15, fontWeight: '600' },
  langNative:       { color: COLORS.textMuted, fontSize: 13 },
});
