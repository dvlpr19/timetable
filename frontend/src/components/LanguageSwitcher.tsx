import { useTranslation } from 'react-i18next';

import { useAuth } from '@/auth/useAuth';
import { LANGUAGES, currentLanguage } from '@/i18n';

interface Props {
  tone?: 'light' | 'dark';
  className?: string;
}

/** Segmented UZ · RU · EN control. Applies instantly and is saved to the profile. */
export function LanguageSwitcher({ tone = 'light', className = '' }: Props) {
  const { t } = useTranslation();
  const { setLanguage } = useAuth();
  const active = currentLanguage();

  const base =
    tone === 'dark' ? 'bg-white/20 text-ink-on-primary' : 'bg-card text-ink-muted shadow-soft';
  const selected =
    tone === 'dark' ? 'bg-white text-primary-700' : 'bg-primary-700 text-ink-on-primary';

  return (
    <div
      role="group"
      aria-label={t('language.label')}
      className={`inline-flex rounded-full p-1 ${base} ${className}`}
    >
      {LANGUAGES.map((lng) => {
        const isActive = lng === active;
        return (
          <button
            key={lng}
            type="button"
            lang={lng}
            aria-pressed={isActive}
            aria-label={t(`language.${lng}`)}
            title={t(`language.${lng}`)}
            onClick={() => void setLanguage(lng)}
            className={`min-h-touch min-w-touch rounded-full px-3 text-sm font-bold uppercase tracking-wide transition-colors ${
              isActive ? selected : 'hover:opacity-80'
            }`}
          >
            {lng}
          </button>
        );
      })}
    </div>
  );
}
