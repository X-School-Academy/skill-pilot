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
  IconClock,
  IconFileText,
  IconFolder,
  IconMessageCirclePlus,
  IconPlus,
  IconRefresh,
  IconSortAscending,
} from '@tabler/icons-react';
import EmbeddedSessionPanel, { WorkflowExecuteStatus } from '../../components/EmbeddedSessionPanel';
import { apiUrl } from '../../libs/api-base';
import { AUTO_EXECUTE_OPTION, buildExecuteSelectOptions, isAutoExecuteTarget } from '../../libs/execute-targets';
import { resolveSelectedProvider, setSelectedProvider } from '../../libs/llm';

const API_BASE_URL = apiUrl('/api');
axios.defaults.withCredentials = true;

type FileKind = 'markdown' | 'text' | 'image' | 'audio' | 'video';
type FeatureRequestMode = 'update' | 'issue';
type ExecuteMode = 'skill' | 'workflow';

interface FileItem {
  name: string;
  path: string;
  type: 'dir' | 'file';
  mtime: number;
  children?: FileItem[];
}

interface FeatureOption {
  name: string;
  path: string;
}

interface LlmProvider {
  id: string;
  name: string;
}

interface FeatureAction {
  label: string;
  defaultSkill: string;
  skillPromptSuffix: string;
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

const developmentProjectPath = (path: string): string => {
  const trimmed = path.replace(/^\/+/, '');
  return trimmed ? `core/development/${trimmed}` : 'core/development';
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

export default function SkillPilotDevelopmentPage() {
  const router = useRouter();
  const { task } = router.query;
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
  const [featureModalOpened, setFeatureModalOpened] = useState(false);
  const [requestModalOpened, setRequestModalOpened] = useState(false);
  const [featureNameInput, setFeatureNameInput] = useState('');
  const [featureRequestMode, setFeatureRequestMode] = useState<FeatureRequestMode>('update');
  const [featureContentInput, setFeatureContentInput] = useState('');
  const [requestFeature, setRequestFeature] = useState('');
  const [requestMode, setRequestMode] = useState<FeatureRequestMode>('update');
  const [requestContent, setRequestContent] = useState('');
  const [featureOptions, setFeatureOptions] = useState<FeatureOption[]>([]);
  const [relatedFeatureInput, setRelatedFeatureInput] = useState<string | null>(null);
  const [requestRelatedFeatureInput, setRequestRelatedFeatureInput] = useState<string | null>(null);
  const [selectedRelatedFeatures, setSelectedRelatedFeatures] = useState<string[]>([]);
  const [requestRelatedFeatures, setRequestRelatedFeatures] = useState<string[]>([]);
  const [creatingEntry, setCreatingEntry] = useState(false);
  const [deletingFile, setDeletingFile] = useState(false);
  const [executeOpened, setExecuteOpened] = useState(false);
  const [executeMode, setExecuteMode] = useState<ExecuteMode>('skill');
  const [skillOptions, setSkillOptions] = useState<string[]>([]);
  const [workflowOptions, setWorkflowOptions] = useState<string[]>([]);
  const [selectedSkill, setSelectedSkill] = useState<string | null>(AUTO_EXECUTE_OPTION);
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(AUTO_EXECUTE_OPTION);
  const [pendingAction, setPendingAction] = useState<FeatureAction | null>(null);
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

  const currentTask = typeof task === 'string' ? task : '';
  const currentFeature = currentTask.includes('/') ? currentTask.split('/')[0] : '';
  const currentFileName = currentTask.split('/').pop() || '';
  const skillSelectOptions = useMemo(() => buildExecuteSelectOptions(skillOptions), [skillOptions]);
  const workflowSelectOptions = useMemo(() => buildExecuteSelectOptions(workflowOptions), [workflowOptions]);

  const selectedExistingFeature = useMemo(
    () => featureOptions.find((item) => item.name === featureNameInput.trim()) || null,
    [featureOptions, featureNameInput],
  );

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
      const res = await axios.get(`${API_BASE_URL}/skill-pilot-development/tree`);
      setTreeData(res.data.items || []);
    } catch (err) {
      console.error('Failed to fetch development tree:', err);
    } finally {
      setTreeLoading(false);
    }
  };

