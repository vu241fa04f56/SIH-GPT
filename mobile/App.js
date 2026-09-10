/**
 * App.js — Root component with bottom-tab navigation
 *
 * Screens:
 *   🌤  Home      — Live weather dashboard
 *   💬  Chat      — AI chatbot with voice support
 *   🚨  Alerts    — Disaster risk & warnings
 *   🌾  Farm      — Agro advisory
 *   📈  History   — Climate trends
 */

import React, { useState, useCallback } from 'react';
import { StatusBar, View } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

import HomeScreen     from './src/screens/HomeScreen';
import ChatScreen     from './src/screens/ChatScreen';
import DisasterScreen from './src/screens/DisasterScreen';
import AgroScreen     from './src/screens/AgroScreen';
import HistoryScreen  from './src/screens/HistoryScreen';

import { COLORS } from './src/constants/colors';

const Tab = createBottomTabNavigator();

// Shared state: selected city propagated to all tabs
export default function App() {
  const [selectedCity, setSelectedCity] = useState({ id: 1, name: 'Mumbai' });
  const [language, setLanguage] = useState('en');

  const sharedProps = { selectedCity, setSelectedCity, language, setLanguage };

  return (
    <SafeAreaProvider>
      <StatusBar barStyle="light-content" backgroundColor={COLORS.bg} />
      <NavigationContainer
        theme={{
          dark: true,
          colors: {
            primary: COLORS.primary,
            background: COLORS.bg,
            card: COLORS.bgCard,
            text: COLORS.textPrimary,
            border: COLORS.border,
            notification: COLORS.danger,
          },
        }}
      >
        <Tab.Navigator
          screenOptions={({ route }) => ({
            headerShown: false,
            tabBarStyle: {
              backgroundColor: COLORS.bgCard,
              borderTopColor: COLORS.border,
              borderTopWidth: 1,
              height: 65,
              paddingBottom: 10,
              paddingTop: 6,
            },
            tabBarActiveTintColor: COLORS.primary,
            tabBarInactiveTintColor: COLORS.textMuted,
            tabBarLabelStyle: { fontSize: 11, fontWeight: '600', marginTop: 2 },
            tabBarIcon: ({ focused, color, size }) => {
              const icons = {
                Weather:  focused ? 'partly-sunny'       : 'partly-sunny-outline',
                Chat:     focused ? 'chatbubbles'        : 'chatbubbles-outline',
                Alerts:   focused ? 'warning'            : 'warning-outline',
                Farm:     focused ? 'leaf'               : 'leaf-outline',
                History:  focused ? 'stats-chart'        : 'stats-chart-outline',
              };
              return (
                <Ionicons
                  name={icons[route.name] || 'ellipse'}
                  size={focused ? 24 : 22}
                  color={color}
                />
              );
            },
          })}
        >
          <Tab.Screen name="Weather"  children={(p) => <HomeScreen     {...p} {...sharedProps} />} />
          <Tab.Screen name="Chat"     children={(p) => <ChatScreen     {...p} {...sharedProps} />} />
          <Tab.Screen name="Alerts"   children={(p) => <DisasterScreen {...p} {...sharedProps} />} />
          <Tab.Screen name="Farm"     children={(p) => <AgroScreen     {...p} {...sharedProps} />} />
          <Tab.Screen name="History"  children={(p) => <HistoryScreen  {...p} {...sharedProps} />} />
        </Tab.Navigator>
      </NavigationContainer>
    </SafeAreaProvider>
  );
}
