export const LANGUAGES = [
  { code: 'en', name: 'English',    nativeName: 'English',    flag: '🇬🇧' },
  { code: 'hi', name: 'Hindi',      nativeName: 'हिन्दी',      flag: '🇮🇳' },
  { code: 'bn', name: 'Bengali',    nativeName: 'বাংলা',       flag: '🇧🇩' },
  { code: 'te', name: 'Telugu',     nativeName: 'తెలుగు',      flag: '🇮🇳' },
  { code: 'mr', name: 'Marathi',    nativeName: 'मराठी',       flag: '🇮🇳' },
  { code: 'ta', name: 'Tamil',      nativeName: 'தமிழ்',       flag: '🇮🇳' },
  { code: 'gu', name: 'Gujarati',   nativeName: 'ગુજરાતી',     flag: '🇮🇳' },
  { code: 'kn', name: 'Kannada',    nativeName: 'ಕನ್ನಡ',       flag: '🇮🇳' },
  { code: 'ml', name: 'Malayalam',  nativeName: 'മലയാളം',      flag: '🇮🇳' },
  { code: 'pa', name: 'Punjabi',    nativeName: 'ਪੰਜਾਬੀ',      flag: '🇮🇳' },
  { code: 'ur', name: 'Urdu',       nativeName: 'اردو',         flag: '🇵🇰' },
];

export const WEATHER_CODE_MAP = {
  0:  { label: 'Clear Sky',           icon: '☀️' },
  1:  { label: 'Mainly Clear',        icon: '🌤️' },
  2:  { label: 'Partly Cloudy',       icon: '⛅' },
  3:  { label: 'Overcast',            icon: '☁️' },
  45: { label: 'Foggy',               icon: '🌫️' },
  48: { label: 'Rime Fog',            icon: '🌫️' },
  51: { label: 'Light Drizzle',       icon: '🌦️' },
  61: { label: 'Light Rain',          icon: '🌧️' },
  63: { label: 'Moderate Rain',       icon: '🌧️' },
  65: { label: 'Heavy Rain',          icon: '⛈️' },
  80: { label: 'Rain Showers',        icon: '🌦️' },
  95: { label: 'Thunderstorm',        icon: '⛈️' },
  99: { label: 'Heavy Thunderstorm',  icon: '🌩️' },
};

export const CROPS = [
  'Rice', 'Wheat', 'Maize', 'Sugarcane', 'Cotton',
  'Soybean', 'Groundnut', 'Mustard', 'Tomato', 'Onion',
];

export const DISASTER_COLORS = {
  low:      '#10b981',
  moderate: '#f59e0b',
  high:     '#f97316',
  extreme:  '#ef4444',
  none:     '#6b7280',
};

export const DISASTER_ICONS = {
  flood:             '🌊',
  cyclone:           '🌀',
  heat_wave:         '🌡️',
  heavy_rain:        '🌧️',
  heavy_rainfall:    '⛈️',
  thunderstorm:      '⚡',
  lightning:         '⚡',
  drought:           '🏜️',
  earthquake:        '🫨',
  landslide:         '⛰️',
  cold_wave:         '❄️',
  air_pollution:     '😷',
  strong_winds:      '💨',
  storm_surge:       '🌊',
  tsunami:           '🌊',
  none:              '✅',
};