  const fetchFeatureOptions = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/skill-pilot-development/features`);
      setFeatureOptions((res.data.items || []).sort((a: FeatureOption, b: FeatureOption) => a.name.localeCompare(b.name)));
    } catch (err) {
      console.error('Failed to fetch feature options:', err);
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
      const res = await axios.get(`${API_BASE_URL}/skill-pilot-development/content`, { params: { path } });
      setSelectedKind((res.data.kind as FileKind) || nextKind);
      setEditorContent(String(res.data.content || ''));
    } catch (err: any) {
      console.error('Failed to fetch development content:', err);
      setEditorError(err?.response?.data?.error || 'Failed to load file content.');
      setEditorContent('');
    } finally {
      setLoading(false);
    }
  };

  const fetchLatest = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/skill-pilot-development/latest`);
      if (res.data.path) {
        router.push(`/skill-pilot-development?task=${encodeURIComponent(res.data.path)}`, undefined, { shallow: true });
      } else {
        setEditorContent('');
        setNotice('');
      }
    } catch (err) {
      console.error('Failed to fetch latest development file:', err);
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
        axios.get(`${API_BASE_URL}/config/skills`),
        axios.get(`${API_BASE_URL}/workflows/tree`),
      ]);

      const nextSkills: string[] = [];
      for (const category of skillsRes.data.categories || []) {
        for (const skill of category.skills || []) {
          if (skill?.name) nextSkills.push(String(skill.name));
        }
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
    if (!currentTask || selectedKind === 'image' || selectedKind === 'audio' || selectedKind === 'video') return true;
    setEditorSaving(true);
    setEditorError('');
    setNotice('');
    try {
      await axios.post(`${API_BASE_URL}/skill-pilot-development/save`, {
        path: currentTask,
        content: editorContent,
      });
      setNotice('Saved.');
      await fetchTree();
      await fetchContent(currentTask);
      return true;
    } catch (err: any) {
      console.error('Failed to save development content:', err);
      setEditorError(err?.response?.data?.error || 'Failed to save content.');
      return false;
    } finally {
      setEditorSaving(false);
    }
  };

  const openFeatureModal = () => {
    setFeatureNameInput(currentFeature || '');
    setFeatureRequestMode('update');
    setFeatureContentInput('');
    setRelatedFeatureInput(null);
    setSelectedRelatedFeatures([]);
    setFeatureModalOpened(true);
    setEditorError('');
    setNotice('');
  };

  const openRequestModal = (feature: string) => {
    setRequestFeature(feature);
    setRequestMode('update');
    setRequestContent('');
    setRequestRelatedFeatureInput(null);
    setRequestRelatedFeatures([]);
    setRequestModalOpened(true);
    setEditorError('');
    setNotice('');
  };

  const addRelatedFeature = (
    value: string | null,
    currentList: string[],
    setList: (items: string[]) => void,
    clearValue: () => void,
  ) => {
    if (!value || currentList.includes(value)) return;
    setList([...currentList, value]);
    clearValue();
  };

  const createEntry = async () => {
    const isExistingFeature = Boolean(selectedExistingFeature);
    const featureName = featureNameInput.trim();
    if (!featureName) return;

    setCreatingEntry(true);
    setEditorError('');
    setNotice('');
    try {
      const relatedFeatures = selectedRelatedFeatures
        .map((name) => featureOptions.find((item) => item.name === name)?.path || '')
        .filter(Boolean);

      const endpoint = !isExistingFeature
        ? `${API_BASE_URL}/skill-pilot-development/create-feature`
        : featureRequestMode === 'update'
          ? `${API_BASE_URL}/skill-pilot-development/create-update-request`
          : `${API_BASE_URL}/skill-pilot-development/create-issue-report`;
      const res = await axios.post(endpoint, {
        feature_name: featureName,
        content: featureContentInput,
        related_features: relatedFeatures,
      });
      const createdPath = String(res.data.path || '');
      setFeatureModalOpened(false);
      await fetchTree();
      if (createdPath) {
        router.push(`/skill-pilot-development?task=${encodeURIComponent(createdPath)}`, undefined, { shallow: true });
      }
    } catch (err: any) {
      console.error('Failed to create feature entry:', err);
      setEditorError(err?.response?.data?.error || 'Failed to create entry.');
    } finally {
      setCreatingEntry(false);
    }
  };

  const createFeatureRequest = async () => {
    setCreatingEntry(true);
    setEditorError('');
    setNotice('');
    try {
      const relatedFeatures = requestRelatedFeatures
        .map((name) => featureOptions.find((item) => item.name === name)?.path || '')
        .filter(Boolean);
      const endpoint = requestMode === 'update'
        ? `${API_BASE_URL}/skill-pilot-development/create-update-request`
        : `${API_BASE_URL}/skill-pilot-development/create-issue-report`;
      const res = await axios.post(endpoint, {
        feature_name: requestFeature,
        content: requestContent,
        related_features: relatedFeatures,
      });
      const createdPath = String(res.data.path || '');
      setRequestModalOpened(false);
      await fetchTree();
      if (createdPath) {
        router.push(`/skill-pilot-development?task=${encodeURIComponent(createdPath)}`, undefined, { shallow: true });
      }
    } catch (err: any) {
      console.error('Failed to create feature request:', err);
      setEditorError(err?.response?.data?.error || 'Failed to create request.');
    } finally {
      setCreatingEntry(false);
    }
  };

  const deleteCurrentFile = async () => {
    if (!currentTask) return;
    let confirmText = '';
    if (currentFileName === 'requirements.md') {
      const typed = window.prompt(`Deleting ${currentTask} will remove the full feature folder. Type delete to confirm.`);
      if (typed === null) return;
      confirmText = typed;
    } else if (!window.confirm(`Delete ${currentTask}?`)) {
      return;
    }

    setDeletingFile(true);
    setEditorError('');
    setNotice('');
    try {
      await axios.post(`${API_BASE_URL}/skill-pilot-development/delete`, { path: currentTask, confirm_text: confirmText });
      await fetchTree();
      router.push('/skill-pilot-development', undefined, { shallow: true });
    } catch (err: any) {
      console.error('Failed to delete feature file:', err);
      setEditorError(err?.response?.data?.error || 'Failed to delete file.');
    } finally {
      setDeletingFile(false);
    }
  };

  const openExecuteModal = (action: FeatureAction) => {
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
          ? `Execute workflow ${workflowProjectPath(target)}. ${pendingAction.skillPromptSuffix.charAt(0).toUpperCase()}${pendingAction.skillPromptSuffix.slice(1)}\n\nYour Workspace path: ${currentFeature ? developmentProjectPath(currentFeature) : 'core/development'}\n\nIf you create any intermediate files, save them inside the project workspace above.`
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
      console.error('Failed to start development session:', err);
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

  useEffect(() => {
    fetchTree();
    fetchFeatureOptions();
    fetchLlmProviders();
    fetchExecuteOptions();
    void axios.get(`${API_BASE_URL}/config/settings`).then((res) => {
      const security = res.data?.security?.newSession;
      if (!security) return;
      setNewSessionSandbox(Boolean(security.sandbox));
      setNewSessionAuto(Boolean(security.auto));
      setNewSessionNetwork(security.network !== false);
    }).catch((err) => {
      console.error('Failed to fetch development session settings:', err);
    });
  }, []);

  useEffect(() => {
    if (currentTask) {
      fetchContent(currentTask);
    } else if (router.isReady) {
      fetchLatest();
    }
  }, [currentTask, router.isReady]);

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
      return (
        <NavLink
          key={item.path}
          label={(
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
              <span>{item.name}</span>
              <ActionIcon
                size="sm"
                variant="subtle"
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  openRequestModal(item.path);
                }}
                title={`New update or issue request for ${item.name}`}
              >
                <IconMessageCirclePlus size="0.95rem" />
              </ActionIcon>
            </div>
          )}
          icon={<IconFolder size="1.2rem" stroke={1.5} color={theme.colors.blue[6]} />}
          childrenOffset={16}
          opened={expandedFolders.includes(item.path)}
          onChange={(nextOpened) => {
            setExpandedFolders((prev) => (
              nextOpened ? Array.from(new Set([...prev, item.path])) : prev.filter((path) => path !== item.path)
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
        onClick={() => {
          router.push(`/skill-pilot-development?task=${encodeURIComponent(item.path)}`, undefined, { shallow: true });
          setOpened(false);
        }}
      />
    );
  });

  const currentInstructionPath = currentTask ? developmentProjectPath(currentTask) : '';
  const fileActions = useMemo<FeatureAction[]>(() => {
    if (!currentInstructionPath) return [];
    if (currentFileName === 'requirements.md') {
      return [
        { label: 'Refine', defaultSkill: 'skill-pilot-feature-refine', skillPromptSuffix: `to refine the ${currentInstructionPath}` },
        { label: 'Initial', defaultSkill: 'skill-pilot-feature-initial', skillPromptSuffix: `to create a new branch for the feature defined at ${currentInstructionPath}` },
        { label: 'Plan', defaultSkill: 'skill-pilot-feature-plan', skillPromptSuffix: `to make a development plan for requirement ${currentInstructionPath}` },
      ];
    }
    if (currentFileName === 'plan.md') {
      return [{ label: 'Implement', defaultSkill: 'skill-pilot-feature-implement', skillPromptSuffix: `to implement the code as the ${currentInstructionPath}` }];
    }
    if (currentFileName === 'implement.md') {
      return [
        { label: 'Review', defaultSkill: 'skill-pilot-feature-review', skillPromptSuffix: `to review the code of the implementation of the ${currentInstructionPath}` },
        { label: 'Test', defaultSkill: 'skill-pilot-feature-test', skillPromptSuffix: `to test the code of the implementation of the ${currentInstructionPath}` },
        { label: 'Merge', defaultSkill: 'skill-pilot-feature-merge', skillPromptSuffix: `to merge the code of the implementation of the ${currentInstructionPath}` },
      ];
    }
    if (currentFileName === 'update.md') {
      return [{ label: 'Update Code', defaultSkill: 'skill-pilot-feature-update', skillPromptSuffix: `to update the code based on the update request defined in ${currentInstructionPath}` }];
    }
    if (currentFileName === 'issues.md') {
      return [{ label: 'Fix Issues', defaultSkill: 'skill-pilot-feature-fix-issues', skillPromptSuffix: `to fix the issues defined in ${currentInstructionPath}` }];
    }
    return [];
  }, [currentFileName, currentInstructionPath]);

  const mediaUrl = currentTask ? `${API_BASE_URL}/skill-pilot-development/file?path=${encodeURIComponent(currentTask)}` : '';
  const renderHeaderActions = () => {
    if (!currentTask) return null;
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 8, flex: '0 0 auto', flexWrap: 'wrap' }}>
        {selectedKind === 'markdown' && (
          <>
            <Button size="xs" variant={markdownView === 'editor' ? 'filled' : 'default'} onClick={() => setMarkdownView('editor')}>Edit</Button>
            <Button size="xs" variant={markdownView === 'preview' ? 'filled' : 'default'} onClick={() => setMarkdownView('preview')}>Preview</Button>
          </>
        )}
        {fileActions.map((action) => (
          <Button key={action.label} size="xs" variant="default" onClick={() => openExecuteModal(action)}>{action.label}</Button>
        ))}
      </div>
    );
  };

  const renderMainContent = () => {
    if (!currentTask) {
      if (loading) return null;
      if (treeData.length === 0) {
        return (
          <div style={{ minHeight: '60vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ width: '100%', maxWidth: 560, padding: '36px 32px', borderRadius: 20, border: `1px solid ${theme.colorScheme === 'dark' ? theme.colors.dark[4] : '#d6def8'}`, background: theme.colorScheme === 'dark' ? 'linear-gradient(180deg, rgba(37,38,43,0.98) 0%, rgba(28,29,33,0.98) 100%)' : 'linear-gradient(180deg, #fbfcff 0%, #f2f6ff 100%)', boxShadow: theme.colorScheme === 'dark' ? '0 24px 60px rgba(0, 0, 0, 0.28)' : '0 24px 60px rgba(50, 84, 160, 0.12)', textAlign: 'center' }}>
              <Text size="xs" weight={700} transform="uppercase" style={{ letterSpacing: '0.12em', color: theme.colors.blue[6] }}>Skill Pilot Development</Text>
              <Text size={28} weight={800} mt={10}>Start your first feature</Text>
              <Text size="sm" color="dimmed" mt={12} style={{ maxWidth: 420, margin: '12px auto 0 auto', lineHeight: 1.6 }}>Create a feature requirement, link related feature files, then refine, plan, implement, review, test, and merge from the same workspace.</Text>
              <Group position="center" mt="xl"><Button onClick={openFeatureModal}>New Feature</Button></Group>
            </div>
          </div>
        );
      }
      return <Text align="center" py="xl" color="dimmed">Select a feature file from the sidebar to begin.</Text>;
    }

    if (selectedKind === 'image' && currentTask) {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
          <div style={{ flex: 1, minHeight: 0, display: 'flex', justifyContent: 'center', alignItems: 'center', padding: 16, overflow: 'auto' }}>
            <img src={mediaUrl} alt={currentFileName} style={{ maxWidth: '100%', maxHeight: '70vh', objectFit: 'contain', borderRadius: 8 }} />
          </div>
          <div style={PAGE_ACTION_BAR_STYLE}><Button size="xs" color="red" variant="light" onClick={() => void deleteCurrentFile()} loading={deletingFile}>Delete</Button></div>
        </div>
      );
    }

    if (selectedKind === 'audio' && currentTask) {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
          <div style={{ flex: 1, minHeight: 0, padding: 24 }}><audio controls src={mediaUrl} style={{ width: '100%' }}>Your browser does not support audio playback.</audio></div>
          <div style={PAGE_ACTION_BAR_STYLE}><Button size="xs" color="red" variant="light" onClick={() => void deleteCurrentFile()} loading={deletingFile}>Delete</Button></div>
        </div>
      );
    }

    if (selectedKind === 'video' && currentTask) {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
          <div style={{ flex: 1, minHeight: 0, display: 'flex', justifyContent: 'center', padding: 16 }}><video controls src={mediaUrl} style={{ width: '100%', maxHeight: '70vh', borderRadius: 8 }}>Your browser does not support video playback.</video></div>
          <div style={PAGE_ACTION_BAR_STYLE}><Button size="xs" color="red" variant="light" onClick={() => void deleteCurrentFile()} loading={deletingFile}>Delete</Button></div>
        </div>
      );
    }

    if (selectedKind === 'markdown') {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
          {markdownView === 'editor' ? (
            <>
              <div style={{ flex: 1, minHeight: 0 }}>
                <Textarea
                  value={editorContent}
                  onChange={(e) => { setEditorContent(e.currentTarget.value); if (editorError) setEditorError(''); if (notice) setNotice(''); }}
                  autosize={false}
                  minRows={1}
                  styles={{
                    root: { height: '100%' },
                    wrapper: { height: '100%' },
                    input: {
                      height: '100%',
                      minHeight: '100%',
                      resize: 'none',
                      border: 'none',
                      borderRadius: 0,
                      padding: '18px 20px',
                      fontFamily: PAGE_EDITOR_FONT,
                      fontSize: 13,
                      lineHeight: 1.65,
                    },
                  }}
                />
              </div>
              <div style={PAGE_ACTION_BAR_STYLE}><Button size="xs" onClick={() => void saveCurrentContent()} loading={editorSaving}>Save</Button><Button size="xs" color="red" variant="light" onClick={() => void deleteCurrentFile()} loading={deletingFile}>Delete</Button></div>
            </>
          ) : (
            <>
              <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: '20px 24px' }}>
                <div className="doc-markdown" style={{ maxWidth: 'none', margin: 0, minHeight: '100%', padding: '18px 20px 24px', border: 'none', borderRadius: 0, boxShadow: 'none', background: '#ffffff' }}><ReactMarkdown remarkPlugins={[remarkGfm]}>{editorContent}</ReactMarkdown></div>
              </div>
              <div style={PAGE_ACTION_BAR_STYLE}><Button size="xs" color="red" variant="light" onClick={() => void deleteCurrentFile()} loading={deletingFile}>Delete</Button></div>
            </>
          )}
        </div>
      );
    }

    return (
      <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
        <div style={{ flex: 1, minHeight: 0 }}>
          <Textarea
            value={editorContent}
            onChange={(e) => { setEditorContent(e.currentTarget.value); if (editorError) setEditorError(''); if (notice) setNotice(''); }}
            autosize={false}
            minRows={1}
            styles={{
              root: { height: '100%' },
              wrapper: { height: '100%' },
              input: {
                height: '100%',
                minHeight: '100%',
                resize: 'none',
                border: 'none',
                borderRadius: 0,
                padding: '18px 20px',
                fontFamily: PAGE_EDITOR_FONT,
                fontSize: 13,
                lineHeight: 1.65,
              },
            }}
          />
        </div>
        <div style={PAGE_ACTION_BAR_STYLE}><Button size="xs" onClick={() => void saveCurrentContent()} loading={editorSaving}>Save</Button><Button size="xs" color="red" variant="light" onClick={() => void deleteCurrentFile()} loading={deletingFile}>Delete</Button></div>
      </div>
    );
  };

  const relatedFeatureChoices = featureOptions.filter((item) => !selectedRelatedFeatures.includes(item.name) && item.name !== featureNameInput.trim());
  const requestRelatedFeatureChoices = featureOptions.filter((item) => !requestRelatedFeatures.includes(item.name) && item.name !== requestFeature);

  return (
    <AppShell
      styles={{ main: { background: theme.colorScheme === 'dark' ? theme.colors.dark[8] : theme.colors.gray[0], padding: 0, marginTop: 60, display: 'flex', flexDirection: 'column', overflow: 'hidden', height: 'calc(100vh - 60px)', minHeight: 0 } }}
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
              <MediaQuery largerThan="sm" styles={{ display: 'none' }}><Burger opened={opened} onClick={() => setOpened((o) => !o)} size="sm" color={theme.colors.gray[6]} mr="xl" /></MediaQuery>
              <a href="/"><img className="h-10" src="/images/skill-pilot-2.png" alt="Logo" /></a>
            </div>
            <Group spacing="xs">
              <Select placeholder="LLM" value={llmProvider} onChange={(value) => { if (!value) return; setLlmProvider(value); setSelectedProvider(value); }} data={llmProviders.map((p) => ({ value: p.id, label: p.name }))} size="xs" style={{ width: 200 }} />
            </Group>
          </div>
        </Header>
      }
    >
      <Head><title>Skill Pilot - Development</title></Head>

      <Modal opened={featureModalOpened} onClose={() => setFeatureModalOpened(false)} title="New Feature" centered size="lg">
        <Stack spacing="md">
          <div>
            <Text size="sm" weight={700} mb={4}>Feature Name</Text>
            <TextInput
              placeholder="feature-name"
              value={featureNameInput}
              onChange={(e) => setFeatureNameInput(e.currentTarget.value)}
              list="feature-name-options"
              description="Type a new feature name to create a new feature, or select an existing feature to create an update or issue request."
            />
            <datalist id="feature-name-options">
              {featureOptions.map((item) => (<option key={item.name} value={item.name} />))}
            </datalist>
          </div>

          {selectedExistingFeature && (
            <div>
              <Text size="sm" weight={700} mb={4}>Request Type</Text>
              <Group mt="xs">
                <Radio value="update" checked={featureRequestMode === 'update'} onChange={() => setFeatureRequestMode('update')} label="Update" />
                <Radio value="issue" checked={featureRequestMode === 'issue'} onChange={() => setFeatureRequestMode('issue')} label="Bug/Issues" />
              </Group>
            </div>
          )}

          <div>
            <Text size="sm" weight={700} mb={4}>Related Features</Text>
            <Group align="end">
              <Select
                placeholder="Select a related feature"
                value={relatedFeatureInput}
                onChange={setRelatedFeatureInput}
                data={relatedFeatureChoices.map((item) => ({ value: item.name, label: item.name }))}
                searchable
                clearable
                style={{ flex: 1 }}
              />
              <Button
                variant="default"
                onClick={() => addRelatedFeature(relatedFeatureInput, selectedRelatedFeatures, setSelectedRelatedFeatures, () => setRelatedFeatureInput(null))}
              >
                Add
              </Button>
            </Group>
            {selectedRelatedFeatures.length > 0 && (
              <div style={{ marginTop: 10 }}>
                {selectedRelatedFeatures.map((item) => (
                  <Group key={item} spacing={8} mb={6}>
                    <Text size="sm">{item}</Text>
                    <Button size="xs" variant="subtle" color="red" onClick={() => setSelectedRelatedFeatures((prev) => prev.filter((entry) => entry !== item))}>Remove</Button>
                  </Group>
                ))}
              </div>
            )}
          </div>

          <div>
            <Text size="sm" weight={700} mb={4}>{selectedExistingFeature ? (featureRequestMode === 'update' ? 'Update Request' : 'Bug/Issues') : 'Requirement'}</Text>
            <Textarea value={featureContentInput} onChange={(e) => setFeatureContentInput(e.currentTarget.value)} minRows={10} autosize />
          </div>
        </Stack>
        <Group position="right" mt="md">
          <Button variant="default" onClick={() => setFeatureModalOpened(false)}>Cancel</Button>
          <Button onClick={() => void createEntry()} loading={creatingEntry} disabled={!featureNameInput.trim()}>{selectedExistingFeature ? 'Create Request' : 'Create Feature'}</Button>
        </Group>
      </Modal>

      <Modal opened={requestModalOpened} onClose={() => setRequestModalOpened(false)} title="New Request" centered size="lg">
        <Stack spacing="md">
          <div>
            <Text size="sm" weight={700} mb={4}>Feature</Text>
            <Text size="sm">{requestFeature}</Text>
          </div>
          <div>
            <Text size="sm" weight={700} mb={4}>Request Type</Text>
            <Group mt="xs">
              <Radio value="update" checked={requestMode === 'update'} onChange={() => setRequestMode('update')} label="Update" />
              <Radio value="issue" checked={requestMode === 'issue'} onChange={() => setRequestMode('issue')} label="Bug/Issues" />
            </Group>
          </div>
          <div>
            <Text size="sm" weight={700} mb={4}>Related Features</Text>
            <Group align="end">
              <Select
                placeholder="Select a related feature"
                value={requestRelatedFeatureInput}
                onChange={setRequestRelatedFeatureInput}
                data={requestRelatedFeatureChoices.map((item) => ({ value: item.name, label: item.name }))}
                searchable
                clearable
                style={{ flex: 1 }}
              />
              <Button
                variant="default"
                onClick={() => addRelatedFeature(requestRelatedFeatureInput, requestRelatedFeatures, setRequestRelatedFeatures, () => setRequestRelatedFeatureInput(null))}
              >
                Add
              </Button>
            </Group>
            {requestRelatedFeatures.length > 0 && (
              <div style={{ marginTop: 10 }}>
                {requestRelatedFeatures.map((item) => (
                  <Group key={item} spacing={8} mb={6}>
                    <Text size="sm">{item}</Text>
                    <Button size="xs" variant="subtle" color="red" onClick={() => setRequestRelatedFeatures((prev) => prev.filter((entry) => entry !== item))}>Remove</Button>
                  </Group>
                ))}
              </div>
            )}
          </div>
          <div>
            <Text size="sm" weight={700} mb={4}>{requestMode === 'update' ? 'Update Request' : 'Bug/Issues'}</Text>
            <Textarea value={requestContent} onChange={(e) => setRequestContent(e.currentTarget.value)} minRows={10} autosize />
          </div>
        </Stack>
        <Group position="right" mt="md">
          <Button variant="default" onClick={() => setRequestModalOpened(false)}>Cancel</Button>
          <Button onClick={() => void createFeatureRequest()} loading={creatingEntry} disabled={!requestFeature.trim()}>Create</Button>
        </Group>
      </Modal>

      <Modal opened={executeOpened} onClose={() => setExecuteOpened(false)} title={pendingAction ? pendingAction.label : 'Run Action'} centered size="lg">
        <Stack spacing="md">
          <div>
            <Text size="sm" weight={700} mb={4}>Run By</Text>
            <Group mt="xs">
              <Radio value="skill" checked={executeMode === 'skill'} onChange={() => setExecuteMode('skill')} label="Skill" />
              <Radio value="workflow" checked={executeMode === 'workflow'} onChange={() => setExecuteMode('workflow')} label="Workflow" />
            </Group>
          </div>
          {executeMode === 'skill' ? (
            <Select label="Skill" placeholder="Select a skill" value={selectedSkill} onChange={setSelectedSkill} data={skillSelectOptions} searchable clearable={false} />
          ) : (
            <Select label="Workflow" placeholder="Select a workflow" value={selectedWorkflow} onChange={setSelectedWorkflow} data={workflowSelectOptions} searchable clearable={false} />
          )}
          <div>
            <Text size="sm" weight={700} mb={4}>Instruction File</Text>
            <Text size="sm">{currentInstructionPath || '(no file selected)'}</Text>
          </div>
        </Stack>
        <Group position="right" mt="md">
          <Button variant="default" onClick={() => setExecuteOpened(false)}>Cancel</Button>
          <Button onClick={() => void runAction()} disabled={!currentTask || (executeMode === 'skill' ? !selectedSkill : !selectedWorkflow)}>Run</Button>
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
                  <ActionIcon variant="subtle" onClick={() => { void router.push('/'); }} title="Back to Home">
                    <IconArrowLeft size="1rem" />
                  </ActionIcon>
                  <Text weight={700} size="lg">Features</Text>
                </Group>
                <Group spacing={4}>
                  <Tooltip label="New Feature"><ActionIcon variant="subtle" onClick={openFeatureModal}><IconPlus size="1.1rem" /></ActionIcon></Tooltip>
                  <Tooltip label="Refresh"><ActionIcon variant="subtle" onClick={() => void fetchTree()}><IconRefresh size="1.1rem" /></ActionIcon></Tooltip>
                  <Tooltip label={sortByTime ? 'Sorted by Time' : 'Sorted Alpha'}><ActionIcon variant="subtle" onClick={() => setSortByTime(!sortByTime)}>{sortByTime ? <IconClock size="1.1rem" /> : <IconSortAscending size="1.1rem" />}</ActionIcon></Tooltip>
                </Group>
              </Group>
            </div>
            <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
              <ScrollArea style={{ height: '100%' }} px="md" py="sm">
                {treeLoading && treeData.length === 0 ? <Box py="xl" sx={{ textAlign: 'center' }}><Text size="sm" color="dimmed">Loading...</Text></Box> : renderTree(sortedTreeData)}
              </ScrollArea>
            </div>
            <div onMouseDown={startResizing} style={{ position: 'absolute', top: 0, right: 0, width: '4px', height: '100%', cursor: 'col-resize', backgroundColor: isResizing ? theme.colors.blue[5] : 'transparent', transition: 'background-color 200ms ease', zIndex: 100 }} onMouseEnter={(e) => { if (!isResizing) e.currentTarget.style.backgroundColor = theme.colors.gray[3]; }} onMouseLeave={(e) => { if (!isResizing) e.currentTarget.style.backgroundColor = 'transparent'; }} />
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
                  {currentTask || 'Select a feature file from the sidebar'}
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
                  currentLabel={currentTask || 'Skill Pilot development session'}
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

export async function getStaticProps({ locale }: GetStaticPropsContext) {
  return {
    props: {
      ...(await serverSideTranslations(locale ?? 'en', ['common'])),
    },
  };
}
