import { api } from './api';

/** Web Push in the browser: permission, subscription, and sending it to the server. */

export type PushSupport = 'supported' | 'unsupported' | 'ios-needs-install';

export function pushSupport(): PushSupport {
  const ios = /iphone|ipad|ipod/i.test(navigator.userAgent);
  const standalone =
    window.matchMedia?.('(display-mode: standalone)').matches ||
    (navigator as Navigator & { standalone?: boolean }).standalone === true;
  if (ios && !standalone) return 'ios-needs-install'; // iOS 16.4+: only installed web apps
  if (
    !('serviceWorker' in navigator) ||
    !('PushManager' in window) ||
    !('Notification' in window)
  ) {
    return 'unsupported';
  }
  return 'supported';
}

function keyBytes(base64url: string): Uint8Array {
  const padded =
    base64url.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - (base64url.length % 4)) % 4);
  return Uint8Array.from(atob(padded), (c) => c.charCodeAt(0));
}

async function registration(): Promise<ServiceWorkerRegistration> {
  // Production registers the full worker on load; in development only its push part runs.
  const existing = await navigator.serviceWorker.getRegistration();
  if (existing) return existing;
  return navigator.serviceWorker.register(import.meta.env.PROD ? '/sw.js' : '/sw.js?push-only=1');
}

export async function currentSubscription(): Promise<PushSubscription | null> {
  if (pushSupport() !== 'supported') return null;
  const reg = await navigator.serviceWorker.getRegistration();
  return (await reg?.pushManager.getSubscription()) ?? null;
}

/** Ask for permission and subscribe. Returns false when the person said no. */
export async function enablePush(publicKey: string): Promise<boolean> {
  const permission = await Notification.requestPermission();
  if (permission !== 'granted') return false;
  const reg = await registration();
  await navigator.serviceWorker.ready;
  const sub =
    (await reg.pushManager.getSubscription()) ??
    (await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: keyBytes(publicKey),
    }));
  await api('/api/notifications/push/', { method: 'POST', body: sub.toJSON() });
  return true;
}

export async function disablePush(): Promise<void> {
  const sub = await currentSubscription();
  if (!sub) return;
  try {
    await api('/api/notifications/push/', { method: 'DELETE', body: { endpoint: sub.endpoint } });
  } finally {
    await sub.unsubscribe();
  }
}
