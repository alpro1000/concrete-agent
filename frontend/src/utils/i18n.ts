// src/utils/i18n.ts
// Konfigurace internationalizace

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Import jazykových souborů
import cs from '../locales/cs.json';
import en from '../locales/en.json';
import ru from '../locales/ru.json';

const resources = {
  cs: {
    translation: cs
  },
  en: {
    translation: en
  },
  ru: {
    translation: ru
  }
};

i18n
  // Detekce jazyka z prohlížeče
  .use(LanguageDetector)
  // Integrace s React
  .use(initReactI18next)
  // Inicializace
  .init({
    resources,
    
    // Výchozí jazyk (čeština)
    fallbackLng: 'cs',
    
    // Ladění (pouze ve vývoji)
    debug: process.env.NODE_ENV === 'development',
    
    // Detekce jazyka z localStorage, cookie, navigatoru
    detection: {
      order: ['localStorage', 'cookie', 'navigator'],
      caches: ['localStorage', 'cookie'],
    },
    
    // Interpolace
    interpolation: {
      escapeValue: false, // React už escapuje
    },
    
    // Chování při chybějících překladech
    parseMissingKeyHandler: (key) => {
      console.warn(`Missing translation key: ${key}`);
      return key;
    },
    
    // Namespace (používáme jen jeden)
    defaultNS: 'translation',
    
    // Separátory pro vnořené objekty
    keySeparator: '.',
    nsSeparator: false,
  });

export default i18n;

// Export typů pro lepší TypeScript podporu
export type Language = 'cs' | 'en' | 'ru';

export const supportedLanguages: Language[] = ['cs', 'en', 'ru'];

export const getLanguageNames = (currentLang: Language) => {
  const names = {
    cs: {
      cs: 'Čeština',
      en: 'Angličtina',
      ru: 'Ruština'
    },
    en: {
      cs: 'Czech',
      en: 'English',
      ru: 'Russian'
    },
    ru: {
      cs: 'Чешский',
      en: 'Английский',
      ru: 'Русский'
    }
  };
  
  return names[currentLang] || names.cs;
};