/**
 * api.js — Central API configuration
 *
 * For physical device testing, replace BACKEND_IP with your machine's LAN IP.
 * For Android emulator use 10.0.2.2, for iOS simulator use localhost.
 */

import { Platform } from 'react-native';

const HOST = Platform.OS === 'android' ? '10.0.2.2' : 'localhost';

export const API_BASE_URL = `http://${HOST}:8000`;
export const CHATBOT_URL  = `http://${HOST}:8001`;
export const WS_URL       = `ws://${HOST}:8000/ws`;

