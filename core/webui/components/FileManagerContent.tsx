import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/router';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  IconArrowLeft,
  IconChevronDown,
  IconChevronRight,
  IconCopy,
  IconCut,
  IconEdit,
  IconFile,
  IconFileUpload,
  IconFolder,
  IconLayoutGrid,
  IconList,
  IconPencil,
  IconPlus,
  IconRefresh,
  IconGripHorizontal,
  IconTerminal2,
  IconTrash,
} from '@tabler/icons-react';

import { EditorView, lineNumbers, keymap, ViewUpdate } from '@codemirror/view';
import { EditorState, Compartment } from '@codemirror/state';
import { defaultKeymap, history, historyKeymap } from '@codemirror/commands';
import { syntaxHighlighting, defaultHighlightStyle } from '@codemirror/language';
import { javascript } from '@codemirror/lang-javascript';
import { python } from '@codemirror/lang-python';
import { json } from '@codemirror/lang-json';
import { markdown as markdownLang } from '@codemirror/lang-markdown';
import { rust } from '@codemirror/lang-rust';
import { java } from '@codemirror/lang-java';
import { php } from '@codemirror/lang-php';

import { apiUrl } from '../libs/api-base';
import {
  createFileEventSource,
  type FileChangeEvent,
  type FileStreamStatusEvent,
} from '../libs/file-events';

type FileKind = 'text' | 'markdown' | 'image' | 'audio' | 'video' | 'binary';
type FileViewMode = 'preview' | 'edit';
type ContentLayout = 'list' | 'grid';
type SortKey = 'name' | 'type' | 'modified' | 'size';

interface FileEntry {
  id: string;
  type: 'folder' | 'file';
  label?: string;
  rootKind?: 'project' | 'worktree';
  size?: number;
  date?: number;
  lazy?: boolean;
  virtualRoot?: boolean;
}

interface OpenFile {
  path: string;
  content: string;
  kind: FileKind;
}

interface FileRoot {
  id: string;
  label: string;
  kind: 'project' | 'worktree';
}

interface FileManagerInfo {
  projectName: string;
  roots: FileRoot[];
  supportsWorktrees: boolean;
}

type ClipboardMode = 'copy' | 'cut';

type ContextMenuState = {
  x: number;
  y: number;
  targetPath: string;
  targetType: 'file' | 'folder' | 'background';
};

function normalizePath(path: string | null | undefined): string {
  if (!path || path === '/') return '/';
  const normalized = `/${path}`.replace(/\/+/g, '/');
  return normalized.length > 1 && normalized.endsWith('/') ? normalized.slice(0, -1) : normalized;
}

function parentPath(path: string): string {
  const normalized = normalizePath(path);
  if (normalized === '/') return '/';
  const parts = normalized.split('/').filter(Boolean);
  parts.pop();
  return parts.length ? `/${parts.join('/')}` : '/';
}

function pathName(path: string): string {
  const normalized = normalizePath(path);
  if (normalized === '/') return 'Root';
  return normalized.split('/').filter(Boolean).pop() ?? normalized;
}

function ancestorPaths(path: string): string[] {
  const normalized = normalizePath(path);
  const parts = normalized.split('/').filter(Boolean);
  const ancestors = ['/'];
  let current = '';
  for (const part of parts) {
    current = `${current}/${part}`;
    ancestors.push(current);
  }
  return ancestors;
}

function fileKind(path: string): FileKind {
  const lower = path.toLowerCase();
  if (/\.(png|jpe?g|gif|webp|bmp|svg|ico)$/.test(lower)) return 'image';
  if (/\.(mp4|mov|webm|m4v|avi|mkv)$/.test(lower)) return 'video';
  if (/\.(mp3|wav|ogg|m4a|aac|flac)$/.test(lower)) return 'audio';
  if (/\.(md|markdown)$/.test(lower)) return 'markdown';
  return 'text';
}

function languageExtension(filename: string) {
  const ext = filename.split('.').pop()?.toLowerCase() ?? '';
  switch (ext) {
    case 'js': case 'jsx': case 'mjs': case 'cjs':
      return javascript({ jsx: true });
    case 'ts': case 'tsx':
      return javascript({ jsx: true, typescript: true });
    case 'py':
      return python();
    case 'json': case 'json5': case 'jsonc':
      return json();
    case 'md': case 'markdown':
      return markdownLang();
    case 'rs':
      return rust();
    case 'java':
      return java();
    case 'php':
      return php();
    default:
      return null;
  }
}

function langLabel(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase() ?? '';
  const map: Record<string, string> = {
    js: 'JavaScript', jsx: 'JSX', mjs: 'JS', cjs: 'JS',
    ts: 'TypeScript', tsx: 'TSX',
    py: 'Python', json: 'JSON', json5: 'JSON5', jsonc: 'JSON',
    md: 'Markdown', markdown: 'Markdown',
    rs: 'Rust', java: 'Java', php: 'PHP',
    sh: 'Shell', bash: 'Shell', zsh: 'Shell',
    yaml: 'YAML', yml: 'YAML', toml: 'TOML',
    html: 'HTML', css: 'CSS', scss: 'SCSS', less: 'LESS',
    go: 'Go', rb: 'Ruby', swift: 'Swift', kt: 'Kotlin',
    c: 'C', cpp: 'C++', h: 'C Header', hpp: 'C++',
    txt: 'Text', xml: 'XML', csv: 'CSV',
  };
  return map[ext] ?? (ext.toUpperCase() || 'Plain Text');
}

function formatDate(value?: number): string {
  if (!value) return '-';
  return new Date(value).toLocaleString();
}

