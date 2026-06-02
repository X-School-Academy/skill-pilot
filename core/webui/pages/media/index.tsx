import React, { useEffect, useMemo, useRef, useState } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { GetStaticPropsContext } from 'next';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';
import {
  ActionIcon,
  AppShell,
  Box,
  Button,
  Group,
  Header,
  Loader,
  LoadingOverlay,
  Menu,
  MediaQuery,
  Modal,
  NavLink,
  Radio,
  ScrollArea,
  Select,
  Text,
  TextInput,
  Textarea,
  Tooltip,
  Burger,
  useMantineTheme,
} from '@mantine/core';
import {
  IconArrowLeft,
  IconClock,
  IconFilePlus,
  IconFileText,
  IconFileUpload,
  IconFolder,
  IconFolderPlus,
  IconHierarchy,
  IconMusic,
  IconPlus,
  IconRefresh,
  IconSortAscending,
  IconVideo,
} from '@tabler/icons-react';
import EmbeddedSessionPanel, { WorkflowExecuteStatus } from '../../components/EmbeddedSessionPanel';
import MainLayout from '../../components/main-layout';
import { apiUrl } from '../../libs/api-base';
import { AUTO_EXECUTE_OPTION, buildExecuteSelectOptions, isAutoExecuteTarget } from '../../libs/execute-targets';
import { useWorkspaceWatcher } from '../../libs/file-events';
import { resolveSelectedProvider, setSelectedProvider } from '../../libs/llm';

const API_BASE_URL = apiUrl('/api');
axios.defaults.withCredentials = true;

type FileKind = 'markdown' | 'text' | 'image' | 'audio' | 'video' | 'pdf';
type ExecuteMode = 'skill' | 'workflow';
type MediaType = '' | 'create-image-audio' | 'create-slide-show-video' | 'multiple-scene-video' | 'talking-head-video' | 'lipsync-video';

interface FileItem {
  name: string;
  path: string;
  type: 'dir' | 'file';
  mtime: number;
  children?: FileItem[];
}

interface LlmProvider {
  id: string;
  name: string;
}

interface MediaAction {
  label: string;
  defaultSkill: string;
  skillPromptSuffix: string;
}

interface MediaDashboardItem {
  name: string;
  title: string;
  path: string;
  kind: 'image' | 'audio' | 'video';
  initials: string;
  thumbnailPath: string | null;
  mtime: number;
}

const detectFileKind = (path: string): FileKind => {
  const lower = (path || '').toLowerCase();
  if (lower.endsWith('.md') || lower.endsWith('.markdown')) return 'markdown';
  if (lower.endsWith('.pdf')) return 'pdf';
  if (lower.endsWith('.png') || lower.endsWith('.jpg') || lower.endsWith('.jpeg') || lower.endsWith('.gif') || lower.endsWith('.webp') || lower.endsWith('.bmp') || lower.endsWith('.svg')) return 'image';
  if (lower.endsWith('.mp3') || lower.endsWith('.wav') || lower.endsWith('.ogg') || lower.endsWith('.m4a') || lower.endsWith('.aac') || lower.endsWith('.flac')) return 'audio';
  if (lower.endsWith('.mp4') || lower.endsWith('.mov') || lower.endsWith('.webm') || lower.endsWith('.m4v') || lower.endsWith('.avi') || lower.endsWith('.mkv')) return 'video';
  return 'text';
};

const workflowBaseName = (path: string): string => {
  const filename = path.split('/').pop() || path;
  return filename.endsWith('.json') ? filename.slice(0, -5) : filename;
};

const workflowProjectPath = (name: string): string => `core/workflows/${name}.json`;

const mediaProjectPath = (path: string): string => {
  const trimmed = path.replace(/^\/+/, '');
  return trimmed ? `workspace/media/${trimmed}` : 'workspace/media';
};

const mediaRelativePath = (projectPath: string): string => {
  const normalized = projectPath.replace(/^\/+/, '');
  return normalized
    .replace(/^\$project\/workspace\/media\/?/, '')
    .replace(/^workspace\/media\/?/, '');
};

const mediaTypeSkillName = (type: MediaType): string => {
  if (type === 'talking-head-video' || type === 'lipsync-video') return 'media';
  return type;
};

const mediaFileUrl = (path: string): string => `${API_BASE_URL}/media/file?path=${encodeURIComponent(path)}`;

const getFileBaseName = (name: string): string => {
  const dotIndex = name.lastIndexOf('.');
  return dotIndex > 0 ? name.slice(0, dotIndex) : name;
};

const getMediaInitials = (name: string): string => {
  const baseName = getFileBaseName(name);
  const words = baseName.split(/[^a-zA-Z0-9]+/).filter(Boolean);
  const initials = words.map((word) => word[0]?.toUpperCase() || '').join('');
  return (initials || baseName[0]?.toUpperCase() || '?').slice(0, 3);
};

const isVisibleDashboardFile = (item: FileItem): boolean => (
  item.type === 'file' && !item.name.startsWith('.') && !item.name.startsWith('_')
);

const findMediaThumbnail = (item: FileItem, siblings: FileItem[]): string | null => {
  const baseName = getFileBaseName(item.name).toLowerCase();
  const thumbnail = siblings.find((sibling) => {
    if (!isVisibleDashboardFile(sibling)) return false;
    const lower = sibling.name.toLowerCase();
    if (!lower.endsWith('.png') && !lower.endsWith('.jpg') && !lower.endsWith('.jpeg')) return false;
    return getFileBaseName(sibling.name).toLowerCase() === baseName;
  });
  return thumbnail?.path || null;
};

const collectMediaDashboardItems = (items: FileItem[]): MediaDashboardItem[] => {
  const dashboardItems: MediaDashboardItem[] = [];
  for (const folder of items) {
    if (folder.type !== 'dir' || !folder.children) continue;
    const mediaBaseNames = new Set(
      folder.children
        .filter((item) => isVisibleDashboardFile(item))
        .filter((item) => {
          const kind = detectFileKind(item.path);
          return kind === 'audio' || kind === 'video';
        })
        .map((item) => getFileBaseName(item.name).toLowerCase()),
    );
    for (const item of folder.children) {
      if (!isVisibleDashboardFile(item)) continue;
      const segments = item.path.split('/').filter(Boolean);
      if (segments.length !== 2) continue;
      const kind = detectFileKind(item.path);
      if (kind !== 'image' && kind !== 'audio' && kind !== 'video') continue;
      if (kind === 'image' && mediaBaseNames.has(getFileBaseName(item.name).toLowerCase())) continue;
      dashboardItems.push({
        name: item.name,
        title: item.path,
        path: item.path,
        kind,
        initials: getMediaInitials(item.name),
        thumbnailPath: kind === 'audio' || kind === 'video' ? findMediaThumbnail(item, folder.children) : item.path,
        mtime: item.mtime,
      });
    }
  }
  return dashboardItems.sort((a, b) => b.mtime - a.mtime || a.name.localeCompare(b.name));
};

const getAncestorDirectoryPaths = (path: string): string[] => {
  const segments = path.split('/').filter(Boolean);
  if (segments.length <= 1) return [];
  const ancestors: string[] = [];
  for (let i = 1; i < segments.length; i += 1) {
    ancestors.push(segments.slice(0, i).join('/'));
  }
  return ancestors;
};

const collectDirectoryPaths = (items: FileItem[]): string[] => {
  const paths: string[] = [];
  for (const item of items) {
    if (item.type !== 'dir') continue;
    paths.push(item.path);
    if (item.children) paths.push(...collectDirectoryPaths(item.children));
  }
  return paths;
};

const PAGE_HEADER_BAR_STYLE: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 12,
  padding: '8px 18px',
  borderBottom: '1px solid #eef2f7',
  background: '#ffffff',
  flexShrink: 0,
  flexWrap: 'wrap',
};

const PAGE_ACTION_BAR_STYLE: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'flex-end',
  gap: 8,
  padding: '8px 16px',
  borderTop: '1px solid #eef2f7',
  background: '#f8fafc',
  flexShrink: 0,
};

const PAGE_EDITOR_FONT = "'JetBrains Mono', 'Fira Mono', 'Cascadia Code', 'Consolas', monospace";
const PAGE_EDITOR_DARK_INPUT_STYLE = {
  height: '100%',
  minHeight: '100%',
  resize: 'none',
  border: 'none',
  borderRadius: 0,
  padding: '18px 20px',
  fontFamily: PAGE_EDITOR_FONT,
  fontSize: 13,
  lineHeight: 1.65,
  background: '#0f172a',
  color: '#e5e7eb',
  caretColor: '#93c5fd',
} as const;

