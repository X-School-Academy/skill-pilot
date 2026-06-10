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
  Menu,
  Modal,
  Navbar,
  NavLink,
  Radio,
  ScrollArea,
  SegmentedControl,
  Select,
  Text,
  TextInput,
  Textarea,
  Tooltip,
  Accordion,
  Card,
  Badge,
  useMantineTheme,
} from '@mantine/core';
import {
  IconArrowLeft,
  IconBrandLinkedin,
  IconBrandX,
  IconClock,
  IconDeviceFloppy,
  IconEdit,
  IconEye,
  IconFilePlus,
  IconFileText,
  IconPlus,
  IconRefresh,
  IconSend,
  IconSortAscending,
  IconTransform,
  IconTrash,
  IconChecklist,
  IconHash,
  IconNote,
  IconMessageCircle,
  IconPhoto,
} from '@tabler/icons-react';
import EmbeddedSessionPanel, { WorkflowExecuteStatus } from '../../components/EmbeddedSessionPanel';
import { apiUrl } from '../../libs/api-base';
import { AUTO_EXECUTE_OPTION, buildExecuteSelectOptions, isAutoExecuteTarget } from '../../libs/execute-targets';
import { resolveSelectedProvider, setSelectedProvider } from '../../libs/llm';

const API_BASE_URL = apiUrl('/api');
axios.defaults.withCredentials = true;

type FileKind = 'markdown' | 'text';
type ExecuteMode = 'skill' | 'workflow';

type Platform = 'linkedin' | 'x' | 'xiaohongshu';

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

interface SocialAction {
  label: string;
  defaultSkill: string;
  skillPromptSuffix: string;
}

interface HistoryPost {
  platform: string;
  content: string;
  timestamp: string;
}

interface HistoryData {
  posts: HistoryPost[];
  next_scheduled: Record<string, string>;
}

interface CalendarItem {
  id: string;
  topic: string;
  platform: Platform;
  status: 'idea' | 'scheduled' | 'drafted' | 'published';
  scheduledDate: string;
  draftPath: string;
  notes: string;
  createdAt: string;
  publishedAt: string | null;
}

const CALENDAR_STATUS_COLORS: Record<string, string> = {
  idea: 'gray',
  scheduled: 'yellow',
  drafted: 'blue',
  published: 'green',
};

const CALENDAR_STATUS_LABELS: Record<string, string> = {
  idea: 'Idea',
  scheduled: 'Scheduled',
  drafted: 'Drafted',
  published: 'Published',
};

const PLATFORM_LABELS: Record<Platform, string> = {
  linkedin: 'LinkedIn',
  x: 'X',
  xiaohongshu: 'XiaoHongShu',
};

const PLATFORM_ICONS: Record<Platform, React.ReactNode> = {
  linkedin: <IconBrandLinkedin size="1rem" />,
  x: <IconBrandX size="1rem" />,
  xiaohongshu: <IconNote size="1rem" />,
};

const PLATFORM_HINTS: Record<Platform, { title: string; tips: string[] }> = {
  linkedin: {
    title: 'LinkedIn Style Guide',
    tips: [
      'Hook: 1-2 sentences that stop the scroll',
      'Body: Use bullet points and whitespace',
      'CTA: Ask a question to spark comments',
      'Hashtags: 3-5 maximum',
    ],
  },
  x: {
    title: 'X/Twitter Style Guide',
    tips: [
      'Threads: Number tweets (1/n) for engagement',
      'Tone: Fast-paced, punchy, hot takes',
      'Hook first tweet to drive thread expansion',
      'Experimental — limited selectors available',
    ],
  },
  xiaohongshu: {
    title: 'XiaoHongShu Style Guide',
    tips: [
      'Visuals: Mandatory. High-quality images perform best',
      'Title: Use 【...】 brackets or emojis to stand out',
      'Body: Lots of emojis, helpful 干货 content',
      'Tags: 5-10 tags starting with # at the end',
    ],
  },
};

const detectFileKind = (path: string): FileKind => {
  const lower = (path || '').toLowerCase();
  if (lower.endsWith('.md') || lower.endsWith('.markdown')) return 'markdown';
  return 'text';
};

const socialProjectPath = (path: string): string => {
  const trimmed = path.replace(/^\/+/, '');
  return trimmed ? `workspace/social-media/${trimmed}` : 'workspace/social-media';
};

