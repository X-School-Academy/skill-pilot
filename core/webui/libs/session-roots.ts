import { useEffect, useState } from 'react';
import axios from 'axios';

import { apiUrl } from './api-base';

export interface SessionRootOption {
  value: string;
  label: string;
  kind: 'project' | 'worktree';
}

interface SessionRootsResponse {
  roots?: SessionRootOption[];
  has_worktrees?: boolean;
  default_path?: string;
}

const API_BASE_URL = apiUrl('/api');

export function useSessionRoots(initialPath: string = '') {
  const [sessionRootOptions, setSessionRootOptions] = useState<SessionRootOption[]>([]);
  const [hasSessionWorktrees, setHasSessionWorktrees] = useState(false);
  const [selectedSessionPath, setSelectedSessionPath] = useState(initialPath);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      try {
        const res = await axios.get(`${API_BASE_URL}/session-roots`);
        if (cancelled) return;
        const data = (res.data || {}) as SessionRootsResponse;
        const roots = Array.isArray(data.roots) ? data.roots : [];
        const defaultPath = typeof data.default_path === 'string' ? data.default_path : '';
        setSessionRootOptions(roots);
        setHasSessionWorktrees(Boolean(data.has_worktrees));
        setSelectedSessionPath((current) => current || initialPath || defaultPath || roots[0]?.value || '');
      } catch {
        if (cancelled) return;
        setSessionRootOptions([]);
        setHasSessionWorktrees(false);
      }
    };
    void run();
    return () => { cancelled = true; };
  }, [initialPath]);

  useEffect(() => {
    if (!initialPath) return;
    setSelectedSessionPath(initialPath);
  }, [initialPath]);

  return {
    sessionRootOptions,
    hasSessionWorktrees,
    selectedSessionPath,
    setSelectedSessionPath,
  };
}
