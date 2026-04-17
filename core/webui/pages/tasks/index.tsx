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
  NavLink,
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
  IconPlayerPlay,
  IconPlus,
  IconRefresh,
  IconSortAscending,
  IconGripHorizontal,
  IconX,
} from '@tabler/icons-react';
import { apiUrl } from '../../libs/api-base';
import { AUTO_EXECUTE_OPTION, buildExecuteSelectOptions, isAutoExecuteTarget } from '../../libs/execute-targets';
import { resolveSelectedProvider, setSelectedProvider } from '../../libs/llm';
import { useSessionRoots } from '../../libs/session-roots';

const API_BASE_URL = apiUrl('/api');
axios.defaults.withCredentials = true;

type TaskKind = 'markdown' | 'text' | 'image' | 'audio' | 'video';

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

interface SaveTaskResult {
  saved: boolean;
  workflowResumeAvailable: boolean;
}

type ExecuteMode = 'skill' | 'workflow';
type NextNodeTrigger = 'auto_continue' | 'start_by_prompt';

interface WorkflowExecuteStatus {
  status: string;
  error?: string;
  next_node_trigger?: NextNodeTrigger;
  waiting_for_continue?: boolean;
}

const detectTaskKind = (path: string): TaskKind => {
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

const taskProjectPath = (path: string): string => {
  const trimmed = path.replace(/^\/+/, '');
  return trimmed ? `workspace/tasks/${trimmed}` : 'workspace/tasks';
};

const workflowProjectPath = (name: string): string => `core/workflows/${name}.json`;
const TASK_EDITOR_BG = '#0f172a';
const TASK_EDITOR_FG = '#e2e8f0';
const TASK_EDITOR_FONT = "'JetBrains Mono', 'Fira Mono', 'Cascadia Code', 'Consolas', monospace";
const TASK_ACTION_BAR_STYLE: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'flex-end',
  gap: 8,
  padding: '8px 16px',
  borderTop: '1px solid #eef2f7',
  background: '#f8fafc',
  flexShrink: 0,
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

const listFilesInDirectory = (items: FileItem[], directoryPath: string): FileItem[] => {
  if (!directoryPath) {
    return items.filter((item) => item.type === 'file');
  }

  for (const item of items) {
    if (item.type !== 'dir') continue;
    if (item.path === directoryPath) {
      return (item.children || []).filter((child) => child.type === 'file');
    }
    const nested = listFilesInDirectory(item.children || [], directoryPath);
    if (nested.length > 0) return nested;
  }

  return [];
};

export default function TasksPage() {
  const router = useRouter();
  const { task } = router.query;
  const theme = useMantineTheme();
  const isDevMode = process.env.NODE_ENV === 'development';
  const [opened, setOpened] = useState(false);
  const [treeData, setTreeData] = useState<FileItem[]>([]);
  const [selectedKind, setSelectedKind] = useState<TaskKind>('text');
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
  const [addTaskOpened, setAddTaskOpened] = useState(false);
  const [newTaskFolder, setNewTaskFolder] = useState('');
  const [newTaskFile, setNewTaskFile] = useState('new task');
  const [taskTitle, setTaskTitle] = useState('');
  const [creatingTask, setCreatingTask] = useState(false);
  const [deletingTask, setDeletingTask] = useState(false);
  const [executeOpened, setExecuteOpened] = useState(false);
  const [executeMode, setExecuteMode] = useState<ExecuteMode>('skill');
  const [skillOptions, setSkillOptions] = useState<string[]>([]);
  const [workflowOptions, setWorkflowOptions] = useState<string[]>([]);
  const [selectedSkill, setSelectedSkill] = useState<string | null>(AUTO_EXECUTE_OPTION);
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(AUTO_EXECUTE_OPTION);
  const [executeNextNodeTrigger, setExecuteNextNodeTrigger] = useState<NextNodeTrigger>('auto_continue');
  const [selectedReferenceFiles, setSelectedReferenceFiles] = useState<string[]>([]);
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
  const [newSessionNextNodeTrigger, setNewSessionNextNodeTrigger] = useState<NextNodeTrigger>('auto_continue');
  const [newSessionWorkflowResumeAvailable, setNewSessionWorkflowResumeAvailable] = useState(false);
  const [newSessionWorkflowResume, setNewSessionWorkflowResume] = useState(false);
  const [startingSession, setStartingSession] = useState(false);
  const [liveSessionName, setLiveSessionName] = useState<string | null>(null);
  const [workflowSessionActive, setWorkflowSessionActive] = useState(false);
  const [workflowExecuteStatus, setWorkflowExecuteStatus] = useState<WorkflowExecuteStatus | null>(null);
  const [continuingWorkflow, setContinuingWorkflow] = useState(false);
  const rightPaneRef = useRef<HTMLDivElement | null>(null);
  const {
    sessionRootOptions,
    hasSessionWorktrees,
    selectedSessionPath,
    setSelectedSessionPath,
  } = useSessionRoots();

  const currentTask = typeof task === 'string' ? task : '';
  const currentTaskFolder = currentTask.includes('/') ? currentTask.split('/')[0] : '';
  const currentDirectory = currentTask.includes('/') ? currentTask.slice(0, currentTask.lastIndexOf('/')) : '';
  const currentDirectoryFiles = useMemo(
    () => listFilesInDirectory(treeData, currentDirectory).filter((item) => item.path !== currentTask),
    [treeData, currentDirectory, currentTask],
  );
  const skillSelectOptions = useMemo(() => buildExecuteSelectOptions(skillOptions), [skillOptions]);
  const workflowSelectOptions = useMemo(() => buildExecuteSelectOptions(workflowOptions), [workflowOptions]);
  const workflowSelectsAuto = isAutoExecuteTarget(selectedWorkflow);
  const taskFolderOptions = useMemo(
    () => treeData
      .filter((item) => item.type === 'dir' && !item.path.includes('/'))
      .map((item) => item.path)
      .sort((a, b) => a.localeCompare(b)),
    [treeData],
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

    const handleMouseUp = () => {
      setIsSessionPanelResizing(false);
    };

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
      const res = await axios.get(`${API_BASE_URL}/tasks/tree`);
      setTreeData(res.data.items || []);
    } catch (err) {
      console.error('Failed to fetch task tree:', err);
    } finally {
      setTreeLoading(false);
    }
  };

  const fetchContent = async (path: string) => {
    const nextKind = detectTaskKind(path);
    setLoading(true);
    setEditorError('');
    setNotice('');
    setTaskTitle(path.split('/').pop() || path);
    setSelectedKind(nextKind);
    setMarkdownView('editor');

    if (nextKind === 'image' || nextKind === 'audio' || nextKind === 'video') {
      setEditorContent('');
      setLoading(false);
      return;
    }

    try {
      const res = await axios.get(`${API_BASE_URL}/tasks/content`, { params: { path } });
      setSelectedKind((res.data.kind as TaskKind) || nextKind);
      setEditorContent(String(res.data.content || ''));
    } catch (err: any) {
      console.error('Failed to fetch task content:', err);
      setEditorError(err?.response?.data?.error || 'Failed to load task content.');
      setEditorContent('');
    } finally {
      setLoading(false);
    }
  };

  const fetchLatest = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/tasks/latest`);
      if (res.data.path) {
        router.push(`/tasks?task=${encodeURIComponent(res.data.path)}`, undefined, { shallow: true });
      } else {
        setTaskTitle('');
        setEditorContent('');
        setNotice('');
      }
    } catch (err) {
      console.error('Failed to fetch latest task:', err);
    }
  };

  const fetchLlmProviders = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/llm/providers`);
      const providers: LlmProvider[] = res.data.providers || [];
      setLlmProviders(providers);
      const serverDefault: string = res.data.default || '';
      const defaultId = resolveSelectedProvider(providers, serverDefault, 'gemini');
      if (defaultId) {
        setSelectedProvider(defaultId);
      }
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

  const saveCurrentTaskContent = async (options?: { checkWorkflowResume?: boolean; workflowPath?: string }): Promise<SaveTaskResult> => {
    if (!currentTask || selectedKind === 'image' || selectedKind === 'audio' || selectedKind === 'video') {
      return { saved: true, workflowResumeAvailable: false };
    }
    const projectReferenceFiles = Array.from(new Set(selectedReferenceFiles.map((path) => taskProjectPath(path))))
      .sort((a, b) => a.localeCompare(b));
    setEditorSaving(true);
    setEditorError('');
    setNotice('');
    try {
      const res = await axios.post(`${API_BASE_URL}/tasks/save`, {
        path: currentTask,
        content: editorContent,
        check_workflow_resume: Boolean(options?.checkWorkflowResume),
        workflow_path: options?.workflowPath || '',
        reference_files: projectReferenceFiles,
      });
      setNotice('Saved.');
      await fetchTree();
      await fetchContent(currentTask);
      return {
        saved: true,
        workflowResumeAvailable: Boolean(res.data?.workflow_resume_available),
      };
    } catch (err: any) {
      console.error('Failed to save task content:', err);
      setEditorError(err?.response?.data?.error || 'Failed to save task content.');
      return { saved: false, workflowResumeAvailable: false };
    } finally {
      setEditorSaving(false);
    }
  };

  const saveContent = async () => {
    await saveCurrentTaskContent();
  };

  const createTask = async () => {
    const trimmedFile = newTaskFile.trim();
    if (!trimmedFile) return;
    setCreatingTask(true);
    setEditorError('');
    setNotice('');
    try {
      const res = await axios.post(`${API_BASE_URL}/tasks/create`, {
        folder: newTaskFolder.trim(),
        file: trimmedFile,
      });
      const createdPath = String(res.data.path || trimmedFile);
      setAddTaskOpened(false);
      setNewTaskFolder(currentTaskFolder);
      setNewTaskFile('new task');
      await fetchTree();
      router.push(`/tasks?task=${encodeURIComponent(createdPath)}`, undefined, { shallow: true });
    } catch (err: any) {
      console.error('Failed to create task:', err);
      setEditorError(err?.response?.data?.error || 'Failed to create task.');
    } finally {
      setCreatingTask(false);
    }
  };

  const deleteTask = async () => {
    if (!currentTask) return;
    if (!window.confirm(`Delete ${currentTask}?`)) return;
    setDeletingTask(true);
    setEditorError('');
    setNotice('');
    try {
      await axios.post(`${API_BASE_URL}/tasks/delete`, { path: currentTask });
      await fetchTree();
      router.push('/tasks', undefined, { shallow: true });
    } catch (err: any) {
      console.error('Failed to delete task:', err);
      setEditorError(err?.response?.data?.error || 'Failed to delete task.');
    } finally {
      setDeletingTask(false);
    }
  };

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
      console.error('Failed to fetch task session settings:', err);
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
    setSelectedReferenceFiles((prev) => prev.filter((path) => currentDirectoryFiles.some((item) => item.path === path)));
  }, [currentDirectoryFiles]);

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

  useEffect(() => {
    if (executeMode !== 'workflow' || workflowSelectsAuto) {
      setExecuteNextNodeTrigger('auto_continue');
    }
  }, [executeMode, workflowSelectsAuto]);

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
          label={item.name}
          icon={<IconFolder size="1.2rem" stroke={1.5} color={theme.colors.blue[6]} />}
          childrenOffset={16}
          opened={expandedFolders.includes(item.path)}
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
        onClick={() => {
          router.push(`/tasks?task=${encodeURIComponent(item.path)}`, undefined, { shallow: true });
          setOpened(false);
        }}
      />
    );
  });

  const mediaUrl = currentTask ? `${API_BASE_URL}/tasks/file?path=${encodeURIComponent(currentTask)}` : '';
  const isMarkdownEditor = selectedKind === 'markdown';
  const isTextEditor = selectedKind === 'text';

  const openExecuteScreen = () => {
    setExecuteMode('skill');
    setSelectedSkill(AUTO_EXECUTE_OPTION);
    setSelectedWorkflow(AUTO_EXECUTE_OPTION);
    setExecuteNextNodeTrigger('auto_continue');
    setSelectedReferenceFiles([]);
    setExecuteOpened(true);
    setNotice('');
    setEditorError('');
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

  const toggleReferenceFile = (path: string, checked: boolean) => {
    setSelectedReferenceFiles((prev) => (
      checked
        ? (prev.includes(path) ? prev : [...prev, path])
        : prev.filter((item) => item !== path)
    ));
  };

  const runExecuteAction = async () => {
    if (!currentTask) return;
    const target = executeMode === 'skill' ? selectedSkill : selectedWorkflow;
    if (!target) return;
    const shouldRunWorkflow = executeMode === 'workflow' && !isAutoExecuteTarget(target);
    const saveResult = await saveCurrentTaskContent({
      checkWorkflowResume: shouldRunWorkflow,
      workflowPath: shouldRunWorkflow ? workflowProjectPath(target) : undefined,
    });
    if (!saveResult.saved) return;

    const instructionPath = taskProjectPath(currentTask);
    const projectReferenceFiles = Array.from(new Set(selectedReferenceFiles.map((path) => taskProjectPath(path))))
      .sort((a, b) => a.localeCompare(b));
    const referenceSentence = selectedReferenceFiles.length > 0 ? ` Reference files: ${projectReferenceFiles.join(', ')}.` : '';
    const prompt = executeMode === 'skill'
      ? (isAutoExecuteTarget(target)
          ? `Find and use the correct agent skill for the instructions defined at ${instructionPath}.${referenceSentence}`
          : `Use agent skill ${target} for the instructions defined at ${instructionPath}.${referenceSentence}`)
      : (shouldRunWorkflow
          ? `Execute workflow ${workflowProjectPath(target)}.\n\nFollow the instructions defined at ${instructionPath}.\n\nWorkspace path: ${currentDirectory ? taskProjectPath(currentDirectory) : 'workspace/tasks'}\n\nIf you create any intermediate files, save them inside the task workspace above.${selectedReferenceFiles.length > 0 ? `\n\nReference files:\n- ${projectReferenceFiles.join('\n- ')}` : ''}`
          : `Find and use the correct workflow for the instructions defined at ${instructionPath}.${referenceSentence}`);

    setExecuteOpened(false);
    setSessionPromptText(prompt);
    setNewSessionWorkflow(shouldRunWorkflow ? `${target}.json` : null);
    setNewSessionNextNodeTrigger(shouldRunWorkflow ? executeNextNodeTrigger : 'auto_continue');
    setNewSessionWorkflowResumeAvailable(shouldRunWorkflow ? saveResult.workflowResumeAvailable : false);
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
        } else {
          setWorkflowSessionActive(false);
          setWorkflowExecuteStatus(null);
        }
      }
    } catch (err) {
      console.error('Failed to start task session:', err);
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

  const handleSessionPromptKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      void handleStartSession();
    }
  };

  const renderSessionPanel = () => {
    const panelBorder = theme.colorScheme === 'dark' ? theme.colors.dark[4] : '#cfdaf6';
    const panelBackground = theme.colorScheme === 'dark' ? theme.colors.dark[7] : '#ffffff';

    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          minHeight: 0,
          borderRadius: liveSessionName ? 0 : 10,
          border: `1px solid ${panelBorder}`,
          background: panelBackground,
          boxShadow: theme.colorScheme === 'dark'
            ? '0 20px 40px rgba(0, 0, 0, 0.24)'
            : '0 20px 40px rgba(60, 91, 173, 0.12)',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '10px 14px',
            borderBottom: `1px solid ${panelBorder}`,
            background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#f7f9ff',
          }}
        >
          <div style={{ minWidth: 0 }}>
            <Text size="sm" weight={700}>
              {liveSessionName ? 'Session Terminal' : 'New Session'}
            </Text>
            <Text size="xs" color="dimmed" truncate>
              {liveSessionName ? liveSessionName : currentTask || 'Task execution'}
            </Text>
          </div>
          <ActionIcon variant="subtle" onClick={closeSessionPanel} aria-label="Close session panel">
            <IconX size="1rem" />
          </ActionIcon>
        </div>

        {liveSessionName ? (
          <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
            {workflowExecuteStatus && (workflowExecuteStatus.status === 'error' || workflowExecuteStatus.status === 'terminated') && (
              <div style={{ padding: '8px 12px', borderBottom: `1px solid ${panelBorder}`, background: '#fde8e8', color: '#c0392b', fontSize: 13 }}>
                Workflow execution failed{workflowExecuteStatus.error ? `: ${workflowExecuteStatus.error}` : ''}
              </div>
            )}
            {workflowExecuteStatus && workflowExecuteStatus.status === 'finished' && (
              <div style={{ padding: '8px 12px', borderBottom: `1px solid ${panelBorder}`, background: '#e8fde8', color: '#1f8a4c', fontSize: 13 }}>
                Workflow completed
              </div>
            )}
            {workflowExecuteStatus && workflowSessionActive && workflowExecuteStatus.status !== 'finished' && workflowExecuteStatus.status !== 'error' && workflowExecuteStatus.status !== 'terminated' && (
              <div style={{ padding: '8px 12px', borderBottom: `1px solid ${panelBorder}`, background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#f7f9ff', fontSize: 13 }}>
                Workflow status: {workflowExecuteStatus.status}
                {workflowExecuteStatus.error ? ` - ${workflowExecuteStatus.error}` : ''}
              </div>
            )}
            <div style={{ flex: 1, minHeight: 0, background: '#0b1220' }}>
              <iframe
                key={liveSessionName}
                src={`/terminal?session=${encodeURIComponent(liveSessionName)}&compact=1`}
                style={{ width: '100%', height: '100%', border: 'none' }}
              />
            </div>
            {workflowSessionActive && workflowExecuteStatus?.waiting_for_continue && (
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'flex-end',
                  padding: '10px 14px',
                  borderTop: `1px solid ${panelBorder}`,
                  background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#f7f9ff',
                }}
              >
                <Button size="xs" variant="light" onClick={() => void handleWorkflowContinue()} loading={continuingWorkflow}>
                  Continue Next Node
                </Button>
              </div>
            )}
          </div>
        ) : (
          <>
            <div style={{ padding: '10px 14px 0 14px' }}>
              {newSessionWorkflow && (
                <Text size="xs" color="dimmed" mb={8}>
                  Workflow mode: {`core/workflows/${newSessionWorkflow}`}
                </Text>
              )}
              {hasSessionWorktrees && (
                <Select
                  label="Worktree"
                  placeholder="Choose where to start"
                  value={selectedSessionPath || null}
                  onChange={(value) => setSelectedSessionPath(value || '')}
                  data={sessionRootOptions.map((root) => ({ value: root.value, label: root.label }))}
                  size="xs"
                  mb={8}
                />
              )}
            </div>
            <div style={{ flex: 1, minHeight: 0, padding: '0 14px 14px 14px' }}>
              <Textarea
                placeholder="What would you like to do?"
                value={sessionPromptText}
                onChange={(event) => setSessionPromptText(event.currentTarget.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
                    event.preventDefault();
                    void handleStartSession(selectedSessionPath || undefined);
                    return;
                  }
                  handleSessionPromptKeyDown(event);
                }}
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
                    padding: 0,
                    background: 'transparent',
                    fontSize: 14,
                    lineHeight: 1.6,
                  },
                }}
              />
            </div>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 12,
                padding: '10px 14px',
                borderTop: `1px solid ${panelBorder}`,
                background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#f7f9ff',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer' }}>
                  <input type="checkbox" checked={newSessionSandbox} onChange={(event) => setNewSessionSandbox(event.currentTarget.checked)} />
                  <span>Sandbox</span>
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer' }}>
                  <input type="checkbox" checked={newSessionAuto} onChange={(event) => setNewSessionAuto(event.currentTarget.checked)} />
                  <span>Auto Run (Yolo)</span>
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer' }}>
                  <input type="checkbox" checked={newSessionNetwork} onChange={(event) => setNewSessionNetwork(event.currentTarget.checked)} />
                  <span>Network Access</span>
                </label>
                {newSessionWorkflow && (
                  <>
                    <Select
                      value={newSessionNextNodeTrigger}
                      onChange={(value) => setNewSessionNextNodeTrigger((value as NextNodeTrigger) || 'auto_continue')}
                      data={[
                        { value: 'auto_continue', label: 'Auto continue' },
                        { value: 'start_by_prompt', label: 'Start by prompt' },
                      ]}
                      size="xs"
                      style={{ width: 160 }}
                    />
                    {newSessionWorkflowResumeAvailable && (
                      <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer' }}>
                        <input type="checkbox" checked={newSessionWorkflowResume} onChange={(event) => setNewSessionWorkflowResume(event.currentTarget.checked)} />
                        <span>Resume Workflow</span>
                      </label>
                    )}
                  </>
                )}
              </div>
              <Button onClick={() => void handleStartSession(selectedSessionPath || undefined)} disabled={!sessionPromptText.trim() || startingSession} loading={startingSession}>
                Start
              </Button>
            </div>
          </>
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
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: 24,
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
                Tasks Workspace
              </Text>
              <Text size={28} weight={800} mt={10}>
                Start your first task
              </Text>
              <Text size="sm" color="dimmed" mt={12} style={{ maxWidth: 420, margin: '12px auto 0 auto', lineHeight: 1.6 }}>
                Create a task file, then edit it directly or execute it with a skill or workflow from the same screen.
              </Text>
              <Group position="center" mt="xl">
                <Button
                  onClick={() => {
                    setNewTaskFolder(currentTaskFolder);
                    setNewTaskFile('new task');
                    setAddTaskOpened(true);
                  }}
                >
                  New Task
                </Button>
              </Group>
            </div>
          </div>
        );
      }
      return (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b', fontSize: 14 }}>
          Select a task file from the sidebar to begin.
        </div>
      );
    }

    if (selectedKind === 'image' && currentTask) {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
          <div style={{ flex: 1, minHeight: 0, display: 'flex', justifyContent: 'center', alignItems: 'center', padding: 16, overflow: 'auto' }}>
            <img src={mediaUrl} alt={taskTitle} style={{ maxWidth: '100%', maxHeight: '70vh', objectFit: 'contain', borderRadius: 8 }} />
          </div>
          <div style={TASK_ACTION_BAR_STYLE}>
            <Button size="xs" color="red" variant="light" onClick={() => void deleteTask()} loading={deletingTask}>Delete</Button>
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
          <div style={TASK_ACTION_BAR_STYLE}>
            <Button size="xs" color="red" variant="light" onClick={() => void deleteTask()} loading={deletingTask}>Delete</Button>
          </div>
        </div>
      );
    }

    if (selectedKind === 'video' && currentTask) {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
          <div style={{ flex: 1, minHeight: 0, display: 'flex', justifyContent: 'center', padding: 16, background: '#0f172a' }}>
            <video controls src={mediaUrl} style={{ width: '100%', maxHeight: '70vh', borderRadius: 8 }}>
              Your browser does not support video playback.
            </video>
          </div>
          <div style={{ ...TASK_ACTION_BAR_STYLE, borderTop: '1px solid #20324d', background: '#111827' }}>
            <Button size="xs" color="red" variant="light" onClick={() => void deleteTask()} loading={deletingTask}>Delete</Button>
          </div>
        </div>
      );
    }

    if (isMarkdownEditor) {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
          {markdownView === 'editor' ? (
            <div style={{ flex: 1, minHeight: 0, background: TASK_EDITOR_BG }}>
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
                  wrapper: { height: '100%', background: TASK_EDITOR_BG },
                  input: {
                    height: '100%',
                    minHeight: '100%',
                    resize: 'none',
                    border: 'none',
                    borderRadius: 0,
                    padding: '18px 20px',
                    fontFamily: TASK_EDITOR_FONT,
                    fontSize: 13,
                    lineHeight: 1.65,
                    background: TASK_EDITOR_BG,
                    color: TASK_EDITOR_FG,
                    caretColor: '#f8fafc',
                  },
                }}
              />
            </div>
          ) : (
            <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: '20px 24px', background: '#ffffff' }}>
              <div
                className="doc-markdown"
                style={{
                  maxWidth: 'none',
                  margin: 0,
                  minHeight: '100%',
                  padding: '18px 20px 24px',
                  border: 'none',
                  borderRadius: 0,
                  boxShadow: 'none',
                  background: '#ffffff',
                }}
              >
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{editorContent}</ReactMarkdown>
              </div>
            </div>
          )}
          <div style={TASK_ACTION_BAR_STYLE}>
            <Button size="xs" onClick={() => void saveContent()} loading={editorSaving}>Save</Button>
            <Button size="xs" color="red" variant="light" onClick={() => void deleteTask()} loading={deletingTask}>Delete</Button>
          </div>
        </div>
      );
    }

    if (isTextEditor) {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
          <div style={{ flex: 1, minHeight: 0, background: TASK_EDITOR_BG }}>
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
                wrapper: { height: '100%', background: TASK_EDITOR_BG },
                input: {
                  height: '100%',
                  minHeight: '100%',
                  resize: 'none',
                  border: 'none',
                  borderRadius: 0,
                  padding: '18px 20px',
                  fontFamily: TASK_EDITOR_FONT,
                  fontSize: 13,
                  lineHeight: 1.65,
                  background: TASK_EDITOR_BG,
                  color: TASK_EDITOR_FG,
                  caretColor: '#f8fafc',
                },
              }}
            />
          </div>
          <div style={TASK_ACTION_BAR_STYLE}>
            <Button size="xs" onClick={() => void saveContent()} loading={editorSaving}>Save</Button>
            <Button size="xs" color="red" variant="light" onClick={() => void deleteTask()} loading={deletingTask}>Delete</Button>
          </div>
        </div>
      );
    }

    return !loading ? (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b', fontSize: 14 }}>
        Select a task file from the sidebar to begin.
      </div>
    ) : null;
  };

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
        <title>Skill Pilot - Tasks</title>
      </Head>

      <Modal opened={addTaskOpened} onClose={() => setAddTaskOpened(false)} title="Add Task" centered>
        <Stack spacing="md">
          <TextInput
            label="Task"
            placeholder="Current folder or new subfolder"
            value={newTaskFolder}
            onChange={(e) => setNewTaskFolder(e.currentTarget.value)}
            list="task-folder-options"
            description="Top-level subfolders under workspace/tasks. Leave blank for the root folder."
          />
          <datalist id="task-folder-options">
            {taskFolderOptions.map((folder) => (
              <option key={folder} value={folder} />
            ))}
          </datalist>
          <TextInput
            label="File"
            placeholder="new task"
            value={newTaskFile}
            onChange={(e) => setNewTaskFile(e.currentTarget.value)}
            description="Names are converted to lowercase kebab-case. Missing extensions default to .md and duplicates get _1, _2, etc."
          />
        </Stack>
        <Group position="right" mt="md">
          <Button variant="default" onClick={() => setAddTaskOpened(false)}>Cancel</Button>
          <Button onClick={() => void createTask()} disabled={!newTaskFile.trim()} loading={creatingTask}>Create Task</Button>
        </Group>
      </Modal>

      <Modal
        opened={executeOpened}
        onClose={() => setExecuteOpened(false)}
        title="Execute Task"
        centered
        size="lg"
      >
        <Stack spacing="md">
          <div>
            <Text size="sm" weight={600} mb={6}>Executed By</Text>
            <Group spacing="lg">
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                <input
                  type="radio"
                  name="execute-mode"
                  checked={executeMode === 'skill'}
                  onChange={() => setExecuteMode('skill')}
                />
                <span>Skill</span>
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                <input
                  type="radio"
                  name="execute-mode"
                  checked={executeMode === 'workflow'}
                  onChange={() => setExecuteMode('workflow')}
                />
                <span>Workflow</span>
              </label>
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
            />
          ) : (
            <>
              <Select
                label="Workflow"
                placeholder="Select a workflow"
                value={selectedWorkflow}
                onChange={setSelectedWorkflow}
                data={workflowSelectOptions}
                searchable
                clearable={false}
              />
              <Select
                label="Next Node Trigger"
                value={executeNextNodeTrigger}
                onChange={(value) => setExecuteNextNodeTrigger((value as NextNodeTrigger) || 'auto_continue')}
                data={[
                  { value: 'auto_continue', label: 'Auto continue' },
                  { value: 'start_by_prompt', label: 'Start by prompt' },
                ]}
                disabled={workflowSelectsAuto}
                description={workflowSelectsAuto ? 'Disabled for Auto because the session will choose a workflow from the prompt.' : undefined}
              />
            </>
          )}

          <div>
            <Text size="sm" weight={600}>Instruction File</Text>
            <Text size="sm" color="dimmed" mt={4}>{currentTask || '(no file selected)'}</Text>
          </div>

          <div>
            <Text size="sm" weight={600} mb={6}>Reference Files</Text>
            {currentDirectoryFiles.length > 0 ? (
              <div
                style={{
                  border: `1px solid ${theme.colorScheme === 'dark' ? theme.colors.dark[4] : theme.colors.gray[3]}`,
                  borderRadius: 8,
                  padding: 12,
                  maxHeight: 220,
                  overflowY: 'auto',
                }}
              >
                {currentDirectoryFiles.map((item) => (
                  <label
                    key={item.path}
                    style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0', cursor: 'pointer' }}
                  >
                    <input
                      type="checkbox"
                      checked={selectedReferenceFiles.includes(item.path)}
                      onChange={(e) => toggleReferenceFile(item.path, e.currentTarget.checked)}
                    />
                    <span>{item.name}</span>
                  </label>
                ))}
              </div>
            ) : (
              <Text size="sm" color="dimmed">No other files found in this directory.</Text>
            )}
          </div>
          <Group position="right">
            <Button variant="default" onClick={() => setExecuteOpened(false)}>Cancel</Button>
            <Button
              onClick={runExecuteAction}
              disabled={!currentTask || (executeMode === 'skill' ? !selectedSkill : !selectedWorkflow)}
            >
              Run
            </Button>
          </Group>
        </Stack>
      </Modal>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden', minHeight: 0 }}>
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
            <div style={{ padding: '12px 14px', minHeight: 46, borderBottom: '1px solid #eef2f7', flexShrink: 0, display: 'flex', alignItems: 'center' }}>
              <button
                type="button"
                onClick={() => { void router.push('/'); }}
                className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-semibold text-[#5e6b9d] hover:bg-[#eef2ff] hover:text-[#1a2455] transition"
                title="Back to Home"
              >
                <IconArrowLeft size="1rem" />
                <span>Back to Home</span>
              </button>
            </div>
            <div style={{ padding: '12px 14px', minHeight: 46, borderBottom: '1px solid #eef2f7', flexShrink: 0 }}>
              <Group position="apart" align="center">
              <Text weight={700} size="lg">Tasks</Text>
              <Group spacing={4}>
                <Tooltip label="Add Task">
                  <ActionIcon
                    variant="subtle"
                    onClick={() => {
                      setNewTaskFolder(currentTaskFolder);
                      setNewTaskFile('new task');
                      setAddTaskOpened(true);
                    }}
                  >
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
            padding: 0,
            background: '#ffffff',
            minHeight: 0,
            height: '100%',
          }}
        >
          <div style={{ minHeight: 0, height: '100%', overflow: 'hidden', display: 'flex', flexDirection: 'column', borderBottom: sessionPanelOpen ? 'none' : '1px solid #e9ecef', background: '#ffffff' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 12,
                padding: '8px 18px',
                borderBottom: '1px solid #eef2f7',
                background: '#ffffff',
                flexShrink: 0,
                flexWrap: 'wrap',
              }}
            >
              <div style={{ fontSize: 12, color: '#64748b', minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: '1 1 240px' }}>
                {currentTask || 'Select a task file from the sidebar'}
              </div>
              {currentTask ? (
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 8, flex: '0 0 auto', flexWrap: 'wrap' }}>
                  {selectedKind === 'markdown' && (
                    <>
                      <Button size="xs" variant={markdownView === 'editor' ? 'filled' : 'default'} onClick={() => setMarkdownView('editor')}>
                        Edit
                      </Button>
                      <Button size="xs" variant={markdownView === 'preview' ? 'filled' : 'default'} onClick={() => setMarkdownView('preview')}>
                        Preview
                      </Button>
                    </>
                  )}
                  {(selectedKind === 'markdown' || selectedKind === 'text') && (
                    <Button
                      size="xs"
                      variant="default"
                      leftIcon={<IconPlayerPlay size="1rem" />}
                      onClick={openExecuteScreen}
                    >
                      Execute
                    </Button>
                  )}
                  </div>
              ) : null}
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

          {sessionPanelOpen && (
            <>
              <div
                onMouseDown={(event) => {
                  event.preventDefault();
                  setIsSessionPanelResizing(true);
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'row-resize',
                  color: theme.colorScheme === 'dark' ? theme.colors.gray[5] : '#93a4cc',
                }}
                aria-label="Resize session panel"
              >
                <IconGripHorizontal size="1rem" />
              </div>
              <div style={{ minHeight: 0, overflow: 'hidden', borderLeft: '1px solid #e9ecef', borderTop: '1px solid #e9ecef', background: '#ffffff' }}>
                <div style={{ width: '100%', height: '100%' }}>
                  {renderSessionPanel()}
                </div>
              </div>
            </>
          )}
        </main>
      </div>
    </AppShell>
  );
}

export const getStaticProps = async (context: GetStaticPropsContext) => {
  return {
    props: {
      ...(await serverSideTranslations(context.locale ?? 'en', ['common'])),
    },
  };
};
