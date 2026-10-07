import { X } from 'lucide-react';
import { useEffect, useId, useRef } from 'react';
import type { ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { useTranslation } from 'react-i18next';

import { cn } from '@/lib/cn';

interface Props {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  /** "dialog" = centered box, "drawer" = panel sliding from the right */
  variant?: 'dialog' | 'drawer';
  size?: 'sm' | 'md' | 'lg';
}

const FOCUSABLE = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

/** Accessible modal: focus moves inside, Esc closes, focus returns to the opener. */
export function Modal({
  open,
  title,
  onClose,
  children,
  footer,
  variant = 'dialog',
  size = 'md',
}: Props) {
  const { t } = useTranslation();
  const titleId = useId();
  const panel = useRef<HTMLDivElement>(null);
  // Keep the latest onClose without re-running the focus effect on every render.
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    if (!open) return;
    const opener = document.activeElement as HTMLElement | null;
    const first = panel.current?.querySelector<HTMLElement>(`[data-autofocus], ${FOCUSABLE}`);
    first?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeRef.current();
      if (event.key !== 'Tab' || !panel.current) return;
      const items = [...panel.current.querySelectorAll<HTMLElement>(FOCUSABLE)].filter(
        (el) => !el.hasAttribute('disabled'),
      );
      if (!items.length) return;
      const [head, tail] = [items[0], items[items.length - 1]];
      if (event.shiftKey && document.activeElement === head) {
        event.preventDefault();
        tail.focus();
      } else if (!event.shiftKey && document.activeElement === tail) {
        event.preventDefault();
        head.focus();
      }
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      opener?.focus?.();
    };
  }, [open]);

  if (!open) return null;
  const widths = { sm: 'max-w-md', md: 'max-w-xl', lg: 'max-w-3xl' };
  return createPortal(
    <div className="fixed inset-0 z-50 flex">
      <div className="absolute inset-0 bg-ink/40" aria-hidden="true" onClick={onClose} />
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className={cn(
          'relative flex max-h-full w-full flex-col bg-card shadow-xl',
          variant === 'drawer'
            ? 'ml-auto h-full max-w-lg animate-[slide-in_150ms_ease-out]'
            : cn('m-auto max-h-[90dvh] rounded-card', widths[size]),
        )}
      >
        <header className="flex items-center justify-between gap-4 border-b border-line px-6 py-4">
          <h2 id={titleId} className="text-lg font-bold text-ink">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label={t('actions.close')}
            className="flex min-h-touch min-w-touch items-center justify-center rounded-button text-ink-muted hover:bg-subtle"
          >
            <X size={20} aria-hidden="true" />
          </button>
        </header>
        <div className="flex-1 overflow-y-auto px-6 py-4">{children}</div>
        {footer && (
          <footer className="flex flex-wrap justify-end gap-2 border-t border-line px-6 py-4">
            {footer}
          </footer>
        )}
      </div>
    </div>,
    document.body,
  );
}
