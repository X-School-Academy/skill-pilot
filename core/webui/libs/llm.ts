const PROVIDER_KEY = 'juniorit_llm_provider';
const CLIENT_ID_KEY = 'juniorit_llm_client_id';

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

export const dispatchLlmStatus = (running: boolean) => {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent('llm:status', { detail: { running } }));
};
