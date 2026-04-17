import { apiUrl } from './api-base';

export interface FileChangeEventPath {
  path: string;
  kind: 'file' | 'folder';
  change: 'created' | 'modified' | 'deleted' | 'moved';
}

export interface FileChangeEvent {
  revision: number;
  paths: FileChangeEventPath[];
  timestamp: number;
}

export interface FileStreamWatcherStatus {
  healthy: boolean;
  started: boolean;
  thread_alive: boolean;
  subscriber_count: number;
  last_error: string | null;
  last_error_at: number | null;
  last_event_at: number | null;
  last_start_at: number | null;
}

export interface FileStreamStatusEvent {
  timestamp: number;
  watcher: FileStreamWatcherStatus;
}

function getFileEventsBaseUrl(): string {
  const configured = (
    process.env.NEXT_PUBLIC_FILE_EVENTS_API ||
    process.env.NEXT_PUBLIC_CODES_API ||
    process.env.CODES_API_SSR ||
    ''
  ).replace(/\/$/, '');

  if (configured) {
    return configured;
  }

  return '';
}

export function createFileEventSource(dir: string, file?: string | null): EventSource {
  const params = new URLSearchParams({ dir });
  if (file) params.set('file', file);
  const base = getFileEventsBaseUrl();
  const path = `/api/files/events?${params.toString()}`;
  const url = base ? `${base}${path}` : apiUrl(path);
  return new EventSource(url, { withCredentials: true });
}
