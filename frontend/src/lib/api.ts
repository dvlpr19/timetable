import { currentLanguage } from '@/i18n';

import { tokenStore } from './tokens';

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string | undefined,
    public data: unknown,
  ) {
    super(detail ?? `HTTP ${status}`);
  }
}

/** Thrown when the server cannot be reached at all. */
export class NetworkError extends Error {}

type Options = Omit<RequestInit, 'body'> & {
  body?: unknown;
  auth?: boolean;
  /** return the response body as a Blob (file downloads) */
  blob?: boolean;
};

async function refreshAccess(): Promise<boolean> {
  const refresh = tokenStore.refresh;
  if (!refresh) return false;
  const resp = await fetch('/api/auth/refresh/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  });
  if (!resp.ok) {
    tokenStore.clear();
    return false;
  }
  const data = (await resp.json()) as { access: string; refresh?: string };
  tokenStore.set(data.access, data.refresh);
  return true;
}

export async function api<T>(path: string, options: Options = {}, retried = false): Promise<T> {
  const { body, auth = true, blob = false, headers, ...rest } = options;
  const isForm = body instanceof FormData;
  const finalHeaders = new Headers(headers);
  finalHeaders.set('Accept-Language', currentLanguage());
  if (body !== undefined && !isForm) finalHeaders.set('Content-Type', 'application/json');
  const access = tokenStore.access;
  if (auth && access) finalHeaders.set('Authorization', `Bearer ${access}`);

  let resp: Response;
  try {
    resp = await fetch(path, {
      ...rest,
      headers: finalHeaders,
      body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
    });
  } catch (err) {
    throw new NetworkError(String(err));
  }

  if (resp.status === 401 && auth && !retried && (await refreshAccess())) {
    return api<T>(path, options, true);
  }

  if (blob && resp.ok) return (await resp.blob()) as T;
  const data: unknown = resp.status === 204 ? null : await resp.json().catch(() => null);
  if (!resp.ok) {
    const detail =
      data && typeof data === 'object' && 'detail' in data ? String(data.detail) : undefined;
    throw new ApiError(resp.status, detail, data);
  }
  return data as T;
}

/** Download a file from the API (auth + language headers) and save it in the browser. */
export async function download(path: string, filename: string): Promise<void> {
  const file = await api<Blob>(path, { blob: true });
  const url = URL.createObjectURL(file);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
