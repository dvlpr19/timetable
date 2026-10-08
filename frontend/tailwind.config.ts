import type { Config } from 'tailwindcss';

// Design tokens live as CSS variables (src/styles/tokens.css) so dark mode can swap them.
const token = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    fontFamily: {
      sans: ['Inter', 'Roboto', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
    },
    extend: {
      colors: {
        primary: {
          900: token('primary-900'),
          700: token('primary-700'),
          500: token('primary-500'),
          300: token('primary-300'),
          200: token('primary-200'),
        },
        accent: token('accent'),
        mint: token('mint'),
        gold: token('gold'),
        page: token('page'),
        card: token('card'),
        subtle: token('subtle'),
        ink: {
          DEFAULT: token('ink'),
          muted: token('ink-muted'),
          'on-primary': token('ink-on-primary'),
        },
        link: token('link'),
        line: token('line'),
        warning: { bg: token('warning-bg'), fg: token('warning-fg') },
        danger: { bg: token('danger-bg'), fg: token('danger-fg') },
        lesson: {
          lecture: token('lesson-lecture'),
          'lecture-bg': token('lesson-lecture-bg'),
          practice: token('lesson-practice'),
          'practice-bg': token('lesson-practice-bg'),
          seminar: token('lesson-seminar'),
          'seminar-bg': token('lesson-seminar-bg'),
          lab: token('lesson-lab'),
          'lab-bg': token('lesson-lab-bg'),
        },
      },
      borderRadius: {
        card: '20px',
        tile: '24px',
        button: '14px',
        header: '32px',
      },
      boxShadow: {
        soft: '0 2px 6px rgb(var(--shadow) / 0.04), 0 8px 24px rgb(var(--shadow) / 0.06)',
        lift: '0 4px 10px rgb(var(--shadow) / 0.06), 0 16px 40px rgb(var(--shadow) / 0.10)',
      },
      backgroundImage: {
        hero: 'linear-gradient(180deg, rgb(var(--primary-700)) 0%, rgb(var(--primary-300)) 100%)',
        feature: 'linear-gradient(90deg, rgb(var(--primary-700)) 0%, rgb(var(--primary-200)) 100%)',
      },
      minHeight: { touch: '44px' },
      minWidth: { touch: '44px' },
      transitionDuration: { DEFAULT: '150ms' },
    },
  },
  plugins: [],
} satisfies Config;