export default function MediaPage() {
  const router = useRouter();
  const { media } = router.query;
  const theme = useMantineTheme();
  const isDevMode = process.env.NODE_ENV === 'development';
  const [opened, setOpened] = useState(false);
  const [treeData, setTreeData] = useState<FileItem[]>([]);
  const [selectedKind, setSelectedKind] = useState<FileKind>('text');
  const [loading, setLoading] = useState(false);
  const [treeLoading, setTreeLoading] = useState(false);
  const [sortByTime, setSortByTime] = useState(true);
  const [expandedFolders, setExpandedFolders] = useState<string[]>([]);
  const [llmProviders, setLlmProviders] = useState<LlmProvider[]>([]);
  const [llmProvider, setLlmProvider] = useState<string | null>(null);
  const [editorSaving, setEditorSaving] = useState(false);
  const [editorError, setEditorError] = useState('');
  const [notice, setNotice] = useState('');
  const [editorContent, setEditorContent] = useState('');
  const [markdownView, setMarkdownView] = useState<'editor' | 'preview'>('editor');
  const [mediaModalOpened, setMediaModalOpened] = useState(false);
  const [mediaNameInput, setMediaNameInput] = useState('');
  const [mediaRequirementsInput, setMediaRequirementsInput] = useState('');
  const [mediaType, setMediaType] = useState<MediaType>('');
  const [creatingMedia, setCreatingMedia] = useState(false);
  const [deletingFile, setDeletingFile] = useState(false);
  const [fileContextMenu, setFileContextMenu] = useState<{ x: number; y: number; item: FileItem } | null>(null);
  const [executeOpened, setExecuteOpened] = useState(false);
  const [executeMode, setExecuteMode] = useState<ExecuteMode>('skill');
  const [skillOptions, setSkillOptions] = useState<string[]>([]);
  const [workflowOptions, setWorkflowOptions] = useState<string[]>([]);
  const [selectedSkill, setSelectedSkill] = useState<string | null>(AUTO_EXECUTE_OPTION);
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(AUTO_EXECUTE_OPTION);
  const [pendingAction, setPendingAction] = useState<MediaAction | null>(null);
  const [navbarWidth, setNavbarWidth] = useState(300);
  const [isResizing, setIsResizing] = useState(false);
  const [sessionPanelOpen, setSessionPanelOpen] = useState(false);
  const [sessionPanelHeight, setSessionPanelHeight] = useState(50);
  const [isSessionPanelResizing, setIsSessionPanelResizing] = useState(false);
  const [sessionPromptText, setSessionPromptText] = useState('');
  const [newSessionWorkflow, setNewSessionWorkflow] = useState<string | null>(null);
  const [newSessionSandbox, setNewSessionSandbox] = useState(false);
  const [newSessionAuto, setNewSessionAuto] = useState(false);
  const [newSessionNetwork, setNewSessionNetwork] = useState(true);
  const [newSessionNextNodeTrigger, setNewSessionNextNodeTrigger] = useState<'auto_continue' | 'start_by_prompt'>('auto_continue');
  const [newSessionWorkflowResumeAvailable, setNewSessionWorkflowResumeAvailable] = useState(false);
  const [newSessionWorkflowResume, setNewSessionWorkflowResume] = useState(false);
  const [startingSession, setStartingSession] = useState(false);
  const [liveSessionName, setLiveSessionName] = useState<string | null>(null);
  const [workflowSessionActive, setWorkflowSessionActive] = useState(false);
  const [workflowExecuteStatus, setWorkflowExecuteStatus] = useState<WorkflowExecuteStatus | null>(null);
  const [continuingWorkflow, setContinuingWorkflow] = useState(false);
  const [mediaPreview, setMediaPreview] = useState<MediaDashboardItem | null>(null);
  const [mediaPreviewSize, setMediaPreviewSize] = useState<{ width: number; height: number } | null>(null);
  const rightPaneRef = useRef<HTMLDivElement | null>(null);
  const uploadInputRef = useRef<HTMLInputElement | null>(null);
  const uploadTargetRef = useRef<string>('workspace/media');
  const autoSaveTimerRef = useRef<number | null>(null);
  const lastLoadedContentRef = useRef<string>('');
  const editorContentRef = useRef<string>('');
  useEffect(() => { editorContentRef.current = editorContent; }, [editorContent]);

  const currentTask = typeof media === 'string' ? media : '';
  const currentView = router.query.view === 'explorer' || typeof media === 'string' ? 'explorer' : 'dashboard';
  const currentMediaFolder = currentTask.includes('/') ? currentTask.split('/')[0] : '';
  const currentFileName = currentTask.split('/').pop() || '';
  const skillSelectOptions = useMemo(() => buildExecuteSelectOptions(skillOptions), [skillOptions]);
  const workflowSelectOptions = useMemo(() => buildExecuteSelectOptions(workflowOptions), [workflowOptions]);

  const startResizing = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  };

  const stopResizing = () => setIsResizing(false);

  const resize = (e: MouseEvent) => {
    if (!isResizing) return;
    const newWidth = e.clientX;
    if (newWidth > 150 && newWidth < 600) {
      setNavbarWidth(newWidth);
    }
  };

  useEffect(() => {
    window.addEventListener('mousemove', resize);
    window.addEventListener('mouseup', stopResizing);
    return () => {
      window.removeEventListener('mousemove', resize);
      window.removeEventListener('mouseup', stopResizing);
    };
  }, [isResizing]);

  useEffect(() => {
    if (!isSessionPanelResizing) return undefined;
    const handleMouseMove = (event: MouseEvent) => {
      if (!rightPaneRef.current) return;
      const bounds = rightPaneRef.current.getBoundingClientRect();
      if (bounds.height <= 0) return;
      const offsetY = event.clientY - bounds.top;
      const nextTopPercent = (offsetY / bounds.height) * 100;
      const nextBottomPercent = Math.max(28, Math.min(72, 100 - nextTopPercent));
      setSessionPanelHeight(nextBottomPercent);
    };
    const handleMouseUp = () => setIsSessionPanelResizing(false);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isSessionPanelResizing]);

  useEffect(() => {
    if (!currentTask) return;
    const ancestorPaths = getAncestorDirectoryPaths(currentTask);
    if (ancestorPaths.length === 0) return;
    setExpandedFolders((prev) => Array.from(new Set([...prev, ...ancestorPaths])));
  }, [currentTask]);

  useEffect(() => {
    const validPaths = new Set(collectDirectoryPaths(treeData));
    setExpandedFolders((prev) => prev.filter((path) => validPaths.has(path)));
  }, [treeData]);

  const fetchTree = async () => {
    setTreeLoading(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/media/tree`);
      setTreeData(res.data.items || []);
    } catch (err) {
      console.error('Failed to fetch media tree:', err);
    } finally {
      setTreeLoading(false);
    }
  };

  const fetchContent = async (path: string) => {
    const nextKind = detectFileKind(path);
    setLoading(true);
    setEditorError('');
    setNotice('');
    setSelectedKind(nextKind);
    setMarkdownView('editor');

    if (nextKind === 'image' || nextKind === 'audio' || nextKind === 'video' || nextKind === 'pdf') {
      setEditorContent('');
      setLoading(false);
      return;
    }

    try {
      const res = await axios.get(`${API_BASE_URL}/media/content`, { params: { path } });
      setSelectedKind((res.data.kind as FileKind) || nextKind);
      const content = String(res.data.content || '');
      setEditorContent(content);
      lastLoadedContentRef.current = content;
    } catch (err: any) {
      console.error('Failed to fetch media content:', err);
      setEditorError(err?.response?.data?.error || 'Failed to load file content.');
      setEditorContent('');
    } finally {
      setLoading(false);
    }
  };

  const fetchLatest = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/media/latest`);
      if (res.data.path) {
        router.push(`/media?media=${encodeURIComponent(res.data.path)}`, undefined, { shallow: true });
      } else {
        setEditorContent('');
        setNotice('');
      }
    } catch (err) {
      console.error('Failed to fetch latest media file:', err);
    }
  };

  const fetchLlmProviders = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/llm/providers`);
      const providers: LlmProvider[] = res.data.providers || [];
      setLlmProviders(providers);
      const serverDefault: string = res.data.default || '';
      const defaultId = resolveSelectedProvider(providers, serverDefault, 'gemini');
      if (defaultId) setSelectedProvider(defaultId);
      setLlmProvider(defaultId);
    } catch (err) {
      console.error('Failed to fetch LLM providers:', err);
    }
  };

  const fetchExecuteOptions = async () => {
    try {
      const [skillsRes, workflowsRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/config/skills/installed`),
        axios.get(`${API_BASE_URL}/workflows/tree`),
      ]);

      const nextSkills: string[] = [];
      for (const skill of skillsRes.data.skills || []) {
        if (skill?.name) nextSkills.push(String(skill.name));
      }
      setSkillOptions(nextSkills.sort((a, b) => a.localeCompare(b)));

      const nextWorkflows = (workflowsRes.data.items || [])
        .filter((item: FileItem) => item.type === 'file')
        .map((item: FileItem) => workflowBaseName(item.path))
        .sort((a: string, b: string) => a.localeCompare(b));
      setWorkflowOptions(nextWorkflows);
    } catch (err) {
      console.error('Failed to fetch execute options:', err);
    }
  };

  const saveCurrentContent = async (): Promise<boolean> => {
    if (!currentTask || selectedKind === 'image' || selectedKind === 'audio' || selectedKind === 'video' || selectedKind === 'pdf') {
      return true;
    }
    const contentToSave = editorContentRef.current;
    setEditorSaving(true);
    setEditorError('');
    setNotice('');
    try {
      await axios.post(`${API_BASE_URL}/media/save`, {
        path: currentTask,
        content: contentToSave,
      });
      lastLoadedContentRef.current = contentToSave;
      setNotice('Saved automatically.');
      await fetchTree();
      return true;
    } catch (err: any) {
      console.error('Failed to save media content:', err);
      setEditorError(err?.response?.data?.error || 'Failed to save content.');
      return false;
    } finally {
      setEditorSaving(false);
    }
  };

  const openMediaModal = () => {
    setMediaNameInput(currentMediaFolder || '');
    setMediaRequirementsInput('');
    setMediaType('');
    setMediaModalOpened(true);
    setEditorError('');
    setNotice('');
  };

  const createMedia = async () => {
    setCreatingMedia(true);
    setEditorError('');
    setNotice('');
    try {
      const skillName = mediaTypeSkillName(mediaType);
      const requirements = skillName
        ? `Use agent skill \`${skillName}\` to finish the task:\n\n${mediaRequirementsInput}`.trimEnd()
        : mediaRequirementsInput;
      const res = await axios.post(`${API_BASE_URL}/media/create`, {
        folder: mediaNameInput,
        file: 'requirements.md',
        requirements,
      });
      const createdPath = String(res.data.path || '');
      setMediaModalOpened(false);
      await fetchTree();
      if (createdPath) {
        router.push(`/media?media=${encodeURIComponent(createdPath)}`, undefined, { shallow: true });
      }
    } catch (err: any) {
      console.error('Failed to create media:', err);
      setEditorError(err?.response?.data?.error || 'Failed to create media.');
    } finally {
      setCreatingMedia(false);
    }
  };

  const deleteCurrentFile = async () => {
    if (!currentTask) return;

    let confirmText = '';
    if (currentFileName === 'requirements.md') {
      const typed = window.prompt(`Deleting ${currentTask} will remove the full media folder. Type delete to confirm.`);
      if (typed === null) return;
      confirmText = typed;
    } else if (!window.confirm(`Delete ${currentTask}?`)) {
      return;
    }

    setDeletingFile(true);
    setEditorError('');
    setNotice('');
    try {
      await axios.post(`${API_BASE_URL}/media/delete`, {
        path: currentTask,
        confirm_text: confirmText,
      });
      await fetchTree();
      router.push('/media', undefined, { shallow: true });
    } catch (err: any) {
      console.error('Failed to delete media file:', err);
      setEditorError(err?.response?.data?.error || 'Failed to delete file.');
    } finally {
      setDeletingFile(false);
    }
  };

  const createFileInMedia = async (mediaFolderPath: string) => {
    setFileContextMenu(null);
    const name = window.prompt('File name');
    if (!name) return;
    const parentPath = mediaProjectPath(mediaFolderPath);
    const projectPath = `${parentPath}/${name}`.replace(/\/+/g, '/');
    setEditorError('');
    setNotice('');
    try {
      await axios.post(apiUrl('/api/files/write'), {
        path: projectPath,
        content: '',
      });
      const nextPath = mediaRelativePath(projectPath);
      setExpandedFolders((prev) => Array.from(new Set([...prev, mediaFolderPath])));
      await fetchTree();
      router.push(`/media?media=${encodeURIComponent(nextPath)}`, undefined, { shallow: true });
    } catch (err: any) {
      console.error('Failed to create media file:', err);
      setEditorError(err?.response?.data?.error || 'Failed to create file.');
    }
  };

  const createFolderInMedia = async (mediaFolderPath: string) => {
    setFileContextMenu(null);
    const name = window.prompt('Folder name');
    if (!name) return;
    setEditorError('');
    setNotice('');
    try {
      await axios.post(apiUrl('/api/files/mkdir'), {
        parent: mediaProjectPath(mediaFolderPath),
        name,
      });
      setExpandedFolders((prev) => Array.from(new Set([...prev, mediaFolderPath])));
      await fetchTree();
    } catch (err: any) {
      console.error('Failed to create media folder:', err);
      setEditorError(err?.response?.data?.error || 'Failed to create folder.');
    }
  };

  const openUploadForMedia = (mediaFolderPath: string) => {
    setFileContextMenu(null);
    uploadTargetRef.current = mediaProjectPath(mediaFolderPath);
    uploadInputRef.current?.click();
  };

  const uploadFilesToMedia = async (files: FileList | null) => {
    if (!files?.length) return;
    setEditorError('');
    setNotice('');
    try {
      for (const file of Array.from(files)) {
        const formData = new FormData();
        formData.append('path', uploadTargetRef.current);
        formData.append('file', file);
        await axios.post(apiUrl('/api/files/upload'), formData);
      }
      const mediaFolderPath = mediaRelativePath(uploadTargetRef.current);
      if (mediaFolderPath) {
        setExpandedFolders((prev) => Array.from(new Set([...prev, mediaFolderPath])));
      }
      await fetchTree();
    } catch (err: any) {
      console.error('Failed to upload media file:', err);
      setEditorError(err?.response?.data?.error || 'Failed to upload file.');
    }
  };

  const renameMediaPath = async (item: FileItem) => {
    const nextName = window.prompt('Rename', item.name);
    if (!nextName || nextName === item.name) return;
    setEditorError('');
    setNotice('');
    try {
      const res = await axios.post(apiUrl('/api/files/rename'), {
        id: mediaProjectPath(item.path),
        name: nextName,
      });
      const nextPath = mediaRelativePath(String(res.data?.newId || ''));
      setFileContextMenu(null);
      await fetchTree();
      if (currentTask === item.path && nextPath) {
        router.push(`/media?media=${encodeURIComponent(nextPath)}`, undefined, { shallow: true });
      } else if (currentTask.startsWith(`${item.path}/`) && nextPath) {
        const suffix = currentTask.slice(item.path.length);
        router.push(`/media?media=${encodeURIComponent(`${nextPath}${suffix}`)}`, undefined, { shallow: true });
      }
    } catch (err: any) {
      console.error('Failed to rename media path:', err);
      setEditorError(err?.response?.data?.error || 'Failed to rename file.');
    }
  };

  const deleteMediaFolder = async (item: FileItem) => {
    const typed = window.prompt(`Deleting ${item.path} will remove this folder and every file inside it. Type delete to confirm.`);
    if (typed === null) return;
    if (typed.trim().toLowerCase() !== 'delete') {
      setEditorError("Type 'delete' to confirm removing the folder.");
      return;
    }

    setEditorError('');
    setNotice('');
    setDeletingFile(true);
    try {
      await axios.post(apiUrl('/api/files/delete'), {
        ids: [mediaProjectPath(item.path)],
      });
      setFileContextMenu(null);
      setExpandedFolders((prev) => prev.filter((path) => path !== item.path && !path.startsWith(`${item.path}/`)));
      await fetchTree();
      if (currentTask === item.path || currentTask.startsWith(`${item.path}/`)) {
        router.push('/media', undefined, { shallow: true });
      }
    } catch (err: any) {
      console.error('Failed to delete media folder:', err);
      setEditorError(err?.response?.data?.error || 'Failed to delete folder.');
    } finally {
      setDeletingFile(false);
    }
  };

  const deleteMediaFile = async (item: FileItem) => {
    let confirmText = '';
    if (item.name === 'requirements.md') {
      const typed = window.prompt(`Deleting ${item.path} will remove the full media folder. Type delete to confirm.`);
      if (typed === null) return;
      confirmText = typed;
    } else if (!window.confirm(`Delete ${item.path}?`)) {
      return;
    }

    setEditorError('');
    setNotice('');
    setDeletingFile(true);
    try {
      await axios.post(`${API_BASE_URL}/media/delete`, {
        path: item.path,
        confirm_text: confirmText,
      });
      setFileContextMenu(null);
      await fetchTree();
      if (currentTask === item.path) {
        router.push('/media', undefined, { shallow: true });
      }
    } catch (err: any) {
      console.error('Failed to delete media file:', err);
      setEditorError(err?.response?.data?.error || 'Failed to delete file.');
    } finally {
      setDeletingFile(false);
    }
  };

  const copyMediaPath = async (item: FileItem) => {
    try {
      await navigator.clipboard.writeText(mediaProjectPath(item.path));
      setFileContextMenu(null);
      setNotice('Path copied.');
    } catch {
      setEditorError('Failed to copy path.');
    }
  };

  const openExecuteModal = (action: MediaAction) => {
    setPendingAction(action);
    setExecuteMode('skill');
    setSelectedSkill(AUTO_EXECUTE_OPTION);
    setSelectedWorkflow(AUTO_EXECUTE_OPTION);
    setExecuteOpened(true);
  };

  const runAction = async () => {
    if (!currentTask || !pendingAction) return;
    const target = executeMode === 'skill' ? selectedSkill : selectedWorkflow;
    if (!target) return;
    const shouldRunWorkflow = executeMode === 'workflow' && !isAutoExecuteTarget(target);

    const saved = await saveCurrentContent();
    if (!saved) return;

    const prompt = executeMode === 'skill'
      ? (isAutoExecuteTarget(target)
          ? `Find and use the correct agent skill ${pendingAction.skillPromptSuffix}`
          : `Use agent skill ${target} ${pendingAction.skillPromptSuffix}`)
      : (shouldRunWorkflow
          ? `Execute workflow ${workflowProjectPath(target)}. ${pendingAction.skillPromptSuffix.charAt(0).toUpperCase()}${pendingAction.skillPromptSuffix.slice(1)}\n\nYour Workspace path: ${currentMediaFolder ? mediaProjectPath(currentMediaFolder) : 'workspace/media'}\n\nIf you create any intermediate files, save them inside the media workspace above.`
          : `Find and use the correct workflow ${pendingAction.skillPromptSuffix}`);

    setExecuteOpened(false);
    setSessionPromptText(prompt);
    setNewSessionWorkflow(shouldRunWorkflow ? `${target}.json` : null);
    setNewSessionNextNodeTrigger('auto_continue');
    setNewSessionWorkflowResumeAvailable(false);
    setNewSessionWorkflowResume(false);
    setLiveSessionName(null);
    setWorkflowSessionActive(false);
    setWorkflowExecuteStatus(null);
    setSessionPanelHeight(50);
    setSessionPanelOpen(true);
  };

  const closeSessionPanel = () => {
    setSessionPanelOpen(false);
    setIsSessionPanelResizing(false);
    setLiveSessionName(null);
    setWorkflowSessionActive(false);
    setWorkflowExecuteStatus(null);
    setStartingSession(false);
    setNewSessionWorkflow(null);
    setNewSessionWorkflowResumeAvailable(false);
    setNewSessionWorkflowResume(false);
  };

  const openNewMediaPromptPanel = () => {
    setSessionPromptText('Describe the image, audio, or video you want to create:\n\n');
    setNewSessionWorkflow(null);
    setNewSessionNextNodeTrigger('auto_continue');
    setNewSessionWorkflowResumeAvailable(false);
    setNewSessionWorkflowResume(false);
    setLiveSessionName(null);
    setWorkflowSessionActive(false);
    setWorkflowExecuteStatus(null);
    setSessionPanelHeight(50);
    setSessionPanelOpen(true);
  };

  const handleStartSession = async (path?: string) => {
    const trimmedPrompt = sessionPromptText.trim();
    if (!trimmedPrompt || startingSession) return;
    const provider = llmProvider || 'gemini';
    setStartingSession(true);
    try {
      const endpoint = newSessionWorkflow ? `${API_BASE_URL}/workflows/execute` : `${API_BASE_URL}/terminal/tmux/create`;
      const payload = newSessionWorkflow
        ? {
            workflow: newSessionWorkflow,
            prompt: trimmedPrompt,
            path: path || undefined,
            sandbox: newSessionSandbox,
            auto: newSessionAuto,
            network: newSessionNetwork,
            next_node_trigger: newSessionNextNodeTrigger,
            resume: newSessionWorkflowResume,
          }
        : {
            provider_id: provider,
            prompt: trimmedPrompt,
            path: path || undefined,
            sandbox: newSessionSandbox,
            auto: newSessionAuto,
            network: newSessionNetwork,
          };
      const res = await axios.post(endpoint, payload);
      const sessionName: string | undefined = res.data?.session?.name;
      if (sessionName) {
        setLiveSessionName(sessionName);
        if (newSessionWorkflow) {
          setWorkflowSessionActive(true);
          setWorkflowExecuteStatus(null);
        }
      }
    } catch (err) {
      console.error('Failed to start media session:', err);
    } finally {
      setStartingSession(false);
    }
  };

  const handleWorkflowContinue = async () => {
    if (continuingWorkflow) return;
    setContinuingWorkflow(true);
    try {
      await axios.post(`${API_BASE_URL}/workflows/execute/continue`, {}, { withCredentials: true });
      const res = await axios.get(`${API_BASE_URL}/workflows/execute/status`, { withCredentials: true });
      setWorkflowExecuteStatus(res.data as WorkflowExecuteStatus);
    } catch (err) {
      console.error('Failed to continue workflow:', err);
    } finally {
      setContinuingWorkflow(false);
    }
  };

  useWorkspaceWatcher({
    prefix: '/workspace/media',
    onTreeChange: () => { void fetchTree(); },
    currentFilePath: currentTask ? `/workspace/media/${currentTask}` : null,
    onCurrentFileChange: () => {
      if (!currentTask) return;
      if (editorContentRef.current === lastLoadedContentRef.current) {
        setNotice('File updated on disk.');
        void fetchContent(currentTask);
      } else {
        setEditorError('File changed on disk. Reload after saving or discard your edits.');
      }
    },
  });

  useEffect(() => {
    const closeFileContextMenu = () => setFileContextMenu(null);
    window.addEventListener('pointerdown', closeFileContextMenu);
    return () => window.removeEventListener('pointerdown', closeFileContextMenu);
  }, []);

  useEffect(() => {
    fetchTree();
    fetchLlmProviders();
    fetchExecuteOptions();
    void axios.get(`${API_BASE_URL}/config/settings`).then((res) => {
      const security = res.data?.security?.newSession;
      if (!security) return;
      setNewSessionSandbox(Boolean(security.sandbox));
      setNewSessionAuto(Boolean(security.auto));
      setNewSessionNetwork(security.network !== false);
    }).catch((err) => {
      console.error('Failed to fetch media session settings:', err);
    });
  }, []);

  useEffect(() => {
    if (currentTask) {
      fetchContent(currentTask);
    } else if (router.isReady && currentView === 'explorer') {
      fetchLatest();
    }
  }, [currentTask, currentView, router.isReady]);

  useEffect(() => {
    if (autoSaveTimerRef.current) {
      window.clearTimeout(autoSaveTimerRef.current);
      autoSaveTimerRef.current = null;
    }

    if (
      !currentTask ||
      loading ||
      (selectedKind !== 'markdown' && selectedKind !== 'text') ||
      editorContent === lastLoadedContentRef.current
    ) {
      return undefined;
    }

    autoSaveTimerRef.current = window.setTimeout(() => {
      autoSaveTimerRef.current = null;
      void saveCurrentContent();
    }, 900);

    return () => {
      if (autoSaveTimerRef.current) {
        window.clearTimeout(autoSaveTimerRef.current);
        autoSaveTimerRef.current = null;
      }
    };
  }, [currentTask, editorContent, loading, selectedKind]);

  useEffect(() => {
    if (!workflowSessionActive) return undefined;

    const poll = async () => {
      try {
        const res = await axios.get(`${API_BASE_URL}/workflows/execute/status`, { withCredentials: true });
        const status = res.data as WorkflowExecuteStatus;
        setWorkflowExecuteStatus(status);
        if (status.status === 'finished' || status.status === 'error' || status.status === 'terminated') {
          setWorkflowSessionActive(false);
        }
      } catch {
        // Ignore transient polling failures while the session is running.
      }
    };

    void poll();
    const intervalId = window.setInterval(() => void poll(), 3000);
    return () => window.clearInterval(intervalId);
  }, [workflowSessionActive]);

  const sortItems = (items: FileItem[]): FileItem[] => {
    const sorted = [...items].sort((a, b) => {
      if (a.type === 'dir' && b.type !== 'dir') return -1;
      if (a.type !== 'dir' && b.type === 'dir') return 1;
      if (sortByTime) return b.mtime - a.mtime;
      return a.name.localeCompare(b.name);
    });
    return sorted.map((item) => (item.children ? { ...item, children: sortItems(item.children) } : item));
  };

  const sortedTreeData = useMemo(() => sortItems(treeData), [treeData, sortByTime]);
  const dashboardItems = useMemo(() => collectMediaDashboardItems(sortedTreeData), [sortedTreeData]);

  const renderTree = (items: FileItem[]) => items.map((item) => {
    const isSelected = currentTask === item.path;
    if (item.type === 'dir') {
      const mediaLabel = (
        <Group position="apart" spacing={6} noWrap style={{ width: '100%' }}>
          <Text size="sm" truncate>{item.name}</Text>
          <Menu shadow="md" width={160} withinPortal position="bottom-end">
            <Menu.Target>
              <ActionIcon
                size="sm"
                variant="subtle"
                aria-label={`Add to ${item.name}`}
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                }}
              >
                <IconPlus size="0.95rem" />
              </ActionIcon>
            </Menu.Target>
            <Menu.Dropdown onClick={(event) => event.stopPropagation()}>
              <Menu.Item icon={<IconFilePlus size="0.95rem" />} onClick={() => void createFileInMedia(item.path)}>
                New File
              </Menu.Item>
              <Menu.Item icon={<IconFolderPlus size="0.95rem" />} onClick={() => void createFolderInMedia(item.path)}>
                New Folder
              </Menu.Item>
              <Menu.Item icon={<IconFileUpload size="0.95rem" />} onClick={() => openUploadForMedia(item.path)}>
                Upload File
              </Menu.Item>
            </Menu.Dropdown>
          </Menu>
        </Group>
      );
      return (
        <NavLink
          key={item.path}
          label={mediaLabel}
          icon={<IconFolder size="1.2rem" stroke={1.5} color={theme.colors.blue[6]} />}
          childrenOffset={16}
          opened={expandedFolders.includes(item.path)}
          onContextMenu={(event) => {
            event.preventDefault();
            event.stopPropagation();
            setFileContextMenu({ x: event.clientX, y: event.clientY, item });
          }}
          onChange={(nextOpened) => {
            setExpandedFolders((prev) => (
              nextOpened
                ? Array.from(new Set([...prev, item.path]))
                : prev.filter((path) => path !== item.path)
            ));
          }}
        >
          {item.children && renderTree(item.children)}
        </NavLink>
      );
    }

    return (
      <NavLink
        key={item.path}
        label={item.name}
        icon={<IconFileText size="1.2rem" stroke={1.5} color={theme.colors.gray[6]} />}
        active={isSelected}
        onContextMenu={(event) => {
          event.preventDefault();
          event.stopPropagation();
          setFileContextMenu({ x: event.clientX, y: event.clientY, item });
        }}
        onClick={() => {
          setFileContextMenu(null);
          router.push(`/media?media=${encodeURIComponent(item.path)}`, undefined, { shallow: true });
          setOpened(false);
        }}
      />
    );
  });

  const currentInstructionPath = currentTask ? mediaProjectPath(currentTask) : '';
  const fileActions = useMemo<MediaAction[]>(() => {
    if (currentFileName !== 'requirements.md' || !currentInstructionPath) return [];
    return [
      {
        label: 'Create',
        defaultSkill: 'create-image-audio',
        skillPromptSuffix: `to create media from the requirements defined at ${currentInstructionPath}`,
      },
    ];
  }, [currentFileName, currentInstructionPath]);

  const mediaUrl = currentTask ? `${API_BASE_URL}/media/file?path=${encodeURIComponent(currentTask)}` : '';
  const isMarkdownEditor = selectedKind === 'markdown';
  const isTextEditor = selectedKind === 'text';
  const renderHeaderActions = () => {
    if (!currentTask) return null;
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 8, flex: '0 0 auto', flexWrap: 'wrap' }}>
        {(isMarkdownEditor || isTextEditor) && (
          <Text size="xs" color={editorSaving ? 'dimmed' : 'green'}>
            {editorSaving ? 'Saving...' : 'Auto-save on'}
          </Text>
        )}
        {isMarkdownEditor && (
          <>
            <Button size="xs" variant={markdownView === 'editor' ? 'filled' : 'default'} onClick={() => setMarkdownView('editor')}>
              Edit
            </Button>
            <Button size="xs" variant={markdownView === 'preview' ? 'filled' : 'default'} onClick={() => setMarkdownView('preview')}>
              Preview
            </Button>
          </>
        )}
        {fileActions.map((action) => (
          <Button key={action.label} size="xs" variant="default" onClick={() => openExecuteModal(action)}>
            {action.label}
          </Button>
        ))}
      </div>
    );
  };

  const renderMainContent = () => {
    if (!currentTask) {
      if (loading) return null;
      if (treeData.length === 0) {
        return (
          <div
            style={{
              minHeight: '60vh',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <div
              style={{
                width: '100%',
                maxWidth: 560,
                padding: '36px 32px',
                borderRadius: 20,
                border: `1px solid ${theme.colorScheme === 'dark' ? theme.colors.dark[4] : '#d6def8'}`,
                background: theme.colorScheme === 'dark'
                  ? 'linear-gradient(180deg, rgba(37,38,43,0.98) 0%, rgba(28,29,33,0.98) 100%)'
                  : 'linear-gradient(180deg, #fbfcff 0%, #f2f6ff 100%)',
                boxShadow: theme.colorScheme === 'dark'
                  ? '0 24px 60px rgba(0, 0, 0, 0.28)'
                  : '0 24px 60px rgba(50, 84, 160, 0.12)',
                textAlign: 'center',
              }}
            >
              <Text
                size="xs"
                weight={700}
                transform="uppercase"
                style={{ letterSpacing: '0.12em', color: theme.colors.blue[6] }}
              >
                Media Workspace
              </Text>
              <Text size={28} weight={800} mt={10}>
                Start your first media
              </Text>
              <Text size="sm" color="dimmed" mt={12} style={{ maxWidth: 420, margin: '12px auto 0 auto', lineHeight: 1.6 }}>
                Create a media folder with a requirements file, then refine it or create video, audio, or image outputs with a skill or workflow.
              </Text>
              <Group position="center" mt="xl">
                <Button onClick={openMediaModal}>New Media</Button>
              </Group>
            </div>
          </div>
        );
      }
      return <Text align="center" py="xl" color="dimmed">Select a media file from the sidebar to begin.</Text>;
    }

    if (selectedKind === 'pdf' && currentTask) {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
          <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
            <iframe title={currentFileName} src={mediaUrl} style={{ width: '100%', height: '100%', border: 'none' }} />
          </div>
          <div style={PAGE_ACTION_BAR_STYLE}>
            <Button size="xs" color="red" variant="light" onClick={() => void deleteCurrentFile()} loading={deletingFile}>Delete</Button>
          </div>
        </div>
      );
    }

    if (selectedKind === 'image' && currentTask) {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
          <div style={{ flex: 1, minHeight: 0, display: 'flex', justifyContent: 'center', alignItems: 'center', padding: 16, overflow: 'auto' }}>
            <img src={mediaUrl} alt={currentFileName} style={{ maxWidth: '100%', maxHeight: '70vh', objectFit: 'contain', borderRadius: 8 }} />
          </div>
          <div style={PAGE_ACTION_BAR_STYLE}>
            <Button size="xs" color="red" variant="light" onClick={() => void deleteCurrentFile()} loading={deletingFile}>Delete</Button>
          </div>
        </div>
      );
    }

    if (selectedKind === 'audio' && currentTask) {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
          <div style={{ flex: 1, minHeight: 0, padding: 24 }}>
            <audio controls src={mediaUrl} style={{ width: '100%' }}>
              Your browser does not support audio playback.
            </audio>
          </div>
          <div style={PAGE_ACTION_BAR_STYLE}>
            <Button size="xs" color="red" variant="light" onClick={() => void deleteCurrentFile()} loading={deletingFile}>Delete</Button>
          </div>
        </div>
      );
    }

    if (selectedKind === 'video' && currentTask) {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
          <div style={{ flex: 1, minHeight: 0, display: 'flex', justifyContent: 'center', padding: 16 }}>
            <video controls src={mediaUrl} style={{ width: '100%', maxHeight: '70vh', borderRadius: 8 }}>
              Your browser does not support video playback.
            </video>
          </div>
          <div style={PAGE_ACTION_BAR_STYLE}>
            <Button size="xs" color="red" variant="light" onClick={() => void deleteCurrentFile()} loading={deletingFile}>Delete</Button>
          </div>
        </div>
      );
    }

    if (isMarkdownEditor) {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
          {markdownView === 'editor' ? (
            <>
              <div style={{ flex: 1, minHeight: 0 }}>
                <Textarea
                  value={editorContent}
                  onChange={(e) => {
                    setEditorContent(e.currentTarget.value);
                    if (editorError) setEditorError('');
                    if (notice) setNotice('');
                  }}
                  autosize={false}
                  minRows={1}
                  styles={{
                    root: { height: '100%' },
                    wrapper: { height: '100%' },
                    input: PAGE_EDITOR_DARK_INPUT_STYLE,
                  }}
                />
              </div>
            </>
          ) : (
            <>
              <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: '20px 24px' }}>
                <div className="doc-markdown" style={{ maxWidth: 'none', margin: 0, minHeight: '100%', padding: '18px 20px 24px', border: 'none', borderRadius: 0, boxShadow: 'none', background: '#ffffff' }}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{editorContent}</ReactMarkdown>
                </div>
              </div>
            </>
          )}
        </div>
      );
    }

    if (isTextEditor) {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
          <div style={{ flex: 1, minHeight: 0 }}>
            <Textarea
              value={editorContent}
              onChange={(e) => {
                setEditorContent(e.currentTarget.value);
                if (editorError) setEditorError('');
                if (notice) setNotice('');
              }}
              autosize={false}
              minRows={1}
              styles={{
                root: { height: '100%' },
                wrapper: { height: '100%' },
                input: PAGE_EDITOR_DARK_INPUT_STYLE,
              }}
            />
          </div>
        </div>
      );
    }

    return !loading ? <Text align="center" py="xl" color="dimmed">Select a media file from the sidebar to begin.</Text> : null;
  };

  const renderDashboardThumb = (item: MediaDashboardItem) => {
    if (item.thumbnailPath) {
      return (
        <img
          src={mediaFileUrl(item.thumbnailPath)}
          alt={item.title}
          style={{ width: 84, height: 84, objectFit: 'cover', borderRadius: 8, display: 'block', background: '#e2e8f0' }}
        />
      );
    }
    const Icon = item.kind === 'audio' ? IconMusic : IconVideo;
    return (
      <div
        style={{
          width: 84,
          height: 84,
          borderRadius: 8,
          background: item.kind === 'audio' ? '#fef3c7' : '#dbeafe',
          color: item.kind === 'audio' ? '#92400e' : '#1d4ed8',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative',
          fontWeight: 800,
          fontSize: 24,
        }}
      >
        {item.initials}
        <Icon size="1rem" style={{ position: 'absolute', right: 8, bottom: 8, opacity: 0.7 }} />
      </div>
    );
  };

  const renderDashboard = () => (
    <MainLayout title="Media">
      <div
        ref={rightPaneRef}
        style={{
          height: 'calc(100vh - 60px)',
          minHeight: 0,
          display: 'grid',
          gridTemplateRows: sessionPanelOpen ? `${100 - sessionPanelHeight}fr 12px ${sessionPanelHeight}fr` : '1fr',
          overflow: 'hidden',
          background: '#ffffff',
        }}
      >
        <div style={{ minHeight: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          {(editorError || notice) && (
            <div style={{ flexShrink: 0, borderBottom: '1px solid #e5e7eb' }}>
              {editorError && <Text color="red" size="sm" px={24} py={10}>{editorError}</Text>}
              {!editorError && notice && <Text color="green" size="sm" px={24} py={10}>{notice}</Text>}
            </div>
          )}
          <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
            <div style={{ padding: '20px 24px', borderBottom: '1px solid #e5e7eb', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
              <div>
                <Text size={20} weight={800}>Media</Text>
                <Text size="sm" color="dimmed">Images, audio, and videos</Text>
              </div>
              <Group spacing={8}>
                <Tooltip label="Refresh">
                  <ActionIcon variant="light" size="lg" onClick={() => void fetchTree()} aria-label="Refresh media">
                    <IconRefresh size="1.2rem" />
                  </ActionIcon>
                </Tooltip>
                <Tooltip label="Directory Tree">
                  <ActionIcon
                    variant="light"
                    size="lg"
                    onClick={() => { void router.push('/media?view=explorer', undefined, { shallow: true }); }}
                    aria-label="Open Directory Tree view"
                  >
                    <IconHierarchy size="1.25rem" />
                  </ActionIcon>
                </Tooltip>
              </Group>
            </div>
            <div style={{ padding: '28px 32px' }}>
              {treeLoading && dashboardItems.length === 0 ? (
                <Text color="dimmed">Loading media...</Text>
              ) : (
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(132px, 1fr))',
                    gap: 22,
                    alignItems: 'start',
                  }}
                >
                  {dashboardItems.map((item) => (
                    <button
                      key={item.path}
                      type="button"
                      onClick={() => {
                        setMediaPreviewSize(null);
                        setMediaPreview(item);
                      }}
                      style={{
                        border: '1px solid transparent',
                        background: 'transparent',
                        padding: 12,
                        borderRadius: 8,
                        cursor: 'pointer',
                        minHeight: 132,
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: 10,
                      }}
                      onMouseEnter={(event) => {
                        event.currentTarget.style.borderColor = '#dbe3f0';
                        event.currentTarget.style.background = '#f8fafc';
                      }}
                      onMouseLeave={(event) => {
                        event.currentTarget.style.borderColor = 'transparent';
                        event.currentTarget.style.background = 'transparent';
                      }}
                    >
                      {renderDashboardThumb(item)}
                      <Text size="sm" weight={700} align="center" style={{ lineHeight: 1.25, wordBreak: 'break-word' }}>
                        {item.title}
                      </Text>
                    </button>
                  ))}
                  <button
                    type="button"
                    onClick={openNewMediaPromptPanel}
                    style={{
                      border: '1px dashed #94a3b8',
                      background: '#f8fafc',
                      color: '#334155',
                      padding: 12,
                      borderRadius: 8,
                      cursor: 'pointer',
                      minHeight: 132,
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 10,
                    }}
                  >
                    <IconPlus size={52} stroke={1.6} />
                    <Text size="sm" weight={700}>New Media</Text>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
        {sessionPanelOpen && (
          <>
            <div
              onMouseDown={(event) => {
                event.preventDefault();
                setIsSessionPanelResizing(true);
              }}
              style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'row-resize', color: '#93a4cc' }}
            >
              <span style={{ fontSize: 16, lineHeight: 1 }}>...</span>
            </div>
            <div style={{ minHeight: 0, overflow: 'hidden' }}>
              <EmbeddedSessionPanel
                currentLabel="Media session"
                liveSessionName={liveSessionName}
                sessionPromptText={sessionPromptText}
                setSessionPromptText={setSessionPromptText}
                newSessionWorkflow={newSessionWorkflow}
                newSessionSandbox={newSessionSandbox}
                setNewSessionSandbox={setNewSessionSandbox}
                newSessionAuto={newSessionAuto}
                setNewSessionAuto={setNewSessionAuto}
                newSessionNetwork={newSessionNetwork}
                setNewSessionNetwork={setNewSessionNetwork}
                newSessionNextNodeTrigger={newSessionNextNodeTrigger}
                setNewSessionNextNodeTrigger={setNewSessionNextNodeTrigger}
                newSessionWorkflowResumeAvailable={newSessionWorkflowResumeAvailable}
                newSessionWorkflowResume={newSessionWorkflowResume}
                setNewSessionWorkflowResume={setNewSessionWorkflowResume}
                startingSession={startingSession}
                onStart={() => void handleStartSession('workspace/media')}
                onClose={closeSessionPanel}
                workflowExecuteStatus={workflowExecuteStatus}
                workflowSessionActive={workflowSessionActive}
                continuingWorkflow={continuingWorkflow}
                onContinueWorkflow={() => void handleWorkflowContinue()}
                hideSessionRootSelect
              />
            </div>
          </>
        )}
        {mediaPreview && (
          <FloatingPopup
            title={mediaPreview.title}
            onClose={() => {
              setMediaPreview(null);
              setMediaPreviewSize(null);
            }}
            initialWidth={mediaPreviewSize?.width || (mediaPreview.kind === 'audio' ? 520 : 920)}
            initialHeight={mediaPreviewSize?.height || (mediaPreview.kind === 'audio' ? 180 : 560)}
          >
            {mediaPreview.kind === 'image' && (
              <img src={mediaFileUrl(mediaPreview.path)} alt={mediaPreview.title} style={{ width: '100%', display: 'block' }} />
            )}
            {mediaPreview.kind === 'video' && (
              <PopupVideoPlayer
                src={mediaFileUrl(mediaPreview.path)}
                title={mediaPreview.title}
                onRatioDetected={(ratio) => {
                  const maxWidth = Math.max(320, window.innerWidth - 96);
                  const maxContentHeight = Math.max(220, window.innerHeight - 160);
                  let nextWidth = Math.min(920, maxWidth);
                  let nextContentHeight = nextWidth / ratio;
                  if (nextContentHeight > maxContentHeight) {
                    nextContentHeight = maxContentHeight;
                    nextWidth = nextContentHeight * ratio;
                  }
                  setMediaPreviewSize({
                    width: Math.round(nextWidth),
                    height: Math.round(nextContentHeight + 44),
                  });
                }}
              />
            )}
            {mediaPreview.kind === 'audio' && (
              <div style={{ padding: 18 }}>
                <audio src={mediaFileUrl(mediaPreview.path)} controls autoPlay style={{ width: '100%' }} />
              </div>
            )}
          </FloatingPopup>
        )}
      </div>
    </MainLayout>
  );

  if (currentView === 'dashboard') {
    return renderDashboard();
  }

  return (
    <AppShell
      styles={{
        main: {
          background: theme.colorScheme === 'dark' ? theme.colors.dark[8] : theme.colors.gray[0],
          padding: 0,
          marginTop: 60,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          height: 'calc(100vh - 60px)',
          minHeight: 0,
        },
      }}
      navbarOffsetBreakpoint="sm"
      header={
        <Header
          height={{ base: 60 }}
          p="md"
          styles={{
            root: isDevMode ? { borderBottom: '2px solid #228be6' } : undefined,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', height: '100%', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <MediaQuery largerThan="sm" styles={{ display: 'none' }}>
                <Burger opened={opened} onClick={() => setOpened((o) => !o)} size="sm" color={theme.colors.gray[6]} mr="xl" />
              </MediaQuery>
              <a href="/"><img className="h-10" src="/images/skill-pilot-2.png" alt="Logo" /></a>
            </div>
            <Group spacing="xs">
              <Select
                placeholder="LLM"
                value={llmProvider}
                onChange={(value) => {
                  if (!value) return;
                  setLlmProvider(value);
                  setSelectedProvider(value);
                }}
                data={llmProviders.map((p) => ({ value: p.id, label: p.name }))}
                size="xs"
                style={{ width: 200 }}
              />
            </Group>
          </div>
        </Header>
      }
    >
      <Head>
        <title>Skill Pilot - Media</title>
      </Head>

      <input
        ref={uploadInputRef}
        type="file"
        multiple
        style={{ display: 'none' }}
        onChange={(event) => {
          void uploadFilesToMedia(event.currentTarget.files);
          event.currentTarget.value = '';
        }}
      />

      {fileContextMenu && (
        <div
          style={{
            position: 'fixed',
            top: fileContextMenu.y,
            left: fileContextMenu.x,
            zIndex: 1000,
            minWidth: 150,
            padding: 6,
            borderRadius: 8,
            border: '1px solid #dbe3ef',
            background: '#ffffff',
            boxShadow: '0 18px 40px rgba(15, 23, 42, 0.16)',
          }}
          onPointerDown={(event) => event.stopPropagation()}
          onContextMenu={(event) => event.preventDefault()}
        >
          {fileContextMenu.item.type === 'dir' && (
            <>
              <button
                type="button"
                onClick={() => { void createFileInMedia(fileContextMenu.item.path); }}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '8px 10px',
                  border: 'none',
                  borderRadius: 6,
                  background: 'transparent',
                  color: '#1f2937',
                  cursor: 'pointer',
                  textAlign: 'left',
                }}
              >
                <IconFilePlus size="0.95rem" />
                Add File
              </button>
              <button
                type="button"
                onClick={() => { void createFolderInMedia(fileContextMenu.item.path); }}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '8px 10px',
                  border: 'none',
                  borderRadius: 6,
                  background: 'transparent',
                  color: '#1f2937',
                  cursor: 'pointer',
                  textAlign: 'left',
                }}
              >
                <IconFolderPlus size="0.95rem" />
                Add Folder
              </button>
              <button
                type="button"
                onClick={() => openUploadForMedia(fileContextMenu.item.path)}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '8px 10px',
                  border: 'none',
                  borderRadius: 6,
                  background: 'transparent',
                  color: '#1f2937',
                  cursor: 'pointer',
                  textAlign: 'left',
                }}
              >
                <IconFileUpload size="0.95rem" />
                Upload File
              </button>
              <div style={{ height: 1, margin: '6px 4px', background: '#e5e7eb' }} />
            </>
          )}
          <button
            type="button"
            onClick={() => {
              if (fileContextMenu.item.type === 'dir') {
                void deleteMediaFolder(fileContextMenu.item);
              } else {
                void deleteMediaFile(fileContextMenu.item);
              }
            }}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 10px',
              border: 'none',
              borderRadius: 6,
              background: 'transparent',
              color: '#dc2626',
              cursor: 'pointer',
              textAlign: 'left',
            }}
          >
            Delete
          </button>
          <button
            type="button"
            onClick={() => { void renameMediaPath(fileContextMenu.item); }}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 10px',
              border: 'none',
              borderRadius: 6,
              background: 'transparent',
              color: '#1f2937',
              cursor: 'pointer',
              textAlign: 'left',
            }}
          >
            Rename
          </button>
          <button
            type="button"
            onClick={() => { void copyMediaPath(fileContextMenu.item); }}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 10px',
              border: 'none',
              borderRadius: 6,
              background: 'transparent',
              color: '#1f2937',
              cursor: 'pointer',
              textAlign: 'left',
            }}
          >
            Copy Path
          </button>
        </div>
      )}

      <Modal opened={mediaModalOpened} onClose={() => setMediaModalOpened(false)} title="New Media" centered>
        <div>
          <Text size="sm" weight={700} mb={4}>Media Name</Text>
          <TextInput
            placeholder="media-name"
            value={mediaNameInput}
            onChange={(e) => setMediaNameInput(e.currentTarget.value)}
            description="A media folder will be created in kebab-case with requirements.md inside. Duplicates get _1, _2, and so on."
          />
        </div>
        <div style={{ marginTop: 16 }}>
          <Select
            label="Media Type"
            value={mediaType}
            onChange={(value) => setMediaType((value as MediaType) || '')}
            data={[
              { value: '', label: 'Auto' },
              { value: 'create-image-audio', label: 'Image or Audio' },
              { value: 'create-slide-show-video', label: 'Slide Video' },
              { value: 'multiple-scene-video', label: 'Multiple Scence Video' },
              { value: 'talking-head-video', label: 'Talking Head Video' },
              { value: 'lipsync-video', label: 'Lipsync Video' },
            ]}
            clearable={false}
          />
        </div>
        <div style={{ marginTop: 16 }}>
          <Text size="sm" weight={700} mb={4}>Media Requirements</Text>
          <Textarea
            value={mediaRequirementsInput}
            onChange={(e) => setMediaRequirementsInput(e.currentTarget.value)}
            minRows={10}
            autosize
          />
        </div>
        <Group position="right" mt="md">
          <Button variant="default" onClick={() => setMediaModalOpened(false)}>Cancel</Button>
          <Button onClick={() => void createMedia()} loading={creatingMedia} disabled={!mediaNameInput.trim()}>
            Create Media
          </Button>
        </Group>
      </Modal>

      <Modal
        opened={executeOpened}
        onClose={() => setExecuteOpened(false)}
        title={pendingAction ? pendingAction.label : 'Create Media'}
        centered
        size="lg"
      >
        <div>
          <Text size="sm" weight={700} mb={4}>Create By</Text>
          <Group mt="xs">
            <Radio value="skill" checked={executeMode === 'skill'} onChange={() => setExecuteMode('skill')} label="Skill" />
            <Radio value="workflow" checked={executeMode === 'workflow'} onChange={() => setExecuteMode('workflow')} label="Workflow" />
          </Group>
        </div>
        <div style={{ marginTop: 16 }}>
          {executeMode === 'skill' ? (
            <Select
              label="Skill"
              placeholder="Select a skill"
              value={selectedSkill}
              onChange={setSelectedSkill}
              data={skillSelectOptions}
              searchable
              clearable={false}
            />
          ) : (
            <Select
              label="Workflow"
              placeholder="Select a workflow"
              value={selectedWorkflow}
              onChange={setSelectedWorkflow}
              data={workflowSelectOptions}
              searchable
              clearable={false}
            />
          )}
        </div>
        <div style={{ marginTop: 16 }}>
          <Text size="sm" weight={700} mb={4}>Instruction File</Text>
          <Text size="sm">{currentInstructionPath || '(no file selected)'}</Text>
        </div>
        <Group position="right" mt="md">
          <Button variant="default" onClick={() => setExecuteOpened(false)}>Cancel</Button>
          <Button onClick={() => void runAction()} disabled={!currentTask || (executeMode === 'skill' ? !selectedSkill : !selectedWorkflow)}>
            Create
          </Button>
        </Group>
      </Modal>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <MediaQuery
          smallerThan="sm"
          styles={{
            display: opened ? 'flex' : 'none',
            position: 'absolute',
            inset: '0 auto 0 0',
            zIndex: 30,
          }}
        >
          <aside
            style={{
              width: navbarWidth,
              flexShrink: 0,
              minHeight: 0,
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              background: '#ffffff',
              borderRight: '1px solid #e9ecef',
              position: 'relative',
              transition: isResizing ? 'none' : 'width 200ms ease',
            }}
          >
            <div style={{ padding: '12px 14px', minHeight: 46, borderBottom: '1px solid #eef2f7', flexShrink: 0 }}>
              <Group position="apart" align="center">
                <Group spacing={6} align="center">
                  <ActionIcon
                    variant="subtle"
                    onClick={() => { void router.push('/'); }}
                    title="Back to Home"
                  >
                    <IconArrowLeft size="1rem" />
                  </ActionIcon>
                  <Text weight={700} size="lg">Media</Text>
                </Group>
                <Group spacing={4}>
                  <Tooltip label="Dashboard">
                    <ActionIcon
                      variant="subtle"
                      onClick={() => { void router.push('/media', undefined, { shallow: true }); }}
                      aria-label="Open dashboard view"
                    >
                      <IconVideo size="1.1rem" />
                    </ActionIcon>
                  </Tooltip>
                  <Tooltip label="New Media">
                    <ActionIcon variant="subtle" onClick={openMediaModal}>
                      <IconPlus size="1.1rem" />
                    </ActionIcon>
                  </Tooltip>
                  <Tooltip label="Refresh">
                    <ActionIcon variant="subtle" onClick={() => void fetchTree()}>
                      <IconRefresh size="1.1rem" />
                    </ActionIcon>
                  </Tooltip>
                  <Tooltip label={sortByTime ? 'Sorted by Time' : 'Sorted Alpha'}>
                    <ActionIcon variant="subtle" onClick={() => setSortByTime(!sortByTime)}>
                      {sortByTime ? <IconClock size="1.1rem" /> : <IconSortAscending size="1.1rem" />}
                    </ActionIcon>
                  </Tooltip>
                </Group>
              </Group>
            </div>
            <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
              <ScrollArea style={{ height: '100%' }} px="md" py="sm">
                {treeLoading && treeData.length === 0 ? (
                  <Box py="xl" sx={{ textAlign: 'center' }}><Text size="sm" color="dimmed">Loading...</Text></Box>
                ) : (
                  renderTree(sortedTreeData)
                )}
              </ScrollArea>
            </div>

            <div
              onMouseDown={startResizing}
              style={{
                position: 'absolute',
                top: 0,
                right: 0,
                width: '4px',
                height: '100%',
                cursor: 'col-resize',
                backgroundColor: isResizing ? theme.colors.blue[5] : 'transparent',
                transition: 'background-color 200ms ease',
                zIndex: 100,
              }}
              onMouseEnter={(e) => {
                if (!isResizing) e.currentTarget.style.backgroundColor = theme.colors.gray[3];
              }}
              onMouseLeave={(e) => {
                if (!isResizing) e.currentTarget.style.backgroundColor = 'transparent';
              }}
            />
          </aside>
        </MediaQuery>

        <main
          ref={rightPaneRef}
          style={{
            flex: 1,
            minWidth: 0,
            display: 'grid',
            gridTemplateRows: sessionPanelOpen ? `${100 - sessionPanelHeight}fr 12px ${sessionPanelHeight}fr` : '1fr',
            overflow: 'hidden',
          }}
        >
          <div style={{ minHeight: 0, overflow: 'hidden' }}>
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0, background: '#ffffff', borderLeft: '1px solid #d6def8' }}>
              <div style={PAGE_HEADER_BAR_STYLE}>
                <div style={{ fontSize: 12, color: '#64748b', minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: '1 1 240px' }}>
                  {currentTask || 'Select a media file from the sidebar'}
                </div>
                {renderHeaderActions()}
              </div>
              {(editorError || notice) && (
                <div style={{ flexShrink: 0 }}>
                  {editorError && <Text color="red" size="sm" px={18} py={10}>{editorError}</Text>}
                  {!editorError && notice && <Text color="green" size="sm" px={18} py={10}>{notice}</Text>}
                </div>
              )}
              <div style={{ flex: 1, minHeight: 0, overflow: 'hidden', position: 'relative', display: 'flex', flexDirection: 'column' }}>
                <LoadingOverlay visible={loading} overlayBlur={2} />
                {renderMainContent()}
              </div>
            </div>
          </div>
          {sessionPanelOpen && (
            <>
              <div
                onMouseDown={(event) => {
                  event.preventDefault();
                  setIsSessionPanelResizing(true);
                }}
                style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'row-resize', color: '#93a4cc' }}
              >
                <span style={{ fontSize: 16, lineHeight: 1 }}>⋯</span>
              </div>
              <div style={{ minHeight: 0, overflow: 'hidden' }}>
                <EmbeddedSessionPanel
                  currentLabel={currentTask || 'Media session'}
                  liveSessionName={liveSessionName}
                  sessionPromptText={sessionPromptText}
                  setSessionPromptText={setSessionPromptText}
                  newSessionWorkflow={newSessionWorkflow}
                  newSessionSandbox={newSessionSandbox}
                  setNewSessionSandbox={setNewSessionSandbox}
                  newSessionAuto={newSessionAuto}
                  setNewSessionAuto={setNewSessionAuto}
                  newSessionNetwork={newSessionNetwork}
                  setNewSessionNetwork={setNewSessionNetwork}
                  newSessionNextNodeTrigger={newSessionNextNodeTrigger}
                  setNewSessionNextNodeTrigger={setNewSessionNextNodeTrigger}
                  newSessionWorkflowResumeAvailable={newSessionWorkflowResumeAvailable}
                  newSessionWorkflowResume={newSessionWorkflowResume}
                  setNewSessionWorkflowResume={setNewSessionWorkflowResume}
                  startingSession={startingSession}
                  onStart={(path) => void handleStartSession(path)}
                  onClose={closeSessionPanel}
                  workflowExecuteStatus={workflowExecuteStatus}
                  workflowSessionActive={workflowSessionActive}
                  continuingWorkflow={continuingWorkflow}
                  onContinueWorkflow={() => void handleWorkflowContinue()}
                />
              </div>
            </>
          )}
        </main>
      </div>
    </AppShell>
  );
}

