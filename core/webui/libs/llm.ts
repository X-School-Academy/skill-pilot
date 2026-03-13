const PROVIDER_KEY = 'juniorit_llm_provider';
const CLIENT_ID_KEY = 'juniorit_llm_client_id';

type ProviderOption = {
  id: string;
};

export const getClientId = (): string => {
  if (typeof window === 'undefined') return 'server';
  let id = localStorage.getItem(CLIENT_ID_KEY);
  if (!id) {
    id = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
    localStorage.setItem(CLIENT_ID_KEY, id);
  }
  return id;
};

export const getSelectedProvider = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(PROVIDER_KEY);
};

export const setSelectedProvider = (providerId: string) => {
  if (typeof window === 'undefined') return;
  localStorage.setItem(PROVIDER_KEY, providerId);
};

export const resolveSelectedProvider = (
  providers: ProviderOption[],
  serverDefault?: string | null,
  fallbackId?: string | null,
): string | null => {
  const validIds = new Set(providers.map((provider) => provider.id).filter(Boolean));
  const stored = getSelectedProvider();
  if (stored && validIds.has(stored)) return stored;
  if (serverDefault && validIds.has(serverDefault)) return serverDefault;
  if (fallbackId && validIds.has(fallbackId)) return fallbackId;
  return providers[0]?.id || null;
};

export const dispatchLlmStatus = (running: boolean) => {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent('llm:status', { detail: { running } }));
};
