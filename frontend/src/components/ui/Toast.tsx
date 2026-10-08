import { CheckCircle2, AlertCircle } from 'lucide-react';
import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

import { cn } from '@/lib/cn';

type Tone = 'success' | 'error';
interface Toast {
  id: number;
  text: string;
  tone: Tone;
}

const ToastContext = createContext<(text: string, tone?: Tone) => void>(() => undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const show = useCallback((text: string, tone: Tone = 'success') => {
    const id = Date.now() + Math.random();
    setToasts((list) => [...list, { id, text, tone }]);
    setTimeout(() => setToasts((list) => list.filter((x) => x.id !== id)), 4000);
  }, []);
  const value = useMemo(() => show, [show]);
  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed inset-x-0 bottom-4 z-[60] flex flex-col items-center gap-2 px-4"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role="status"
            className={cn(
              'pointer-events-auto flex max-w-md items-center gap-3 rounded-button px-4 py-3 text-sm font-semibold shadow-lg',
              toast.tone === 'success'
                ? 'bg-primary-700 text-ink-on-primary'
                : 'bg-danger-bg text-danger-fg',
            )}
          >
            {toast.tone === 'success' ? (
              <CheckCircle2 size={18} aria-hidden="true" />
            ) : (
              <AlertCircle size={18} aria-hidden="true" />
            )}
            {toast.text}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
