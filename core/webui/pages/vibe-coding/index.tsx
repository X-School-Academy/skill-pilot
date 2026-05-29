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
  LoadingOverlay,
  MediaQuery,
  Modal,
  Navbar,
  NavLink,
  Radio,
  ScrollArea,
  Select,
  Stack,
  Text,
  TextInput,
  Textarea,
  Tooltip,
  Burger,
  useMantineTheme,
} from '@mantine/core';
import {
  IconArrowLeft,
  IconBug,
  IconClock,
  IconCode,
  IconFilePlus,
  IconFileText,
  IconFileUpload,
  IconFolder,
  IconFolderPlus,
  IconHierarchy,
  IconMessageCirclePlus,
  IconPackage,
  IconPlayerPlay,
  IconPlayerStop,
  IconPlus,
  IconRefresh,
  IconRocket,
  IconSortAscending,
  IconUpload,
} from '@tabler/icons-react';
import EmbeddedSessionPanel, { WorkflowExecuteStatus } from '../../components/EmbeddedSessionPanel';
import MainLayout from '../../components/main-layout';
import { apiUrl } from '../../libs/api-base';
import { AUTO_EXECUTE_OPTION, buildExecuteSelectOptions, isAutoExecuteTarget } from '../../libs/execute-targets';
import { useWorkspaceWatcher } from '../../libs/file-events';
import { resolveSelectedProvider, setSelectedProvider } from '../../libs/llm';

const API_BASE_URL = apiUrl('/api');
axios.defaults.withCredentials = true;

type FileKind = 'markdown' | 'text' | 'image' | 'audio' | 'video';
type RequestMode = 'update' | 'issue';
type ExecuteMode = 'skill' | 'workflow';

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

interface VibeAction {
  label: string;
  defaultSkill: string;
  skillPromptSuffix: string;
}

interface VibeProjectSummary {
  name: string;
  path: string;
  display_name: string;
  initials: string;
  icon_path: string | null;
  commands: Record<'start' | 'dev' | 'build' | 'stop', string>;
  mtime: number;
}