const socialRelativePath = (projectPath: string): string => {
  return projectPath
    .replace(/^\$project\/workspace\/social-media\/?/, '')
    .replace(/^workspace\/social-media\/?/, '');
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

export default function SocialMediaPage() {
  const router = useRouter();
  const { draft } = router.query;
  const theme = useMantineTheme();

  const [treeData, setTreeData] = useState<FileItem[]>([]);
  const [historyData, setHistoryData] = useState<HistoryData>({ posts: [], next_scheduled: {} });
  const [calendarItems, setCalendarItems] = useState<CalendarItem[]>([]);
  const [calendarLoading, setCalendarLoading] = useState(false);
  const [calendarModalOpened, setCalendarModalOpened] = useState(false);
  const [calendarEditItem, setCalendarEditItem] = useState<CalendarItem | null>(null);
  const [newItemTopic, setNewItemTopic] = useState('');
  const [newItemPlatform, setNewItemPlatform] = useState<Platform>('linkedin');
  const [newItemDate, setNewItemDate] = useState('');
  const [newItemStatus, setNewItemStatus] = useState<string>('idea');
  const [newItemNotes, setNewItemNotes] = useState('');
  const [newItemDraftPath, setNewItemDraftPath] = useState('');
  const [selectedKind, setSelectedKind] = useState<FileKind>('text');
  const [loading, setLoading] = useState(false);
  const [treeLoading, setTreeLoading] = useState(false);
  const [sortByTime, setSortByTime] = useState(true);
  const [llmProviders, setLlmProviders] = useState<LlmProvider[]>([]);
  const [llmProvider, setLlmProvider] = useState<string | null>(null);
  const [editorSaving, setEditorSaving] = useState(false);
  const [editorError, setEditorError] = useState('');
  const [notice, setNotice] = useState('');
  const [editorContent, setEditorContent] = useState('');
  const [markdownView, setMarkdownView] = useState<'editor' | 'preview'>('editor');
  const [selectedPlatform, setSelectedPlatform] = useState<Platform>('linkedin');

  const [executeOpened, setExecuteOpened] = useState(false);
  const [executeMode, setExecuteMode] = useState<ExecuteMode>('skill');
  const [skillOptions, setSkillOptions] = useState<string[]>([]);
  const [workflowOptions, setWorkflowOptions] = useState<string[]>([]);
  const [selectedSkill, setSelectedSkill] = useState<string | null>(AUTO_EXECUTE_OPTION);
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(AUTO_EXECUTE_OPTION);
  const [pendingAction, setPendingAction] = useState<SocialAction | null>(null);

  const [navbarWidth, setNavbarWidth] = useState(280);
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
  const [publishingDirectly, setPublishingDirectly] = useState(false);
  const [startingSession, setStartingSession] = useState(false);
  const [liveSessionName, setLiveSessionName] = useState<string | null>(null);
  const [workflowSessionActive, setWorkflowSessionActive] = useState(false);
  const [workflowExecuteStatus, setWorkflowExecuteStatus] = useState<WorkflowExecuteStatus | null>(null);
  const [continuingWorkflow, setContinuingWorkflow] = useState(false);

  const rightPaneRef = useRef<HTMLDivElement | null>(null);
  const autoSaveTimerRef = useRef<number | null>(null);
  const lastLoadedContentRef = useRef<string>('');
  const editorContentRef = useRef<string>('');
  useEffect(() => { editorContentRef.current = editorContent; }, [editorContent]);

  const currentDraft = typeof draft === 'string' ? draft : '';

  // ---------------------------------------------------------------------------
  // Data fetching
  // ---------------------------------------------------------------------------

  const fetchTree = async () => {
    setTreeLoading(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/social/tree`);
      setTreeData(res.data?.items || []);
    } catch (err) {
      console.error('Failed to fetch social media tree:', err);
    } finally {
      setTreeLoading(false);
    }
  };

  const fetchHistory = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/social/history`);
      setHistoryData(res.data || { posts: [], next_scheduled: {} });
    } catch (err) {
      console.error('Failed to fetch social media history:', err);
    }
  };

  const fetchCalendar = async () => {
    setCalendarLoading(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/social/calendar`, {
        params: { platform: selectedPlatform },
      });
      setCalendarItems(res.data?.items || []);
    } catch (err) {
      console.error('Failed to fetch calendar:', err);
    } finally {
      setCalendarLoading(false);
    }
  };

  const createCalendarItem = async () => {
    if (!newItemTopic.trim()) return;
    try {
      await axios.post(`${API_BASE_URL}/social/calendar`, {
        topic: newItemTopic.trim(),
        platform: newItemPlatform,
        status: newItemStatus,
        scheduledDate: newItemDate,
        notes: newItemNotes.trim(),
        draftPath: newItemDraftPath.trim(),
      });
      await fetchCalendar();
      resetCalendarForm();
      setNotice('Calendar item created');
    } catch (err: any) {
      setEditorError(err?.response?.data?.error || 'Failed to create calendar item');
    }
  };

  const updateCalendarItem = async (itemId: string, updates: Record<string, any>) => {
    try {
      await axios.patch(`${API_BASE_URL}/social/calendar/${itemId}`, updates);
      await fetchCalendar();
    } catch (err: any) {
      setEditorError(err?.response?.data?.error || 'Failed to update calendar item');
    }
  };

  const deleteCalendarItem = async (itemId: string) => {
    try {
      await axios.delete(`${API_BASE_URL}/social/calendar/${itemId}`);
      await fetchCalendar();
      setNotice('Calendar item deleted');
    } catch (err: any) {
      setEditorError(err?.response?.data?.error || 'Failed to delete calendar item');
    }
  };

  const resetCalendarForm = () => {
    setCalendarModalOpened(false);
    setCalendarEditItem(null);
    setNewItemTopic('');
    setNewItemPlatform(selectedPlatform);
    setNewItemDate('');
    setNewItemStatus('idea');
    setNewItemNotes('');
    setNewItemDraftPath('');
  };

  const openCalendarCreate = (prefill?: { draftPath?: string; platform?: Platform }) => {
    setCalendarEditItem(null);
    setNewItemTopic('');
    setNewItemPlatform(prefill?.platform || selectedPlatform);
    setNewItemDate('');
    setNewItemStatus('idea');
    setNewItemNotes('');
    setNewItemDraftPath(prefill?.draftPath || '');
    setCalendarModalOpened(true);
  };

  const openCalendarEdit = (item: CalendarItem) => {
    setCalendarEditItem(item);
    setNewItemTopic(item.topic);
    setNewItemPlatform(item.platform);
    setNewItemDate(item.scheduledDate || '');
    setNewItemStatus(item.status);
    setNewItemNotes(item.notes || '');
    setNewItemDraftPath(item.draftPath || '');
    setCalendarModalOpened(true);
  };

  const saveCalendarItem = () => {
    if (calendarEditItem) {
      updateCalendarItem(calendarEditItem.id, {
        topic: newItemTopic.trim(),
        platform: newItemPlatform,
        status: newItemStatus,
        scheduledDate: newItemDate,
        notes: newItemNotes.trim(),
        draftPath: newItemDraftPath.trim(),
      });
    } else {
      createCalendarItem();
    }
  };

  const cycleCalendarStatus = (item: CalendarItem) => {
    const order = ['idea', 'scheduled', 'drafted', 'published'];
    const idx = order.indexOf(item.status);
    const next = order[(idx + 1) % order.length];
    updateCalendarItem(item.id, { status: next });
  };

  const fetchContent = async (path: string) => {
    setLoading(true);
    setEditorError('');
    setNotice('');
    try {
      const res = await axios.get(`${API_BASE_URL}/social/content`, { params: { path } });
      const kind = detectFileKind(path);
      setSelectedKind(kind);
      setEditorContent(res.data?.content || '');
      lastLoadedContentRef.current = res.data?.content || '';
    } catch (err: any) {
      const msg = err?.response?.data?.error || 'Failed to load content';
      setEditorError(msg);
      if (err?.response?.status === 404) {
        setEditorContent('');
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchLatest = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/social/latest`);
      if (res.data?.path) {
        const path = res.data.path;
        router.replace({ query: { draft: path } }, undefined, { shallow: true });
      }
    } catch (err) {
      console.error('Failed to fetch latest draft:', err);
    }
  };

  // ---------------------------------------------------------------------------
  // Save / Create / Delete
  // ---------------------------------------------------------------------------

  const saveCurrentContent = async (): Promise<boolean> => {
    if (!currentDraft) return false;
    const contentToSave = editorContentRef.current;
    try {
      setEditorSaving(true);
      await axios.post(`${API_BASE_URL}/social/save`, {
        path: currentDraft,
        content: contentToSave,
      });
      lastLoadedContentRef.current = contentToSave;
      setEditorSaving(false);
      setEditorError('');
      fetchTree();
      return true;
    } catch (err: any) {
      setEditorError(err?.response?.data?.error || 'Failed to save');
      setEditorSaving(false);
      return false;
    }
  };

  const handleCreateDraft = async () => {
    try {
      const res = await axios.post(`${API_BASE_URL}/social/create`, {
        platform: selectedPlatform,
        title: `draft-${Date.now()}`,
      });
      await fetchTree();
      const newPath = res.data?.path;
      if (newPath) {
        router.replace({ query: { draft: newPath } }, undefined, { shallow: true });
      }
      setNotice('Draft created');
    } catch (err: any) {
      setEditorError(err?.response?.data?.error || 'Failed to create draft');
    }
  };

  const handleDeleteDraft = async (path: string) => {
    if (!path) return;
    try {
      await axios.post(`${API_BASE_URL}/social/delete`, { path });
      await fetchTree();
      if (currentDraft === path) {
        router.replace({ query: {} }, undefined, { shallow: true });
        setEditorContent('');
      }
      setNotice('Draft deleted');
    } catch (err: any) {
      setEditorError(err?.response?.data?.error || 'Failed to delete draft');
    }
  };

  const handleDirectPublish = async () => {
    if (!currentDraft) return;
    const saved = await saveCurrentContent();
    if (!saved) return;

    setPublishingDirectly(true);
    setEditorError('');
    setNotice('');
    try {
      const res = await axios.post(`${API_BASE_URL}/social/publish`, {
        path: currentDraft,
        platform: selectedPlatform,
      });
      if (res.data?.status === 'ok') {
        setNotice(`Published to ${PLATFORM_LABELS[selectedPlatform]} via automation script. No AI tokens used.`);
        fetchHistory();
      } else {
        setEditorError(res.data?.stderr || res.data?.error || 'Publish script failed. Try "Publish with AI" instead.');
      }
    } catch (err: any) {
      setEditorError(err?.response?.data?.error || 'Direct publish failed. Try "Publish with AI" instead.');
    } finally {
      setPublishingDirectly(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Session panel
  // ---------------------------------------------------------------------------

  const openExecuteModal = (action: SocialAction) => {
    setPendingAction(action);
    setExecuteOpened(true);
  };

  const runAction = async () => {
    if (!pendingAction) return;

    const saved = await saveCurrentContent();
    if (!saved && currentDraft) return;

    const currentLabel = currentDraft || socialProjectPath(`${selectedPlatform}/`);

    let prompt = '';
    if (executeMode === 'skill') {
      if (selectedSkill && !isAutoExecuteTarget(selectedSkill)) {
        prompt = `Use agent skill ${selectedSkill} ${pendingAction.skillPromptSuffix}`;
      } else {
        prompt = `Find and use the correct agent skill ${pendingAction.skillPromptSuffix}`;
      }
    } else {
      if (selectedWorkflow && !isAutoExecuteTarget(selectedWorkflow)) {
        prompt = `Execute workflow core/workflows/${selectedWorkflow}.json. ${pendingAction.skillPromptSuffix}\n\nYour Workspace path: ${currentLabel}`;
      } else {
        prompt = `Find and use the correct workflow ${pendingAction.skillPromptSuffix}\n\nYour Workspace path: ${currentLabel}`;
      }
    }

    setExecuteOpened(false);
    setSessionPanelOpen(true);
    setSessionPromptText(prompt);
    setNewSessionWorkflow(
      executeMode === 'workflow' && selectedWorkflow && !isAutoExecuteTarget(selectedWorkflow)
        ? selectedWorkflow
        : null
    );
  };

  const handleStartSession = async (path?: string) => {
    setStartingSession(true);
    const trimmedPrompt = sessionPromptText.trim();

    if (newSessionWorkflow) {
      try {
        const res = await axios.post(`${API_BASE_URL}/workflows/execute`, {
          workflow: newSessionWorkflow,
          prompt: trimmedPrompt,
          path: path || socialProjectPath(currentDraft || `${selectedPlatform}/`),
          sandbox: newSessionSandbox,
          auto: newSessionAuto,
          network: newSessionNetwork,
          next_node_trigger: newSessionNextNodeTrigger,
          resume: newSessionWorkflowResume,
        });
        setLiveSessionName(res.data?.session?.name || null);
        setWorkflowSessionActive(true);
      } catch (err: any) {
        setEditorError(err?.response?.data?.error || 'Failed to start workflow');
      }
    } else {
      try {
        const res = await axios.post(`${API_BASE_URL}/terminal/tmux/create`, {
          provider_id: llmProvider,
          prompt: trimmedPrompt,
          path: path || socialProjectPath(currentDraft || `${selectedPlatform}/`),
          sandbox: newSessionSandbox,
          auto: newSessionAuto,
          network: newSessionNetwork,
        });
        setLiveSessionName(res.data?.session?.name || null);
      } catch (err: any) {
        setEditorError(err?.response?.data?.error || 'Failed to start session');
      }
    }
    setStartingSession(false);
  };

  const handleWorkflowContinue = async () => {
    setContinuingWorkflow(true);
    try {
      await axios.post(`${API_BASE_URL}/workflows/execute/continue`);
      const statusRes = await axios.get(`${API_BASE_URL}/workflows/execute/status`);
      setWorkflowExecuteStatus(statusRes.data || null);
    } catch (err: any) {
      setEditorError(err?.response?.data?.error || 'Failed to continue workflow');
    } finally {
      setContinuingWorkflow(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Effects
  // ---------------------------------------------------------------------------

  useEffect(() => {
    fetchTree();
    fetchHistory();
  }, []);

  useEffect(() => {
    fetchCalendar();
  }, [selectedPlatform]);

  useEffect(() => {
    if (currentDraft) {
      fetchContent(currentDraft);
    }
  }, [currentDraft]);

  useEffect(() => {
    if (!currentDraft && treeData.length > 0) {
      fetchLatest();
    }
  }, [treeData]);

  useEffect(() => {
    if (!currentDraft || loading || selectedKind !== 'markdown' && selectedKind !== 'text') return;
    if (editorContent === lastLoadedContentRef.current) return;

    if (autoSaveTimerRef.current) window.clearTimeout(autoSaveTimerRef.current);
    autoSaveTimerRef.current = window.setTimeout(() => {
      void saveCurrentContent();
    }, 900);

    return () => {
      if (autoSaveTimerRef.current) window.clearTimeout(autoSaveTimerRef.current);
    };
  }, [currentDraft, editorContent, loading, selectedKind]);

  useEffect(() => {
    if (workflowSessionActive && liveSessionName) {
      const intervalId = window.setInterval(async () => {
        try {
          const res = await axios.get(`${API_BASE_URL}/workflows/execute/status`);
          const status = res.data;
          setWorkflowExecuteStatus(status);
          if (status?.status === 'finished' || status?.status === 'error' || status?.status === 'terminated') {
            setWorkflowSessionActive(false);
          }
        } catch {
          // status endpoint not available yet
        }
      }, 3000);
      return () => window.clearInterval(intervalId);
    }
  }, [workflowSessionActive, liveSessionName]);

  useEffect(() => {
    const loadProviders = async () => {
      try {
        const res = await axios.get(`${API_BASE_URL}/llm/providers`);
        setLlmProviders(res.data?.providers || []);
        const resolved = resolveSelectedProvider(res.data?.providers, res.data?.default);
        setLlmProvider(resolved);
      } catch {
        // providers not available
      }
    };
    loadProviders();
  }, []);

  useEffect(() => {
    const loadExecuteOptions = async () => {
      try {
        const [skillsRes, workflowsRes, settingsRes] = await Promise.all([
          axios.get(`${API_BASE_URL}/config/skills/installed`),
          axios.get(`${API_BASE_URL}/workflows/tree`),
          axios.get(`${API_BASE_URL}/config/settings`),
        ]);

        const skillNames: string[] = (skillsRes.data?.items || [])
          .map((s: any) => s.name || '')
          .filter(Boolean);
        setSkillOptions(skillNames);

        const workflowNames: string[] = (workflowsRes.data?.items || [])
          .filter((w: any) => w.type === 'file')
          .map((w: any) => w.name || '')
          .filter(Boolean);
        setWorkflowOptions(workflowNames);

        if (settingsRes.data) {
          if (settingsRes.data.sandbox !== undefined) setNewSessionSandbox(!!settingsRes.data.sandbox);
          if (settingsRes.data.auto !== undefined) setNewSessionAuto(!!settingsRes.data.auto);
          if (settingsRes.data.network !== undefined) setNewSessionNetwork(!!settingsRes.data.network);
        }
      } catch {
        // execute options not available
      }
    };
    loadExecuteOptions();
  }, []);

  // Navbar resize effect
  useEffect(() => {
    const handleMouseMove = (e: PointerEvent) => {
      if (!isResizing) return;
      const newWidth = Math.min(500, Math.max(200, e.clientX));
      setNavbarWidth(newWidth);
    };
    const handleMouseUp = () => setIsResizing(false);
    if (isResizing) {
      window.addEventListener('pointermove', handleMouseMove);
      window.addEventListener('pointerup', handleMouseUp);
    }
    return () => {
      window.removeEventListener('pointermove', handleMouseMove);
      window.removeEventListener('pointerup', handleMouseUp);
    };
  }, [isResizing]);

  // Session panel resize effect
  useEffect(() => {
    const handleMouseMove = (e: PointerEvent) => {
      if (!isSessionPanelResizing || !rightPaneRef.current) return;
      const rect = rightPaneRef.current.getBoundingClientRect();
      const h = ((rect.bottom - e.clientY) / rect.height) * 100;
      setSessionPanelHeight(Math.min(85, Math.max(15, h)));
    };
    const handleMouseUp = () => setIsSessionPanelResizing(false);
    if (isSessionPanelResizing) {
      window.addEventListener('pointermove', handleMouseMove);
      window.addEventListener('pointerup', handleMouseUp);
    }
    return () => {
      window.removeEventListener('pointermove', handleMouseMove);
      window.removeEventListener('pointerup', handleMouseUp);
    };
  }, [isSessionPanelResizing]);

  // ---------------------------------------------------------------------------
  // Derived data
  // ---------------------------------------------------------------------------

  const platformDrafts = useMemo(() => {
    const platformDir = treeData.find(
      (d) => d.type === 'dir' && d.name === selectedPlatform
    );
    if (!platformDir || !platformDir.children) return [];
    return platformDir.children
      .filter((item) => item.type === 'file')
      .sort((a, b) => sortByTime ? b.mtime - a.mtime : a.name.localeCompare(b.name));
  }, [treeData, selectedPlatform, sortByTime]);

  const platformHistory = useMemo(() => {
    return historyData.posts
      .filter((p) => p.platform === selectedPlatform)
      .slice(-10)
      .reverse();
  }, [historyData, selectedPlatform]);

  const currentFileName = currentDraft.split('/').pop() || '';

  // ---------------------------------------------------------------------------
  // Render helpers
  // ---------------------------------------------------------------------------

  const renderTree = () => {
    if (treeLoading && treeData.length === 0) {
      return (
        <Text size="sm" color="dimmed" px="md" py="sm">
          Loading...
        </Text>
      );
    }

    const draftItems = platformDrafts;

    if (draftItems.length === 0) {
      return (
        <Box px="md" py="sm">
          <Text size="sm" color="dimmed">
            No drafts yet for {PLATFORM_LABELS[selectedPlatform]}
          </Text>
        </Box>
      );
    }

    return (
      <>
        {draftItems.map((item) => (
          <NavLink
            key={item.path}
            label={item.name}
            icon={<IconFileText size="1rem" />}
            active={currentDraft === item.path}
            onClick={() => {
              router.replace({ query: { draft: item.path } }, undefined, { shallow: true });
            }}
            description={
              sortByTime
                ? new Date(item.mtime * 1000).toLocaleDateString()
                : undefined
            }
            rightSection={
              <Menu shadow="md" width={160}>
                <Menu.Target>
                  <ActionIcon
                    size="xs"
                    onClick={(e: React.MouseEvent) => e.stopPropagation()}
                  >
                    <IconTrash size="0.8rem" />
                  </ActionIcon>
                </Menu.Target>
                <Menu.Dropdown>
                  <Menu.Item
                    icon={<IconClock size="0.9rem" />}
                    onClick={(e: React.MouseEvent) => {
                      e.stopPropagation();
                      openCalendarCreate({ draftPath: item.path, platform: selectedPlatform });
                    }}
                  >
                    Schedule
                  </Menu.Item>
                  <Menu.Item
                    color="red"
                    icon={<IconTrash size="0.9rem" />}
                    onClick={(e: React.MouseEvent) => {
                      e.stopPropagation();
                      handleDeleteDraft(item.path);
                    }}
                  >
                    Delete
                  </Menu.Item>
                </Menu.Dropdown>
              </Menu>
            }
          />
        ))}
      </>
    );
  };

  const renderHistory = () => {
    if (platformHistory.length === 0) {
      return (
        <Text size="xs" color="dimmed" px="md" pb="sm">
          No posts published yet.
        </Text>
      );
    }

    return (
      <>
        {platformHistory.map((post, idx) => (
          <Box key={idx} px="md" pb="xs">
            <Group spacing={6} mb={4}>
              <IconClock size="0.8rem" />
              <Text size="xs" color="dimmed">
                {new Date(post.timestamp).toLocaleString()}
              </Text>
            </Group>
            <Text size="xs" lineClamp={3} sx={{ whiteSpace: 'pre-wrap' }}>
              {post.content?.slice(0, 200)}
              {(post.content?.length || 0) > 200 ? '...' : ''}
            </Text>
          </Box>
        ))}
      </>
    );
  };

  const renderPreviewHints = () => {
    const hints = PLATFORM_HINTS[selectedPlatform];
    return (
      <Card shadow="sm" padding="sm" radius="sm" mb="sm" sx={{ flexShrink: 0 }}>
        <Group spacing={8} mb={6}>
          <IconChecklist size="1rem" />
          <Text size="sm" weight={600}>
            {hints.title}
          </Text>
        </Group>
        {hints.tips.map((tip, i) => (
          <Text key={i} size="xs" color="dimmed" mb={2}>
            • {tip}
          </Text>
        ))}
      </Card>
    );
  };

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------

  const REPURPOSE_ACTION: SocialAction = {
    label: 'Repurpose',
    defaultSkill: 'social-content',
    skillPromptSuffix: `to repurpose the content from workspace/social-media/${currentDraft || selectedPlatform + '/'} into platform-specific variants for LinkedIn, X, and XiaoHongShu. Read the current draft first, then generate optimized versions for each platform.`,
  };

  const PUBLISH_ACTION: SocialAction = {
    label: 'Publish',
    defaultSkill: 'social-marketing',
    skillPromptSuffix: `to publish the content from workspace/social-media/${currentDraft || selectedPlatform + '/'} to ${PLATFORM_LABELS[selectedPlatform]}. Follow the full publishing workflow: check history, present draft for approval, then use agent-browser to publish.`,
  };

  // ---------------------------------------------------------------------------
  // Empty state
  // ---------------------------------------------------------------------------

  if (treeData.length === 0 && !treeLoading) {
    const platformLabels = Object.values(PLATFORM_LABELS).join(', ');
    return (
      <AppShell
        padding={0}
        navbar={
          <Navbar width={{ base: navbarWidth }} p="xs">
            <Navbar.Section>
              <Text size="sm" weight={600} px="sm" pt="sm" pb="xs">
                Social Media
              </Text>
            </Navbar.Section>
          </Navbar>
        }
        header={
          <Header height={52} px="md" sx={{ display: 'flex', alignItems: 'center' }}>
            <Text size="lg" weight={700}>
              Social Media
            </Text>
          </Header>
        }
        styles={{ main: { background: '#f5f7fa' } }}
      >
        <Head>
          <title>Social Media - Skill Pilot</title>
        </Head>
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            gap: 16,
          }}
        >
          <IconSend size="3rem" color={theme.colors.gray[5]} />
          <Text size="xl" weight={600} color="dimmed">
            Start creating social media content
          </Text>
          <Text size="sm" color="dimmed" align="center" maw={400}>
            Write and manage posts for {platformLabels}. Draft your content here, then repurpose across platforms or publish directly.
          </Text>
          <Button
            leftIcon={<IconPlus size="1rem" />}
            onClick={handleCreateDraft}
          >
            New Draft
          </Button>
        </Box>
      </AppShell>
    );
  }

  // ---------------------------------------------------------------------------
  // Main render
  // ---------------------------------------------------------------------------

  return (
    <AppShell
      padding={0}
      navbar={
        <Navbar width={{ base: navbarWidth }} p={0} sx={{ borderRight: '1px solid #eef2f7' }}>
          <Navbar.Section p="xs">
            <Group spacing={6} mb="xs">
              <Text size="sm" weight={600}>
                Social Media
              </Text>
              <Tooltip label="Refresh" withArrow>
                <ActionIcon size="sm" onClick={() => { fetchTree(); fetchHistory(); fetchCalendar(); }}>
                  <IconRefresh size="0.9rem" />
                </ActionIcon>
              </Tooltip>
            </Group>
            <SegmentedControl
              fullWidth
              size="xs"
              value={selectedPlatform}
              onChange={(v) => {
                setSelectedPlatform(v as Platform);
                router.replace({ query: {} }, undefined, { shallow: true });
                setEditorContent('');
              }}
              data={[
                { label: 'LinkedIn', value: 'linkedin' },
                { label: 'X', value: 'x' },
                { label: 'XHS', value: 'xiaohongshu' },
              ]}
            />
          </Navbar.Section>

          <Navbar.Section p="xs" pt={0}>
            <Group spacing={6} mb={4}>
              <Button
                fullWidth
                size="xs"
                variant="light"
                leftIcon={<IconPlus size="0.9rem" />}
                onClick={handleCreateDraft}
              >
                New Draft
              </Button>
              <Tooltip label={sortByTime ? 'Sort by name' : 'Sort by time'} withArrow>
                <ActionIcon
                  size="sm"
                  variant="subtle"
                  onClick={() => setSortByTime(!sortByTime)}
                >
                  <IconSortAscending size="0.9rem" />
                </ActionIcon>
              </Tooltip>
            </Group>
          </Navbar.Section>

          <Navbar.Section grow component={ScrollArea} px={0}>
            {renderTree()}
          </Navbar.Section>

          <Navbar.Section>
            <Accordion variant="filled" defaultValue={calendarItems.length > 0 ? 'calendar' : 'history'}>
              <Accordion.Item value="calendar">
                <Accordion.Control>
                  <Group spacing={8}>
                    <IconClock size="0.9rem" />
                    <Text size="xs" weight={500}>
                      Content Calendar ({calendarItems.length})
                    </Text>
                  </Group>
                </Accordion.Control>
                <Accordion.Panel>
                  <Box px="xs" pb="xs">
                    <Button
                      fullWidth
                      size="xs"
                      variant="light"
                      leftIcon={<IconPlus size="0.8rem" />}
                      mb="xs"
                      onClick={() => openCalendarCreate()}
                    >
                      New Item
                    </Button>
                    {calendarLoading ? (
                      <Text size="xs" color="dimmed" align="center">Loading...</Text>
                    ) : calendarItems.length === 0 ? (
                      <Text size="xs" color="dimmed" align="center" pb="sm">
                        No items yet. Plan your content.
                      </Text>
                    ) : (
                      calendarItems.map((item) => (
                        <Box key={item.id} mb="xs" sx={{ position: 'relative' }}>
                          <Group spacing={4} mb={2}>
                            <Badge
                              size="xs"
                              color={CALENDAR_STATUS_COLORS[item.status]}
                              variant="filled"
                              sx={{ cursor: 'pointer', textTransform: 'lowercase' }}
                              onClick={() => cycleCalendarStatus(item)}
                              title="Click to cycle status"
                            >
                              {CALENDAR_STATUS_LABELS[item.status]}
                            </Badge>
                            {item.scheduledDate && (
                              <Text size="xs" color="dimmed">
                                {new Date(item.scheduledDate).toLocaleDateString()}
                              </Text>
                            )}
                          </Group>
                          <Text size="xs" weight={500} lh={1.3}>
                            {item.topic}
                          </Text>
                          {item.draftPath && (
                            <Text size="xs" color="dimmed" sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {item.draftPath}
                            </Text>
                          )}
                          <Group spacing={4} mt={2}>
                            <ActionIcon
                              size="xs"
                              variant="subtle"
                              onClick={() => openCalendarEdit(item)}
                              title="Edit"
                            >
                              <IconEdit size="0.7rem" />
                            </ActionIcon>
                            <ActionIcon
                              size="xs"
                              variant="subtle"
                              color="red"
                              onClick={() => deleteCalendarItem(item.id)}
                              title="Delete"
                            >
                              <IconTrash size="0.7rem" />
                            </ActionIcon>
                          </Group>
                        </Box>
                      ))
                    )}
                  </Box>
                </Accordion.Panel>
              </Accordion.Item>
              <Accordion.Item value="history">
                <Accordion.Control>
                  <Group spacing={8}>
                    <IconClock size="0.9rem" />
                    <Text size="xs" weight={500}>
                      Post History ({platformHistory.length})
                    </Text>
                  </Group>
                </Accordion.Control>
                <Accordion.Panel>
                  {renderHistory()}
                </Accordion.Panel>
              </Accordion.Item>
            </Accordion>
          </Navbar.Section>
        </Navbar>
      }
      header={
        <Header height={52} px="md" sx={{ display: 'flex', alignItems: 'center' }}>
          <Group spacing="xs">
            <IconSend size="1.2rem" />
            <Text size="md" weight={700}>
              Social Media
            </Text>
          </Group>
        </Header>
      }
      styles={{ main: { background: '#f5f7fa' } }}
    >
      <Head>
        <title>Social Media - Skill Pilot</title>
      </Head>

      {/* Drag handle for navbar resize */}
      <Box
        sx={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: 4,
          height: '100%',
          cursor: 'col-resize',
          zIndex: 10,
          '&:hover': { background: theme.colors.blue[3] },
        }}
        onPointerDown={(e: React.PointerEvent) => {
          e.preventDefault();
          setIsResizing(true);
        }}
      />

      <Box
        ref={rightPaneRef}
        sx={{
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          overflow: 'hidden',
        }}
      >
        {/* Header bar */}
        <Box style={PAGE_HEADER_BAR_STYLE}>
          <Group spacing="xs">
            {currentDraft ? (
              <>
                {PLATFORM_ICONS[selectedPlatform]}
                <Text size="sm" weight={500}>
                  {currentDraft}
                </Text>
              </>
            ) : (
              <Text size="sm" color="dimmed">
                {PLATFORM_LABELS[selectedPlatform]} — Select a draft or create a new one
              </Text>
            )}
            {editorSaving && (
              <Text size="xs" color="dimmed">
                Saving...
              </Text>
            )}
          </Group>
          <Group spacing="xs">
            {currentDraft && (selectedKind === 'markdown' || selectedKind === 'text') && (
              <SegmentedControl
                size="xs"
                value={markdownView}
                onChange={(v) => setMarkdownView(v as 'editor' | 'preview')}
                data={[
                  { label: 'Edit', value: 'editor' },
                  { label: 'Preview', value: 'preview' },
                ]}
              />
            )}
            {currentDraft && (
              <>
                <Button
                  size="xs"
                  variant="light"
                  color="violet"
                  leftIcon={<IconTransform size="0.9rem" />}
                  onClick={() => openExecuteModal(REPURPOSE_ACTION)}
                >
                  Repurpose
                </Button>
                <Button
                  size="xs"
                  variant="filled"
                  color="blue"
                  leftIcon={<IconSend size="0.9rem" />}
                  onClick={handleDirectPublish}
                  loading={publishingDirectly}
                >
                  Publish
                </Button>
              </>
            )}
          </Group>
        </Box>

        {/* Error / Notice bar */}
        {editorError && (
          <Box px="md" py="xs" sx={{ background: '#fff0f0', borderBottom: '1px solid #ffcccc', flexShrink: 0 }}>
            <Text size="sm" color="red">
              {editorError}
            </Text>
          </Box>
        )}
        {notice && (
          <Box px="md" py="xs" sx={{ background: '#f0fff0', borderBottom: '1px solid #ccffcc', flexShrink: 0 }}>
            <Text size="sm" color="green">
              {notice}
            </Text>
          </Box>
        )}

        {/* Content area */}
        <Box
          sx={{
            flex: sessionPanelOpen ? `0 0 ${100 - sessionPanelHeight}%` : '1 1 auto',
            overflow: 'hidden',
            position: 'relative',
          }}
        >
          <LoadingOverlay visible={loading} overlayBlur={2} />

          {!currentDraft ? (
            <Box
              sx={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                gap: 12,
              }}
            >
              {renderPreviewHints()}
              <Text size="sm" color="dimmed">
                Select a draft from the sidebar or create a new one to get started.
              </Text>
            </Box>
          ) : markdownView === 'preview' ? (
            <ScrollArea sx={{ height: '100%' }}>
              <Box px="lg" py="md" sx={{ maxWidth: 800, margin: '0 auto' }}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {editorContent || '*No content yet*'}
                </ReactMarkdown>
              </Box>
            </ScrollArea>
          ) : (
            <Box sx={{ height: '100%' }}>
              {selectedKind === 'text' || selectedKind === 'markdown' ? (
                <>
                  {renderPreviewHints()}
                  <Box sx={{ height: 'calc(100% - 140px)' }}>
                    <Textarea
                      value={editorContent}
                      onChange={(e) => setEditorContent(e.target.value)}
                      placeholder={`Write your ${PLATFORM_LABELS[selectedPlatform]} post...`}
                      styles={{
                        root: { height: '100%' },
                        wrapper: { height: '100%' },
                        input: PAGE_EDITOR_DARK_INPUT_STYLE,
                      }}
                      autosize={false}
                    />
                  </Box>
                </>
              ) : null}
            </Box>
          )}
        </Box>

        {/* Session panel resize handle */}
        {sessionPanelOpen && (
          <Box
            sx={{
              height: 5,
              cursor: 'ns-resize',
              background: isSessionPanelResizing ? theme.colors.blue[3] : '#eef2f7',
              flexShrink: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              '&:hover': { background: theme.colors.blue[3] },
            }}
            onPointerDown={(e: React.PointerEvent) => {
              e.preventDefault();
              setIsSessionPanelResizing(true);
            }}
          >
            <Text size="xs" color="dimmed" sx={{ userSelect: 'none', lineHeight: 1 }}>
              ...
            </Text>
          </Box>
        )}

        {/* Embedded session panel */}
        {sessionPanelOpen && (
          <Box
            sx={{
              flex: `0 0 ${sessionPanelHeight}%`,
              minHeight: 120,
              overflow: 'hidden',
              borderTop: '1px solid #eef2f7',
            }}
          >
            <EmbeddedSessionPanel
              currentLabel={currentDraft || socialProjectPath(`${selectedPlatform}/`)}
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
              onStart={handleStartSession}
              onClose={() => {
                setSessionPanelOpen(false);
                setLiveSessionName(null);
                setWorkflowSessionActive(false);
                setWorkflowExecuteStatus(null);
              }}
              workflowExecuteStatus={workflowExecuteStatus}
              workflowSessionActive={workflowSessionActive}
              continuingWorkflow={continuingWorkflow}
              onContinueWorkflow={handleWorkflowContinue}
            />
          </Box>
        )}
      </Box>

      {/* Calendar modal */}
      <Modal
        opened={calendarModalOpened}
        onClose={resetCalendarForm}
        title={calendarEditItem ? 'Edit Calendar Item' : 'New Calendar Item'}
        size="sm"
      >
        <TextInput
          label="Topic"
          placeholder="What do you want to post about?"
          value={newItemTopic}
          onChange={(e) => setNewItemTopic(e.target.value)}
          mb="sm"
          data-autofocus
        />
        <Select
          label="Platform"
          value={newItemPlatform}
          onChange={(v) => setNewItemPlatform(v as Platform)}
          data={[
            { label: 'LinkedIn', value: 'linkedin' },
            { label: 'X', value: 'x' },
            { label: 'XiaoHongShu', value: 'xiaohongshu' },
          ]}
          mb="sm"
        />
        <TextInput
          label="Scheduled Date"
          type="date"
          value={newItemDate}
          onChange={(e) => setNewItemDate(e.target.value)}
          mb="sm"
        />
        <Select
          label="Status"
          value={newItemStatus}
          onChange={(v) => v && setNewItemStatus(v)}
          data={[
            { label: 'Idea', value: 'idea' },
            { label: 'Scheduled', value: 'scheduled' },
            { label: 'Drafted', value: 'drafted' },
            { label: 'Published', value: 'published' },
          ]}
          mb="sm"
        />
        <TextInput
          label="Draft Path"
          placeholder="workspace/social-media/linkedin/draft-001.md"
          value={newItemDraftPath}
          onChange={(e) => setNewItemDraftPath(e.target.value)}
          mb="sm"
        />
        <Textarea
          label="Notes"
          placeholder="Any ideas or context..."
          value={newItemNotes}
          onChange={(e) => setNewItemNotes(e.target.value)}
          minRows={2}
          mb="md"
        />
        <Group spacing="sm" position="right">
          <Button variant="subtle" onClick={resetCalendarForm}>
            Cancel
          </Button>
          <Button onClick={saveCalendarItem} disabled={!newItemTopic.trim()}>
            {calendarEditItem ? 'Save' : 'Create'}
          </Button>
        </Group>
      </Modal>

      {/* Execute modal */}
      <Modal
        opened={executeOpened}
        onClose={() => setExecuteOpened(false)}
        title={pendingAction?.label || 'Execute'}
        size="md"
      >
        <Radio.Group
          value={executeMode}
          onChange={(v) => setExecuteMode(v as ExecuteMode)}
          label="Execution mode"
          mb="md"
        >
          <Group spacing="xl">
            <Radio value="skill" label="Agent Skill" />
            <Radio value="workflow" label="Workflow" />
          </Group>
        </Radio.Group>

        {executeMode === 'skill' ? (
          <Select
            label="Skill"
            placeholder="Select a skill"
            data={buildExecuteSelectOptions(skillOptions)}
            value={selectedSkill}
            onChange={setSelectedSkill}
            searchable
            clearable
            mb="md"
          />
        ) : (
          <Select
            label="Workflow"
            placeholder="Select a workflow"
            data={buildExecuteSelectOptions(workflowOptions)}
            value={selectedWorkflow}
            onChange={setSelectedWorkflow}
            searchable
            clearable
            mb="md"
          />
        )}

        <Button fullWidth onClick={runAction} color="blue">
          Run
        </Button>
      </Modal>
    </AppShell>
  );
}

export async function getStaticProps({ locale }: GetStaticPropsContext) {
  return {
    props: {
      ...(await serverSideTranslations(locale || 'en', ['common'])),
    },
  };
}