function FloatingPopup({
  title,
  children,
  onClose,
  initialWidth = 920,
  initialHeight = 560,
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
  initialWidth?: number;
  initialHeight?: number;
}) {
  const [size, setSize] = useState({ width: initialWidth, height: initialHeight });
  const [position, setPosition] = useState({ x: 80, y: 80 });
  const [dragStart, setDragStart] = useState<{ x: number; y: number; left: number; top: number } | null>(null);
  const [resizeStart, setResizeStart] = useState<{ x: number; y: number; width: number; height: number } | null>(null);

  useEffect(() => {
    const nextWidth = Math.min(initialWidth, Math.max(320, window.innerWidth - 48));
    const nextHeight = Math.min(initialHeight, Math.max(180, window.innerHeight - 96));
    setSize({ width: nextWidth, height: nextHeight });
    setPosition({
      x: Math.max(24, Math.round((window.innerWidth - nextWidth) / 2)),
      y: Math.max(24, Math.round((window.innerHeight - nextHeight) / 2)),
    });
  }, [initialHeight, initialWidth]);

  const stopPointerAction = () => {
    setDragStart(null);
    setResizeStart(null);
  };

  const movePopup = (event: React.PointerEvent<HTMLDivElement>) => {
    if (dragStart) {
      setPosition({
        x: Math.min(Math.max(8, dragStart.left + event.clientX - dragStart.x), Math.max(8, window.innerWidth - size.width - 8)),
        y: Math.min(Math.max(8, dragStart.top + event.clientY - dragStart.y), Math.max(8, window.innerHeight - 80)),
      });
    }
    if (resizeStart) {
      setSize({
        width: Math.min(Math.max(320, resizeStart.width + event.clientX - resizeStart.x), Math.max(320, window.innerWidth - position.x - 8)),
        height: Math.min(Math.max(180, resizeStart.height + event.clientY - resizeStart.y), Math.max(180, window.innerHeight - position.y - 8)),
      });
    }
  };

  return (
    <div
      style={{ position: 'fixed', inset: 0, zIndex: 2200, pointerEvents: 'none' }}
      onPointerMove={movePopup}
      onPointerUp={stopPointerAction}
      onPointerCancel={stopPointerAction}
    >
      <div
        style={{
          position: 'absolute',
          left: position.x,
          top: position.y,
          width: size.width,
          height: size.height,
          minWidth: 320,
          minHeight: 180,
          background: '#ffffff',
          border: '1px solid #dbe3ef',
          boxShadow: '0 24px 70px rgba(15, 23, 42, 0.28)',
          borderRadius: 8,
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          pointerEvents: 'auto',
        }}
      >
        <div
          onPointerDown={(event) => {
            event.currentTarget.setPointerCapture(event.pointerId);
            setDragStart({ x: event.clientX, y: event.clientY, left: position.x, top: position.y });
          }}
          style={{
            height: 44,
            flexShrink: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 12,
            padding: '0 10px 0 14px',
            borderBottom: '1px solid #e5e7eb',
            cursor: 'move',
            background: '#f8fafc',
          }}
        >
          <Text size="sm" weight={700} truncate>{title}</Text>
          <Button
            variant="subtle"
            size="xs"
            onPointerDown={(event) => event.stopPropagation()}
            onClick={(event) => {
              event.stopPropagation();
              onClose();
            }}
          >
            Close
          </Button>
        </div>
        <div style={{ flex: 1, minHeight: 0, overflow: 'auto', background: '#ffffff' }}>
          {children}
        </div>
        <div
          onPointerDown={(event) => {
            event.currentTarget.setPointerCapture(event.pointerId);
            setResizeStart({ x: event.clientX, y: event.clientY, width: size.width, height: size.height });
          }}
          title="Resize"
          style={{
            position: 'absolute',
            right: 0,
            bottom: 0,
            width: 28,
            height: 28,
            cursor: 'nwse-resize',
            display: 'flex',
            alignItems: 'flex-end',
            justifyContent: 'flex-end',
            padding: 5,
            zIndex: 2,
          }}
        >
          <div
            aria-hidden="true"
            style={{
              width: 13,
              height: 13,
              background: 'repeating-linear-gradient(135deg, transparent 0 4px, #64748b 4px 6px, transparent 6px 8px)',
              opacity: 0.85,
            }}
          />
        </div>
      </div>
    </div>
  );
}

