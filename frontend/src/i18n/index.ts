import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from './en.json';
import cs from './cs.json';
import ru from './ru.json';

export interface LanguageOption {
  code: string;
  name: string;
  flag: string;
}

export const languageOptions: LanguageOption[] = [
  { code: 'cs', name: 'Čeština', flag: '🇨🇿' },
  { code: 'ru', name: 'Русский', flag: '🇷🇺' },
  { code: 'en', name: 'English', flag: '🇬🇧' },
];

const resources = {
  en: { translation: en },
  cs: { translation: cs },
  ru: { translation: ru },
};

// Get saved language or detect browser language
const savedLanguage = localStorage.getItem('language');
const browserLanguage = navigator.language.split('-')[0];
const defaultLanguage = savedLanguage || 
  (browserLanguage === 'cs' ? 'cs' : 
   browserLanguage === 'ru' ? 'ru' : 
   'cs'); // Fallback to Czech, not English!

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: defaultLanguage,
    fallbackLng: 'cs', // Fallback to Czech!
    interpolation: {
      escapeValue: false,
    },
  });

export default i18n;
