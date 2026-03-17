export const getApiBase = (): string => {
  const configured = (process.env.NEXT_PUBLIC_CODES_API || '').replace(/\/$/, '');
  if (typeof window === 'undefined') {
    // SSR: use URL derived from config/settings.json5 via next.config.js
    return configured || (process.env.CODES_API_SSR || '').replace(/\/$/, '') || 'http://127.0.0.1:3001';
  }
  // Browser default: same-origin so Next dev server can proxy /api to engine.
  return configured || '';
};

export const apiUrl = (path: string): string => {
  const base = getApiBase();
  if (!path.startsWith('/')) return `${base}/${path}`;
  return `${base}${path}`;
};

export interface ApiReadyOptions {
  maxWaitMs?: number;
  intervalMs?: number;
  requestTimeoutMs?: number;
}

export interface ApiReadyResult {
  ready: boolean;
  attempts: number;
  timedOut: boolean;
}

const sleep = (ms: number): Promise<void> =>
  new Promise((resolve) => window.setTimeout(resolve, ms));

export async function probeApiHealth(requestTimeoutMs = 1200): Promise<boolean> {
  if (typeof window === 'undefined') return true;

  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), requestTimeoutMs);

  try {
    const response = await fetch(apiUrl('/api/health'), {
      method: 'GET',
      cache: 'no-store',
      credentials: 'include',
      signal: controller.signal,
    });

    if (!response.ok) return false;

    const payload = await response.json().catch(() => null);
    return !payload || payload.status === 'ok';
  } catch {
    return false;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export async function waitForApiReady(options: ApiReadyOptions = {}): Promise<ApiReadyResult> {
  if (typeof window === 'undefined') {
    return { ready: true, attempts: 0, timedOut: false };
  }

  const {
    maxWaitMs = 20000,
    intervalMs = 600,
    requestTimeoutMs = 1200,
  } = options;

  const deadline = Date.now() + maxWaitMs;
  let attempts = 0;

  while (Date.now() <= deadline) {
    attempts += 1;
    if (await probeApiHealth(requestTimeoutMs)) {
      return { ready: true, attempts, timedOut: false };
    }

    if (Date.now() + intervalMs > deadline) {
      break;
    }
    await sleep(intervalMs);
  }

  return { ready: false, attempts, timedOut: true };
}