function formatSize(bytes?: number, type?: FileEntry['type']): string {
  if (type === 'folder') return '-';
  if (!bytes && bytes !== 0) return '-';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

const editorTheme = EditorView.theme({
  '&': {
    height: '100%',
    fontSize: '13px',
    fontFamily: "'JetBrains Mono', 'Fira Mono', 'Cascadia Code', 'Consolas', monospace",
    background: '#0f172a',
    color: '#e2e8f0',
  },
  '.cm-scroller': { overflow: 'auto', height: '100%' },
  '.cm-content': { padding: '14px 0' },
  '.cm-line': { padding: '0 16px' },
  '.cm-gutters': { background: '#111827', borderRight: '1px solid #1f2937', color: '#64748b' },
  '.cm-activeLineGutter': { background: '#172033', color: '#cbd5e1' },
  '.cm-activeLine': { background: '#172033' },
  '.cm-cursor': { borderLeftColor: '#f8fafc' },
  '.cm-selectionBackground, ::selection': { background: '#1d4ed8 !important' },
  '.cm-focused .cm-selectionBackground': { background: '#2563eb !important' },
  '.cm-panels': { background: '#111827', color: '#e2e8f0' },
  '.cm-searchMatch': { background: '#7c3aed55', outline: '1px solid #8b5cf6' },
  '.cm-searchMatch.cm-searchMatch-selected': { background: '#a855f7aa' },
});

const iconButtonStyle: React.CSSProperties = {
  width: 34,
  height: 34,
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  borderRadius: 8,
  border: '1px solid #d6dce5',
  background: '#fff',
  color: '#334155',
  cursor: 'pointer',
  padding: 0,
};

function buildFileManagerTerminalSessionName(): string {
  if (typeof window === 'undefined') return 'sp-webui-file-manager';
  const port = window.location.port.trim() || 'default';
  return `sp-webui-file-manager-${port.replace(/[^a-zA-Z0-9_-]/g, '')}`;
}

export default function FileManagerContent() {
  const router = useRouter();
  const isDevMode = process.env.NODE_ENV === 'development';
  const routerRef = useRef(router);
  useEffect(() => { routerRef.current = router; }, [router]);

  const initializedRef = useRef(false);
  const directoryItemsRef = useRef<Record<string, FileEntry[]>>({});
  const uploadInputRef = useRef<HTMLInputElement>(null);
  const fileManagerInfoSignatureRef = useRef('');
  const rightPaneRef = useRef<HTMLDivElement>(null);

  const editorContainerRef = useRef<HTMLDivElement>(null);
  const editorViewRef = useRef<EditorView | null>(null);
  const langCompartmentRef = useRef<Compartment | null>(null);
  if (!langCompartmentRef.current) langCompartmentRef.current = new Compartment();

  const autoSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const realtimeNoticeTimerRef = useRef<number | null>(null);
  const currentPathRef = useRef<string | null>(null);
  const switchingFileRef = useRef(false);
  const openFileRef = useRef<OpenFile | null>(null);
  const fileContentRef = useRef('');
  const lastSavedPathRef = useRef<string | null>(null);
  const lastSavedContentRef = useRef('');
  const latestRealtimeRevisionRef = useRef(0);
  const lastOpenFileMtimeRef = useRef<number | null>(null);
  const pollingFallbackEnabledRef = useRef(false);
  const lastStreamActivityAtRef = useRef(0);
  const streamConnectedRef = useRef(false);

  const [directoryItems, setDirectoryItems] = useState<Record<string, FileEntry[]>>({});
  const [loadingDirs, setLoadingDirs] = useState<Record<string, boolean>>({});
  const [expandedDirs, setExpandedDirs] = useState<Set<string>>(new Set(['/']));
  const [projectLabel, setProjectLabel] = useState('Project');
  const [fileRoots, setFileRoots] = useState<FileRoot[]>([]);
  const [supportsWorktrees, setSupportsWorktrees] = useState(false);
  const [currentDir, setCurrentDir] = useState('/');
  const [openFile, setOpenFile] = useState<OpenFile | null>(null);
  const [fileViewMode, setFileViewMode] = useState<FileViewMode>('edit');
  const [fileContent, setFileContent] = useState('');
  const [panelError, setPanelError] = useState<string | null>(null);
  const [isLoadingFile, setIsLoadingFile] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [contentLayout, setContentLayout] = useState<ContentLayout>('list');
  const [showAddMenu, setShowAddMenu] = useState(false);
  const [editorReady, setEditorReady] = useState(false);
  const [clipboard, setClipboard] = useState<{ ids: string[]; mode: ClipboardMode } | null>(null);
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null);
  const [contextSelectionPath, setContextSelectionPath] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>('name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [realtimeNotice, setRealtimeNotice] = useState<string | null>(null);
  const [streamNotice, setStreamNotice] = useState<string | null>(null);
  const [terminalPanelOpen, setTerminalPanelOpen] = useState(false);
  const [terminalPanelHeight, setTerminalPanelHeight] = useState(38);
  const [isTerminalPanelResizing, setIsTerminalPanelResizing] = useState(false);
  const [terminalSessionName, setTerminalSessionName] = useState<string | null>(null);
  const [terminalSessionPath, setTerminalSessionPath] = useState('/');
  const [isStartingTerminal, setIsStartingTerminal] = useState(false);

  useEffect(() => {
    directoryItemsRef.current = directoryItems;
  }, [directoryItems]);

  useEffect(() => {
    openFileRef.current = openFile;
  }, [openFile]);

  const buildFileManagerInfoSignature = useCallback((info: FileManagerInfo): string => JSON.stringify({
    projectName: info.projectName,
    supportsWorktrees: info.supportsWorktrees,
    roots: info.roots.map((root) => [root.id, root.label, root.kind]),
  }), []);

  const loadFileManagerInfo = useCallback(async (): Promise<FileManagerInfo | null> => {
    try {
      const resp = await fetch(apiUrl('/api/files/info'), {
        credentials: 'include',
      });
      if (!resp.ok) return null;
      const data = await resp.json();
      const projectName = typeof data.projectName === 'string' && data.projectName.trim() ? data.projectName.trim() : 'Project';
      const roots: FileRoot[] = Array.isArray(data.roots)
        ? data.roots
          .filter((root: unknown): root is FileRoot => !!root && typeof root === 'object' && typeof (root as FileRoot).id === 'string' && typeof (root as FileRoot).label === 'string' && (((root as FileRoot).kind === 'project') || ((root as FileRoot).kind === 'worktree')))
        : [];
      const info: FileManagerInfo = {
        projectName,
        roots,
        supportsWorktrees: Boolean(data.supportsWorktrees),
      };
      setProjectLabel(info.projectName);
      setFileRoots(info.roots);
      setSupportsWorktrees(info.supportsWorktrees);
      return info;
    } catch {
      setProjectLabel('Project');
      setFileRoots([]);
      setSupportsWorktrees(false);
      return {
        projectName: 'Project',
        roots: [],
        supportsWorktrees: false,
      };
    }
  }, []);

  const rootEntryById = useMemo(
    () => Object.fromEntries(fileRoots.map((root) => [root.id, root])),
    [fileRoots],
  );

  const sortedRootIds = useMemo(
    () => [...fileRoots].sort((left, right) => right.id.length - left.id.length).map((root) => root.id),
    [fileRoots],
  );

  const rootForPath = useCallback((path: string): FileRoot | null => {
    const normalized = normalizePath(path);
    for (const rootId of sortedRootIds) {
      if (normalized === rootId || normalized.startsWith(`${rootId}/`)) {
        return rootEntryById[rootId] ?? null;
      }
    }
    return null;
  }, [rootEntryById, sortedRootIds]);

  const projectRootId = useMemo(
    () => fileRoots.find((root) => root.kind === 'project')?.id ?? '/',
    [fileRoots],
  );

  const createTargetPath = useMemo(
    () => (supportsWorktrees && currentDir === '/' ? projectRootId : currentDir),
    [currentDir, projectRootId, supportsWorktrees],
  );

  const displayNameForPath = useCallback((path: string): string => {
    const normalized = normalizePath(path);
    if (normalized === '/') return supportsWorktrees ? 'Workspace' : projectLabel;
    const root = rootEntryById[normalized];
    if (root) return root.label;
    return pathName(normalized);
  }, [projectLabel, rootEntryById, supportsWorktrees]);

  const displayPath = useCallback((path: string): string => {
    const normalized = normalizePath(path);
    if (normalized === '/') return supportsWorktrees ? '/' : `/${projectLabel}`;
    const root = rootForPath(normalized);
    if (!root) return normalized;
    const suffix = normalized.slice(root.id.length);
    return `/${root.label}${suffix}`;
  }, [projectLabel, rootForPath, supportsWorktrees]);

  useEffect(() => {
    fileContentRef.current = fileContent;
  }, [fileContent]);

  useEffect(() => {
    if (realtimeNoticeTimerRef.current) {
      clearTimeout(realtimeNoticeTimerRef.current);
      realtimeNoticeTimerRef.current = null;
    }

    if (realtimeNotice !== 'This file was updated on disk.') {
      return undefined;
    }

    realtimeNoticeTimerRef.current = window.setTimeout(() => {
      setRealtimeNotice((current) =>
        current === 'This file was updated on disk.' ? null : current,
      );
      realtimeNoticeTimerRef.current = null;
    }, 5000);

    return () => {
      if (realtimeNoticeTimerRef.current) {
        clearTimeout(realtimeNoticeTimerRef.current);
        realtimeNoticeTimerRef.current = null;
      }
    };
  }, [realtimeNotice]);

  useEffect(() => {
    if (!isTerminalPanelResizing) return undefined;

    const handleMouseMove = (event: MouseEvent) => {
      if (!rightPaneRef.current) return;
      const bounds = rightPaneRef.current.getBoundingClientRect();
      if (bounds.height <= 0) return;
      const offsetY = event.clientY - bounds.top;
      const nextTopPercent = (offsetY / bounds.height) * 100;
      const nextBottomPercent = Math.max(24, Math.min(68, 100 - nextTopPercent));
      setTerminalPanelHeight(nextBottomPercent);
    };

    const handleMouseUp = () => {
      setIsTerminalPanelResizing(false);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isTerminalPanelResizing]);

  const updateUrlPath = useCallback((path: string) => {
    void routerRef.current.replace(
      { pathname: '/file-manager', query: { path } },
      undefined,
      { shallow: true },
    );
  }, []);

  const loadDirectory = useCallback(async (
    path: string,
    options?: { force?: boolean; quiet?: boolean },
  ): Promise<FileEntry[] | null> => {
    const normalized = normalizePath(path);
    const cached = directoryItemsRef.current[normalized];
    if (!options?.force && cached) return cached;

    setLoadingDirs(prev => ({ ...prev, [normalized]: true }));
    try {
      const resp = await fetch(apiUrl(`/api/files/list?path=${encodeURIComponent(normalized)}`), {
        credentials: 'include',
      });
      if (!resp.ok) {
        if (!options?.quiet) setPanelError('Failed to load folder');
        return null;
      }
      const data = await resp.json();
      const items: FileEntry[] = Array.isArray(data.data) ? data.data : [];
      setDirectoryItems(prev => ({ ...prev, [normalized]: items }));
      return items;
    } catch {
      if (!options?.quiet) setPanelError('Network error loading folder');
      return null;
    } finally {
      setLoadingDirs(prev => ({ ...prev, [normalized]: false }));
    }
  }, []);

  const syncFileManagerRoots = useCallback(async (options?: { quiet?: boolean }) => {
    const info = await loadFileManagerInfo();
    if (!info) return;
    const nextSignature = buildFileManagerInfoSignature(info);
    const previousSignature = fileManagerInfoSignatureRef.current;
    fileManagerInfoSignatureRef.current = nextSignature;
    if (!previousSignature || previousSignature === nextSignature) return;
    await loadDirectory('/', { force: true, quiet: options?.quiet });
  }, [buildFileManagerInfoSignature, loadDirectory, loadFileManagerInfo]);

  const ensureTreePath = useCallback(async (path: string) => {
    const directories = ancestorPaths(path);
    setExpandedDirs(prev => {
      const next = new Set(prev);
      directories.forEach(dir => next.add(dir));
      return next;
    });
    for (const dir of directories) {
      await loadDirectory(dir, { quiet: true });
    }
  }, [loadDirectory]);

  const refreshCurrentDir = useCallback(async () => {
    if (currentDir === '/') {
      await syncFileManagerRoots();
    }
    await loadDirectory(currentDir, { force: true });
  }, [currentDir, loadDirectory, syncFileManagerRoots]);

  const openTerminalPanel = useCallback(async () => {
    if (isStartingTerminal) return;
    setPanelError(null);
    setTerminalPanelOpen(true);
    setTerminalPanelHeight((current) => (current < 24 ? 38 : current));

    const targetPath = normalizePath(currentDir);
    setIsStartingTerminal(true);
    try {
      if (terminalSessionName && terminalSessionPath !== targetPath) {
        await fetch(apiUrl('/api/terminal/tmux/kill'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ session: terminalSessionName }),
        }).catch(() => null);
        setTerminalSessionName(null);
      }
      const resp = await fetch(apiUrl('/api/terminal/tmux/create'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          session_type: 'shell',
          path: targetPath,
          path_mode: 'file_manager',
          session_name: buildFileManagerTerminalSessionName(),
        }),
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        setPanelError(data.error ?? 'Failed to start terminal');
        setTerminalPanelOpen(false);
        return;
      }
      const sessionName = typeof data?.session?.name === 'string' ? data.session.name : null;
      if (!sessionName) {
        setPanelError('Terminal session did not start');
        setTerminalPanelOpen(false);
        return;
      }
      setTerminalSessionName(sessionName);
      setTerminalSessionPath(targetPath);
    } catch {
      setTerminalSessionName(null);
      setPanelError('Network error starting terminal');
      setTerminalPanelOpen(false);
    } finally {
      setIsStartingTerminal(false);
    }
  }, [currentDir, isStartingTerminal, terminalSessionName, terminalSessionPath]);

  const toggleTerminalPanel = useCallback(() => {
    if (terminalPanelOpen) {
      setTerminalPanelOpen(false);
      return;
    }
    void openTerminalPanel();
  }, [openTerminalPanel, terminalPanelOpen]);

  const saveFileNow = useCallback(async (path: string, content: string) => {
    const normalizedPath = normalizePath(path);
    const resp = await fetch(apiUrl('/api/files/write'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ path: normalizedPath, content }),
    });
    if (!resp.ok) throw new Error('save failed');
    lastSavedPathRef.current = normalizedPath;
    lastSavedContentRef.current = content;
  }, []);

  const flushCurrentFileSave = useCallback(async () => {
    const activeFile = openFileRef.current;
    if (!activeFile) return;
    if (activeFile.kind !== 'text' && activeFile.kind !== 'markdown') return;

    const path = activeFile.path;
    const content = fileContentRef.current;
    const alreadySaved =
      lastSavedPathRef.current === path &&
      lastSavedContentRef.current === content;
    if (alreadySaved) return;

    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
      autoSaveTimerRef.current = null;
    }

    try {
      setSaveStatus('saving');
      await saveFileNow(path, content);
      setSaveStatus('saved');
      setTimeout(() => setSaveStatus('idle'), 1600);
    } catch {
      setSaveStatus('error');
    }
  }, [saveFileNow]);

  const scheduleAutoSave = useCallback((path: string, content: string) => {
    if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
    setSaveStatus('idle');
    autoSaveTimerRef.current = setTimeout(async () => {
      setSaveStatus('saving');
      try {
        await saveFileNow(path, content);
        setSaveStatus('saved');
        setTimeout(() => setSaveStatus('idle'), 1600);
      } catch {
        setSaveStatus('error');
      }
    }, 1000);
  }, [saveFileNow]);

  const openFileInPanel = useCallback(async (path: string, options?: { updateUrl?: boolean; skipClearNotice?: boolean }) => {
    await flushCurrentFileSave();
    const normalized = normalizePath(path);
    const kind = fileKind(normalized);
    setPanelError(null);
    if (!options?.skipClearNotice) setRealtimeNotice(null);
    setShowAddMenu(false);
    setContextMenu(null);
    setFileViewMode('edit');

    if (kind === 'image' || kind === 'audio' || kind === 'video') {
      currentPathRef.current = null;
      if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
      setSaveStatus('idle');
      setOpenFile({ path: normalized, content: '', kind });
      setFileContent('');
      if (options?.updateUrl !== false) updateUrlPath(normalized);
      return;
    }

    setIsLoadingFile(true);
    try {
      const resp = await fetch(apiUrl(`/api/files/read?path=${encodeURIComponent(normalized)}`), {
        credentials: 'include',
      });
      const data = await resp.json();

      if (!resp.ok) {
        if (resp.status === 415) {
          currentPathRef.current = null;
          setOpenFile({ path: normalized, content: '', kind: 'binary' });
          setFileContent('');
          setFileViewMode('preview');
          if (options?.updateUrl !== false) updateUrlPath(normalized);
          return;
        }
        setOpenFile(null);
        setPanelError(data.error ?? 'Failed to load file');
        return;
      }

      const loaded: OpenFile = {
        path: normalized,
        content: data.content ?? '',
        kind: data.kind ?? kind,
      };
      setOpenFile(loaded);
      setFileContent(loaded.content);
      lastSavedPathRef.current = loaded.path;
      lastSavedContentRef.current = loaded.content;
      const parentEntries = directoryItemsRef.current[parentPath(normalized)] ?? [];
      const currentEntry = parentEntries.find((entry) => entry.id === normalized);
      lastOpenFileMtimeRef.current = currentEntry?.date ?? null;
      setFileViewMode('edit');
      if (options?.updateUrl !== false) updateUrlPath(normalized);
    } catch {
      setOpenFile(null);
      setPanelError('Network error loading file');
    } finally {
      setIsLoadingFile(false);
    }
  }, [flushCurrentFileSave, updateUrlPath]);

  const navigateToDirectory = useCallback(async (
    path: string,
    options?: { updateUrl?: boolean; force?: boolean },
  ) => {
    await flushCurrentFileSave();
    const normalized = normalizePath(path);
    setPanelError(null);
    setRealtimeNotice(null);
    setShowAddMenu(false);
    setContextMenu(null);
    setOpenFile(null);
    setCurrentDir(normalized);
    await ensureTreePath(normalized);
    await loadDirectory(normalized, { force: options?.force });
    if (options?.updateUrl !== false) updateUrlPath(normalized);
  }, [ensureTreePath, flushCurrentFileSave, loadDirectory, updateUrlPath]);

  const createNewFolder = useCallback(async () => {
    const name = window.prompt('Folder name');
    if (!name) return;
    const resp = await fetch(apiUrl('/api/files/mkdir'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ parent: createTargetPath, name }),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      setPanelError(data.error ?? 'Failed to create folder');
      return;
    }
    setExpandedDirs(prev => new Set(prev).add(createTargetPath));
    setShowAddMenu(false);
    if (createTargetPath !== currentDir) {
      setCurrentDir(createTargetPath);
      await ensureTreePath(createTargetPath);
      await loadDirectory(createTargetPath, { force: true });
      updateUrlPath(createTargetPath);
      return;
    }
    await refreshCurrentDir();
  }, [createTargetPath, currentDir, ensureTreePath, loadDirectory, refreshCurrentDir, updateUrlPath]);

  const createNewFile = useCallback(async () => {
    const name = window.prompt('File name');
    if (!name) return;
    const path = normalizePath(`${createTargetPath}/${name}`);
    const resp = await fetch(apiUrl('/api/files/write'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ path, content: '' }),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      setPanelError(data.error ?? 'Failed to create file');
      return;
    }
    setShowAddMenu(false);
    if (createTargetPath !== currentDir) {
      setCurrentDir(createTargetPath);
      await ensureTreePath(createTargetPath);
      await loadDirectory(createTargetPath, { force: true });
    } else {
      await refreshCurrentDir();
    }
    await openFileInPanel(path);
  }, [createTargetPath, currentDir, ensureTreePath, loadDirectory, openFileInPanel, refreshCurrentDir]);

  const uploadFiles = useCallback(async (files: FileList | null) => {
    if (!files?.length) return;
    setPanelError(null);

    for (const file of Array.from(files)) {
      const formData = new FormData();
      formData.append('path', createTargetPath);
      formData.append('file', file);

      const resp = await fetch(apiUrl('/api/files/upload'), {
        method: 'POST',
        credentials: 'include',
        body: formData,
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        setPanelError(data.error ?? `Failed to upload ${file.name}`);
        return;
      }
    }

    setShowAddMenu(false);
    if (createTargetPath !== currentDir) {
      setCurrentDir(createTargetPath);
      await ensureTreePath(createTargetPath);
      await loadDirectory(createTargetPath, { force: true });
      updateUrlPath(createTargetPath);
      return;
    }
    await refreshCurrentDir();
  }, [createTargetPath, currentDir, ensureTreePath, loadDirectory, refreshCurrentDir, updateUrlPath]);

  useEffect(() => {
    if (!router.isReady || initializedRef.current) return;
    initializedRef.current = true;

    void (async () => {
      const rawQueryPath = typeof router.query.path === 'string' ? router.query.path : null;

      const info = await loadFileManagerInfo();
      if (info) {
        fileManagerInfoSignatureRef.current = buildFileManagerInfoSignature(info);
      }
      const defaultPath = info?.supportsWorktrees
        ? info.roots.find((root) => root.kind === 'project')?.id ?? '/'
        : '/';
      const requestedPath = normalizePath(rawQueryPath ?? defaultPath);
      await loadDirectory('/', { quiet: true });

      if (requestedPath === '/') {
        setCurrentDir('/');
        return;
      }

      const asDirectory = await loadDirectory(requestedPath, { quiet: true });
      if (asDirectory) {
        setCurrentDir(requestedPath);
        await ensureTreePath(requestedPath);
        return;
      }

      const containingDir = parentPath(requestedPath);
      setCurrentDir(containingDir);
      await ensureTreePath(containingDir);
      await loadDirectory(containingDir, { quiet: true });
      await openFileInPanel(requestedPath, { updateUrl: false });
    })();
  }, [buildFileManagerInfoSignature, ensureTreePath, loadDirectory, loadFileManagerInfo, openFileInPanel, router.isReady, router.query.path]);

  useEffect(() => {
    const view = editorViewRef.current;

    if (!openFile) {
      currentPathRef.current = null;
      if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
      setSaveStatus('idle');
      return;
    }

    if (openFile.kind !== 'text' && openFile.kind !== 'markdown') {
      currentPathRef.current = null;
      if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
      setSaveStatus('idle');
      return;
    }

    if (!editorReady || !view) return;

    const langExt = languageExtension(openFile.path);
    currentPathRef.current = null;
    switchingFileRef.current = true;
    view.dispatch({
      changes: { from: 0, to: view.state.doc.length, insert: openFile.content },
      effects: langCompartmentRef.current!.reconfigure(langExt ?? []),
    });
    switchingFileRef.current = false;
    currentPathRef.current = openFile.path;
    view.requestMeasure();
    if (fileViewMode === 'edit') view.focus();
    setSaveStatus('idle');
    if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
  }, [editorReady, fileViewMode, openFile]);

  useEffect(() => {
    if (fileViewMode === 'edit' && editorViewRef.current) {
      editorViewRef.current.requestMeasure();
      editorViewRef.current.focus();
    }
  }, [fileViewMode]);

  useEffect(() => {
    const handleBeforeUnload = () => {
      void flushCurrentFileSave();
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
      void flushCurrentFileSave();
    };
  }, [flushCurrentFileSave]);

  useEffect(() => {
    const handlePointerDown = () => {
      setContextMenu(null);
      setShowAddMenu(false);
      setContextSelectionPath(null);
    };
    window.addEventListener('pointerdown', handlePointerDown);
    return () => {
      window.removeEventListener('pointerdown', handlePointerDown);
    };
  }, []);

  const toggleTreeNode = useCallback((path: string) => {
    const normalized = normalizePath(path);
    setExpandedDirs(prev => {
      const next = new Set(prev);
      if (next.has(normalized) && normalized !== '/') next.delete(normalized);
      else next.add(normalized);
      return next;
    });
    if (!directoryItemsRef.current[normalized]) {
      void loadDirectory(normalized, { quiet: true });
    }
  }, [loadDirectory]);

  const currentEntries = directoryItems[currentDir] ?? [];
  const hasRootDirectory = Object.prototype.hasOwnProperty.call(directoryItems, '/');
  const fileName = openFile ? pathName(openFile.path) : '';
  const isVirtualWorkspaceRoot = supportsWorktrees && currentDir === '/';
  const realtimeSubscriptionEnabled = hasRootDirectory && !isVirtualWorkspaceRoot;
  const isEditorVisible = !!(
    openFile &&
    (openFile.kind === 'text' || openFile.kind === 'markdown') &&
    fileViewMode === 'edit'
  );

  const saveColor = saveStatus === 'error' ? '#dc2626'
    : saveStatus === 'saving' ? '#64748b'
    : saveStatus === 'saved' ? '#15803d'
    : 'transparent';
  const saveText = saveStatus === 'saving' ? 'Saving...'
    : saveStatus === 'saved' ? 'Saved'
    : saveStatus === 'error' ? 'Save failed'
    : '';

  const folderEntries = useMemo(
    () => currentEntries.filter(entry => entry.type === 'folder'),
    [currentEntries],
  );
  const fileEntries = useMemo(
    () => currentEntries.filter(entry => entry.type === 'file'),
    [currentEntries],
  );

  const compareEntries = useCallback((left: FileEntry, right: FileEntry) => {
    const direction = sortDirection === 'asc' ? 1 : -1;
    const leftName = left.label ?? pathName(left.id);
    const rightName = right.label ?? pathName(right.id);

    if (sortKey === 'name') {
      return leftName.localeCompare(rightName) * direction;
    }

    if (sortKey === 'type') {
      const leftType = left.type === 'folder' ? 'Folder' : langLabel(leftName);
      const rightType = right.type === 'folder' ? 'Folder' : langLabel(rightName);
      const byType = leftType.localeCompare(rightType);
      if (byType !== 0) return byType * direction;
      return leftName.localeCompare(rightName) * direction;
    }

    if (sortKey === 'modified') {
      const leftDate = left.date ?? 0;
      const rightDate = right.date ?? 0;
      if (leftDate !== rightDate) return (leftDate - rightDate) * direction;
      return leftName.localeCompare(rightName) * direction;
    }

    const leftSize = left.type === 'folder' ? -1 : (left.size ?? 0);
    const rightSize = right.type === 'folder' ? -1 : (right.size ?? 0);
    if (leftSize !== rightSize) return (leftSize - rightSize) * direction;
    return leftName.localeCompare(rightName) * direction;
  }, [sortDirection, sortKey]);

  const sortedFolderEntries = useMemo(
    () => [...folderEntries].sort(compareEntries),
    [compareEntries, folderEntries],
  );

  const sortedFileEntries = useMemo(
    () => [...fileEntries].sort(compareEntries),
    [compareEntries, fileEntries],
  );

  const sortedListEntries = useMemo(
    () => [...sortedFolderEntries, ...sortedFileEntries],
    [sortedFileEntries, sortedFolderEntries],
  );

  const toggleSort = useCallback((nextKey: SortKey) => {
    if (sortKey === nextKey) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
      return;
    }
    setSortKey(nextKey);
    setSortDirection(nextKey === 'modified' || nextKey === 'size' ? 'desc' : 'asc');
  }, [sortKey]);

  const openEntry = useCallback(async (entry: FileEntry) => {
    if (entry.type === 'folder') {
      await navigateToDirectory(entry.id);
      return;
    }
    await openFileInPanel(entry.id);
  }, [navigateToDirectory, openFileInPanel]);

  const renamePath = useCallback(async (path: string) => {
    const currentName = pathName(path);
    const name = window.prompt('Rename', currentName);
    if (!name || name === currentName) return;
    const resp = await fetch(apiUrl('/api/files/rename'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ id: path, name }),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      setPanelError(data.error ?? 'Failed to rename');
      return;
    }
    setContextMenu(null);
    await refreshCurrentDir();
  }, [refreshCurrentDir]);

  const deletePaths = useCallback(async (ids: string[]) => {
    if (!ids.length) return;
    const confirmed = window.confirm(`Delete ${ids.length > 1 ? `${ids.length} items` : pathName(ids[0])}?`);
    if (!confirmed) return;
    await flushCurrentFileSave();
    const resp = await fetch(apiUrl('/api/files/delete'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ ids }),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      setPanelError(data.error ?? 'Failed to delete');
      return;
    }
    if (openFileRef.current && ids.includes(openFileRef.current.path)) {
      setOpenFile(null);
      setFileContent('');
    }
    setContextMenu(null);
    await refreshCurrentDir();
  }, [flushCurrentFileSave, refreshCurrentDir]);

  const pasteClipboard = useCallback(async (targetPath: string) => {
    if (!clipboard || !clipboard.ids.length) return;
    const endpoint = clipboard.mode === 'copy' ? '/api/files/copy' : '/api/files/move';
    const resp = await fetch(apiUrl(endpoint), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ ids: clipboard.ids, target: targetPath }),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      setPanelError(data.error ?? 'Failed to paste');
      return;
    }
    if (clipboard.mode === 'cut') setClipboard(null);
    setContextMenu(null);
    await refreshCurrentDir();
    if (targetPath !== currentDir) {
      await loadDirectory(targetPath, { force: true, quiet: true });
    }
  }, [clipboard, currentDir, loadDirectory, refreshCurrentDir]);

  const refreshTreeForChanges = useCallback(async (paths: string[]) => {
    const cachedDirectories = directoryItemsRef.current;
    const targetDirs = new Set<string>();
    for (const changedPath of paths) {
      const normalized = normalizePath(changedPath);
      const relevantDir = normalized === '/' ? '/' : parentPath(normalized);
      for (const ancestor of ancestorPaths(relevantDir)) {
        if (cachedDirectories[ancestor]) targetDirs.add(ancestor);
      }
      if (cachedDirectories[normalized]) targetDirs.add(normalized);
    }
    await Promise.all(
      Array.from(targetDirs).map((dirPath) => loadDirectory(dirPath, { force: true, quiet: true })),
    );
  }, [loadDirectory]);

  const maybeReloadOpenFile = useCallback(async (directorySnapshot?: FileEntry[] | null) => {
    const activeFile = openFileRef.current;
    if (!activeFile || (activeFile.kind !== 'text' && activeFile.kind !== 'markdown')) return;

    const activeFileDir = parentPath(activeFile.path);
    if (directorySnapshot === null) return;
    const entries = directorySnapshot ?? directoryItemsRef.current[activeFileDir];
    if (!entries) return;
    const matchingEntry = entries.find((entry) => entry.id === activeFile.path);
    if (!matchingEntry) {
      setRealtimeNotice('This file was removed on disk.');
      setOpenFile(null);
      setFileContent('');
      return;
    }

    const previousMtime = lastOpenFileMtimeRef.current;
    const nextMtime = matchingEntry.date ?? null;
    if (previousMtime !== null && nextMtime === previousMtime) return;
    lastOpenFileMtimeRef.current = nextMtime;

    const hasUnsavedChanges =
      lastSavedPathRef.current === activeFile.path &&
      fileContentRef.current !== lastSavedContentRef.current;
    if (hasUnsavedChanges) {
      setRealtimeNotice('This file changed on disk. Reload after saving or discard your edits.');
      return;
    }

    setRealtimeNotice('This file was updated on disk.');
    await openFileInPanel(activeFile.path, { updateUrl: false, skipClearNotice: true });
  }, [openFileInPanel]);

  const streamUnavailableMessage = useCallback((watcher?: FileStreamStatusEvent['watcher']) => {
    const isDevWebui = typeof window !== 'undefined' && window.location.port === '3003';
    if (watcher?.last_error) {
      return `Realtime stream unhealthy: ${watcher.last_error}. Using fallback refresh.`;
    }
    if (isDevWebui) {
      return 'Realtime stream unavailable or stale. Using fallback refresh. Check the dev engine API on 127.0.0.1:3002.';
    }
    return 'Realtime stream unavailable or stale. Using fallback refresh.';
  }, []);

  const applyStreamStatus = useCallback((statusEvent: FileStreamStatusEvent) => {
    lastStreamActivityAtRef.current = Date.now();
    streamConnectedRef.current = true;
    if (statusEvent.watcher.healthy) {
      pollingFallbackEnabledRef.current = false;
      setStreamNotice(null);
      return;
    }
    pollingFallbackEnabledRef.current = true;
    setStreamNotice(streamUnavailableMessage(statusEvent.watcher));
  }, [streamUnavailableMessage]);

  const shouldRefreshActiveFile = useCallback((changedPaths: string[]) => {
    const activeFile = openFileRef.current;
    if (!activeFile || (activeFile.kind !== 'text' && activeFile.kind !== 'markdown')) return false;
    const activeFileDir = parentPath(activeFile.path);
    return changedPaths.some((rawPath) => {
      const normalized = normalizePath(rawPath);
      return (
        normalized === activeFile.path ||
        normalized === activeFileDir ||
        parentPath(normalized) === activeFileDir
      );
    });
  }, []);

  useEffect(() => {
    if (!realtimeSubscriptionEnabled) {
      pollingFallbackEnabledRef.current = false;
      streamConnectedRef.current = false;
      setStreamNotice(null);
      return;
    }

    const source = createFileEventSource(currentDir, openFile?.path);
    lastStreamActivityAtRef.current = Date.now();
    streamConnectedRef.current = false;

    const parseStatusEvent = (event: MessageEvent<string>): FileStreamStatusEvent | null => {
      try {
        return JSON.parse(event.data) as FileStreamStatusEvent;
      } catch {
        return null;
      }
    };

    const handleReady = (event: MessageEvent<string>) => {
      const payload = parseStatusEvent(event);
      if (!payload) return;
      applyStreamStatus(payload);
    };

    const handleHeartbeat = (event: MessageEvent<string>) => {
      const payload = parseStatusEvent(event);
      if (!payload) return;
      applyStreamStatus(payload);
    };

    const handleChange = (event: MessageEvent<string>) => {
      let payload: FileChangeEvent;
      try {
        payload = JSON.parse(event.data) as FileChangeEvent;
      } catch {
        return;
      }
      lastStreamActivityAtRef.current = Date.now();
      streamConnectedRef.current = true;
      pollingFallbackEnabledRef.current = false;
      setStreamNotice(null);
      if (payload.revision <= latestRealtimeRevisionRef.current) return;
      latestRealtimeRevisionRef.current = payload.revision;
      const changedPaths = payload.paths.map((entry) => normalizePath(entry.path));
      void refreshTreeForChanges(changedPaths);

      if (!shouldRefreshActiveFile(changedPaths)) return;
      const activeFile = openFileRef.current;
      if (!activeFile) return;
      const activeFileDir = parentPath(activeFile.path);
      void (async () => {
        const snapshot = await loadDirectory(activeFileDir, { force: true, quiet: true });
        await maybeReloadOpenFile(snapshot);
      })();
    };

    source.addEventListener('ready', handleReady as EventListener);
    source.addEventListener('heartbeat', handleHeartbeat as EventListener);
    source.addEventListener('change', handleChange as EventListener);
    source.onopen = () => {
      lastStreamActivityAtRef.current = Date.now();
    };
    source.onerror = () => {
      pollingFallbackEnabledRef.current = true;
      setStreamNotice(streamUnavailableMessage());
    };
    return () => {
      source.removeEventListener('ready', handleReady as EventListener);
      source.removeEventListener('heartbeat', handleHeartbeat as EventListener);
      source.removeEventListener('change', handleChange as EventListener);
      source.close();
    };
  }, [
    applyStreamStatus,
    currentDir,
    loadDirectory,
    maybeReloadOpenFile,
    openFile?.path,
    refreshTreeForChanges,
    realtimeSubscriptionEnabled,
    shouldRefreshActiveFile,
    streamUnavailableMessage,
  ]);

  useEffect(() => {
    if (!hasRootDirectory) return;

    const interval = window.setInterval(() => {
      if (document.visibilityState !== 'visible') return;
      void syncFileManagerRoots({ quiet: true });
      if (
        realtimeSubscriptionEnabled &&
        streamConnectedRef.current &&
        Date.now() - lastStreamActivityAtRef.current > 35000
      ) {
        pollingFallbackEnabledRef.current = true;
        setStreamNotice(streamUnavailableMessage());
      }
      if (!pollingFallbackEnabledRef.current) return;
      void (async () => {
        const activeFile = openFileRef.current;
        const targetDir =
          activeFile && (activeFile.kind === 'text' || activeFile.kind === 'markdown')
            ? parentPath(activeFile.path)
            : currentDir;
        const snapshot = await loadDirectory(targetDir, { force: true, quiet: true });
        await maybeReloadOpenFile(snapshot);
      })();
    }, 1500);

    return () => window.clearInterval(interval);
  }, [currentDir, hasRootDirectory, loadDirectory, maybeReloadOpenFile, realtimeSubscriptionEnabled, streamUnavailableMessage, syncFileManagerRoots]);

  const openContextMenu = useCallback((
    event: React.MouseEvent,
    targetPath: string,
    targetType: 'file' | 'folder' | 'background',
  ) => {
    event.preventDefault();
    event.stopPropagation();
    setShowAddMenu(false);
    setContextSelectionPath(targetType === 'background' ? null : targetPath);
    setContextMenu({
      x: event.clientX,
      y: event.clientY,
      targetPath,
      targetType,
    });
  }, []);

  const copyRelativePath = useCallback(async (path: string) => {
    const normalized = normalizePath(path);
    const root = rootForPath(normalized);
    const relative = root
      ? normalized.slice(root.id.length).replace(/^\/+/, '')
      : normalized === '/' ? '' : normalized.slice(1);
    try {
      await navigator.clipboard.writeText(relative);
      setContextMenu(null);
      setContextSelectionPath(null);
    } catch {
      setPanelError('Failed to copy path');
    }
  }, [rootForPath]);

  const canMutatePath = useCallback((path: string) => !isVirtualWorkspaceRoot && !rootEntryById[normalizePath(path)], [isVirtualWorkspaceRoot, rootEntryById]);

  const renderTree = useCallback((path: string, depth = 0): React.ReactNode => {
    const folders = (directoryItems[path] ?? []).filter(item => item.type === 'folder');
    if (!folders.length) return null;

    return folders.map(folder => {
      const isExpanded = expandedDirs.has(folder.id);
      const isSelected = currentDir === folder.id;
      const isLoading = !!loadingDirs[folder.id];
      const isContextSelected = contextSelectionPath === folder.id;

      return (
        <div key={folder.id}>
          <button
            type="button"
            onClick={() => { void navigateToDirectory(folder.id); }}
            onContextMenu={(event) => openContextMenu(event, folder.id, 'folder')}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 10px',
              paddingLeft: 12 + depth * 16,
              border: 'none',
              borderRadius: 8,
              background: isContextSelected ? '#dbeafe' : isSelected ? '#e8f1ff' : 'transparent',
              color: isSelected ? '#123a75' : '#1f2937',
              cursor: 'pointer',
              textAlign: 'left',
            }}
          >
            <span
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                toggleTreeNode(folder.id);
              }}
              style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 16, height: 16, color: '#64748b' }}
            >
              {isExpanded ? <IconChevronDown size={14} /> : <IconChevronRight size={14} />}
            </span>
            <IconFolder size={18} color="#d97706" />
            <span style={{ flex: 1, fontSize: 13, fontWeight: isSelected ? 700 : 500 }}>
              {folder.label ?? displayNameForPath(folder.id)}
            </span>
            {isLoading ? <span style={{ color: '#94a3b8', fontSize: 11 }}>...</span> : null}
          </button>
          {isExpanded ? renderTree(folder.id, depth + 1) : null}
        </div>
      );
    });
  }, [contextSelectionPath, currentDir, directoryItems, displayNameForPath, expandedDirs, loadingDirs, navigateToDirectory, openContextMenu, toggleTreeNode]);

  useEffect(() => {
    if (!hasRootDirectory || editorViewRef.current || !editorContainerRef.current) return;

    const view = new EditorView({
      parent: editorContainerRef.current,
      state: EditorState.create({
        doc: '',
        extensions: [
          history(),
          lineNumbers(),
          syntaxHighlighting(defaultHighlightStyle),
          langCompartmentRef.current!.of([]),
          editorTheme,
          keymap.of([...defaultKeymap, ...historyKeymap]),
          EditorView.lineWrapping,
          EditorView.updateListener.of((update: ViewUpdate) => {
            if (!update.docChanged || switchingFileRef.current) return;
            const path = currentPathRef.current;
            if (!path) return;
            const content = update.state.doc.toString();
            setFileContent(content);
            setOpenFile(prev => (prev ? { ...prev, content } : prev));
            scheduleAutoSave(path, content);
          }),
        ],
      }),
    });

    editorViewRef.current = view;
    setEditorReady(true);
    return () => {
      view.destroy();
      editorViewRef.current = null;
      setEditorReady(false);
    };
  }, [hasRootDirectory, scheduleAutoSave]);

  if (!hasRootDirectory) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#868e96', fontSize: 14 }}>
        Loading...
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', background: '#fff' }}>
      <style>{`
        .fm-markdown {
          max-width: 880px;
          margin: 0 auto;
          color: #1f2937;
          font-size: 15px;
          line-height: 1.8;
        }
        .fm-markdown h1,
        .fm-markdown h2,
        .fm-markdown h3,
        .fm-markdown h4 {
          color: #0f172a;
          line-height: 1.25;
          margin: 1.4em 0 0.6em;
        }
        .fm-markdown h1 { font-size: 2rem; }
        .fm-markdown h2 { font-size: 1.5rem; padding-bottom: 0.25rem; border-bottom: 1px solid #e5e7eb; }
        .fm-markdown h3 { font-size: 1.2rem; }
        .fm-markdown p,
        .fm-markdown ul,
        .fm-markdown ol,
        .fm-markdown blockquote,
        .fm-markdown pre,
        .fm-markdown table {
          margin: 1em 0;
        }
        .fm-markdown ul,
        .fm-markdown ol {
          padding-left: 1.5rem;
        }
        .fm-markdown li + li {
          margin-top: 0.35rem;
        }
        .fm-markdown a {
          color: #2563eb;
        }
        .fm-markdown blockquote {
          border-left: 4px solid #cbd5e1;
          background: #f8fafc;
          padding: 0.85rem 1rem;
          border-radius: 0 10px 10px 0;
        }
        .fm-markdown code {
          background: #f1f5f9;
          color: #0f172a;
          border-radius: 6px;
          padding: 0.15rem 0.35rem;
          font-size: 0.92em;
        }
        .fm-markdown pre {
          background: #0f172a;
          color: #e2e8f0;
          border-radius: 12px;
          padding: 1rem;
          overflow: auto;
        }
        .fm-markdown pre code {
          background: transparent;
          color: inherit;
          padding: 0;
        }
        .fm-markdown table {
          width: 100%;
          border-collapse: collapse;
          overflow: hidden;
          border-radius: 12px;
        }
        .fm-markdown th,
        .fm-markdown td {
          border: 1px solid #e5e7eb;
          padding: 0.75rem;
          text-align: left;
        }
        .fm-markdown th {
          background: #f8fafc;
          color: #0f172a;
        }
      `}</style>

      <input
        ref={uploadInputRef}
        type="file"
        multiple
        style={{ display: 'none' }}
        onChange={(event) => {
          void uploadFiles(event.target.files);
          event.currentTarget.value = '';
        }}
      />

      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '0 16px',
        height: 46,
        flexShrink: 0,
        borderBottom: isDevMode ? '2px solid #228be6' : '1px solid #e9ecef',
        background: '#f8f9fa',
      }}>
        <a href="/" style={{ display: 'flex', alignItems: 'center', textDecoration: 'none' }} title="Back to Skill Pilot">
          <img src="/images/skill-pilot-2.png" alt="Skill Pilot" style={{ height: 28 }} />
        </a>
        <div style={{ width: 1, height: 20, background: '#dee2e6' }} />
        <span style={{ fontSize: 13, fontWeight: 700, color: '#1f2937' }}>File Manager</span>
        <div style={{ width: 1, height: 20, background: '#dee2e6' }} />
        <button
          type="button"
          onClick={() => {
            if (window.history.length > 1) router.back();
            else void router.push('/');
          }}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            border: 'none',
            background: 'transparent',
            color: '#334155',
            cursor: 'pointer',
            fontSize: 12,
            fontWeight: 600,
            padding: 0,
            flexShrink: 0,
          }}
        >
          <IconArrowLeft size={16} />
          Back
        </button>
        <span style={{ fontSize: 12, color: '#64748b', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {openFile ? displayPath(openFile.path) : displayPath(currentDir)}
        </span>
        {openFile && (openFile.kind === 'text' || openFile.kind === 'markdown') && (
          <>
            <span style={{ padding: '2px 8px', borderRadius: 4, background: '#e9ecef', fontSize: 11, color: '#6c757d', flexShrink: 0 }}>
              {langLabel(fileName)}
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <button
                type="button"
                onClick={() => setFileViewMode('edit')}
                style={{
                  padding: '4px 10px',
                  borderRadius: 6,
                  border: '1px solid #d6dce5',
                  background: fileViewMode === 'edit' ? '#0f5cc0' : '#fff',
                  color: fileViewMode === 'edit' ? '#fff' : '#334155',
                  cursor: 'pointer',
                  fontSize: 12,
                }}
              >
                Edit
              </button>
              <button
                type="button"
                onClick={() => {
                  void flushCurrentFileSave().finally(() => setFileViewMode('preview'));
                }}
                style={{
                  padding: '4px 10px',
                  borderRadius: 6,
                  border: '1px solid #d6dce5',
                  background: fileViewMode === 'preview' ? '#0f5cc0' : '#fff',
                  color: fileViewMode === 'preview' ? '#fff' : '#334155',
                  cursor: 'pointer',
                  fontSize: 12,
                }}
              >
                Preview
              </button>
            </div>
            {saveText && (
              <span style={{ flexShrink: 0, fontSize: 11, color: saveColor }}>{saveText}</span>
            )}
          </>
        )}
      </div>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden', minHeight: 0 }}>
        <aside style={{
          width: 320,
          flexShrink: 0,
          borderRight: '1px solid #e9ecef',
          background: '#fbfcfe',
          display: 'flex',
          flexDirection: 'column',
          minHeight: 0,
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 8,
            padding: '12px 14px',
            borderBottom: '1px solid #edf1f5',
          }}>
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, color: '#0f172a', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                Directory Tree
              </div>
              <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
                Always visible
              </div>
            </div>
            <button
              type="button"
              onClick={() => { void refreshCurrentDir(); }}
              title="Refresh"
              style={iconButtonStyle}
            >
              <IconRefresh size={16} />
            </button>
          </div>

          <div style={{ padding: 10, overflow: 'auto', flex: 1 }}>
            {supportsWorktrees ? (
              renderTree('/', 0)
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => { void navigateToDirectory('/'); }}
                  onContextMenu={(event) => openContextMenu(event, '/', 'folder')}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    padding: '8px 10px',
                    border: 'none',
                    borderRadius: 8,
                    background: currentDir === '/' ? '#e8f1ff' : 'transparent',
                    color: currentDir === '/' ? '#123a75' : '#1f2937',
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                >
                  <span
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      toggleTreeNode('/');
                    }}
                    style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 16, height: 16, color: '#64748b' }}
                  >
                    {expandedDirs.has('/') ? <IconChevronDown size={14} /> : <IconChevronRight size={14} />}
                  </span>
                  <IconFolder size={18} color="#d97706" />
                  <span style={{ fontSize: 13, fontWeight: currentDir === '/' ? 700 : 600 }}>{projectLabel}</span>
                </button>
                {expandedDirs.has('/') ? renderTree('/', 1) : null}
              </>
            )}
          </div>
        </aside>

        <section
          ref={rightPaneRef}
          style={{
            flex: 1,
            minWidth: 0,
            display: 'grid',
            gridTemplateRows: terminalPanelOpen ? `${100 - terminalPanelHeight}fr 12px ${terminalPanelHeight}fr` : '1fr',
            overflow: 'hidden',
            position: 'relative',
            minHeight: 0,
          }}
        >
          <div style={{ minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative' }}>
          {isLoadingFile && (
            <div style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'rgba(255,255,255,0.82)',
              zIndex: 5,
            }}>
              <span style={{ color: '#64748b', fontSize: 14 }}>Loading file...</span>
            </div>
          )}

          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 12,
            padding: '14px 18px',
            borderBottom: '1px solid #eef2f7',
            background: '#fff',
            flexShrink: 0,
          }}>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#0f172a', display: 'flex', alignItems: 'center', gap: 8 }}>
                <IconFolder size={20} color="#d97706" />
                {openFile ? fileName : displayNameForPath(currentDir)}
              </div>
              <div style={{ fontSize: 12, color: '#64748b', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {openFile ? displayPath(openFile.path) : `${displayPath(currentDir)} contents`}
              </div>
            </div>

            {openFile ? (
              <button
                type="button"
                onClick={() => {
                  void flushCurrentFileSave().finally(() => {
                    setOpenFile(null);
                    setPanelError(null);
                    updateUrlPath(currentDir);
                  });
                }}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '6px 12px',
                  borderRadius: 8,
                  border: '1px solid #d6dce5',
                  background: '#fff',
                  color: '#334155',
                  cursor: 'pointer',
                  fontSize: 12,
                  flexShrink: 0,
                }}
              >
                <IconArrowLeft size={14} />
                Folder
              </button>
            ) : (
              <div
                style={{ display: 'flex', alignItems: 'center', gap: 8, position: 'relative' }}
                onPointerDown={(event) => event.stopPropagation()}
              >
                <button
                  type="button"
                  onClick={() => setShowAddMenu(prev => !prev)}
                  disabled={isVirtualWorkspaceRoot}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 6,
                    padding: '6px 12px',
                    borderRadius: 8,
                    border: '1px solid #d6dce5',
                    background: isVirtualWorkspaceRoot ? '#f8fafc' : '#fff',
                    color: isVirtualWorkspaceRoot ? '#94a3b8' : '#334155',
                    cursor: isVirtualWorkspaceRoot ? 'not-allowed' : 'pointer',
                    fontSize: 12,
                    fontWeight: 600,
                  }}
                >
                  <IconPlus size={14} />
                  Add New
                </button>

                {showAddMenu && !isVirtualWorkspaceRoot && (
                  <div style={{
                    position: 'absolute',
                    top: 'calc(100% + 8px)',
                    left: 0,
                    minWidth: 180,
                    background: '#fff',
                    border: '1px solid #d6dce5',
                    borderRadius: 10,
                    boxShadow: '0 12px 28px rgba(15, 23, 42, 0.12)',
                    padding: 6,
                    zIndex: 10,
                  }}>
                    <button
                      type="button"
                      onClick={() => { void createNewFile(); }}
                      style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 8, border: 'none', background: 'transparent', padding: '8px 10px', borderRadius: 8, cursor: 'pointer', textAlign: 'left', color: '#1f2937' }}
                    >
                      <IconFile size={16} />
                      New File
                    </button>
                    <button
                      type="button"
                      onClick={() => { void createNewFolder(); }}
                      style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 8, border: 'none', background: 'transparent', padding: '8px 10px', borderRadius: 8, cursor: 'pointer', textAlign: 'left', color: '#1f2937' }}
                    >
                      <IconFolder size={16} color="#d97706" />
                      New Folder
                    </button>
                    <button
                      type="button"
                      onClick={() => uploadInputRef.current?.click()}
                      style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 8, border: 'none', background: 'transparent', padding: '8px 10px', borderRadius: 8, cursor: 'pointer', textAlign: 'left', color: '#1f2937' }}
                    >
                      <IconFileUpload size={16} />
                      Upload File
                    </button>
                  </div>
                )}

                <button
                  type="button"
                  onClick={() => { void refreshCurrentDir(); }}
                  title="Refresh folder"
                  style={iconButtonStyle}
                >
                  <IconRefresh size={16} />
                </button>
                <button
                  type="button"
                  onClick={() => setContentLayout('list')}
                  title="List layout"
                  style={{
                    ...iconButtonStyle,
                    background: contentLayout === 'list' ? '#e8f1ff' : '#fff',
                    color: contentLayout === 'list' ? '#0f5cc0' : '#334155',
                  }}
                >
                  <IconList size={16} />
                </button>
                <button
                  type="button"
                  onClick={() => setContentLayout('grid')}
                  title="Grid layout"
                  style={{
                    ...iconButtonStyle,
                    background: contentLayout === 'grid' ? '#e8f1ff' : '#fff',
                    color: contentLayout === 'grid' ? '#0f5cc0' : '#334155',
                  }}
                >
                  <IconLayoutGrid size={16} />
                </button>
                <button
                  type="button"
                  onClick={toggleTerminalPanel}
                  title={terminalPanelOpen ? 'Hide terminal panel' : 'Show terminal panel'}
                  style={{
                    ...iconButtonStyle,
                    background: terminalPanelOpen ? '#e8f1ff' : '#fff',
                    color: terminalPanelOpen ? '#0f5cc0' : '#334155',
                  }}
                >
                  <IconTerminal2 size={16} />
                </button>
              </div>
            )}
          </div>

          {panelError && (
            <div style={{ padding: 18, color: '#e03131', fontSize: 14 }}>
              {panelError}
            </div>
          )}

          {!panelError && streamNotice && (
            <div style={{ padding: '12px 18px', color: '#9a3412', background: '#fff7ed', borderBottom: '1px solid #fed7aa', fontSize: 13 }}>
              {streamNotice}
            </div>
          )}

          {!panelError && realtimeNotice && (
            <div style={{ padding: '12px 18px', color: '#8a5a00', background: '#fff8db', borderBottom: '1px solid #ffe08a', fontSize: 13 }}>
              {realtimeNotice}
            </div>
          )}

          {!panelError && !openFile && contentLayout === 'list' && (
            <div
              style={{ display: 'flex', flexDirection: 'column', minHeight: 0, flex: 1 }}
              onContextMenu={(event) => openContextMenu(event, currentDir, 'background')}
            >
              <div style={{ display: 'grid', gridTemplateColumns: 'minmax(320px, 1.8fr) 120px 180px 120px', gap: 12, padding: '10px 18px', borderBottom: '1px solid #eef2f7', background: '#f8fafc', fontSize: 12, fontWeight: 700, color: '#475569' }}>
                {([
                  ['name', 'Name'],
                  ['type', 'Type'],
                  ['modified', 'Modified'],
                  ['size', 'Size'],
                ] as Array<[SortKey, string]>).map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => toggleSort(key)}
                    style={{
                      border: 'none',
                      background: 'transparent',
                      padding: 0,
                      cursor: 'pointer',
                      textAlign: 'left',
                      fontSize: 12,
                      fontWeight: 700,
                      color: sortKey === key ? '#0f5cc0' : '#475569',
                    }}
                  >
                    {label}{sortKey === key ? (sortDirection === 'asc' ? ' ↑' : ' ↓') : ''}
                  </button>
                ))}
              </div>

              <div style={{ flex: 1, overflow: 'auto' }}>
                {loadingDirs[currentDir] ? (
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 220, color: '#64748b', fontSize: 14 }}>
                    Loading folder...
                  </div>
                ) : currentEntries.length === 0 ? (
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 220, color: '#94a3b8', fontSize: 14 }}>
                    This folder is empty.
                  </div>
                ) : (
                  sortedListEntries.map(entry => {
                    const isContextSelected = contextSelectionPath === entry.id;
                    return (
                      <button
                        key={entry.id}
                        type="button"
                        onClick={() => { void openEntry(entry); }}
                        onContextMenu={(event) => openContextMenu(event, entry.id, entry.type)}
                        style={{
                          width: '100%',
                          display: 'grid',
                          gridTemplateColumns: 'minmax(320px, 1.8fr) 120px 180px 120px',
                          gap: 12,
                          alignItems: 'center',
                          padding: '12px 18px',
                          border: 'none',
                          borderBottom: '1px solid #f1f5f9',
                          background: isContextSelected ? '#dbeafe' : '#fff',
                          color: '#1f2937',
                          cursor: 'pointer',
                          textAlign: 'left',
                          fontSize: 13,
                        }}
                      >
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: entry.type === 'folder' ? 700 : 500, display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                          {entry.type === 'folder' ? <IconFolder size={18} color="#d97706" /> : <IconFile size={18} color="#64748b" />}
                          {entry.label ?? displayNameForPath(entry.id)}
                        </span>
                        <span style={{ color: '#64748b' }}>{entry.type === 'folder' ? 'Folder' : langLabel(pathName(entry.id))}</span>
                        <span style={{ color: '#64748b' }}>{formatDate(entry.date)}</span>
                        <span style={{ color: '#64748b' }}>{formatSize(entry.size, entry.type)}</span>
                      </button>
                    );
                  })
                )}
              </div>
            </div>
          )}

          {!panelError && !openFile && contentLayout === 'grid' && (
            <div
              style={{ flex: 1, overflow: 'auto', padding: 18 }}
              onContextMenu={(event) => openContextMenu(event, currentDir, 'background')}
            >
              {loadingDirs[currentDir] ? (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 220, color: '#64748b', fontSize: 14 }}>
                  Loading folder...
                </div>
              ) : currentEntries.length === 0 ? (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 220, color: '#94a3b8', fontSize: 14 }}>
                  This folder is empty.
                </div>
              ) : (
                <>
                  {folderEntries.length > 0 && (
                    <div style={{ marginBottom: 24 }}>
                      <div style={{ fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12 }}>
                        Folders
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 14 }}>
                        {sortedFolderEntries.map(entry => {
                          const isContextSelected = contextSelectionPath === entry.id;
                          return (
                            <button
                              key={entry.id}
                              type="button"
                              onClick={() => { void openEntry(entry); }}
                              onContextMenu={(event) => openContextMenu(event, entry.id, entry.type)}
                              style={{
                                border: '1px solid #e5e7eb',
                                background: isContextSelected ? '#dbeafe' : '#fff',
                                borderRadius: 14,
                                padding: '16px 14px',
                                textAlign: 'left',
                                cursor: 'pointer',
                                color: '#1f2937',
                              }}
                            >
                              <IconFolder size={28} color="#d97706" />
                              <div style={{ marginTop: 12, fontSize: 13, fontWeight: 700, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {entry.label ?? displayNameForPath(entry.id)}
                              </div>
                              <div style={{ marginTop: 6, fontSize: 11, color: '#64748b' }}>
                                {formatDate(entry.date)}
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {fileEntries.length > 0 && (
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12 }}>
                        Files
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 14 }}>
                        {sortedFileEntries.map(entry => {
                          const isContextSelected = contextSelectionPath === entry.id;
                          return (
                            <button
                              key={entry.id}
                              type="button"
                              onClick={() => { void openEntry(entry); }}
                              onContextMenu={(event) => openContextMenu(event, entry.id, entry.type)}
                              style={{
                                border: '1px solid #e5e7eb',
                                background: isContextSelected ? '#dbeafe' : '#fff',
                                borderRadius: 14,
                                padding: '16px 14px',
                                textAlign: 'left',
                                cursor: 'pointer',
                                color: '#1f2937',
                              }}
                            >
                              <IconFile size={28} color="#64748b" />
                              <div style={{ marginTop: 12, fontSize: 13, fontWeight: 700, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {pathName(entry.id)}
                              </div>
                              <div style={{ marginTop: 6, fontSize: 11, color: '#64748b' }}>
                                {langLabel(pathName(entry.id))}
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {!panelError && openFile?.kind === 'binary' && (
            <div style={{ padding: 24, color: '#64748b', fontSize: 14 }}>
              Binary file. Preview is not available.
            </div>
          )}

          {!panelError && openFile?.kind === 'image' && (
            <div style={{ flex: 1, overflow: 'auto', display: 'flex', alignItems: 'flex-start', justifyContent: 'center', padding: 16 }}>
              <img
                src={apiUrl(`/api/files/download?path=${encodeURIComponent(openFile.path)}`)}
                alt={fileName}
                style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', borderRadius: 6 }}
              />
            </div>
          )}

          {!panelError && openFile?.kind === 'audio' && (
            <div style={{ padding: 24 }}>
              <audio
                controls
                style={{ width: '100%' }}
                src={apiUrl(`/api/files/download?path=${encodeURIComponent(openFile.path)}`)}
              />
            </div>
          )}

          {!panelError && openFile?.kind === 'video' && (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16, background: '#0f172a' }}>
              <video
                controls
                style={{ width: '100%', maxHeight: '100%', borderRadius: 8, background: '#000' }}
                src={apiUrl(`/api/files/download?path=${encodeURIComponent(openFile.path)}`)}
              />
            </div>
          )}

          {!panelError && openFile?.kind === 'markdown' && fileViewMode === 'preview' && (
            <div style={{ flex: 1, padding: 28, overflow: 'auto', background: '#fff' }}>
              <div className="fm-markdown">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {fileContent}
                </ReactMarkdown>
              </div>
            </div>
          )}

          {!panelError && openFile?.kind === 'text' && fileViewMode === 'preview' && (
            <div style={{ flex: 1, overflow: 'auto', background: '#f8fafc', padding: 24 }}>
              <pre style={{ margin: 0, fontSize: 13, lineHeight: 1.7, color: '#0f172a', fontFamily: "'JetBrains Mono', 'Fira Mono', 'Cascadia Code', 'Consolas', monospace" }}>
                {fileContent}
              </pre>
            </div>
          )}

          <div
            ref={editorContainerRef}
            style={{
              flex: isEditorVisible ? 1 : 0,
              minHeight: 0,
              minWidth: 0,
              overflow: 'hidden',
              display: isEditorVisible ? 'flex' : 'none',
              flexDirection: 'column',
              background: '#fff',
            }}
          />

          </div>

          {terminalPanelOpen && (
            <>
              <div
                onMouseDown={(event) => {
                  event.preventDefault();
                  setIsTerminalPanelResizing(true);
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'row-resize',
                  color: '#93a4cc',
                  background: '#fff',
                  borderTop: '1px solid #e9ecef',
                  borderBottom: '1px solid #e9ecef',
                }}
                aria-label="Resize terminal panel"
              >
                <IconGripHorizontal size={16} />
              </div>
              <div style={{ minHeight: 0, overflow: 'hidden', background: '#fff' }}>
                <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0, borderTop: '1px solid #e9ecef' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, padding: '10px 14px', borderBottom: '1px solid #e9ecef', background: '#f8fafc' }}>
                    <div style={{ minWidth: 0, fontSize: 11, color: '#64748b', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {`Terminal: ${terminalSessionName ?? buildFileManagerTerminalSessionName()}`}
                    </div>
                  </div>
                  <div style={{ flex: 1, minHeight: 0, background: '#0b1220' }}>
                    {terminalSessionName ? (
                      <iframe
                        key={terminalSessionName}
                        src={`/terminal?session=${encodeURIComponent(terminalSessionName)}&compact=1`}
                        style={{ width: '100%', height: '100%', border: 'none' }}
                      />
                    ) : (
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#cbd5e1', fontSize: 14 }}>
                        {isStartingTerminal ? 'Starting terminal...' : 'No terminal session'}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </>
          )}

          {contextMenu && (
            <div
              style={{
                position: 'fixed',
                top: contextMenu.y,
                left: contextMenu.x,
                minWidth: 180,
                background: '#fff',
                border: '1px solid #d6dce5',
                borderRadius: 10,
                boxShadow: '0 12px 28px rgba(15, 23, 42, 0.16)',
                padding: 6,
                zIndex: 50,
              }}
              onPointerDown={(event) => event.stopPropagation()}
            >
              {contextMenu.targetType !== 'background' && (
                <button
                  type="button"
                  onClick={() => {
                    setContextMenu(null);
                    void openEntry({
                      id: contextMenu.targetPath,
                      type: contextMenu.targetType,
                    } as FileEntry);
                  }}
                  style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 8, border: 'none', background: 'transparent', padding: '8px 10px', borderRadius: 8, cursor: 'pointer', textAlign: 'left', color: '#1f2937' }}
                >
                  <IconEdit size={16} />
                  Open
                </button>
              )}
              {contextMenu.targetType !== 'background' && canMutatePath(contextMenu.targetPath) && (
                <button
                  type="button"
                  onClick={() => {
                    setClipboard({ ids: [contextMenu.targetPath], mode: 'copy' });
                    setContextMenu(null);
                  }}
                  style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 8, border: 'none', background: 'transparent', padding: '8px 10px', borderRadius: 8, cursor: 'pointer', textAlign: 'left', color: '#1f2937' }}
                >
                  <IconCopy size={16} />
                  Copy
                </button>
              )}
              {contextMenu.targetType !== 'background' && (
                <button
                  type="button"
                  onClick={() => { void copyRelativePath(contextMenu.targetPath); }}
                  style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 8, border: 'none', background: 'transparent', padding: '8px 10px', borderRadius: 8, cursor: 'pointer', textAlign: 'left', color: '#1f2937' }}
                >
                  <IconCopy size={16} />
                  Copy Path
                </button>
              )}
              {contextMenu.targetType !== 'background' && canMutatePath(contextMenu.targetPath) && (
                <button
                  type="button"
                  onClick={() => {
                    setClipboard({ ids: [contextMenu.targetPath], mode: 'cut' });
                    setContextMenu(null);
                  }}
                  style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 8, border: 'none', background: 'transparent', padding: '8px 10px', borderRadius: 8, cursor: 'pointer', textAlign: 'left', color: '#1f2937' }}
                >
                  <IconCut size={16} />
                  Cut
                </button>
              )}
              {clipboard && (
                <button
                  type="button"
                  onClick={() => { void pasteClipboard(contextMenu.targetType === 'background' ? currentDir : (contextMenu.targetType === 'folder' ? contextMenu.targetPath : currentDir)); }}
                  disabled={contextMenu.targetType === 'background' ? isVirtualWorkspaceRoot : (contextMenu.targetType === 'folder' ? !canMutatePath(contextMenu.targetPath) : isVirtualWorkspaceRoot)}
                  style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 8, border: 'none', background: 'transparent', padding: '8px 10px', borderRadius: 8, cursor: 'pointer', textAlign: 'left', color: '#1f2937' }}
                >
                  <IconPencil size={16} />
                  Paste
                </button>
              )}
              {contextMenu.targetType !== 'background' && canMutatePath(contextMenu.targetPath) && (
                <button
                  type="button"
                  onClick={() => { void renamePath(contextMenu.targetPath); }}
                  style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 8, border: 'none', background: 'transparent', padding: '8px 10px', borderRadius: 8, cursor: 'pointer', textAlign: 'left', color: '#1f2937' }}
                >
                  <IconPencil size={16} />
                  Rename
                </button>
              )}
              {contextMenu.targetType !== 'background' && canMutatePath(contextMenu.targetPath) && (
                <button
                  type="button"
                  onClick={() => { void deletePaths([contextMenu.targetPath]); }}
                  style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 8, border: 'none', background: 'transparent', padding: '8px 10px', borderRadius: 8, cursor: 'pointer', textAlign: 'left', color: '#b91c1c' }}
                >
                  <IconTrash size={16} />
                  Delete
                </button>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
