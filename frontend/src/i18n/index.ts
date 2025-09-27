import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

// Import translation files
import cs from './cs.json';
import en from './en.json';
import ru from './ru.json';

import type { Language, LanguageOption } from '../types/api';

// Available language options with flags
export const languageOptions: LanguageOption[] = [
  { code: 'cs', name: 'Čeština', flag: '🇨🇿' },
  { code: 'en', name: 'English', flag: '🇺🇸' },
  { code: 'ru', name: 'Русский', flag: '🇷🇺' },
];

const resources = {
  cs: { translation: cs },
  en: { translation: en },
  ru: { translation: ru },
};

i18n
  .use(initReactI18next) // passes i18n down to react-i18next
  .init({
    resources,
    lng: 'cs', // default language (Czech as per requirements)
    fallbackLng: 'en', // fallback language
    
    interpolation: {
      escapeValue: false, // react already does escaping
    },
    
    // Enable debug mode in development
    debug: import.meta.env.DEV,
    
    // Configure key separator and namespace separator
    keySeparator: '.',
    nsSeparator: ':',
    
    // React specific options
    react: {
      useSuspense: false, // Disable suspense for SSR compatibility
    },
  });

export default i18n;

// Helper function to get language name by code
export const getLanguageName = (code: Language): string => {
  const lang = languageOptions.find(option => option.code === code);
  return lang ? lang.name : code;
};

// Helper function to get language flag by code
export const getLanguageFlag = (code: Language): string => {
  const lang = languageOptions.find(option => option.code === code);
  return lang ? lang.flag : '🌐';
};