function PopupVideoPlayer({
  src,
  title,
  onRatioDetected,
}: {
  src: string;
  title: string;
  onRatioDetected?: (ratio: number) => void;
}) {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
  }, [src]);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', minHeight: 220, background: '#000' }}>
      <video
        src={src}
        controls
        autoPlay
        aria-label={title}
        onLoadStart={() => setLoading(true)}
        onWaiting={() => setLoading(true)}
        onLoadedMetadata={(event) => {
          const video = event.currentTarget;
          if (video.videoWidth > 0 && video.videoHeight > 0) {
            onRatioDetected?.(video.videoWidth / video.videoHeight);
          }
        }}
        onCanPlay={() => setLoading(false)}
        onPlaying={() => setLoading(false)}
        onError={() => setLoading(false)}
        style={{ width: '100%', height: '100%', display: 'block', objectFit: 'contain', background: '#000' }}
      />
      {loading && (
        <div
          aria-label="Loading video"
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            pointerEvents: 'none',
            background: 'rgba(0, 0, 0, 0.18)',
          }}
        >
          <Loader size="lg" color="blue" />
        </div>
      )}
    </div>
  );
}

export async function getStaticProps({ locale }: GetStaticPropsContext) {
  return {
    props: {
      ...(await serverSideTranslations(locale ?? 'en', ['common'])),
    },
  };
}
