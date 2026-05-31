import { useEffect, useRef } from 'react';
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

const normalizePath = (p: string): string => {
  if (!p) return '/';
  const withSlash = p.startsWith('/') ? p : `/${p}`;
  return withSlash.replace(/\/+/g, '/').replace(/\/+$/, '') || '/';
};

export interface WorkspaceWatcherOptions {
  prefix: string;
  onTreeChange: () => void;
  currentFilePath?: string | null;
  onCurrentFileChange?: () => void;
  debounceMs?: number;
}

export function useWorkspaceWatcher(opts: WorkspaceWatcherOptions): void {
  const { prefix, onTreeChange, currentFilePath, onCurrentFileChange, debounceMs = 250 } = opts;
  const onTreeChangeRef = useRef(onTreeChange);
  const onCurrentFileChangeRef = useRef(onCurrentFileChange);
  const currentFileRef = useRef<string | null>(null);

  useEffect(() => { onTreeChangeRef.current = onTreeChange; }, [onTreeChange]);
  useEffect(() => { onCurrentFileChangeRef.current = onCurrentFileChange; }, [onCurrentFileChange]);
  useEffect(() => { currentFileRef.current = currentFilePath ? normalizePath(currentFilePath) : null; }, [currentFilePath]);

  useEffect(() => {
    const normalizedPrefix = normalizePath(prefix);
    const watchedPrefixes = Array.from(new Set([
      normalizedPrefix,
      normalizedPrefix === '/' ? '/' : `/$project${normalizedPrefix}`,
    ]));
    const source = createFileEventSource(normalizedPrefix);
    let revision = 0;
    let treeTimer: number | null = null;
    let fileTimer: number | null = null;

    const scheduleTree = () => {
      if (treeTimer !== null) return;
      treeTimer = window.setTimeout(() => {
        treeTimer = null;
        onTreeChangeRef.current();
      }, debounceMs);
    };

    const scheduleFile = () => {
      if (fileTimer !== null) return;
      fileTimer = window.setTimeout(() => {
        fileTimer = null;
        onCurrentFileChangeRef.current?.();
      }, debounceMs);
    };

    const handler = (ev: MessageEvent<string>) => {
      let payload: { revision?: number; paths?: { path: string }[] };
      try {
        payload = JSON.parse(ev.data);
      } catch {
        return;
      }
      if (typeof payload.revision === 'number') {
        if (payload.revision <= revision) return;
        revision = payload.revision;
      }
      const paths = (payload.paths || []).map((p) => normalizePath(p.path));
      if (paths.length === 0) return;
      const treeHit = paths.some((p) => watchedPrefixes.some((watchedPrefix) => {
        const prefixMatch = watchedPrefix === '/' ? '/' : `${watchedPrefix}/`;
        return p === watchedPrefix || p.startsWith(prefixMatch);
      }));
      if (treeHit) scheduleTree();
      const watchedFile = currentFileRef.current;
      if (watchedFile && onCurrentFileChangeRef.current) {
        const projectWatchedFile = watchedFile === '/' ? '/' : `/$project${watchedFile}`;
        const fileHit = paths.some((p) => p === watchedFile || p === projectWatchedFile);
        if (fileHit) scheduleFile();
      }
    };

    source.addEventListener('change', handler as EventListener);
    return () => {
      source.removeEventListener('change', handler as EventListener);
      source.close();
      if (treeTimer !== null) window.clearTimeout(treeTimer);
      if (fileTimer !== null) window.clearTimeout(fileTimer);
    };
  }, [prefix, debounceMs]);
}