const detectFileKind = (path: string): FileKind => {
  const lower = (path || '').toLowerCase();
  if (lower.endsWith('.md') || lower.endsWith('.markdown')) return 'markdown';
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

const vibeProjectPath = (path: string): string => {
  const trimmed = path.replace(/^\/+/, '');
  return trimmed ? `workspace/vibe-coding/${trimmed}` : 'workspace/vibe-coding';
};

const vibeRelativePath = (projectPath: string): string => {
  const normalized = projectPath.replace(/^\/+/, '');
  return normalized
    .replace(/^\$project\/workspace\/vibe-coding\/?/, '')
    .replace(/^workspace\/vibe-coding\/?/, '');
};

const VIBE_ROOT_DESIGN_DOCS = new Set([
  'requirements.md',
  'plan.md',
  'implement.md',
  'implementation.md',
  'brainstorm.md',
  'update.md',
  'issues.md',
  'reviewed.md',
  'tested.md',
  'deployment.md',
  'initialized.md',
  'prompt.md',
]);

const getVibeProjectName = (path: string): string => {
  const segments = path.split('/').filter(Boolean);
  return segments[0] || '';
};

const isVibeDesignDocPath = (path: string, fileName?: string): boolean => {
  const segments = path.split('/').filter(Boolean);
  if (segments.length !== 2) return false;
  if (!VIBE_ROOT_DESIGN_DOCS.has(segments[1])) return false;
  return fileName ? segments[1] === fileName : true;
};

const vibeProjectDesignDocsPath = (project: string): string => (
  project ? `workspace/vibe-coding/${project}` : 'workspace/vibe-coding'
);

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
const CONTEXT_MENU_BUTTON_STYLE: React.CSSProperties = {
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
};
const CONTEXT_MENU_DANGER_BUTTON_STYLE: React.CSSProperties = {
  ...CONTEXT_MENU_BUTTON_STYLE,
  color: '#dc2626',
};

export default function VibeCodingPage() {
  const router = useRouter();
  const { task } = router.query;
  const theme = useMantineTheme();
  const isDevMode = process.env.NODE_ENV === 'development';
  const [opened, setOpened] = useState(false);
  const [treeData, setTreeData] = useState<FileItem[]>([]);
  const [projects, setProjects] = useState<VibeProjectSummary[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(false);
  const [commandStarting, setCommandStarting] = useState<string | null>(null);
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
  const [projectModalOpened, setProjectModalOpened] = useState(false);
  const [requestModalOpened, setRequestModalOpened] = useState(false);
  const [projectNameInput, setProjectNameInput] = useState('');
  const [projectRequirementsInput, setProjectRequirementsInput] = useState('');
  const [requestMode, setRequestMode] = useState<RequestMode>('update');
  const [requestProject, setRequestProject] = useState('');
  const [requestContent, setRequestContent] = useState('');
  const [creatingEntry, setCreatingEntry] = useState(false);
  const [deletingFile, setDeletingFile] = useState(false);
  const [executeOpened, setExecuteOpened] = useState(false);
  const [executeMode, setExecuteMode] = useState<ExecuteMode>('skill');
  const [skillOptions, setSkillOptions] = useState<string[]>([]);
  const [workflowOptions, setWorkflowOptions] = useState<string[]>([]);
  const [selectedSkill, setSelectedSkill] = useState<string | null>(AUTO_EXECUTE_OPTION);
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(AUTO_EXECUTE_OPTION);
  const [pendingAction, setPendingAction] = useState<VibeAction | null>(null);
  const [fileContextMenu, setFileContextMenu] = useState<{ x: number; y: number; item: FileItem } | null>(null);
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
  const rightPaneRef = useRef<HTMLDivElement | null>(null);
  const uploadInputRef = useRef<HTMLInputElement | null>(null);
  const uploadTargetRef = useRef<string>('workspace/vibe-coding');
  const lastLoadedContentRef = useRef<string>('');
  const editorContentRef = useRef<string>('');
  const autoSaveTimerRef = useRef<number | null>(null);
  const pendingSelfSaveRef = useRef<Record<string, string>>({});
  useEffect(() => { editorContentRef.current = editorContent; }, [editorContent]);

  const currentTask = typeof task === 'string' ? task : '';
  const currentView = router.query.view === 'explorer' || typeof task === 'string' ? 'explorer' : 'dashboard';
  const selectedProjectName = typeof router.query.project === 'string' ? router.query.project : '';
  const selectedProject = useMemo(
    () => projects.find((project) => project.name === selectedProjectName) || null,
    [projects, selectedProjectName],
  );
  const currentProject = getVibeProjectName(currentTask);
  const currentFileName = currentTask.split('/').pop() || '';
  const currentDesignDocName = isVibeDesignDocPath(currentTask) ? currentFileName : '';
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
      const res = await axios.get(`${API_BASE_URL}/vibe-coding/tree`);
      setTreeData(res.data.items || []);
    } catch (err) {
      console.error('Failed to fetch vibe coding tree:', err);
    } finally {
      setTreeLoading(false);
    }
  };

  const fetchProjects = async () => {
    setProjectsLoading(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/vibe-coding/projects`);
      setProjects(res.data.items || []);
    } catch (err) {
      console.error('Failed to fetch vibe coding projects:', err);
    } finally {
      setProjectsLoading(false);
    }
  };

  const fetchContent = async (path: string) => {
    const nextKind = detectFileKind(path);
    setLoading(true);
    setEditorError('');
    setNotice('');
    setSelectedKind(nextKind);
    setMarkdownView('editor');

    if (nextKind === 'image' || nextKind === 'audio' || nextKind === 'video') {
      setEditorContent('');
      setLoading(false);
      return;
    }

    try {
      const res = await axios.get(`${API_BASE_URL}/vibe-coding/content`, { params: { path } });
      setSelectedKind((res.data.kind as FileKind) || nextKind);
      const content = String(res.data.content || '');
      setEditorContent(content);
      lastLoadedContentRef.current = content;
    } catch (err: any) {
      console.error('Failed to fetch vibe coding content:', err);
      setEditorError(err?.response?.data?.error || 'Failed to load file content.');
      setEditorContent('');
    } finally {
      setLoading(false);
    }
  };

  const fetchLatest = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/vibe-coding/latest`);
      if (res.data.path) {
        router.push(`/vibe-coding?view=explorer&task=${encodeURIComponent(res.data.path)}`, undefined, { shallow: true });
      } else {
        setEditorContent('');
        setNotice('');
      }
    } catch (err) {
      console.error('Failed to fetch latest vibe coding file:', err);
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
    if (!currentTask || selectedKind === 'image' || selectedKind === 'audio' || selectedKind === 'video') {
      return true;
    }
    const nextContent = editorContentRef.current;
    setEditorSaving(true);
    setEditorError('');
    setNotice('');
    try {
      await axios.post(`${API_BASE_URL}/vibe-coding/save`, {
        path: currentTask,
        content: nextContent,
      });
      lastLoadedContentRef.current = nextContent;
      pendingSelfSaveRef.current[currentTask] = nextContent;
      setNotice('Saved automatically.');
      await fetchTree();
      return true;
    } catch (err: any) {
      console.error('Failed to save vibe coding content:', err);
      setEditorError(err?.response?.data?.error || 'Failed to save content.');
      return false;
    } finally {
      setEditorSaving(false);
    }
  };

  const openProjectModal = () => {
    setProjectNameInput(currentProject || '');
    setProjectRequirementsInput('');
    setProjectModalOpened(true);
    setEditorError('');
    setNotice('');
  };

  const openRequestModal = (project: string) => {
    setRequestMode('update');
    setRequestProject(project);
    setRequestContent('');
    setRequestModalOpened(true);
    setEditorError('');
    setNotice('');
  };

  const createProject = async () => {
    setCreatingEntry(true);
    setEditorError('');
    setNotice('');
    try {
      const res = await axios.post(`${API_BASE_URL}/vibe-coding/create-project`, {
        project_name: projectNameInput,
        requirements: projectRequirementsInput,
      });
      const createdPath = String(res.data.path || '');
      const createdProject = String(res.data.project || '');
      setProjectModalOpened(false);
      await fetchTree();
      await fetchProjects();
      if (createdProject) {
        router.push(`/vibe-coding?project=${encodeURIComponent(createdProject)}`, undefined, { shallow: true });
      } else if (createdPath) {
        router.push(`/vibe-coding?view=explorer&task=${encodeURIComponent(createdPath)}`, undefined, { shallow: true });
      }
    } catch (err: any) {
      console.error('Failed to create vibe coding project:', err);
      setEditorError(err?.response?.data?.error || 'Failed to create project.');
    } finally {
      setCreatingEntry(false);
    }
  };

  const createProjectRequest = async () => {
    setCreatingEntry(true);
    setEditorError('');
    setNotice('');
    try {
      const endpoint = requestMode === 'update'
        ? `${API_BASE_URL}/vibe-coding/create-update-request`
        : `${API_BASE_URL}/vibe-coding/create-issue-report`;
      const res = await axios.post(endpoint, {
        project_name: requestProject,
        content: requestContent,
      });
      const createdPath = String(res.data.path || '');
      setRequestModalOpened(false);
      await fetchTree();
      await fetchProjects();
      if (createdPath) {
        router.push(`/vibe-coding?view=explorer&task=${encodeURIComponent(createdPath)}`, undefined, { shallow: true });
      }
    } catch (err: any) {
      console.error('Failed to create vibe coding request:', err);
      setEditorError(err?.response?.data?.error || 'Failed to create request.');
    } finally {
      setCreatingEntry(false);
    }
  };

  const deleteCurrentFile = async () => {
    if (!currentTask) return;

    let confirmText = '';
    if (currentDesignDocName === 'requirements.md') {
      const typed = window.prompt(`Deleting ${currentTask} will remove the full project folder. Type delete to confirm.`);
      if (typed === null) return;
      confirmText = typed;
    } else if (!window.confirm(`Delete ${currentTask}?`)) {
      return;
    }

    setDeletingFile(true);
    setEditorError('');
    setNotice('');
    try {
      await axios.post(`${API_BASE_URL}/vibe-coding/delete`, {
        path: currentTask,
        confirm_text: confirmText,
      });
      await fetchTree();
      await fetchProjects();
      router.push('/vibe-coding', undefined, { shallow: true });
    } catch (err: any) {
      console.error('Failed to delete vibe coding file:', err);
      setEditorError(err?.response?.data?.error || 'Failed to delete file.');
    } finally {
      setDeletingFile(false);
    }
  };

  const deleteVibeFile = async (item: FileItem) => {
    let confirmText = '';
    if (isVibeDesignDocPath(item.path, 'requirements.md')) {
      const typed = window.prompt(`Deleting ${item.path} will remove the full project folder. Type delete to confirm.`);
      if (typed === null) return;
      confirmText = typed;
    } else if (!window.confirm(`Delete ${item.path}?`)) {
      return;
    }

    setDeletingFile(true);
    setEditorError('');
    setNotice('');
    try {
      await axios.post(`${API_BASE_URL}/vibe-coding/delete`, {
        path: item.path,
        confirm_text: confirmText,
      });
      setFileContextMenu(null);
      await fetchTree();
      await fetchProjects();
      if (currentTask === item.path) {
        router.push('/vibe-coding', undefined, { shallow: true });
      }
    } catch (err: any) {
      console.error('Failed to delete vibe coding file:', err);
      setEditorError(err?.response?.data?.error || 'Failed to delete file.');
    } finally {
      setDeletingFile(false);
    }
  };

  const createFileInVibeFolder = async (folderPath: string) => {
    setFileContextMenu(null);
    const name = window.prompt('File name');
    if (!name) return;
    const parentPath = vibeProjectPath(folderPath);
    const projectPath = `${parentPath}/${name}`.replace(/\/+/g, '/');
    setEditorError('');
    setNotice('');
    try {
      await axios.post(apiUrl('/api/files/write'), {
        path: projectPath,
        content: '',
      });
      const nextPath = vibeRelativePath(projectPath);
      setExpandedFolders((prev) => Array.from(new Set([...prev, folderPath])));
      await fetchTree();
      await fetchProjects();
      router.push(`/vibe-coding?view=explorer&task=${encodeURIComponent(nextPath)}`, undefined, { shallow: true });
    } catch (err: any) {
      console.error('Failed to create vibe coding file:', err);
      setEditorError(err?.response?.data?.error || 'Failed to create file.');
    }
  };

  const createFolderInVibeFolder = async (folderPath: string) => {
    setFileContextMenu(null);
    const name = window.prompt('Folder name');
    if (!name) return;
    setEditorError('');
    setNotice('');
    try {
      await axios.post(apiUrl('/api/files/mkdir'), {
        parent: vibeProjectPath(folderPath),
        name,
      });
      setExpandedFolders((prev) => Array.from(new Set([...prev, folderPath])));
      await fetchTree();
      await fetchProjects();
    } catch (err: any) {
      console.error('Failed to create vibe coding folder:', err);
      setEditorError(err?.response?.data?.error || 'Failed to create folder.');
    }
  };

  const openUploadForVibeFolder = (folderPath: string) => {
    setFileContextMenu(null);
    uploadTargetRef.current = vibeProjectPath(folderPath);
    uploadInputRef.current?.click();
  };

  const uploadFilesToVibeFolder = async (files: FileList | null) => {
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
      const folderPath = vibeRelativePath(uploadTargetRef.current);
      if (folderPath) {
        setExpandedFolders((prev) => Array.from(new Set([...prev, folderPath])));
      }
      await fetchTree();
      await fetchProjects();
    } catch (err: any) {
      console.error('Failed to upload vibe coding file:', err);
      setEditorError(err?.response?.data?.error || 'Failed to upload file.');
    }
  };

  const renameVibePath = async (item: FileItem) => {
    const nextName = window.prompt('Rename', item.name);
    if (!nextName || nextName === item.name) return;
    setEditorError('');
    setNotice('');
    try {
      const res = await axios.post(apiUrl('/api/files/rename'), {
        id: vibeProjectPath(item.path),
        name: nextName,
      });
      const nextPath = vibeRelativePath(String(res.data?.newId || ''));
      setFileContextMenu(null);
      await fetchTree();
      await fetchProjects();
      if (currentTask === item.path && nextPath) {
        router.push(`/vibe-coding?view=explorer&task=${encodeURIComponent(nextPath)}`, undefined, { shallow: true });
      } else if (currentTask.startsWith(`${item.path}/`) && nextPath) {
        const suffix = currentTask.slice(item.path.length);
        router.push(`/vibe-coding?view=explorer&task=${encodeURIComponent(`${nextPath}${suffix}`)}`, undefined, { shallow: true });
      }
    } catch (err: any) {
      console.error('Failed to rename vibe coding path:', err);
      setEditorError(err?.response?.data?.error || 'Failed to rename path.');
    }
  };

  const deleteVibeFolder = async (item: FileItem) => {
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
        ids: [vibeProjectPath(item.path)],
      });
      setFileContextMenu(null);
      setExpandedFolders((prev) => prev.filter((path) => path !== item.path && !path.startsWith(`${item.path}/`)));
      await fetchTree();
      await fetchProjects();
      if (currentTask === item.path || currentTask.startsWith(`${item.path}/`)) {
        router.push('/vibe-coding', undefined, { shallow: true });
      }
    } catch (err: any) {
      console.error('Failed to delete vibe coding folder:', err);
      setEditorError(err?.response?.data?.error || 'Failed to delete folder.');
    } finally {
      setDeletingFile(false);
    }
  };

  const copyVibePath = async (item: FileItem) => {
    setFileContextMenu(null);
    try {
      await navigator.clipboard.writeText(vibeProjectPath(item.path));
      setNotice('Path copied.');
      setEditorError('');
    } catch (err) {
      console.error('Failed to copy vibe coding path:', err);
      setEditorError('Failed to copy path.');
    }
  };

  const openPromptRunSession = async () => {
    if (!currentTask || currentFileName !== 'prompt.md') return;
    const saved = await saveCurrentContent();
    if (!saved) return;
    setSessionPromptText(editorContentRef.current);
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

  const openExecuteModal = (action: VibeAction) => {
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

    const projectLabel = currentProject ? `\nVibe coding project name: ${currentProject}` : '';
    const designDocsLabel = currentProject ? `\nDesign docs path: ${vibeProjectDesignDocsPath(currentProject)}` : '';
    const prompt = executeMode === 'skill'
      ? (isAutoExecuteTarget(target)
          ? `Find and use the correct agent skill ${pendingAction.skillPromptSuffix}${projectLabel}${designDocsLabel}`
          : `Use agent skill ${target} ${pendingAction.skillPromptSuffix}${projectLabel}${designDocsLabel}`)
      : (shouldRunWorkflow
          ? `Execute workflow ${workflowProjectPath(target)}. ${pendingAction.skillPromptSuffix.charAt(0).toUpperCase()}${pendingAction.skillPromptSuffix.slice(1)}\n\nYour Workspace path: ${currentProject ? vibeProjectPath(currentProject) : 'workspace/vibe-coding'}${projectLabel}${designDocsLabel}\n\nIf you create or update design docs or intermediate files, save them inside the design docs path above.`
          : `Find and use the correct workflow ${pendingAction.skillPromptSuffix}${projectLabel}${designDocsLabel}`);

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

  const openNewProjectWorkflowPanel = () => {
    setSessionPromptText('Complete the vibe coding project using the `vibe-coding-dev` workflow as the user requirements below. Ask the user clarifying questions before implementation if any requirement is unclear.\n\nRequirements:\n');
    setNewSessionWorkflow('vibe-coding-dev.json');
    setNewSessionNextNodeTrigger('auto_continue');
    setNewSessionWorkflowResumeAvailable(false);
    setNewSessionWorkflowResume(false);
    setLiveSessionName(null);
    setWorkflowSessionActive(false);
    setWorkflowExecuteStatus(null);
    setSessionPanelHeight(50);
    setSessionPanelOpen(true);
  };

  const openProjectPromptPanel = (project: VibeProjectSummary, label: string, prompt: string) => {
    setSessionPromptText(prompt);
    setNewSessionWorkflow(null);
    setNewSessionNextNodeTrigger('auto_continue');
    setNewSessionWorkflowResumeAvailable(false);
    setNewSessionWorkflowResume(false);
    setLiveSessionName(null);
    setWorkflowSessionActive(false);
    setWorkflowExecuteStatus(null);
    setSessionPanelHeight(50);
    setSessionPanelOpen(true);
    setNotice(`${label} prompt is ready for ${project.display_name}.`);
    setEditorError('');
  };

  const openProjectActionPrompt = (project: VibeProjectSummary, action: 'push' | 'update' | 'issue' | 'deploy') => {
    const projectPath = vibeProjectPath(project.name);
    const designDocsPath = vibeProjectDesignDocsPath(project.name);
    const prompts: Record<'push' | 'update' | 'issue' | 'deploy', { label: string; text: string }> = {
      push: {
        label: 'Push',
        text: `Commit and push the code for vibe coding project ${project.display_name} to its GitHub repository.\n\nProject path: ${projectPath}\nDesign docs path: ${designDocsPath}\n\nReview the working tree first, summarize the changes, ask for any missing commit or remote details, then commit and push when ready.`,
      },
      update: {
        label: 'Update',
        text: `Ask the user what feature or change they want to add to vibe coding project ${project.display_name}, then use the vibe-coding skill to complete the update request.\n\nProject path: ${projectPath}\nDesign docs path: ${designDocsPath}\n\nAfter the user provides the request, create or update the required design docs, implement the change, test it, and report the result.`,
      },
      issue: {
        label: 'Issue',
        text: `Ask the user what bug or issue they want fixed in vibe coding project ${project.display_name}, then use the vibe-coding skill to diagnose and fix it.\n\nProject path: ${projectPath}\nDesign docs path: ${designDocsPath}\n\nAfter the user provides the issue, record it in the project design docs, implement the fix, test it, and report the result.`,
      },
      deploy: {
        label: 'Deploy',
        text: `Ask the user to confirm the production deployment target for vibe coding project ${project.display_name}, then use the vibe-coding skill to redeploy it if production deployment is configured.\n\nProject path: ${projectPath}\nDesign docs path: ${designDocsPath}\n\nCheck the deployment notes first, confirm any missing environment details, run the deployment, and report the deployed target.`,
      },
    };
    openProjectPromptPanel(project, prompts[action].label, prompts[action].text);
  };

  const startProjectCommand = async (project: VibeProjectSummary, commandKey: 'start' | 'dev' | 'build' | 'stop') => {
    const command = String(project.commands?.[commandKey] || '').trim();
    if (!command) {
      setEditorError(`No ${commandKey} command is configured in ${project.name}/assets/info.yaml.`);
      setNotice('');
      return;
    }
    const commandId = `${project.name}:${commandKey}`;
    setCommandStarting(commandId);
    setEditorError('');
    setNotice('');
    try {
      const res = await axios.post(`${API_BASE_URL}/terminal/tmux/create`, {
        command,
        path: vibeProjectPath(project.name),
      });
      const sessionName: string | undefined = res.data?.session?.name;
      if (sessionName) {
        setLiveSessionName(sessionName);
        setSessionPromptText('');
        setNewSessionWorkflow(null);
        setWorkflowSessionActive(false);
        setWorkflowExecuteStatus(null);
        setSessionPanelHeight(50);
        setSessionPanelOpen(true);
        setNotice(`${commandKey.charAt(0).toUpperCase()}${commandKey.slice(1)} command started for ${project.display_name}.`);
      }
    } catch (err: any) {
      console.error(`Failed to start ${commandKey} command:`, err);
      setEditorError(err?.response?.data?.error || `Failed to start ${commandKey} command.`);
    } finally {
      setCommandStarting(null);
    }
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
      console.error('Failed to start vibe coding session:', err);
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
    prefix: '/workspace/vibe-coding',
    onTreeChange: () => {
      void fetchTree();
      void fetchProjects();
    },
    currentFilePath: currentTask ? `/workspace/vibe-coding/${currentTask}` : null,
    onCurrentFileChange: () => {
      if (!currentTask) return;
      if (pendingSelfSaveRef.current[currentTask] === editorContentRef.current) {
        delete pendingSelfSaveRef.current[currentTask];
        return;
      }
      if (editorContentRef.current === lastLoadedContentRef.current) {
        setNotice('File updated on disk.');
        void fetchContent(currentTask);
      } else {
        setEditorError('File changed on disk. Reload after saving or discard your edits.');
      }
    },
  });

  useEffect(() => {
    if (autoSaveTimerRef.current) {
      window.clearTimeout(autoSaveTimerRef.current);
      autoSaveTimerRef.current = null;
    }
    if (
      !currentTask
      || loading
      || (selectedKind !== 'markdown' && selectedKind !== 'text')
      || editorContent === lastLoadedContentRef.current
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
    const closeFileContextMenu = () => setFileContextMenu(null);
    window.addEventListener('pointerdown', closeFileContextMenu);
    return () => window.removeEventListener('pointerdown', closeFileContextMenu);
  }, []);

  useEffect(() => {
    fetchTree();
    fetchProjects();
    fetchLlmProviders();
    fetchExecuteOptions();
    void axios.get(`${API_BASE_URL}/config/settings`).then((res) => {
      const security = res.data?.security?.newSession;
      if (!security) return;
      setNewSessionSandbox(Boolean(security.sandbox));
      setNewSessionAuto(Boolean(security.auto));
      setNewSessionNetwork(security.network !== false);
    }).catch((err) => {
      console.error('Failed to fetch vibe coding session settings:', err);
    });
  }, []);

  useEffect(() => {
    if (currentTask) {
      fetchContent(currentTask);
    } else if (router.isReady && currentView === 'explorer') {
      fetchLatest();
    }
  }, [currentTask, router.isReady, currentView]);

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

  const renderTree = (items: FileItem[]) => items.map((item) => {
    const isSelected = currentTask === item.path;
    if (item.type === 'dir') {
      const isProjectDir = !item.path.includes('/');
      return (
        <NavLink
          key={item.path}
          label={(
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
              <span>{item.name}</span>
              {isProjectDir && (
                <ActionIcon
                  size="sm"
                  variant="subtle"
                  onClick={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    openRequestModal(item.name);
                  }}
                  title={`New update or bug request for ${item.name}`}
                >
                  <IconMessageCirclePlus size="0.95rem" />
                </ActionIcon>
              )}
            </div>
          )}
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
          router.push(`/vibe-coding?view=explorer&task=${encodeURIComponent(item.path)}`, undefined, { shallow: true });
          setOpened(false);
        }}
      />
    );
  });

  const currentInstructionPath = currentTask ? vibeProjectPath(currentTask) : '';
  const fileActions = useMemo<VibeAction[]>(() => {
    if (!currentInstructionPath) return [];
    if (currentDesignDocName === 'requirements.md') {
      return [
        {
          label: 'Refine',
          defaultSkill: 'vibe-coding',
          skillPromptSuffix: `to refine the ${currentInstructionPath}`,
        },
        {
          label: 'Brainstorm',
          defaultSkill: 'vibe-coding',
          skillPromptSuffix: `to brainstorm ideas and alternatives for the ${currentInstructionPath}`,
        },
        {
          label: 'Initial',
          defaultSkill: 'vibe-coding',
          skillPromptSuffix: `to init the project defined at ${currentInstructionPath}`,
        },
        {
          label: 'Plan',
          defaultSkill: 'vibe-coding',
          skillPromptSuffix: `to make a development plan for requirement ${currentInstructionPath}`,
        },
      ];
    }
    if (currentDesignDocName === 'plan.md') {
      return [
        {
          label: 'Implement',
          defaultSkill: 'vibe-coding',
          skillPromptSuffix: `to implement the code as the ${currentInstructionPath}`,
        },
      ];
    }
    if (currentDesignDocName === 'implement.md' || currentDesignDocName === 'implementation.md') {
      return [
        {
          label: 'Review',
          defaultSkill: 'vibe-coding',
          skillPromptSuffix: `to review the code of the implementation of the ${currentInstructionPath}`,
        },
        {
          label: 'Test',
          defaultSkill: 'vibe-coding',
          skillPromptSuffix: `to test the code of the implementation of the ${currentInstructionPath}`,
        },
        {
          label: 'Deploy',
          defaultSkill: 'vibe-coding',
          skillPromptSuffix: `to deploy the code of the implementation of the ${currentInstructionPath}`,
        },
      ];
    }
    if (currentDesignDocName === 'update.md') {
      return [
        {
          label: 'Update Code',
          defaultSkill: 'vibe-coding',
          skillPromptSuffix: `to update the code based on the update request defined in ${currentInstructionPath}`,
        },
      ];
    }
    if (currentDesignDocName === 'brainstorm.md') {
      return [
        {
          label: 'Apply to Requirements',
          defaultSkill: 'vibe-coding',
          skillPromptSuffix: `to merge brainstorm ideas from ${currentInstructionPath} into the project requirements`,
        },
      ];
    }
    if (currentDesignDocName === 'issues.md') {
      return [
        {
          label: 'Fix Issues',
          defaultSkill: 'vibe-coding',
          skillPromptSuffix: `to fix the issues defined in ${currentInstructionPath}`,
        },
      ];
    }
    return [];
  }, [currentDesignDocName, currentInstructionPath]);

  const mediaUrl = currentTask ? `${API_BASE_URL}/vibe-coding/file?path=${encodeURIComponent(currentTask)}` : '';
  const isMarkdownEditor = selectedKind === 'markdown';
  const isTextEditor = selectedKind === 'text';
  const headerStatus = editorSaving ? 'Saving...' : notice;
  const renderHeaderActions = () => {
    if (!currentTask) return null;
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 8, flex: '0 0 auto', flexWrap: 'wrap' }}>
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
        {currentFileName === 'prompt.md' && (isMarkdownEditor || isTextEditor) && (
          <Button size="xs" variant="default" onClick={() => void openPromptRunSession()}>
            Run
          </Button>
        )}
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
                Vibe Coding Workspace
              </Text>
              <Text size={28} weight={800} mt={10}>
                Start your first project
              </Text>
              <Text size="sm" color="dimmed" mt={12} style={{ maxWidth: 420, margin: '12px auto 0 auto', lineHeight: 1.6 }}>
                Create a project requirement, then refine, plan, implement, review, test, and deploy from the same workspace.
              </Text>
              <Group position="center" mt="xl">
                <Button onClick={openProjectModal}>New Project</Button>
              </Group>
            </div>
          </div>
        );
      }
      return <Text align="center" py="xl" color="dimmed">Select a project file from the sidebar to begin.</Text>;
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

    return !loading ? <Text align="center" py="xl" color="dimmed">Select a project file from the sidebar to begin.</Text> : null;
  };

  const renderProjectAvatar = (project: VibeProjectSummary, size = 76) => {
    if (project.icon_path) {
      return (
        <div style={{ width: size, height: size, borderRadius: 8, overflow: 'hidden', background: '#eef2f7', flexShrink: 0 }}>
          <img
            src={`${API_BASE_URL}/vibe-coding/file?path=${encodeURIComponent(project.icon_path)}`}
            alt={project.display_name}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
        </div>
      );
    }
    return (
      <div
        style={{
          width: size,
          height: size,
          borderRadius: 8,
          background: '#1f2937',
          color: '#ffffff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: Math.max(20, Math.round(size * 0.32)),
          fontWeight: 800,
          letterSpacing: 0,
          flexShrink: 0,
        }}
      >
        {project.initials}
      </div>
    );
  };

  const dashboardShell = (content: React.ReactNode) => (
    <MainLayout title="Vibe Coding">
      <div
        ref={rightPaneRef}
        style={{
          height: '100%',
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
          {content}
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
                currentLabel={selectedProject?.display_name || 'Vibe coding session'}
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
                hideSessionRootSelect
              />
            </div>
          </>
        )}
      </div>
    </MainLayout>
  );

  const renderDashboard = () => dashboardShell(
    <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
      <div style={{ padding: '20px 24px', borderBottom: '1px solid #e5e7eb', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
        <div>
          <Text size={20} weight={800}>Vibe Coding</Text>
          <Text size="sm" color="dimmed">Projects</Text>
        </div>
        <Tooltip label="Explorer">
          <ActionIcon
            variant="light"
            size="lg"
            onClick={() => { void router.push('/vibe-coding?view=explorer', undefined, { shallow: true }); }}
            aria-label="Open Explorer view"
          >
            <IconHierarchy size="1.25rem" />
          </ActionIcon>
        </Tooltip>
      </div>
      <div style={{ padding: '28px 32px' }}>
        {projectsLoading && projects.length === 0 ? (
          <Text color="dimmed">Loading projects...</Text>
        ) : (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(132px, 1fr))',
              gap: 22,
              alignItems: 'start',
            }}
          >
            {projects.map((project) => (
              <button
                key={project.name}
                type="button"
                onClick={() => { void router.push(`/vibe-coding?project=${encodeURIComponent(project.name)}`, undefined, { shallow: true }); }}
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
                {renderProjectAvatar(project)}
                <Text size="sm" weight={700} align="center" style={{ lineHeight: 1.25, wordBreak: 'break-word' }}>
                  {project.display_name}
                </Text>
              </button>
            ))}
            <button
              type="button"
              onClick={openNewProjectWorkflowPanel}
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
              <Text size="sm" weight={700}>New Project</Text>
            </button>
          </div>
        )}
      </div>
    </div>,
  );

  const renderProjectDetail = (project: VibeProjectSummary | null) => dashboardShell(
    <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
      <div style={{ padding: '20px 24px', borderBottom: '1px solid #e5e7eb', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
        <Group spacing="md" align="center">
          <ActionIcon variant="subtle" onClick={() => { void router.push('/vibe-coding', undefined, { shallow: true }); }} aria-label="Back to dashboard">
            <IconArrowLeft size="1.1rem" />
          </ActionIcon>
          {project && renderProjectAvatar(project, 48)}
          <div>
            <Text size={20} weight={800}>{project?.display_name || selectedProjectName || 'Project'}</Text>
            <Text size="sm" color="dimmed">{project ? vibeProjectPath(project.name) : 'Project metadata not found'}</Text>
          </div>
        </Group>
        <Tooltip label="Explorer">
          <ActionIcon
            variant="light"
            size="lg"
            onClick={() => { void router.push('/vibe-coding?view=explorer', undefined, { shallow: true }); }}
            aria-label="Open Explorer view"
          >
            <IconHierarchy size="1.25rem" />
          </ActionIcon>
        </Tooltip>
      </div>
      {!project ? (
        <Box p="xl">
          <Text color="dimmed">This project is not available. Return to the dashboard and refresh the project list.</Text>
        </Box>
      ) : (
        <Stack spacing="lg" p="xl" style={{ maxWidth: 980 }}>
          <Group spacing="sm">
            {[
              { key: 'start' as const, label: 'Start', icon: <IconPlayerPlay size="1rem" /> },
              { key: 'dev' as const, label: 'Dev', icon: <IconCode size="1rem" /> },
              { key: 'build' as const, label: 'Build', icon: <IconPackage size="1rem" /> },
              { key: 'stop' as const, label: 'Stop', icon: <IconPlayerStop size="1rem" /> },
            ].map((action) => (
              <Button
                key={action.key}
                leftIcon={action.icon}
                variant={action.key === 'stop' ? 'light' : 'filled'}
                color={action.key === 'stop' ? 'red' : 'blue'}
                onClick={() => void startProjectCommand(project, action.key)}
                loading={commandStarting === `${project.name}:${action.key}`}
                disabled={!project.commands?.[action.key]}
              >
                {action.label}
              </Button>
            ))}
          </Group>
          <Group spacing="sm">
            {[
              { key: 'push' as const, label: 'Push', icon: <IconUpload size="1rem" /> },
              { key: 'update' as const, label: 'Update', icon: <IconPlus size="1rem" /> },
              { key: 'issue' as const, label: 'Issue', icon: <IconBug size="1rem" /> },
              { key: 'deploy' as const, label: 'Deploy', icon: <IconRocket size="1rem" /> },
            ].map((action) => (
              <Button
                key={action.key}
                leftIcon={action.icon}
                variant="default"
                onClick={() => openProjectActionPrompt(project, action.key)}
              >
                {action.label}
              </Button>
            ))}
          </Group>
          <Box style={{ border: '1px solid #e2e8f0', borderRadius: 8, padding: 16, background: '#f8fafc' }}>
            <Text size="sm" weight={700} mb={8}>Configured Commands</Text>
            <Stack spacing={4}>
              {(['start', 'dev', 'build', 'stop'] as const).map((key) => (
                <Text key={key} size="sm" color={project.commands?.[key] ? undefined : 'dimmed'} style={{ fontFamily: PAGE_EDITOR_FONT, wordBreak: 'break-word' }}>
                  {key}: {project.commands?.[key] || '(not configured)'}
                </Text>
              ))}
            </Stack>
          </Box>
        </Stack>
      )}
    </div>,
  );

  if (currentView === 'dashboard') {
    if (selectedProjectName) return renderProjectDetail(selectedProject);
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
        <title>Skill Pilot - Vibe Coding</title>
      </Head>

      <input
        ref={uploadInputRef}
        type="file"
        multiple
        style={{ display: 'none' }}
        onChange={(event) => {
          void uploadFilesToVibeFolder(event.currentTarget.files);
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
                onClick={() => { void createFileInVibeFolder(fileContextMenu.item.path); }}
                style={CONTEXT_MENU_BUTTON_STYLE}
              >
                <IconFilePlus size="0.95rem" />
                Add File
              </button>
              <button
                type="button"
                onClick={() => { void createFolderInVibeFolder(fileContextMenu.item.path); }}
                style={CONTEXT_MENU_BUTTON_STYLE}
              >
                <IconFolderPlus size="0.95rem" />
                Add Folder
              </button>
              <button
                type="button"
                onClick={() => openUploadForVibeFolder(fileContextMenu.item.path)}
                style={CONTEXT_MENU_BUTTON_STYLE}
              >
                <IconFileUpload size="0.95rem" />
                Upload File
              </button>
              <div style={{ height: 1, margin: '6px 4px', background: '#e5e7eb' }} />
            </>
          )}
          <button
            type="button"
            onClick={() => { void renameVibePath(fileContextMenu.item); }}
            style={CONTEXT_MENU_BUTTON_STYLE}
          >
            Rename
          </button>
          {fileContextMenu.item.type === 'file' && (
            <button
              type="button"
              onClick={() => { void copyVibePath(fileContextMenu.item); }}
              style={CONTEXT_MENU_BUTTON_STYLE}
            >
              Copy Path
            </button>
          )}
          <button
            type="button"
            onClick={() => {
              if (fileContextMenu.item.type === 'dir') {
                void deleteVibeFolder(fileContextMenu.item);
              } else {
                void deleteVibeFile(fileContextMenu.item);
              }
            }}
            style={CONTEXT_MENU_DANGER_BUTTON_STYLE}
          >
            Delete
          </button>
        </div>
      )}

      <Modal opened={projectModalOpened} onClose={() => setProjectModalOpened(false)} title="New Project" centered>
        <Stack spacing="md">
          <div>
            <Text size="sm" weight={700} mb={4}>Project Name</Text>
            <TextInput
              placeholder="project-name"
              value={projectNameInput}
              onChange={(e) => setProjectNameInput(e.currentTarget.value)}
              description="Creates workspace/vibe-coding/{project-name}/requirements.md. Duplicates get _1, _2, and so on."
            />
          </div>
          <div>
            <Text size="sm" weight={700} mb={4}>Requirements</Text>
            <Textarea
              value={projectRequirementsInput}
              onChange={(e) => setProjectRequirementsInput(e.currentTarget.value)}
              minRows={10}
              autosize
            />
          </div>
        </Stack>
        <Group position="right" mt="md">
          <Button variant="default" onClick={() => setProjectModalOpened(false)}>Cancel</Button>
          <Button
            onClick={() => void createProject()}
            loading={creatingEntry}
            disabled={!projectNameInput.trim()}
          >
            Create
          </Button>
        </Group>
      </Modal>

      <Modal opened={requestModalOpened} onClose={() => setRequestModalOpened(false)} title="New Request" centered size="lg">
        <Stack spacing="md">
          <Radio.Group
            value={requestMode}
            onChange={(value) => setRequestMode(value as RequestMode)}
          >
            <Text size="sm" weight={700} mb={4}>Type</Text>
            <Group mt="xs">
              <Radio value="update" label="Update" />
              <Radio value="issue" label="Bugs" />
            </Group>
          </Radio.Group>
          <div>
            <Text size="sm" weight={700} mb={4}>Project</Text>
            <Text size="sm">{requestProject}</Text>
            <Text size="xs" color="dimmed">{requestProject ? `${vibeProjectDesignDocsPath(requestProject)}/${requestMode === 'update' ? 'update.md' : 'issues.md'}` : ''}</Text>
          </div>
          <div>
            <Text size="sm" weight={700} mb={4}>{requestMode === 'update' ? 'Update Request' : 'Bug/Issue Report'}</Text>
            <Textarea
              value={requestContent}
              onChange={(e) => setRequestContent(e.currentTarget.value)}
              minRows={10}
              autosize
            />
          </div>
        </Stack>
        <Group position="right" mt="md">
          <Button variant="default" onClick={() => setRequestModalOpened(false)}>Cancel</Button>
          <Button
            onClick={() => void createProjectRequest()}
            loading={creatingEntry}
            disabled={!requestProject.trim()}
          >
            Create
          </Button>
        </Group>
      </Modal>

      <Modal
        opened={executeOpened}
        onClose={() => setExecuteOpened(false)}
        title={pendingAction ? pendingAction.label : 'Run Action'}
        centered
        size="lg"
      >
        <Stack spacing="md">
          <div>
            <Text size="sm" weight={700} mb={4}>Run By</Text>
            <Group mt="xs">
              <Radio
                value="skill"
                checked={executeMode === 'skill'}
                onChange={() => setExecuteMode('skill')}
                label="Skill"
              />
              <Radio
                value="workflow"
                checked={executeMode === 'workflow'}
                onChange={() => setExecuteMode('workflow')}
                label="Workflow"
              />
            </Group>
          </div>

          {executeMode === 'skill' ? (
            <Select
              label="Skill"
              placeholder="Select a skill"
              value={selectedSkill}
              onChange={setSelectedSkill}
              data={skillSelectOptions}
              searchable
              clearable={false}
              withinPortal
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
              withinPortal
            />
          )}

          <div>
            <Text size="sm" weight={700} mb={4}>Instruction File</Text>
            <Text size="sm">{currentInstructionPath || '(no file selected)'}</Text>
          </div>
        </Stack>
        <Group position="right" mt="md">
          <Button variant="default" onClick={() => setExecuteOpened(false)}>Cancel</Button>
          <Button
            onClick={() => void runAction()}
            disabled={!currentTask || (executeMode === 'skill' ? !selectedSkill : !selectedWorkflow)}
          >
            Run
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
                  <Text weight={700} size="lg">Projects</Text>
                </Group>
                <Group spacing={4}>
                  <Tooltip label="New">
                    <ActionIcon variant="subtle" onClick={openProjectModal}>
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
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0, flex: '1 1 240px' }}>
                  <span style={{ fontSize: 12, color: '#64748b', minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {currentTask || 'Select a project file from the sidebar'}
                  </span>
                  {headerStatus && (
                    <span style={{ fontSize: 12, color: editorSaving ? '#64748b' : '#16a34a', flex: '0 0 auto', whiteSpace: 'nowrap' }}>
                      {headerStatus}
                    </span>
                  )}
                </div>
                {renderHeaderActions()}
              </div>
              {editorError && (
                <div style={{ flexShrink: 0 }}>
                  {editorError && <Text color="red" size="sm" px={18} py={10}>{editorError}</Text>}
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
                  currentLabel={currentTask || 'Vibe coding session'}
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
                  hideSessionRootSelect
                />
              </div>
            </>
          )}
        </main>
      </div>
    </AppShell>
  );
}

export async function getStaticProps({ locale }: GetStaticPropsContext) {
  return {
    props: {
      ...(await serverSideTranslations(locale ?? 'en', ['common'])),
    },
  };
}
