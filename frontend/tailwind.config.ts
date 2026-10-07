import type { Config } from 'tailwindcss';

// Design tokens live as CSS variables (src/styles/tokens.css) so dark mode can swap them.
const token = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    fontFamily: {
      sans: ['Manrope', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
    },
    extend: {
      colors: {
        primary: {
          900: token('primary-900'),
          700: token('primary-700'),
          500: token('primary-500'),
        },
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
        card: '16px',
        button: '14px',
        header: '28px',
      },
      minHeight: { touch: '44px' },
      minWidth: { touch: '44px' },
      transitionDuration: { DEFAULT: '150ms' },
    },
  },
  plugins: [],
} satisfies Config;
