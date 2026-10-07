import i18n from 'i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import { initReactI18next } from 'react-i18next';

import enAuth from '@/locales/en/auth.json';
import enCommon from '@/locales/en/common.json';
import enDates from '@/locales/en/dates.json';
import ruAuth from '@/locales/ru/auth.json';
import ruCommon from '@/locales/ru/common.json';
import ruDates from '@/locales/ru/dates.json';
import uzAuth from '@/locales/uz/auth.json';
import uzCommon from '@/locales/uz/common.json';
import uzDates from '@/locales/uz/dates.json';

export const LANGUAGES = ['uz', 'ru', 'en'] as const;
export type Language = (typeof LANGUAGES)[number];
export const DEFAULT_LANGUAGE: Language = 'uz';
export const LANGUAGE_STORAGE_KEY = 'dj.language';

export const resources = {
  uz: { common: uzCommon, auth: uzAuth, dates: uzDates },
  ru: { common: ruCommon, auth: ruAuth, dates: ruDates },
  en: { common: enCommon, auth: enAuth, dates: enDates },
} as const;

export function isLanguage(value: unknown): value is Language {
  return typeof value === 'string' && (LANGUAGES as readonly string[]).includes(value);
}

export function currentLanguage(): Language {
  const lng = i18n.resolvedLanguage;
  return isLanguage(lng) ? lng : DEFAULT_LANGUAGE;
}

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    supportedLngs: LANGUAGES,
    nonExplicitSupportedLngs: true,
    load: 'languageOnly',
    fallbackLng: DEFAULT_LANGUAGE,
    defaultNS: 'common',
    ns: ['common', 'auth', 'dates'],
    interpolation: { escapeValue: false },
    returnNull: false,
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: LANGUAGE_STORAGE_KEY,
      caches: ['localStorage'],
    },
  });

const syncDocumentLanguage = (lng: string) => {
  document.documentElement.lang = lng;
  document.title = i18n.t('common:appName');
};
i18n.on('languageChanged', syncDocumentLanguage);
syncDocumentLanguage(currentLanguage());

export default i18n;
