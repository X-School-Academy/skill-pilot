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
