import React, { useState, useEffect, useCallback, useRef } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { GetStaticPropsContext } from 'next';
import axios from 'axios';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';
import {
  AppShell,
  Header,
  Navbar,
  Text,
  NavLink,
  Divider,
  Select,
  Textarea,
  Button,
  Group,
  useMantineTheme,
  MediaQuery,
  Burger,
  ScrollArea,
  Stack,
  Checkbox,
} from '@mantine/core';
import {
  IconTerminal2,
  IconPlus,
  IconSparkles,
  IconSchool,
  IconBriefcase,
  IconSearch,
  IconChecklist,
  IconCode,
  IconHammer,
  IconRocket,
  IconProgress,
  IconWand,
  IconServer,
  IconCalendar,
  IconPuzzle,
  IconUser,
  IconShieldLock,
  IconBrandDiscord,
  IconVectorBezier2,
  IconVideo,
  IconCamera,
  IconFolderOpen,
  IconHistory,
} from '@tabler/icons-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { apiUrl } from '../libs/api-base';
import { resolveSelectedProvider, setSelectedProvider } from '../libs/llm';
import { useSessionRoots } from '../libs/session-roots';
import ExploreView from '../components/explore/ExploreView';

const API_BASE_URL = apiUrl('/api');
axios.defaults.withCredentials = true;

const isProtectedProcessSession = (sessionName: string): boolean => (
  sessionName.startsWith('sp-engine-') ||
  sessionName.startsWith('sp-webui-')
);

interface LlmProvider {
  id: string;
  name: string;
  models: string[];
  effort_levels: string[];
}

interface ExternalTmuxSession {
  name: string;
  attached: boolean;
  created_at: number;
  windows: number;
  system?: boolean;
}

interface McpServer {
  name: string;
  type: string;
  description?: string;
  instructions?: string;
  system?: boolean;
  disabled?: boolean;
  command?: string;
  args?: string[];
  env?: Record<string, string>;
  url?: string;
  headers?: Record<string, string>;
}

interface McpFormData {
  name: string;
  description: string;
  instructions: string;
  type: string;
  command: string;
  args: string;
  env: [string, string][];
  url: string;
  headers: [string, string][];
  disabled: boolean;
}

interface SkillItem {
  name: string;
  description: string;
  disabled: boolean;
}

interface SkillCategory {
  id: string;
  label: string;
  skills: SkillItem[];
}

interface ScheduleItem {
  id: string;
  name: string;
  skill: string;
  cron: string;
  provider: string;
  enabled: boolean;
}

interface ScheduleFormData {
  name: string;
  skill: string;
  provider: string;
  enabled: boolean;
  frequency: 'daily' | 'weekdays' | 'weekly' | 'monthly';
  hour: number;
  minute: number;
  weekday: number;
  monthday: number;
}

type ExtensionType = 'prompt' | 'skill' | 'script';

interface ExtensionItem {
  dir: string;
  name: string;
  description: string;
  type: ExtensionType;
  version?: string;
  license?: string;
  prompt?: string;
  skill?: string;
  script?: string;
  entrypoint?: string;
  installed?: boolean;
}

const EMPTY_MCP_FORM: McpFormData = {
  name: '', description: '', instructions: '', type: 'stdio', command: '', args: '', env: [['', '']],
  url: '', headers: [['', '']], disabled: false,
};

type ActiveView =
  | 'explore'
  | 'home'
  | 'live-terminal'
  | 'learning'
  | 'projects'
  | 'research'
  | 'tasks'
  | 'media'
  | 'development'
  | 'processes'
  | 'discord-bot'
  | 'skills'
  | 'mcp-servers'
  | 'schedule'
  | 'extensions'
  | 'ai-security'
  | 'profile';

type LiveSessionMode = 'llm' | 'shell';

interface SecurityFlags {
  sandbox: boolean;
  auto: boolean;
  network: boolean;
}

type ProviderSecurityMap = Record<string, SecurityFlags>;

interface SecuritySettings {
  security: {
    schedules: SecurityFlags;
    newSession: SecurityFlags;
    remoteBot: SecurityFlags;
    devSwarm: SecurityFlags;
    skillAgent: ProviderSecurityMap;
  };
}

type FixedSecuritySection = 'schedules' | 'newSession' | 'remoteBot' | 'devSwarm';
type NextNodeTrigger = 'auto_continue' | 'start_by_prompt';

interface WorkflowExecuteStatus {
  status: string;
  error?: string;
  next_node_trigger?: NextNodeTrigger;
  waiting_for_continue?: boolean;
}

const SECURITY_SECTION_DEFS: { key: FixedSecuritySection; label: string; defaults: SecurityFlags }[] = [
  { key: 'schedules', label: 'Schedules', defaults: { sandbox: true, auto: true, network: true } },
  { key: 'newSession', label: 'New Session', defaults: { sandbox: false, auto: false, network: true } },
  { key: 'remoteBot', label: 'Remote Bot', defaults: { sandbox: true, auto: true, network: false } },
  { key: 'devSwarm', label: 'Dev Swarm', defaults: { sandbox: true, auto: true, network: true } },
];

interface EnvSafeguardStatus {
  enabled: boolean;
  exists: boolean;
  reason?: string;
}

export default function HomePage() {
  const router = useRouter();
  const theme = useMantineTheme();
  const isDevMode = process.env.NODE_ENV === 'development';
  const [opened, setOpened] = useState(false);
  const [activeView, setActiveView] = useState<ActiveView>('explore');
  const [promptText, setPromptText] = useState('');
  const [newSessionWorkflow, setNewSessionWorkflow] = useState<string | null>(null);
  const [llmProviders, setLlmProviders] = useState<LlmProvider[]>([]);
  const [llmProvider, setLlmProvider] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [selectedEffort, setSelectedEffort] = useState<string | null>(null);
  const [liveSessionName, setLiveSessionName] = useState<string | null>(null);
  const [liveSessionMode, setLiveSessionMode] = useState<LiveSessionMode>('llm');
  const [liveSessionPath, setLiveSessionPath] = useState<string>('');
  const [startingSession, setStartingSession] = useState(false);
  const startingShellRef = useRef(false);
  const [externalSessions, setExternalSessions] = useState<ExternalTmuxSession[]>([]);
  const [activeProcessSession, setActiveProcessSession] = useState<string | null>(null);
  const [loadingExternalSessions, setLoadingExternalSessions] = useState(false);
  const [mcpServers, setMcpServers] = useState<McpServer[]>([]);
  const [mcpEditing, setMcpEditing] = useState<string | null>(null);
  const [mcpForm, setMcpForm] = useState<McpFormData>({ ...EMPTY_MCP_FORM });
  const [mcpSaving, setMcpSaving] = useState(false);
  const [mcpSyncing, setMcpSyncing] = useState(false);
  const [mcpSyncOutput, setMcpSyncOutput] = useState('');
  const [mcpError, setMcpError] = useState('');
  const [skillCategories, setSkillCategories] = useState<SkillCategory[]>([]);
  const [skillDisabled, setSkillDisabled] = useState<Set<string>>(new Set());
  const [skillSaving, setSkillSaving] = useState(false);
  const [skillSaveOutput, setSkillSaveOutput] = useState('');
  const [skillActiveTab, setSkillActiveTab] = useState('all');
  const [skillSearchText, setSkillSearchText] = useState('');
  const [skillAppliedSearch, setSkillAppliedSearch] = useState('');
  const [skillSearchFocused, setSkillSearchFocused] = useState(false);
  const [skillSubScreen, setSkillSubScreen] = useState<null | { mode: 'use' | 'view' | 'edit'; skillName: string; categoryId: string; createSkill?: boolean }>(null);
  const [skillContent, setSkillContent] = useState('');
  const [skillUsePrompt, setSkillUsePrompt] = useState('');
  const [skillEditSaving, setSkillEditSaving] = useState(false);
  const [skillEditOutput, setSkillEditOutput] = useState('');
  const [schedules, setSchedules] = useState<ScheduleItem[]>([]);
  const [scheduleEditing, setScheduleEditing] = useState<null | string>(null);
  const [scheduleForm, setScheduleForm] = useState<ScheduleFormData>({
    name: '', skill: '', provider: '', enabled: true,
    frequency: 'daily', hour: 9, minute: 0, weekday: 1, monthday: 1,
  });
  const [scheduleSaving, setScheduleSaving] = useState(false);
  const [scheduleError, setScheduleError] = useState('');
  const [scheduleSkillFocused, setScheduleSkillFocused] = useState(false);
  const [scheduleProviderFocused, setScheduleProviderFocused] = useState(false);
  const [extensions, setExtensions] = useState<ExtensionItem[]>([]);
  const [extensionsLoading, setExtensionsLoading] = useState(false);
  const [extensionsError, setExtensionsError] = useState('');
  const [extensionActionLoading, setExtensionActionLoading] = useState<Record<string, string>>({});
  const [extensionActionOutput, setExtensionActionOutput] = useState<Record<string, string>>({});
  const [securitySettings, setSecuritySettings] = useState<SecuritySettings>({
    security: {
      schedules: { sandbox: true, auto: true, network: true },
      newSession: { sandbox: false, auto: false, network: true },
      remoteBot: { sandbox: true, auto: true, network: false },
      devSwarm: { sandbox: true, auto: true, network: true },
      skillAgent: {},
    },
  });
  const [securitySaving, setSecuritySaving] = useState(false);
  const [envSafeguardEnabled, setEnvSafeguardEnabled] = useState(false);
  const [envSafeguardBusy, setEnvSafeguardBusy] = useState(false);
  const [envSafeguardMessage, setEnvSafeguardMessage] = useState('');
  const [newSessionSandbox, setNewSessionSandbox] = useState(false);
  const [newSessionAuto, setNewSessionAuto] = useState(false);
  const [newSessionNetwork, setNewSessionNetwork] = useState(true);
  const [newSessionNativeTerminal, setNewSessionNativeTerminal] = useState(false);
  const [workflowSessionActive, setWorkflowSessionActive] = useState(false);
  const [workflowExecuteStatus, setWorkflowExecuteStatus] = useState<WorkflowExecuteStatus | null>(null);
  const [newSessionNextNodeTrigger, setNewSessionNextNodeTrigger] = useState<NextNodeTrigger>('auto_continue');
  const [newSessionWorkflowResumeAvailable, setNewSessionWorkflowResumeAvailable] = useState(false);
  const [newSessionWorkflowResume, setNewSessionWorkflowResume] = useState(false);
  const [continuingWorkflow, setContinuingWorkflow] = useState(false);
  const [defaultLlmProvider, setDefaultLlmProvider] = useState<string>('');
  const [defaultDoctorProvider, setDefaultDoctorProvider] = useState<string>('');
  const [profileData, setProfileData] = useState<Record<string, string>>({});
  const terminalQueryLaunchRef = useRef<string>('');

  // Discord Bot state
  const [discordStatus, setDiscordStatus] = useState<{ has_token: boolean; connected: boolean; bot_name: string | null; guild_count: number } | null>(null);
  const [discordSessions, setDiscordSessions] = useState<{ channel_id: string; channel_name: string; is_dm: boolean; message_count: number; buffer_size: number; has_summary: boolean }[]>([]);
  const [discordActiveTab, setDiscordActiveTab] = useState<string | null>(null);
  const [discordHistory, setDiscordHistory] = useState<{ role: string; message: string; type?: string }[]>([]);
  const [discordLoadingHistory, setDiscordLoadingHistory] = useState(false);
  const [discordTokenInput, setDiscordTokenInput] = useState('');
  const [discordSavingToken, setDiscordSavingToken] = useState(false);
  const [discordError, setDiscordError] = useState('');
  const [discordKeysSafeGuard, setDiscordKeysSafeGuard] = useState(false);
  const [discordAuthRequired, setDiscordAuthRequired] = useState(false);
  const [discordAuthTokenInput, setDiscordAuthTokenInput] = useState('');
  const [discordAuthSaving, setDiscordAuthSaving] = useState(false);
  const [discordAuthError, setDiscordAuthError] = useState('');
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileAddField, setProfileAddField] = useState('');
  const [profileError, setProfileError] = useState('');
  const [timezoneList, setTimezoneList] = useState<string[]>([]);
  const [timezoneFocused, setTimezoneFocused] = useState(false);
  const {
    sessionRootOptions,
    hasSessionWorktrees,
    selectedSessionPath,
    setSelectedSessionPath,
  } = useSessionRoots();

  const fetchLlmProviders = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/llm/providers`);
      const providers: LlmProvider[] = res.data.providers || [];
      const serverDefault: string = res.data.default || '';
      const doctorDefault: string = res.data.doctor_default || '';
      setLlmProviders(providers);
      setDefaultLlmProvider(serverDefault);
      setDefaultDoctorProvider(doctorDefault);
      const defaultId = resolveSelectedProvider(providers, serverDefault, 'gemini');
      if (defaultId) {
        setSelectedProvider(defaultId);
      }
      setLlmProvider(defaultId);
      const defaultProvider = providers.find((p) => p.id === defaultId);
      setSelectedModel(defaultProvider?.models?.[0] || null);
      setSelectedEffort(null);
    } catch (err) {
      console.error('Failed to fetch LLM providers:', err);
    }
  }, []);

  const fetchExternalSessions = useCallback(async (quiet: boolean = false) => {
    if (!quiet) setLoadingExternalSessions(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/terminal/tmux/external-sessions`);
      const sessions: ExternalTmuxSession[] = res.data?.sessions || [];
      setExternalSessions(sessions);
      setActiveProcessSession((prev) => {
        if (prev && sessions.some((s) => s.name === prev)) return prev;
        return null;
      });
    } catch (err) {
      console.error('Failed to fetch external tmux sessions:', err);
    } finally {
      if (!quiet) setLoadingExternalSessions(false);
    }
  }, []);

  const fetchMcpServers = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/config/mcp-servers`);
      setMcpServers(res.data?.servers || []);
      setMcpError('');
    } catch (err: any) {
      setMcpError(err?.response?.data?.error || 'Failed to load MCP servers');
    }
  }, []);

  const fetchSkills = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/config/skills`);
      const cats: SkillCategory[] = res.data?.categories || [];
      setSkillCategories(cats);
      const disabled = new Set<string>();
      for (const cat of cats) {
        for (const skill of cat.skills) {
          if (skill.disabled) disabled.add(skill.name);
        }
      }
      setSkillDisabled(disabled);
    } catch (err) {
      console.error('Failed to fetch skills:', err);
    }
  }, []);

  const fetchSchedules = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/config/schedules`);
      setSchedules(res.data?.schedules || []);
    } catch (err) {
      console.error('Failed to fetch schedules:', err);
    }
  }, []);

  const fetchExtensions = useCallback(async () => {
    setExtensionsLoading(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/config/extensions`);
      setExtensions(res.data?.extensions || []);
      setExtensionsError('');
    } catch (err: any) {
      setExtensions([]);
      setExtensionsError(err?.response?.data?.error || 'Failed to load extensions');
    } finally {
      setExtensionsLoading(false);
    }
  }, []);

  const fetchSecuritySettings = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/config/settings`);
      const data: SecuritySettings = res.data;
      const normalizedSecurity = {
        schedules: { ...SECURITY_SECTION_DEFS[0].defaults, ...(data.security?.schedules || {}) },
        newSession: { ...SECURITY_SECTION_DEFS[1].defaults, ...(data.security?.newSession || {}) },
        remoteBot: { ...SECURITY_SECTION_DEFS[2].defaults, ...(data.security?.remoteBot || {}) },
        devSwarm: { ...SECURITY_SECTION_DEFS[3].defaults, ...(data.security?.devSwarm || {}) },
        skillAgent: data.security?.skillAgent || {},
      };
      setSecuritySettings({ security: normalizedSecurity });
      if (data.security?.newSession) {
        setNewSessionSandbox(data.security.newSession.sandbox ?? false);
        setNewSessionAuto(data.security.newSession.auto ?? false);
        setNewSessionNetwork(data.security.newSession.network ?? true);
      }
    } catch (err) {
      console.error('Failed to fetch security settings:', err);
    }
  }, []);

  const fetchEnvSafeguardStatus = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/config/env-safeguard-status`);
      const data: EnvSafeguardStatus = res.data || { enabled: false, exists: false };
      setEnvSafeguardEnabled(Boolean(data.enabled));
      if (data.enabled) {
        setEnvSafeguardMessage('Safe guard already enabled for config/.env.');
      } else if (!data.exists) {
        setEnvSafeguardMessage('config/.env not found. Create it before enabling safe guard.');
      } else {
        setEnvSafeguardMessage('Safe guard is not enabled.');
      }
    } catch (err: any) {
      setEnvSafeguardEnabled(false);
      setEnvSafeguardMessage(err?.response?.data?.error || 'Failed to check env safe guard status.');
    }
  }, []);

  const fetchProfile = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/config/profile`);
      if (res.data && typeof res.data === 'object') {
        const data: Record<string, string> = {};
        for (const [k, v] of Object.entries(res.data)) {
          data[k] = String(v ?? '');
        }
        setProfileData(data);
      }
    } catch (err) {
      console.error('Failed to fetch profile:', err);
    }
  }, []);

  const detectValidIanaTimezone = useCallback((): string => {
    try {
      const detected = Intl.DateTimeFormat().resolvedOptions().timeZone || '';
      if (!detected) return '';
      if (timezoneList.length > 0) {
        return timezoneList.includes(detected) ? detected : '';
      }
      if (typeof Intl.supportedValuesOf === 'function') {
        return Intl.supportedValuesOf('timeZone').includes(detected) ? detected : '';
      }
      return detected.includes('/') ? detected : '';
    } catch {
      return '';
    }
  }, [timezoneList]);

  const cronToFormData = (cron: string): Partial<ScheduleFormData> => {
    const parts = cron.trim().split(/\s+/);
    if (parts.length !== 5) return {};
    const [minStr, hourStr, dom, , dow] = parts;
    const minute = parseInt(minStr, 10);
    const hour = parseInt(hourStr, 10);
    if (isNaN(minute) || isNaN(hour)) return {};
    if (dom !== '*' && dow === '*') {
      return { frequency: 'monthly', hour, minute, monthday: parseInt(dom, 10) || 1 };
    }
    if (dow === '1-5') return { frequency: 'weekdays', hour, minute };
    if (dow === '*') return { frequency: 'daily', hour, minute };
    const wd = parseInt(dow, 10);
    if (!isNaN(wd)) return { frequency: 'weekly', hour, minute, weekday: wd };
    return { frequency: 'daily', hour, minute };
  };

  const formDataToCron = (form: ScheduleFormData): string => {
    const { frequency, hour, minute, weekday, monthday } = form;
    switch (frequency) {
      case 'daily': return `${minute} ${hour} * * *`;
      case 'weekdays': return `${minute} ${hour} * * 1-5`;
      case 'weekly': return `${minute} ${hour} * * ${weekday}`;
      case 'monthly': return `${minute} ${hour} ${monthday} * *`;
      default: return `${minute} ${hour} * * *`;
    }
  };

  const cronToHumanReadable = (cron: string): string => {
    const parts = cron.trim().split(/\s+/);
    if (parts.length !== 5) return cron;
    const [minStr, hourStr, dom, , dow] = parts;
    const minute = parseInt(minStr, 10);
    const hour = parseInt(hourStr, 10);
    if (isNaN(minute) || isNaN(hour)) return cron;
    const time = `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
    const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    if (dom !== '*' && dow === '*') {
      const d = parseInt(dom, 10);
      const suffix = d === 1 ? 'st' : d === 2 ? 'nd' : d === 3 ? 'rd' : 'th';
      return `Monthly on the ${d}${suffix} at ${time}`;
    }
    if (dow === '1-5') return `Weekdays at ${time}`;
    if (dow === '*') return `Every day at ${time}`;
    const wd = parseInt(dow, 10);
    if (!isNaN(wd) && wd >= 0 && wd <= 6) return `Every ${dayNames[wd]} at ${time}`;
    return cron;
  };

  useEffect(() => {
    const runBootstrap = async () => {
      await fetchLlmProviders();
      await fetchSecuritySettings();
    };

    void runBootstrap();
  }, [fetchLlmProviders, fetchSecuritySettings]);

  useEffect(() => {
    if (activeView !== 'processes') return;
    void fetchExternalSessions();
    const intervalId = window.setInterval(() => {
      void fetchExternalSessions(true);
    }, 5000);
    return () => window.clearInterval(intervalId);
  }, [activeView, fetchExternalSessions]);

  useEffect(() => {
    if (!workflowSessionActive) return;
    const poll = async () => {
      try {
        const res = await axios.get(`${API_BASE_URL}/workflows/execute/status`, { withCredentials: true });
        const st = res.data as WorkflowExecuteStatus;
        setWorkflowExecuteStatus(st);
        if (st.status === 'finished' || st.status === 'error' || st.status === 'terminated') {
          setWorkflowSessionActive(false);
        }
      } catch {
        // ignore polling errors
      }
    };
    void poll();
    const intervalId = window.setInterval(() => void poll(), 3000);
    return () => window.clearInterval(intervalId);
  }, [workflowSessionActive]);

  useEffect(() => {
    if (activeView === 'mcp-servers') {
      void fetchMcpServers();
    }
  }, [activeView, fetchMcpServers]);

  useEffect(() => {
    if (activeView === 'skills') {
      void fetchSkills();
    }
  }, [activeView, fetchSkills]);

  useEffect(() => {
    if (activeView === 'schedule') {
      void fetchSchedules();
      void fetchSkills();
    }
  }, [activeView, fetchSchedules, fetchSkills]);

  useEffect(() => {
    if (activeView === 'extensions') {
      void fetchExtensions();
    }
  }, [activeView, fetchExtensions]);

  useEffect(() => {
    if (activeView === 'ai-security') {
      void fetchSecuritySettings();
      void fetchEnvSafeguardStatus();
    }
  }, [activeView, fetchSecuritySettings, fetchEnvSafeguardStatus]);

  useEffect(() => {
    if (activeView === 'profile') {
      void fetchProfile();
      if (timezoneList.length === 0) {
        axios.get(`${API_BASE_URL}/config/timezones`).then((res) => {
          setTimezoneList(res.data?.timezones || []);
        }).catch(() => {});
      }
    }
  }, [activeView, fetchProfile]);

  useEffect(() => {
    if (activeView !== 'profile') return;
    setProfileData((prev) => {
      const current = prev.timezone || '';
      if (current.trim()) return prev;
      const detected = detectValidIanaTimezone();
      if (!detected) return prev;
      return { ...prev, timezone: detected };
    });
  }, [activeView, detectValidIanaTimezone]);

  const handleStart = useCallback(async () => {
    const trimmedPrompt = promptText.trim();
    if (!trimmedPrompt || startingSession) return;
    const provider = llmProvider || 'gemini';
    setStartingSession(true);
    try {
      const endpoint = newSessionWorkflow ? `${API_BASE_URL}/workflows/execute` : `${API_BASE_URL}/terminal/tmux/create`;
      const payload = newSessionWorkflow
        ? {
            workflow: newSessionWorkflow,
            prompt: trimmedPrompt,
            path: selectedSessionPath || undefined,
            sandbox: newSessionSandbox,
            auto: newSessionAuto,
            network: newSessionNetwork,
            native_terminal: newSessionNativeTerminal,
            next_node_trigger: newSessionNextNodeTrigger,
            resume: newSessionWorkflowResume,
          }
        : {
            provider_id: provider,
            prompt: trimmedPrompt,
            path: selectedSessionPath || undefined,
            sandbox: newSessionSandbox,
            auto: newSessionAuto,
            network: newSessionNetwork,
            native_terminal: newSessionNativeTerminal,
            model: selectedModel || undefined,
            effort: selectedEffort || undefined,
          };
      const res = await axios.post(endpoint, payload);
      const sessionName: string | undefined = res.data?.session?.name;
      const nativeOpened: boolean = Boolean(res.data?.native_terminal?.opened);
      const nativeError: string = String(res.data?.native_terminal?.error || '');
      if (sessionName) {
        if (newSessionNativeTerminal) {
          setLiveSessionName(null);
          setActiveView('home');
          if (!nativeOpened) {
            const details = nativeError ? `: ${nativeError}` : '';
            window.alert(`Native terminal did not open${details}. You can attach manually with tmux session ${sessionName}.`);
          }
        } else {
          setLiveSessionName(sessionName);
          setLiveSessionMode('llm');
          setLiveSessionPath(String(res.data?.session?.cwd || selectedSessionPath || ''));
          setActiveView('live-terminal');
        }
        if (newSessionWorkflow) {
          setWorkflowSessionActive(true);
          setWorkflowExecuteStatus(null);
        }
        setPromptText('');
        setNewSessionWorkflow(null);
        setNewSessionNextNodeTrigger('auto_continue');
        setNewSessionWorkflowResumeAvailable(false);
        setNewSessionWorkflowResume(false);
      }
    } catch (err) {
      console.error('Failed to start session:', err);
    } finally {
      setStartingSession(false);
    }
  }, [
    llmProvider,
    newSessionAuto,
    newSessionNativeTerminal,
    newSessionNetwork,
    newSessionNextNodeTrigger,
    newSessionSandbox,
    newSessionWorkflow,
    newSessionWorkflowResume,
    promptText,
    selectedModel,
    selectedEffort,
    selectedSessionPath,
    startingSession,
  ]);

  const handleStartShellTerminal = useCallback(async (pathOverride?: string) => {
    if (startingShellRef.current) return;
    const requestedPath = (pathOverride ?? '').trim();
    startingShellRef.current = true;
    setStartingSession(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/terminal/tmux/create`, {
        session_type: 'shell',
        path: requestedPath || undefined,
      });
      const sessionName: string | undefined = res.data?.session?.name;
      if (sessionName) {
        setLiveSessionName(sessionName);
        setLiveSessionMode('shell');
        setLiveSessionPath(String(res.data?.session?.cwd || requestedPath || ''));
        setActiveView('live-terminal');
      }
    } catch (err) {
      console.error('Failed to start terminal session:', err);
    } finally {
      startingShellRef.current = false;
      setStartingSession(false);
    }
  }, []);

  useEffect(() => {
    if (!router.isReady) return;

    const {
      prompt,
      new_session,
      new_terminal,
      view,
      workflow,
      next_node_trigger,
      resume,
      resume_available,
      path,
      ...restQuery
    } = router.query;

    if (new_session === 'true' && prompt) {
      setPromptText(prompt as string);
      setSelectedSessionPath(typeof path === 'string' ? path : '');
      setNewSessionWorkflow(typeof workflow === 'string' && workflow ? workflow : null);
      setNewSessionNextNodeTrigger(next_node_trigger === 'start_by_prompt' ? 'start_by_prompt' : 'auto_continue');
      setNewSessionWorkflowResumeAvailable(resume_available === 'true');
      setNewSessionWorkflowResume(resume === 'true');
      setActiveView('home');
      void router.replace({ pathname: '/', query: restQuery }, undefined, { shallow: true });
      return;
    }

    if (new_terminal === 'true') {
      const requestedPath = typeof path === 'string' ? path : '';
      const launchKey = requestedPath || '__project_root__';
      if (terminalQueryLaunchRef.current === launchKey) return;
      terminalQueryLaunchRef.current = launchKey;
      setActiveView('home');
      void handleStartShellTerminal(requestedPath);
      void router.replace({ pathname: '/', query: restQuery }, undefined, { shallow: true });
      return;
    }

    terminalQueryLaunchRef.current = '';

    if (typeof view === 'string' && view) {
      const validViews: ActiveView[] = [
        'explore', 'home', 'live-terminal', 'learning', 'projects', 'research', 'tasks',
        'development', 'processes', 'discord-bot', 'skills', 'mcp-servers',
        'schedule', 'extensions', 'ai-security', 'profile',
      ];
      if (validViews.includes(view as ActiveView)) {
        setActiveView(view as ActiveView);
      }
    }
  }, [handleStartShellTerminal, router.isReady, router.query, router.replace]);

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

  const handleDetachSession = () => {
    setLiveSessionName(null);
    setLiveSessionMode('llm');
    setLiveSessionPath('');
    setActiveView('home');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      void handleStart();
    }
  };

  const navItems: { label: string; view?: ActiveView; href?: string; icon: React.ReactNode; action?: () => void; dividerBefore?: string; disabled?: boolean; active?: boolean }[] = [
    {
      label: 'Explore',
      href: '/?view=explore',
      view: 'explore',
      icon: <IconSparkles size="1rem" />,
    },
    {
      label: 'New Session',
      dividerBefore: '',
      href: '/?view=home',
      view: 'home',
      icon: <IconPlus size="1rem" />,
      action: () => {
        if (activeView === 'live-terminal') {
          handleDetachSession();
        } else if (activeView !== 'home') {
          setActiveView('home');
        }
        void router.push('/?view=home');
      },
      disabled: activeView === 'home',
    },
    { label: 'Live Sessions', href: '/terminals', icon: <IconTerminal2 size="1rem" />, action: () => { void router.push('/terminals'); } },
    { label: 'Session Histories', href: '/terminal-histories', icon: <IconHistory size="1rem" />, action: () => { void router.push('/terminal-histories'); } },
    { dividerBefore: 'Workspace', label: 'Learning', href: '/courses', icon: <IconSchool size="1rem" />, action: () => router.push('/courses') },
    { label: 'Vibe Coding', href: '/vibe-coding', icon: <IconBriefcase size="1rem" />, action: () => router.push('/vibe-coding') },
    { label: 'Research', href: '/research', icon: <IconSearch size="1rem" />, action: () => router.push('/research') },
    { label: 'Tasks', href: '/tasks', icon: <IconChecklist size="1rem" />, action: () => router.push('/tasks') },
    { label: 'Media', href: '/media', icon: <IconVideo size="1rem" />, action: () => router.push('/media') },
    { label: 'File Manager', href: '/file-manager', icon: <IconFolderOpen size="1rem" />, action: () => router.push('/file-manager') },
    { dividerBefore: 'Skill Pilot', label: 'Development', href: '/skill-pilot-development', icon: <IconCode size="1rem" />, action: () => router.push('/skill-pilot-development') },
    { label: 'Codeware', href: '/codeware', icon: <IconHammer size="1rem" />, action: () => router.push('/codeware') },
    { dividerBefore: 'Commercial Project', label: 'Dev Swarm', href: '/dev-swarm', icon: <IconRocket size="1rem" />, action: () => router.push('/dev-swarm') },
    { dividerBefore: '', label: 'Processes', href: '/?view=processes', view: 'processes', icon: <IconProgress size="1rem" /> },
    { label: 'Discord Bot', href: '/?view=discord-bot', view: 'discord-bot', icon: <IconBrandDiscord size="1rem" /> },
    { label: 'Live Avatar', href: '/live-avatar', icon: <IconVideo size="1rem" />, action: () => router.push('/live-avatar') },
    { label: 'Security Cameras', href: '/cameras', icon: <IconCamera size="1rem" />, action: () => router.push('/cameras') },
    { dividerBefore: '', label: 'Skills', href: '/?view=skills', view: 'skills', icon: <IconWand size="1rem" /> },
    { label: 'Workflows', href: '/workflows', icon: <IconVectorBezier2 size="1rem" />, action: () => router.push('/workflows') },
    { label: 'MCP Servers', href: '/?view=mcp-servers', view: 'mcp-servers', icon: <IconServer size="1rem" /> },
    { label: 'Schedules', href: '/?view=schedule', view: 'schedule', icon: <IconCalendar size="1rem" /> },
    { label: 'Extensions', href: '/?view=extensions', view: 'extensions', icon: <IconPuzzle size="1rem" /> },
    { label: 'AI & Security', href: '/?view=ai-security', view: 'ai-security', icon: <IconShieldLock size="1rem" /> },
    { label: 'Profile', href: '/?view=profile', view: 'profile', icon: <IconUser size="1rem" /> },
  ];

  const handleNavItemClick = (event: React.MouseEvent, item: typeof navItems[number]) => {
    if (item.disabled) return;
    if (event.shiftKey && item.href) {
      window.open(item.href, '_blank', 'noopener,noreferrer');
      setOpened(false);
      return;
    }
    if (activeView === 'live-terminal' && (item.view || item.action)) {
      setLiveSessionName(null);
    }
    if (item.action) {
      item.action();
    } else if (item.view) {
      setActiveView(item.view);
    }
    setOpened(false);
  };

  const renderNavItems = () => {
    return navItems.map((item, idx) => {
      const elements: React.ReactNode[] = [];

      if (item.dividerBefore !== undefined) {
        elements.push(
          <Divider
            key={`divider-${idx}`}
            my="xs"
            label={item.dividerBefore || undefined}
            labelPosition="center"
          />
        );
      }

      const isActive = item.active ?? (item.view ? activeView === item.view : false);

      elements.push(
        <NavLink
          key={item.label}
          label={item.label}
          icon={item.icon}
          active={isActive}
          disabled={item.disabled}
          styles={item.disabled ? { root: { opacity: 0.5, cursor: 'default' } } : undefined}
          onClick={(event) => handleNavItemClick(event, item)}
        />
      );

      return elements;
    });
  };

  const renderHomeView = () => (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100%',
      padding: '40px 20px',
      position: 'relative',
    }}>
      <div style={{ position: 'absolute', top: 20, right: 20 }}>
        <Button
          size="sm"
          variant="subtle"
          leftIcon={<IconPlus size="1rem" />}
          onClick={() => void handleStartShellTerminal()}
          loading={startingSession}
          aria-label="New terminal"
        >
          Terminal
        </Button>
      </div>
      <Stack spacing="md" style={{ width: '100%', maxWidth: 600 }}>
        <div>
          <Text size={36} weight={800} mb={8}>Skill Pilot</Text>
          <Text size="lg" color="dimmed" italic>
            Do anything first, then learn anything you want
          </Text>
        </div>
        {hasSessionWorktrees && (
          <Select
            label="Worktree"
            placeholder="Choose where to start"
            value={selectedSessionPath || null}
            onChange={(value) => setSelectedSessionPath(value || '')}
            data={sessionRootOptions.map((root) => ({ value: root.value, label: root.label }))}
          />
        )}
        <Textarea
          placeholder="What would you like to do?"
          value={promptText}
          onChange={(e) => setPromptText(e.currentTarget.value)}
          onKeyDown={handleKeyDown}
          autosize
          minRows={3}
          maxRows={10}
          size="md"
        />
        {!newSessionWorkflow && (
          <Group spacing="md" grow>
            <Select
              label="Model"
              placeholder="Default model"
              value={selectedModel}
              onChange={(value) => setSelectedModel(value || null)}
              data={(llmProviders.find((p) => p.id === llmProvider)?.models || []).map((m) => ({ value: m, label: m }))}
              size="sm"
              clearable
            />
            <Select
              label="Effort"
              placeholder="Default effort"
              value={selectedEffort}
              onChange={(value) => setSelectedEffort(value || null)}
              data={(llmProviders.find((p) => p.id === llmProvider)?.effort_levels || []).map((e) => ({ value: e, label: e }))}
              size="sm"
              clearable
              disabled={!llmProvider || (llmProviders.find((p) => p.id === llmProvider)?.effort_levels || []).length === 0}
            />
          </Group>
        )}
        {newSessionWorkflow && (
          <>
            <Text size="sm" color="dimmed" align="center">
              Workflow mode: providers are controlled by the workflow nodes for {`core/workflows/${newSessionWorkflow}`}
            </Text>
            <Select
              label="Next Node Trigger"
              value={newSessionNextNodeTrigger}
              onChange={(value) => setNewSessionNextNodeTrigger((value as NextNodeTrigger) || 'auto_continue')}
              data={[
                { value: 'auto_continue', label: 'Auto continue' },
                { value: 'start_by_prompt', label: 'Start by prompt' },
              ]}
            />
          </>
        )}
        {workflowExecuteStatus && workflowSessionActive && (
          <Text
            size="sm"
            align="center"
            color={workflowExecuteStatus.status === 'error' || workflowExecuteStatus.status === 'terminated' ? 'red' : 'dimmed'}
          >
            Workflow status: {workflowExecuteStatus.status}
            {workflowExecuteStatus.error ? ` - ${workflowExecuteStatus.error}` : ''}
          </Text>
        )}
        {workflowExecuteStatus && !workflowSessionActive && (workflowExecuteStatus.status === 'finished' || workflowExecuteStatus.status === 'error' || workflowExecuteStatus.status === 'terminated') && (
          <Text
            size="sm"
            align="center"
            color={workflowExecuteStatus.status === 'finished' ? 'green' : 'red'}
          >
            Workflow {workflowExecuteStatus.status}
            {workflowExecuteStatus.error ? ` - ${workflowExecuteStatus.error}` : ''}
          </Text>
        )}
        <Group position="center" spacing="lg">
          <Checkbox
            label="Sandbox"
            checked={newSessionSandbox}
            onChange={(e) => setNewSessionSandbox(e.currentTarget.checked)}
            size="xs"
          />
          <Checkbox
            label="Auto Run (Yolo)"
            checked={newSessionAuto}
            onChange={(e) => setNewSessionAuto(e.currentTarget.checked)}
            size="xs"
          />
          <Checkbox
            label="Network Access"
            checked={newSessionNetwork}
            onChange={(e) => setNewSessionNetwork(e.currentTarget.checked)}
            size="xs"
          />
          <Checkbox
            label="Native Terminal"
            checked={newSessionNativeTerminal}
            onChange={(e) => setNewSessionNativeTerminal(e.currentTarget.checked)}
            size="xs"
          />
        </Group>
        <Group position="center" spacing="md" align="center">
            <Button size="md" onClick={() => void handleStart()} disabled={!promptText.trim() || startingSession} loading={startingSession}>
                Start
            </Button>
            {newSessionWorkflow && newSessionWorkflowResumeAvailable && (
              <Checkbox
                label="Resume Workflow"
                checked={newSessionWorkflowResume}
                onChange={(e) => setNewSessionWorkflowResume(e.currentTarget.checked)}
                size="xs"
              />
            )}
            {workflowSessionActive && workflowExecuteStatus?.waiting_for_continue && (
              <Button
                size="md"
                variant="light"
                onClick={() => void handleWorkflowContinue()}
                loading={continuingWorkflow}
              >
                Continue Next Node
              </Button>
            )}
        </Group>
      </Stack>
    </div>
  );

  const renderLiveTerminalView = () => (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '12px 16px 16px 16px' }}>
      {liveSessionMode === 'shell' && (
        <div style={{ padding: '8px 12px', marginBottom: 8, borderRadius: 6, background: '#eef6ff', color: '#1d4ed8', fontSize: 13 }}>
          Web terminal session{liveSessionPath ? ` · ${liveSessionPath}` : ''}
        </div>
      )}
      {liveSessionMode === 'llm' && workflowExecuteStatus && (workflowExecuteStatus.status === 'error' || workflowExecuteStatus.status === 'terminated') && (
        <div style={{ padding: '8px 12px', marginBottom: 8, borderRadius: 6, background: '#fde8e8', color: '#c0392b', fontSize: 13 }}>
          Workflow execution failed{workflowExecuteStatus.error ? `: ${workflowExecuteStatus.error}` : ''}
        </div>
      )}
      {liveSessionMode === 'llm' && workflowExecuteStatus && workflowExecuteStatus.status === 'finished' && (
        <div style={{ padding: '8px 12px', marginBottom: 8, borderRadius: 6, background: '#e8fde8', color: '#27ae60', fontSize: 13 }}>
          Workflow completed
        </div>
      )}
      <div style={{ flex: 1, position: 'relative' }}>
        {liveSessionName && (
          <iframe
            key={liveSessionName}
            src={`/terminal?session=${encodeURIComponent(liveSessionName)}`}
            style={{
              width: '100%',
              height: '100%',
              border: 'none',
              borderRadius: 8,
            }}
          />
        )}
      </div>
    </div>
  );

  // ── Discord Bot helpers ──

  const fetchDiscordAuthStatus = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/auth/status`, { withCredentials: true });
      const authenticated = !!res.data?.authenticated;
      setDiscordAuthRequired(!authenticated);
      if (authenticated) {
        setDiscordAuthError('');
      }
      return authenticated;
    } catch {
      setDiscordAuthRequired(true);
      return false;
    }
  }, []);

  const fetchDiscordStatus = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/discord/status`, { withCredentials: true });
      setDiscordStatus(res.data);
      setDiscordKeysSafeGuard(!!res.data?.keys_safe_guard_enabled);
      setDiscordAuthRequired(false);
    } catch (err: any) {
      if (err?.response?.status === 401) {
        setDiscordAuthRequired(true);
      }
      setDiscordStatus(null);
    }
  }, []);

  const fetchDiscordSessions = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/discord/sessions`, { withCredentials: true });
      setDiscordSessions(res.data.sessions || []);
      setDiscordAuthRequired(false);
    } catch (err: any) {
      if (err?.response?.status === 401) {
        setDiscordAuthRequired(true);
      }
      setDiscordSessions([]);
    }
  }, []);

  const createDiscordAuthSession = useCallback(async () => {
    const token = discordAuthTokenInput.trim();
    if (!token) return;
    setDiscordAuthSaving(true);
    setDiscordAuthError('');
    try {
      await axios.post(
        `${API_BASE_URL}/auth/session`,
        { auth_token: token },
        { withCredentials: true },
      );
      setDiscordAuthTokenInput('');
      setDiscordAuthRequired(false);
      void fetchDiscordStatus();
      void fetchDiscordSessions();
    } catch (err: any) {
      setDiscordAuthError(err?.response?.data?.error || 'Failed to authenticate');
      setDiscordAuthRequired(true);
    } finally {
      setDiscordAuthSaving(false);
    }
  }, [discordAuthTokenInput, fetchDiscordSessions, fetchDiscordStatus]);

  const fetchDiscordHistory = useCallback(async (channelId: string) => {
    setDiscordLoadingHistory(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/discord/sessions/${channelId}`, { withCredentials: true });
      setDiscordHistory(res.data.messages || []);
      setDiscordAuthRequired(false);
    } catch (err: any) {
      if (err?.response?.status === 401) {
        setDiscordAuthRequired(true);
      }
      setDiscordHistory([]);
    } finally {
      setDiscordLoadingHistory(false);
    }
  }, []);

  const saveDiscordToken = useCallback(async () => {
    if (!discordTokenInput.trim()) return;
    setDiscordSavingToken(true);
    setDiscordError('');
    try {
      const res = await axios.post(
        `${API_BASE_URL}/discord/token`,
        { token: discordTokenInput.trim() },
        { withCredentials: true },
      );
      setDiscordError('');
      setDiscordTokenInput('');
      alert(res.data.message || 'Token saved.');
      void fetchDiscordStatus();
    } catch (err: any) {
      if (err?.response?.status === 401) {
        setDiscordAuthRequired(true);
      }
      setDiscordError(err?.response?.data?.error || 'Failed to save token');
    } finally {
      setDiscordSavingToken(false);
    }
  }, [discordTokenInput, fetchDiscordStatus]);

  useEffect(() => {
    if (activeView !== 'discord-bot') return;
    void (async () => {
      const authenticated = await fetchDiscordAuthStatus();
      if (!authenticated) return;
      await fetchDiscordStatus();
      await fetchDiscordSessions();
    })();
  }, [activeView, fetchDiscordAuthStatus, fetchDiscordSessions, fetchDiscordStatus]);

  const renderDiscordBotView = () => {
    if (discordAuthRequired) {
      return (
        <div style={{ padding: 16, maxWidth: 600 }}>
          <Text size="lg" weight={700} mb={12}>Discord Bot Authentication</Text>
          <Text size="sm" color="dimmed" mb={16}>
            Enter AUTH_TOKEN from config/.env to access Discord bot APIs.
          </Text>
          <Textarea
            placeholder="Paste AUTH_TOKEN"
            value={discordAuthTokenInput}
            onChange={(e) => setDiscordAuthTokenInput(e.currentTarget.value)}
            minRows={2}
            maxRows={3}
            mb={8}
            styles={{ input: { fontFamily: 'monospace', fontSize: 13 } }}
          />
          {discordAuthError && <Text size="xs" color="red" mb={8}>{discordAuthError}</Text>}
          <Button
            size="sm"
            onClick={() => void createDiscordAuthSession()}
            loading={discordAuthSaving}
            disabled={!discordAuthTokenInput.trim()}
          >
            Authenticate
          </Button>
        </div>
      );
    }

    if (discordStatus === null) {
      return (
        <div style={{ padding: 16 }}>
          <Text size="sm" color="dimmed">Loading Discord bot status...</Text>
        </div>
      );
    }

    // Token not configured — show setup form.
    if (discordStatus && !discordStatus.has_token) {
      return (
        <div style={{ padding: 16, maxWidth: 600 }}>
          <Text size="lg" weight={700} mb={12}>Discord Bot Setup</Text>
          <Text size="sm" color="dimmed" mb={16}>
            No DISCORD_BOT_TOKEN found. Enter your bot token to get started.
          </Text>
          {discordKeysSafeGuard && (
            <Text size="xs" color="blue" mb={12} style={{ background: 'rgba(0,100,255,0.06)', padding: '8px 10px', borderRadius: 6 }}>
              Key Safe Guard is enabled. A system authorization dialog will appear on this machine when you save the token.
            </Text>
          )}
          <Textarea
            placeholder="Paste your Discord bot token here"
            value={discordTokenInput}
            onChange={(e) => setDiscordTokenInput(e.currentTarget.value)}
            minRows={2}
            maxRows={3}
            mb={8}
            styles={{ input: { fontFamily: 'monospace', fontSize: 13 } }}
          />
          {discordError && (
            <pre style={{ fontSize: 12, color: 'red', background: 'rgba(255,0,0,0.05)', padding: '8px 10px', borderRadius: 6, whiteSpace: 'pre-wrap', wordBreak: 'break-word', marginBottom: 8 }}>
              {discordError}
            </pre>
          )}
          <Button
            size="sm"
            onClick={() => void saveDiscordToken()}
            loading={discordSavingToken}
            disabled={!discordTokenInput.trim()}
          >
            Save Token &amp; Connect
          </Button>
        </div>
      );
    }

    // Bot is configured — show status + session tabs.
    return (
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '12px 16px 16px 16px' }}>
        {/* Status bar */}
        <Group position="apart" mb={12}>
          <div>
            <Text size="lg" weight={700}>Discord Bot</Text>
            {discordStatus && (
              <Text size="xs" color={discordStatus.connected ? 'green' : 'orange'}>
                {discordStatus.connected
                  ? `Connected as ${discordStatus.bot_name} · ${discordStatus.guild_count} guild(s)`
                  : 'Token configured but bot is not connected'}
              </Text>
            )}
          </div>
          <button
            type="button"
            onClick={() => { void fetchDiscordStatus(); void fetchDiscordSessions(); }}
            style={{
              border: `1px solid ${theme.colors.gray[3]}`,
              borderRadius: 8,
              padding: '4px 10px',
              background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff',
              fontSize: 12,
              cursor: 'pointer',
            }}
          >
            Refresh
          </button>
        </Group>

        {discordSessions.length === 0 ? (
          <Text size="sm" color="dimmed">No chat sessions found.</Text>
        ) : (
          <div style={{ display: 'flex', flex: 1, gap: 0, overflow: 'hidden', border: `1px solid ${theme.colors.gray[3]}`, borderRadius: 8 }}>
            {/* Session tabs — vertical sidebar */}
            <div style={{
              width: 200,
              minWidth: 200,
              borderRight: `1px solid ${theme.colors.gray[3]}`,
              overflowY: 'auto',
              background: theme.colorScheme === 'dark' ? theme.colors.dark[7] : theme.colors.gray[0],
            }}>
              {discordSessions.map((s) => (
                <div
                  key={s.channel_id}
                  onClick={() => {
                    setDiscordActiveTab(s.channel_id);
                    void fetchDiscordHistory(s.channel_id);
                  }}
                  style={{
                    padding: '10px 12px',
                    cursor: 'pointer',
                    borderBottom: `1px solid ${theme.colors.gray[2]}`,
                    background: discordActiveTab === s.channel_id
                      ? (theme.colorScheme === 'dark' ? theme.colors.dark[5] : theme.colors.blue[0])
                      : 'transparent',
                  }}
                >
                  <Text size="xs" weight={600} lineClamp={1}>
                    {s.channel_name || (s.is_dm ? 'DM' : s.channel_id)}
                  </Text>
                  <Text size="xs" color="dimmed" lineClamp={1}>{s.channel_id}</Text>
                  <Text size="xs" color="dimmed">
                    {s.message_count} msg{s.message_count !== 1 ? 's' : ''}
                    {s.has_summary ? ' · summarised' : ''}
                  </Text>
                </div>
              ))}
            </div>

            {/* Message history panel */}
            <div style={{ flex: 1, overflowY: 'auto', padding: 12 }}>
              {!discordActiveTab && (
                <Text size="sm" color="dimmed" style={{ textAlign: 'center', marginTop: 40 }}>
                  Select a session to view message history
                </Text>
              )}
              {discordActiveTab && discordLoadingHistory && (
                <Text size="sm" color="dimmed">Loading messages...</Text>
              )}
              {discordActiveTab && !discordLoadingHistory && discordHistory.length === 0 && (
                <Text size="sm" color="dimmed">No messages in this session.</Text>
              )}
              {discordActiveTab && !discordLoadingHistory && discordHistory.map((msg, i) => (
                <div
                  key={i}
                  style={{
                    marginBottom: 8,
                    padding: '8px 10px',
                    borderRadius: 6,
                    background: msg.type === 'summary'
                      ? (theme.colorScheme === 'dark' ? theme.colors.violet[9] : theme.colors.violet[0])
                      : msg.role === 'assistant'
                        ? (theme.colorScheme === 'dark' ? theme.colors.dark[6] : theme.colors.gray[0])
                        : 'transparent',
                    borderLeft: msg.role === 'user'
                      ? `3px solid ${theme.colors.blue[5]}`
                      : msg.type === 'summary'
                        ? `3px solid ${theme.colors.violet[5]}`
                        : `3px solid ${theme.colors.green[5]}`,
                  }}
                >
                  <Text size="xs" weight={700} color={
                    msg.type === 'summary' ? 'violet' : msg.role === 'user' ? 'blue' : 'green'
                  } mb={2}>
                    {msg.type === 'summary' ? 'Summary' : msg.role === 'user' ? 'User' : 'Assistant'}
                  </Text>
                  <Text size="sm" style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                    {msg.message}
                  </Text>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderPlaceholder = (name: string) => (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100%',
    }}>
      <Text size="xl" color="dimmed">{name} — Coming Soon</Text>
    </div>
  );

  const renderProcessesView = () => {
    const activeProcessProtected = activeProcessSession ? isProtectedProcessSession(activeProcessSession) : false;
    if (activeProcessSession) {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '12px 16px 16px 16px' }}>
          <Group position="apart" mb={8}>
            <Text size="sm" weight={700}>
              Viewing: {activeProcessSession} {activeProcessProtected ? '(system process, read-only)' : '(read-only)'}
            </Text>
            <button
              type="button"
              onClick={() => setActiveProcessSession(null)}
              style={{
                border: `1px solid ${theme.colors.gray[3]}`,
                borderRadius: 8,
                padding: '4px 10px',
                background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff',
                fontSize: 12,
                cursor: 'pointer',
              }}
            >
              Back to List
            </button>
          </Group>
          <div style={{ flex: 1, position: 'relative' }}>
            <iframe
              key={activeProcessSession}
              src={`/terminal?session=${encodeURIComponent(activeProcessSession)}&readonly=1${activeProcessProtected ? '' : '&allowKill=1'}`}
              style={{
                width: '100%',
                height: '100%',
                border: 'none',
                borderRadius: 8,
              }}
            />
          </div>
        </div>
      );
    }

    return (
      <div style={{ padding: 16 }}>
        <Group position="apart" mb={12}>
          <Text size="lg" weight={700}>Processes (External Tmux Sessions)</Text>
          <button
            type="button"
            onClick={() => void fetchExternalSessions()}
            style={{
              border: `1px solid ${theme.colors.gray[3]}`,
              borderRadius: 8,
              padding: '4px 10px',
              background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff',
              fontSize: 12,
              cursor: 'pointer',
            }}
          >
            Refresh
          </button>
        </Group>

        {loadingExternalSessions && externalSessions.length === 0 && (
          <Text size="sm" color="dimmed">Loading sessions...</Text>
        )}

        {!loadingExternalSessions && externalSessions.length === 0 && (
          <Text size="sm" color="dimmed">No external tmux sessions found.</Text>
        )}

        {externalSessions.map((session) => (
          (() => {
            const isSystemProcess = Boolean(session.system) || isProtectedProcessSession(session.name);
            const readonlyUrl = `/terminal?session=${encodeURIComponent(session.name)}&readonly=1${isSystemProcess ? '' : '&allowKill=1'}`;
            return (
          <div
            key={session.name}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              border: `1px solid ${theme.colors.gray[3]}`,
              borderRadius: 8,
              padding: '8px 10px',
              marginBottom: 8,
              background: theme.colorScheme === 'dark' ? theme.colors.dark[7] : '#fff',
            }}
          >
            <div>
              <Group spacing={8}>
                <Text size="sm" weight={600}>{session.name}</Text>
                {isSystemProcess && (
                  <Text
                    size="xs"
                    weight={700}
                    style={{
                      padding: '2px 6px',
                      borderRadius: 999,
                      background: theme.colorScheme === 'dark' ? theme.colors.orange[9] : theme.colors.orange[1],
                      color: theme.colorScheme === 'dark' ? theme.colors.orange[2] : theme.colors.orange[8],
                    }}
                  >
                    System Process
                  </Text>
                )}
              </Group>
              <Text size="xs" color="dimmed">
                {session.attached ? 'Attached' : 'Detached'} · windows {session.windows}{isSystemProcess ? ' · kill disabled' : ''}
              </Text>
            </div>
            <button
              type="button"
              onClick={(e) => {
                if (e.shiftKey) {
                  window.open(readonlyUrl, '_blank');
                } else {
                  setActiveProcessSession(session.name);
                }
              }}
              style={{
                border: `1px solid ${theme.colors.gray[3]}`,
                borderRadius: 8,
                padding: '5px 10px',
                background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff',
                fontSize: 12,
                cursor: 'pointer',
              }}
            >
              View Only
            </button>
          </div>
            );
          })()
        ))}
        <Text size="xs" color="dimmed" mt={4}>Shift+Click &quot;View Only&quot; to open in a new window.</Text>
      </div>
    );
  };

  const skillToggle = (name: string) => {
    setSkillDisabled((prev) => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  };

  const runSkillSearch = (value?: string) => {
    setSkillAppliedSearch((value ?? skillSearchText).trim());
  };

  const skillSave = async () => {
    setSkillSaving(true);
    setSkillSaveOutput('');
    try {
      const res = await axios.post(`${API_BASE_URL}/config/skills/update`, {
        disabled: Array.from(skillDisabled),
      });
      const results = res.data?.results || [];
      setSkillSaveOutput(results.map((r: any) => `[${r.command}] exit=${r.exit_code}\n${r.output}`).join('\n---\n'));
      await fetchSkills();
    } catch (err: any) {
      const results = err?.response?.data?.results || [];
      const output = results.map((r: any) => `[${r.command}] exit=${r.exit_code}\n${r.output}`).join('\n---\n');
      setSkillSaveOutput(output || err?.response?.data?.error || 'Save failed');
    } finally {
      setSkillSaving(false);
    }
  };

  const skillOpenSubScreen = async (mode: 'use' | 'view' | 'edit', skillName: string, categoryId: string) => {
    setSkillSubScreen({ mode, skillName, categoryId });
    setSkillUsePrompt('');
    setSkillEditOutput('');
    if (mode === 'view' || mode === 'edit') {
      try {
        const res = await axios.get(`${API_BASE_URL}/config/skills/${encodeURIComponent(categoryId)}/${encodeURIComponent(skillName)}/content`);
        setSkillContent(res.data?.content || '');
      } catch {
        setSkillContent('Failed to load skill content.');
      }
    }
  };

  const skillEditSave = async () => {
    if (!skillSubScreen) return;
    setSkillEditSaving(true);
    setSkillEditOutput('');
    try {
      const res = await axios.post(
        `${API_BASE_URL}/config/skills/${encodeURIComponent(skillSubScreen.categoryId)}/${encodeURIComponent(skillSubScreen.skillName)}/content`,
        { content: skillContent },
      );
      const results = res.data?.results || [];
      setSkillEditOutput(results.map((r: any) => `[${r.command}] exit=${r.exit_code}\n${r.output}`).join('\n---\n'));
    } catch (err: any) {
      const results = err?.response?.data?.results || [];
      const output = results.map((r: any) => `[${r.command}] exit=${r.exit_code}\n${r.output}`).join('\n---\n');
      setSkillEditOutput(output || err?.response?.data?.error || 'Save failed');
    } finally {
      setSkillEditSaving(false);
    }
  };

  const skillUseSubmit = () => {
    if (!skillSubScreen) return;
    const instruction = skillUsePrompt.trim();
    if (skillSubScreen.createSkill && !instruction) return;
    const name = skillSubScreen.skillName;
    let prompt: string;
    if (skillSubScreen.createSkill) {
      prompt = `Create a user agent skill using agent skill \`agent-skill\`, as user's requirement below:\n\n${instruction}`;
    } else {
      prompt = `Use agent skill: ${name}.`;
      if (instruction) {
        prompt += ` User request: ${instruction}`;
      }
    }
    setSkillSubScreen(null);
    void router.push({ pathname: '/', query: { new_session: 'true', prompt } });
  };

  const renderSkillsView = () => {
    if (skillSubScreen) {
      const { mode, skillName } = skillSubScreen;

      if (mode === 'use') {
        const isCreate = skillSubScreen.createSkill;
        return (
          <div style={{ padding: 16, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
            <Group position="apart" mb={16}>
              <Text size="lg" weight={700}>{isCreate ? 'Create Skill' : `Use Skill: ${skillName}`}</Text>
              <button
                type="button"
                onClick={() => setSkillSubScreen(null)}
                style={{
                  border: `1px solid ${theme.colors.gray[3]}`, borderRadius: 8, padding: '4px 10px',
                  background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff', fontSize: 12, cursor: 'pointer',
                }}
              >
                Back
              </button>
            </Group>
            {isCreate && (
              <Text size="sm" color="dimmed" mb={8}>
                Describe what this agent skill should do. Be as detailed as possible.
              </Text>
            )}
            <textarea
              placeholder={isCreate
                ? "Describe the skill: what it does, inputs, expected behavior..."
                : "Write optional instruction for the AI agent..."}
              value={skillUsePrompt}
              onChange={(e) => setSkillUsePrompt(e.target.value)}
              rows={6}
              style={{
                width: '100%', padding: '8px 10px', fontSize: 13, borderRadius: 6, fontFamily: 'inherit',
                border: `1px solid ${theme.colors.gray[3]}`,
                background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff',
                color: 'inherit', resize: 'vertical', marginBottom: 12,
              }}
            />
            <div>
              <button
                type="button"
                onClick={skillUseSubmit}
                disabled={isCreate && !skillUsePrompt.trim()}
                style={{
                  padding: '8px 24px', fontSize: 13, fontWeight: 600, borderRadius: 8,
                  cursor: (isCreate && !skillUsePrompt.trim()) ? 'not-allowed' : 'pointer',
                  border: `1px solid ${theme.colors.blue[5]}`, background: theme.colors.blue[6], color: '#fff',
                  opacity: (isCreate && !skillUsePrompt.trim()) ? 0.5 : 1,
                }}
              >
                Submit
              </button>
            </div>
          </div>
        );
      }

      if (mode === 'view') {
        let frontmatter: Record<string, string> = {};
        let markdownBody = skillContent;
        if (skillContent.startsWith('---')) {
          const endIdx = skillContent.indexOf('---', 3);
          if (endIdx !== -1) {
            const block = skillContent.slice(3, endIdx);
            for (const line of block.split('\n')) {
              const colonIdx = line.indexOf(':');
              if (colonIdx > 0) {
                const key = line.slice(0, colonIdx).trim();
                const val = line.slice(colonIdx + 1).trim();
                if (key) frontmatter[key] = val;
              }
            }
            markdownBody = skillContent.slice(endIdx + 3).trim();
          }
        }

        return (
          <div style={{ padding: 16, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
            <Group position="apart" mb={16}>
              <Text size="lg" weight={700}>{frontmatter.name || skillName}</Text>
              <button
                type="button"
                onClick={() => setSkillSubScreen(null)}
                style={{
                  border: `1px solid ${theme.colors.gray[3]}`, borderRadius: 8, padding: '4px 10px',
                  background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff', fontSize: 12, cursor: 'pointer',
                }}
              >
                Back
              </button>
            </Group>

            <div style={{ flex: 1, overflowY: 'auto', minHeight: 0, paddingBottom: 24 }}>
              {Object.keys(frontmatter).length > 0 && (
                <table style={{
                  width: '100%', maxWidth: 600, marginBottom: 24, borderCollapse: 'collapse',
                  fontSize: 13,
                }}>
                  <tbody>
                    {Object.entries(frontmatter).map(([key, val]) => (
                      <tr key={key}>
                        <td style={{
                          padding: '6px 12px', fontWeight: 600, whiteSpace: 'nowrap',
                          borderBottom: `1px solid ${theme.colors.gray[2]}`,
                          color: theme.colorScheme === 'dark' ? theme.colors.gray[4] : theme.colors.gray[7],
                          width: 140, verticalAlign: 'top',
                        }}>
                          {key}
                        </td>
                        <td style={{
                          padding: '6px 12px',
                          borderBottom: `1px solid ${theme.colors.gray[2]}`,
                        }}>
                          {val}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}

              <div className="prose max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdownBody}</ReactMarkdown>
              </div>
            </div>
          </div>
        );
      }

      if (mode === 'edit') {
        return (
          <div style={{ padding: 16, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
            <Group position="apart" mb={16}>
              <Text size="lg" weight={700}>Edit: {skillName}</Text>
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  type="button"
                  onClick={() => void skillEditSave()}
                  disabled={skillEditSaving}
                  style={{
                    padding: '4px 14px', fontSize: 12, fontWeight: 600, borderRadius: 8,
                    cursor: skillEditSaving ? 'not-allowed' : 'pointer',
                    border: `1px solid ${theme.colors.blue[5]}`, background: theme.colors.blue[6], color: '#fff',
                  }}
                >
                  {skillEditSaving ? 'Saving...' : 'Save'}
                </button>
                <button
                  type="button"
                  onClick={() => setSkillSubScreen(null)}
                  style={{
                    border: `1px solid ${theme.colors.gray[3]}`, borderRadius: 8, padding: '4px 10px',
                    background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff', fontSize: 12, cursor: 'pointer',
                  }}
                >
                  Back
                </button>
              </div>
            </Group>
            <textarea
              value={skillContent}
              onChange={(e) => setSkillContent(e.target.value)}
              style={{
                flex: 1, width: '100%', padding: '8px 10px', fontSize: 13, borderRadius: 6,
                fontFamily: 'monospace', lineHeight: 1.5,
                border: `1px solid ${theme.colors.gray[3]}`,
                background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff',
                color: 'inherit', resize: 'none',
              }}
            />
            {skillEditOutput && (
              <pre style={{
                marginTop: 12, fontSize: 11, padding: 10, borderRadius: 6,
                maxHeight: 200, overflowY: 'auto', flexShrink: 0,
                background: theme.colorScheme === 'dark' ? theme.colors.dark[8] : theme.colors.gray[1],
                border: `1px solid ${theme.colors.gray[3]}`, whiteSpace: 'pre-wrap', wordBreak: 'break-all',
              }}>
                {skillEditOutput}
              </pre>
            )}
          </div>
        );
      }
    }

    const skillTabs = [
      { id: 'all', label: 'All', skills: skillCategories.flatMap((cat) => cat.skills.map((skill) => ({ ...skill, categoryId: cat.id }))) },
      ...skillCategories.map((cat) => ({
        id: cat.id,
        label: cat.label,
        skills: cat.skills.map((skill) => ({ ...skill, categoryId: cat.id })),
      })),
    ];
    const activeTab = skillTabs.find((tab) => tab.id === skillActiveTab) || skillTabs[0];
    const normalizedSkillSearch = skillSearchText.trim().toLowerCase();
    const skillSuggestions = normalizedSkillSearch
      ? activeTab.skills.filter((skill) => (
        skill.name.toLowerCase().includes(normalizedSkillSearch) ||
        skill.description.toLowerCase().includes(normalizedSkillSearch)
      ))
      : activeTab.skills;
    const normalizedAppliedSearch = skillAppliedSearch.trim().toLowerCase();
    const displayedSkills = normalizedAppliedSearch
      ? activeTab.skills.filter((skill) => (
        skill.name.toLowerCase().includes(normalizedAppliedSearch) ||
        skill.description.toLowerCase().includes(normalizedAppliedSearch)
      ))
      : activeTab.skills;
    return (
      <div style={{ padding: 16, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
        <Group position="apart" mb={12}>
          <Text size="lg" weight={700}>Skills</Text>
          <button
            type="button"
            onClick={() => {
              setSkillSubScreen({ mode: 'use', skillName: 'agent-skill', categoryId: 'system', createSkill: true });
              setSkillUsePrompt('');
            }}
            style={{
              padding: '5px 14px', fontSize: 12, fontWeight: 600, borderRadius: 8, cursor: 'pointer',
              border: `1px solid ${theme.colors.blue[5]}`, background: theme.colors.blue[6], color: '#fff',
            }}
          >
            Create Skill
          </button>
        </Group>

        <div style={{ display: 'flex', gap: 0, borderBottom: `2px solid ${theme.colors.gray[3]}`, marginBottom: 16 }}>
          {skillTabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setSkillActiveTab(tab.id)}
              style={{
                padding: '8px 16px',
                fontSize: 13,
                fontWeight: skillActiveTab === tab.id ? 700 : 400,
                cursor: 'pointer',
                border: 'none',
                borderBottom: skillActiveTab === tab.id ? `2px solid ${theme.colors.blue[6]}` : '2px solid transparent',
                marginBottom: -2,
                background: 'transparent',
                color: skillActiveTab === tab.id ? theme.colors.blue[6] : 'inherit',
              }}
            >
              {tab.label} ({tab.skills.length})
            </button>
          ))}
        </div>

        <div style={{ position: 'relative', marginBottom: 16 }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              type="text"
              value={skillSearchText}
              onChange={(e) => setSkillSearchText(e.target.value)}
              onFocus={() => setSkillSearchFocused(true)}
              onBlur={() => setTimeout(() => setSkillSearchFocused(false), 150)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  runSkillSearch();
                }
              }}
              placeholder={`Search ${activeTab.label.toLowerCase()} skills...`}
              style={{
                flex: 1,
                padding: '8px 10px',
                fontSize: 13,
                borderRadius: 8,
                border: `1px solid ${theme.colors.gray[3]}`,
                background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff',
                color: 'inherit',
              }}
            />
            <button
              type="button"
              onClick={() => runSkillSearch()}
              style={{
                padding: '8px 16px',
                fontSize: 12,
                fontWeight: 600,
                borderRadius: 8,
                cursor: 'pointer',
                border: `1px solid ${theme.colors.blue[5]}`,
                background: theme.colors.blue[6],
                color: '#fff',
              }}
            >
              Search
            </button>
          </div>
          {skillSearchFocused && skillSuggestions.length > 0 && (
            <div style={{
              position: 'absolute',
              top: '100%',
              left: 0,
              right: 88,
              zIndex: 10,
              maxHeight: 220,
              overflowY: 'auto',
              borderRadius: 8,
              marginTop: 4,
              border: `1px solid ${theme.colors.gray[3]}`,
              background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff',
              boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            }}>
              {skillSuggestions.slice(0, 12).map((skill) => (
                <div
                  key={`${skill.categoryId}:${skill.name}`}
                  onMouseDown={() => {
                    setSkillSearchText(skill.name);
                    runSkillSearch(skill.name);
                  }}
                  style={{
                    padding: '8px 10px',
                    cursor: 'pointer',
                    borderBottom: `1px solid ${theme.colors.gray[2]}`,
                  }}
                >
                  <Text size="sm" weight={600}>{skill.name}</Text>
                  <Text size="xs" color="dimmed" lineClamp={1}>{skill.description}</Text>
                </div>
              ))}
            </div>
          )}
        </div>

        <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
          {activeTab.skills.length === 0 && (
            <Text size="sm" color="dimmed">No skills in this category.</Text>
          )}

          {activeTab.skills.length > 0 && displayedSkills.length === 0 && (
            <Text size="sm" color="dimmed">No skills match this search in the current category.</Text>
          )}

          {displayedSkills.map((skill) => (
            <div
              key={`${skill.categoryId}:${skill.name}`}
              style={{
                border: `1px solid ${theme.colors.gray[3]}`,
                borderRadius: 8,
                padding: '8px 12px',
                marginBottom: 6,
                background: theme.colorScheme === 'dark' ? theme.colors.dark[7] : '#fff',
                opacity: skillDisabled.has(skill.name) ? 0.5 : 1,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <Text size="sm" weight={600}>{skill.name}</Text>
                  <Text size="xs" color="dimmed" lineClamp={2}>{skill.description}</Text>
                </div>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', marginLeft: 12, flexShrink: 0 }}>
                  <input
                    type="checkbox"
                    checked={!skillDisabled.has(skill.name)}
                    onChange={() => skillToggle(skill.name)}
                    style={{ width: 16, height: 16, cursor: 'pointer' }}
                  />
                  <Text size="xs">{skillDisabled.has(skill.name) ? 'Disabled' : 'Enabled'}</Text>
                </label>
              </div>
              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                {(['Use', 'View', 'Edit'] as const).map((action) => (
                  <button
                    key={action}
                    type="button"
                    onClick={() => void skillOpenSubScreen(action.toLowerCase() as 'use' | 'view' | 'edit', skill.name, skill.categoryId)}
                    style={{
                      padding: '5px 14px', fontSize: 12, fontWeight: 500, borderRadius: 6, cursor: 'pointer',
                      border: `1px solid ${theme.colors.gray[4]}`,
                      background: theme.colorScheme === 'dark' ? theme.colors.dark[5] : theme.colors.gray[0],
                      color: 'inherit',
                    }}
                  >
                    {action}
                  </button>
                ))}
                <button
                  type="button"
                  onClick={() => {
                    setScheduleForm({
                      name: `Scheduled ${skill.name}`,
                      skill: skill.name,
                      provider: '',
                      enabled: true,
                      frequency: 'daily',
                      hour: 9,
                      minute: 0,
                      weekday: 1,
                      monthday: 1,
                    });
                    setScheduleEditing('__new__');
                    setActiveView('schedule');
                  }}
                  style={{
                    padding: '5px 14px', fontSize: 12, fontWeight: 500, borderRadius: 6, cursor: 'pointer',
                    border: `1px solid ${theme.colors.orange[4]}`,
                    background: theme.colorScheme === 'dark' ? theme.colors.dark[5] : theme.colors.gray[0],
                    color: theme.colors.orange[6],
                  }}
                >
                  Schedule
                </button>
              </div>
            </div>
          ))}
        </div>

        <div style={{ marginTop: 12, borderTop: `1px solid ${theme.colors.gray[3]}`, paddingTop: 12, flexShrink: 0 }}>
          <button
            type="button"
            onClick={() => void skillSave()}
            disabled={skillSaving}
            style={{
              padding: '8px 24px',
              fontSize: 13,
              fontWeight: 600,
              borderRadius: 8,
              cursor: skillSaving ? 'not-allowed' : 'pointer',
              border: `1px solid ${theme.colors.blue[5]}`,
              background: theme.colors.blue[6],
              color: '#fff',
            }}
          >
            {skillSaving ? 'Saving...' : 'Save & Update'}
          </button>
          {skillSaveOutput && (
            <pre style={{
              marginTop: 12,
              fontSize: 11,
              padding: 10,
              borderRadius: 6,
              maxHeight: 200,
              overflowY: 'auto',
              background: theme.colorScheme === 'dark' ? theme.colors.dark[8] : theme.colors.gray[1],
              border: `1px solid ${theme.colors.gray[3]}`,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-all',
            }}>
              {skillSaveOutput}
            </pre>
          )}
        </div>
      </div>
    );
  };

  const scheduleSave = async () => {
    const allSkills = skillCategories.flatMap((c) => c.skills.map((s) => s.name));
    const providerIds = llmProviders.map((p) => p.id);
    if (!allSkills.includes(scheduleForm.skill)) {
      setScheduleError(`Invalid skill: "${scheduleForm.skill}". Select a valid skill from the list.`);
      return;
    }
    if (scheduleForm.provider && !providerIds.includes(scheduleForm.provider)) {
      setScheduleError(`Invalid provider: "${scheduleForm.provider}". Select a valid provider from the list.`);
      return;
    }
    setScheduleSaving(true);
    setScheduleError('');
    try {
      const cron = formDataToCron(scheduleForm);
      const body: any = {
        name: scheduleForm.name,
        skill: scheduleForm.skill,
        cron,
        provider: scheduleForm.provider,
        enabled: scheduleForm.enabled,
      };
      if (scheduleEditing && scheduleEditing !== '__new__') {
        body.id = scheduleEditing;
      }
      await axios.post(`${API_BASE_URL}/config/schedules`, body);
      setScheduleEditing(null);
      await fetchSchedules();
    } catch (err: any) {
      console.error('Failed to save schedule:', err);
      setScheduleError(err?.response?.data?.error || 'Failed to save schedule');
    } finally {
      setScheduleSaving(false);
    }
  };

  const scheduleDelete = async (id: string) => {
    if (!window.confirm('Delete this schedule?')) return;
    try {
      await axios.delete(`${API_BASE_URL}/config/schedules/${encodeURIComponent(id)}`);
      await fetchSchedules();
    } catch (err: any) {
      console.error('Failed to delete schedule:', err);
    }
  };

  const scheduleStartEdit = (item: ScheduleItem) => {
    const parsed = cronToFormData(item.cron);
    setScheduleForm({
      name: item.name,
      skill: item.skill,
      provider: item.provider || '',
      enabled: item.enabled,
      frequency: parsed.frequency || 'daily',
      hour: parsed.hour ?? 9,
      minute: parsed.minute ?? 0,
      weekday: parsed.weekday ?? 1,
      monthday: parsed.monthday ?? 1,
    });
    setScheduleEditing(item.id);
  };

  const renderScheduleForm = () => {
    const isNew = scheduleEditing === '__new__';
    const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    return (
      <div style={{ padding: 16, maxWidth: 600 }}>
        <Group position="apart" mb={16}>
          <Text size="lg" weight={700}>{isNew ? 'Add Schedule' : 'Edit Schedule'}</Text>
          <button
            type="button"
            onClick={() => setScheduleEditing(null)}
            style={{
              border: `1px solid ${theme.colors.gray[3]}`, borderRadius: 8, padding: '4px 10px',
              background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff', fontSize: 12, cursor: 'pointer',
            }}
          >
            Cancel
          </button>
        </Group>

        {scheduleError && <Text size="xs" color="red" mb={8}>{scheduleError}</Text>}

        <div style={{ marginBottom: 12 }}>
          <Text size="sm" weight={600} mb={4}>Name</Text>
          <input
            type="text"
            value={scheduleForm.name}
            onChange={(e) => setScheduleForm((prev) => ({ ...prev, name: e.target.value }))}
            placeholder="e.g. Daily code review"
            style={{
              width: '100%', padding: '6px 8px', fontSize: 13, borderRadius: 6,
              border: `1px solid ${theme.colors.gray[3]}`,
              background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff', color: 'inherit',
            }}
          />
        </div>

        {(() => {
          const allSkills = skillCategories.flatMap((c) => c.skills.map((s) => s.name));
          const filteredSkills = scheduleForm.skill
            ? allSkills.filter((s) => s.toLowerCase().includes(scheduleForm.skill.toLowerCase()))
            : allSkills;
          const skillValid = !scheduleForm.skill || allSkills.includes(scheduleForm.skill);
          return (
            <div style={{ marginBottom: 12, position: 'relative' }}>
              <Text size="sm" weight={600} mb={4}>Skill</Text>
              <input
                type="text"
                value={scheduleForm.skill}
                onChange={(e) => { setScheduleForm((prev) => ({ ...prev, skill: e.target.value })); setScheduleError(''); }}
                onFocus={() => setScheduleSkillFocused(true)}
                onBlur={() => setTimeout(() => setScheduleSkillFocused(false), 150)}
                placeholder="Type to search skills..."
                style={{
                  width: '100%', padding: '6px 8px', fontSize: 13, borderRadius: 6,
                  border: `1px solid ${!skillValid ? theme.colors.red[5] : theme.colors.gray[3]}`,
                  background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff', color: 'inherit',
                }}
              />
              {!skillValid && (
                <Text size="xs" color="red" mt={2}>Skill "{scheduleForm.skill}" not found</Text>
              )}
              {scheduleSkillFocused && filteredSkills.length > 0 && (
                <div style={{
                  position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 10,
                  maxHeight: 180, overflowY: 'auto', borderRadius: 6, marginTop: 2,
                  border: `1px solid ${theme.colors.gray[3]}`,
                  background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                }}>
                  {filteredSkills.map((s) => (
                    <div
                      key={s}
                      onMouseDown={() => { setScheduleForm((prev) => ({ ...prev, skill: s })); setScheduleError(''); }}
                      style={{
                        padding: '6px 10px', fontSize: 13, cursor: 'pointer',
                        background: s === scheduleForm.skill
                          ? (theme.colorScheme === 'dark' ? theme.colors.dark[4] : theme.colors.blue[0])
                          : 'transparent',
                      }}
                    >
                      {s}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })()}

        {(() => {
          const providerIds = llmProviders.map((p) => p.id);
          const filteredProviders = scheduleForm.provider
            ? llmProviders.filter((p) => p.id.toLowerCase().includes(scheduleForm.provider.toLowerCase()) || p.name.toLowerCase().includes(scheduleForm.provider.toLowerCase()))
            : llmProviders;
          const providerValid = !scheduleForm.provider || providerIds.includes(scheduleForm.provider);
          return (
            <div style={{ marginBottom: 12, position: 'relative' }}>
              <Text size="sm" weight={600} mb={4}>Provider (optional, defaults to system default)</Text>
              <input
                type="text"
                value={scheduleForm.provider}
                onChange={(e) => { setScheduleForm((prev) => ({ ...prev, provider: e.target.value })); setScheduleError(''); }}
                onFocus={() => setScheduleProviderFocused(true)}
                onBlur={() => setTimeout(() => setScheduleProviderFocused(false), 150)}
                placeholder="Type to search providers..."
                style={{
                  width: '100%', padding: '6px 8px', fontSize: 13, borderRadius: 6,
                  border: `1px solid ${!providerValid ? theme.colors.red[5] : theme.colors.gray[3]}`,
                  background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff', color: 'inherit',
                }}
              />
              {!providerValid && (
                <Text size="xs" color="red" mt={2}>Provider "{scheduleForm.provider}" not found</Text>
              )}
              {scheduleProviderFocused && filteredProviders.length > 0 && (
                <div style={{
                  position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 10,
                  maxHeight: 180, overflowY: 'auto', borderRadius: 6, marginTop: 2,
                  border: `1px solid ${theme.colors.gray[3]}`,
                  background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                }}>
                  {filteredProviders.map((p) => (
                    <div
                      key={p.id}
                      onMouseDown={() => { setScheduleForm((prev) => ({ ...prev, provider: p.id })); setScheduleError(''); }}
                      style={{
                        padding: '6px 10px', fontSize: 13, cursor: 'pointer',
                        background: p.id === scheduleForm.provider
                          ? (theme.colorScheme === 'dark' ? theme.colors.dark[4] : theme.colors.blue[0])
                          : 'transparent',
                      }}
                    >
                      {p.name} <span style={{ color: theme.colors.gray[5], fontSize: 11 }}>({p.id})</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })()}

        <div style={{ marginBottom: 12 }}>
          <Text size="sm" weight={600} mb={4}>Frequency</Text>
          <select
            value={scheduleForm.frequency}
            onChange={(e) => setScheduleForm((prev) => ({ ...prev, frequency: e.target.value as ScheduleFormData['frequency'] }))}
            style={{
              width: '100%', padding: '6px 8px', fontSize: 13, borderRadius: 6,
              border: `1px solid ${theme.colors.gray[3]}`,
              background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff', color: 'inherit',
            }}
          >
            <option value="daily">Every Day</option>
            <option value="weekdays">Weekdays (Mon-Fri)</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </div>

        {scheduleForm.frequency === 'weekly' && (
          <div style={{ marginBottom: 12 }}>
            <Text size="sm" weight={600} mb={4}>Day of Week</Text>
            <select
              value={scheduleForm.weekday}
              onChange={(e) => setScheduleForm((prev) => ({ ...prev, weekday: parseInt(e.target.value, 10) }))}
              style={{
                width: '100%', padding: '6px 8px', fontSize: 13, borderRadius: 6,
                border: `1px solid ${theme.colors.gray[3]}`,
                background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff', color: 'inherit',
              }}
            >
              {dayNames.map((name, i) => (
                <option key={i} value={i}>{name}</option>
              ))}
            </select>
          </div>
        )}

        {scheduleForm.frequency === 'monthly' && (
          <div style={{ marginBottom: 12 }}>
            <Text size="sm" weight={600} mb={4}>Day of Month</Text>
            <select
              value={scheduleForm.monthday}
              onChange={(e) => setScheduleForm((prev) => ({ ...prev, monthday: parseInt(e.target.value, 10) }))}
              style={{
                width: '100%', padding: '6px 8px', fontSize: 13, borderRadius: 6,
                border: `1px solid ${theme.colors.gray[3]}`,
                background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff', color: 'inherit',
              }}
            >
              {Array.from({ length: 31 }, (_, i) => i + 1).map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>
        )}

        <div style={{ display: 'flex', gap: 16, marginBottom: 12 }}>
          <div style={{ flex: 1 }}>
            <Text size="sm" weight={600} mb={4}>Hour (0-23)</Text>
            <select
              value={scheduleForm.hour}
              onChange={(e) => setScheduleForm((prev) => ({ ...prev, hour: parseInt(e.target.value, 10) }))}
              style={{
                width: '100%', padding: '6px 8px', fontSize: 13, borderRadius: 6,
                border: `1px solid ${theme.colors.gray[3]}`,
                background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff', color: 'inherit',
              }}
            >
              {Array.from({ length: 24 }, (_, i) => i).map((h) => (
                <option key={h} value={h}>{String(h).padStart(2, '0')}</option>
              ))}
            </select>
          </div>
          <div style={{ flex: 1 }}>
            <Text size="sm" weight={600} mb={4}>Minute (0-59)</Text>
            <select
              value={scheduleForm.minute}
              onChange={(e) => setScheduleForm((prev) => ({ ...prev, minute: parseInt(e.target.value, 10) }))}
              style={{
                width: '100%', padding: '6px 8px', fontSize: 13, borderRadius: 6,
                border: `1px solid ${theme.colors.gray[3]}`,
                background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff', color: 'inherit',
              }}
            >
              {Array.from({ length: 60 }, (_, i) => i).map((m) => (
                <option key={m} value={m}>{String(m).padStart(2, '0')}</option>
              ))}
            </select>
          </div>
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={scheduleForm.enabled}
              onChange={(e) => setScheduleForm((prev) => ({ ...prev, enabled: e.target.checked }))}
            />
            Enabled
          </label>
        </div>

        <Text size="xs" color="dimmed" mb={12}>
          Cron preview: <code>{formDataToCron(scheduleForm)}</code> — {cronToHumanReadable(formDataToCron(scheduleForm))}
        </Text>

        <button
          type="button"
          onClick={() => void scheduleSave()}
          disabled={scheduleSaving || !scheduleForm.name.trim() || !scheduleForm.skill.trim()}
          style={{
            padding: '6px 20px', fontSize: 13, borderRadius: 8,
            cursor: (scheduleSaving || !scheduleForm.name.trim() || !scheduleForm.skill.trim()) ? 'not-allowed' : 'pointer',
            border: `1px solid ${theme.colors.blue[5]}`, background: theme.colors.blue[6], color: '#fff',
            opacity: (!scheduleForm.name.trim() || !scheduleForm.skill.trim()) ? 0.5 : 1,
          }}
        >
          {scheduleSaving ? 'Saving...' : 'Save'}
        </button>
      </div>
    );
  };

  const handleDefaultProviderChange = async (value: string, target: 'llm' | 'doctor' = 'llm') => {
    if (target === 'doctor') {
      setDefaultDoctorProvider(value);
    } else {
      setDefaultLlmProvider(value);
    }
    try {
      await axios.post(`${API_BASE_URL}/config/default-provider`, { provider: value, target });
    } catch (err) {
      console.error('Failed to update default provider:', err);
    }
  };

  const renderScheduleView = () => {
    if (scheduleEditing !== null) {
      return renderScheduleForm();
    }

    return (
      <div style={{ padding: 16 }}>
        <Group position="apart" mb={12}>
          <Text size="lg" weight={700}>Schedules</Text>
          <button
            type="button"
            onClick={() => {
              setScheduleForm({
                name: '', skill: '', provider: '', enabled: true,
                frequency: 'daily', hour: 9, minute: 0, weekday: 1, monthday: 1,
              });
              setScheduleEditing('__new__');
            }}
            style={{
              border: `1px solid ${theme.colors.blue[5]}`, borderRadius: 8, padding: '4px 10px',
              background: theme.colors.blue[6], color: '#fff', fontSize: 12, cursor: 'pointer',
            }}
          >
            Add Schedule
          </button>
        </Group>

        {schedules.length === 0 && (
          <Text size="sm" color="dimmed" mb={12}>No schedules configured.</Text>
        )}

        {schedules.map((item) => (
          <div
            key={item.id}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              border: `1px solid ${theme.colors.gray[3]}`, borderRadius: 8, padding: '8px 12px', marginBottom: 8,
              background: theme.colorScheme === 'dark' ? theme.colors.dark[7] : '#fff',
              opacity: item.enabled ? 1 : 0.6,
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Text size="sm" weight={600}>{item.name}</Text>
                <span style={{
                  fontSize: 10, padding: '1px 6px', borderRadius: 4, fontWeight: 600,
                  background: item.enabled ? theme.colors.green[1] : theme.colors.gray[2],
                  color: item.enabled ? theme.colors.green[7] : theme.colors.gray[6],
                }}>
                  {item.enabled ? 'enabled' : 'disabled'}
                </span>
              </div>
              <Text size="xs" color="dimmed">
                Skill: {item.skill} · {cronToHumanReadable(item.cron)}
                {item.provider ? ` · Provider: ${item.provider}` : ''}
              </Text>
            </div>
            <div style={{ display: 'flex', gap: 8, flexShrink: 0, marginLeft: 12 }}>
              <button
                type="button"
                onClick={() => scheduleStartEdit(item)}
                style={{
                  border: `1px solid ${theme.colors.gray[3]}`, borderRadius: 8, padding: '5px 10px',
                  background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff', fontSize: 12, cursor: 'pointer',
                }}
              >
                Edit
              </button>
              <button
                type="button"
                onClick={() => void scheduleDelete(item.id)}
                style={{
                  border: `1px solid ${theme.colors.red[5]}`, color: theme.colors.red[6],
                  borderRadius: 8, padding: '5px 10px', background: 'transparent', fontSize: 12, cursor: 'pointer',
                }}
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    );
  };

  const mcpStartEdit = (server: McpServer) => {
    const envPairs: [string, string][] = server.env
      ? Object.entries(server.env).map(([k, v]) => [k, v])
      : [['', '']];
    if (envPairs.length === 0) envPairs.push(['', '']);
    const headerPairs: [string, string][] = server.headers
      ? Object.entries(server.headers).map(([k, v]) => [k, v])
      : [['', '']];
    if (headerPairs.length === 0) headerPairs.push(['', '']);
    setMcpForm({
      name: server.name,
      description: server.description || '',
      instructions: server.instructions || '',
      type: server.type,
      command: server.command || '',
      args: (server.args || []).join('\n'),
      env: envPairs,
      url: server.url || '',
      headers: headerPairs,
      disabled: server.disabled || false,
    });
    setMcpEditing(server.name);
    setMcpError('');
  };

  const mcpStartAdd = () => {
    setMcpForm({ ...EMPTY_MCP_FORM, env: [['', '']], headers: [['', '']] });
    setMcpEditing('__new__');
    setMcpError('');
  };

  const mcpSave = async () => {
    setMcpError('');
    const isNew = mcpEditing === '__new__';
    const trimmedName = mcpForm.name.trim();
    if (isNew) {
      const allSkillNames = new Set(skillCategories.flatMap((c) => c.skills.map((s) => s.name)));
      if (allSkillNames.has(trimmedName)) {
        setMcpError(`The name "${trimmedName}" is already used by an existing agent skill. Each MCP server name must be unique across all agent skills.`);
        return;
      }
    }
    setMcpSaving(true);
    try {
      const body: any = {
        name: trimmedName,
        description: mcpForm.description.trim(),
        instructions: mcpForm.instructions.trim() || undefined,
        type: mcpForm.type,
        disabled: mcpForm.disabled,
      };
      if (mcpForm.type === 'stdio') {
        body.command = mcpForm.command.trim();
        const args = mcpForm.args.split('\n').map((a) => a.trim()).filter(Boolean);
        if (args.length > 0) body.args = args;
        const env: Record<string, string> = {};
        for (const [k, v] of mcpForm.env) {
          if (k.trim()) env[k.trim()] = v;
        }
        if (Object.keys(env).length > 0) body.env = env;
      } else {
        body.url = mcpForm.url.trim();
        const headers: Record<string, string> = {};
        for (const [k, v] of mcpForm.headers) {
          if (k.trim()) headers[k.trim()] = v;
        }
        if (Object.keys(headers).length > 0) body.headers = headers;
      }
      await axios.post(`${API_BASE_URL}/config/mcp-servers`, body);
      setMcpEditing(null);
      await fetchMcpServers();
    } catch (err: any) {
      setMcpError((err as any)?.response?.data?.error || 'Failed to save MCP server');
    } finally {
      setMcpSaving(false);
    }
  };

  const mcpDelete = async (name: string) => {
    if (!window.confirm(`Delete MCP server "${name}"?`)) return;
    setMcpError('');
    try {
      await axios.delete(`${API_BASE_URL}/config/mcp-servers/${encodeURIComponent(name)}`);
      await fetchMcpServers();
    } catch (err: any) {
      setMcpError(err?.response?.data?.error || 'Failed to delete MCP server');
    }
  };

  const mcpSync = async () => {
    setMcpSyncing(true);
    setMcpSyncOutput('');
    setMcpError('');
    try {
      const res = await axios.post(`${API_BASE_URL}/config/mcp-servers/sync`);
      const results = res.data?.results || [];
      setMcpSyncOutput(results.map((r: any) => `[${r.command}] exit=${r.exit_code}\n${r.output}`).join('\n---\n'));
    } catch (err: any) {
      const results = err?.response?.data?.results || [];
      const errorMsg = err?.response?.data?.error || 'Sync failed';
      const output = results.map((r: any) => `[${r.command}] exit=${r.exit_code}\n${r.output}`).join('\n---\n');
      setMcpSyncOutput(output);
      setMcpError(errorMsg);
    } finally {
      setMcpSyncing(false);
    }
  };

  const updateMcpFormPairs = (field: 'env' | 'headers', index: number, pos: 0 | 1, value: string) => {
    setMcpForm((prev) => {
      const pairs = [...prev[field]] as [string, string][];
      pairs[index] = [...pairs[index]] as [string, string];
      pairs[index][pos] = value;
      return { ...prev, [field]: pairs };
    });
  };

  const addMcpFormPair = (field: 'env' | 'headers') => {
    setMcpForm((prev) => ({ ...prev, [field]: [...prev[field], ['', '']] }));
  };

  const removeMcpFormPair = (field: 'env' | 'headers', index: number) => {
    setMcpForm((prev) => {
      const pairs = prev[field].filter((_, i) => i !== index);
      return { ...prev, [field]: pairs.length === 0 ? [['', '']] : pairs };
    });
  };

  const renderKeyValueEditor = (field: 'env' | 'headers', label: string) => {
    const pairs = mcpForm[field];
    return (
      <div style={{ marginBottom: 12 }}>
        <Text size="sm" weight={600} mb={4}>{label}</Text>
        {pairs.map(([k, v], i) => (
          <div key={i} style={{ display: 'flex', gap: 6, marginBottom: 4 }}>
            <input
              type="text"
              placeholder="Key"
              value={k}
              onChange={(e) => updateMcpFormPairs(field, i, 0, e.target.value)}
              style={{
                flex: 1, padding: '6px 8px', fontSize: 13, borderRadius: 6,
                border: `1px solid ${theme.colors.gray[3]}`,
                background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff',
                color: 'inherit',
              }}
            />
            <input
              type="text"
              placeholder="Value"
              value={v}
              onChange={(e) => updateMcpFormPairs(field, i, 1, e.target.value)}
              style={{
                flex: 2, padding: '6px 8px', fontSize: 13, borderRadius: 6,
                border: `1px solid ${theme.colors.gray[3]}`,
                background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff',
                color: 'inherit',
              }}
            />
            <button
              type="button"
              onClick={() => removeMcpFormPair(field, i)}
              style={{
                padding: '4px 8px', fontSize: 12, borderRadius: 6, cursor: 'pointer',
                border: `1px solid ${theme.colors.gray[3]}`, background: 'transparent', color: theme.colors.red[6],
              }}
            >
              x
            </button>
          </div>
        ))}
        <button
          type="button"
          onClick={() => addMcpFormPair(field)}
          style={{
            padding: '4px 10px', fontSize: 12, borderRadius: 6, cursor: 'pointer',
            border: `1px solid ${theme.colors.gray[3]}`,
            background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff',
            color: 'inherit',
          }}
        >
          + Add
        </button>
      </div>
    );
  };

  const renderMcpServersView = () => {
    if (mcpEditing !== null) {
      const isNew = mcpEditing === '__new__';
      const isStdio = mcpForm.type === 'stdio';
      return (
        <div style={{ padding: 16, maxWidth: 700 }}>
          <Group position="apart" mb={16}>
            <Text size="lg" weight={700}>{isNew ? 'Add MCP Server' : `Edit: ${mcpEditing}`}</Text>
            <button
              type="button"
              onClick={() => { setMcpEditing(null); setMcpError(''); }}
              style={{
                border: `1px solid ${theme.colors.gray[3]}`, borderRadius: 8, padding: '4px 10px',
                background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff', fontSize: 12, cursor: 'pointer',
              }}
            >
              Cancel
            </button>
          </Group>

          {mcpError && <Text size="xs" color="red" mb={8}>{mcpError}</Text>}

          <div style={{ marginBottom: 12 }}>
            <Text size="sm" weight={600} mb={4}>Name</Text>
            <input
              type="text"
              value={mcpForm.name}
              disabled={!isNew}
              onChange={(e) => setMcpForm((prev) => ({ ...prev, name: e.target.value }))}
              style={{
                width: '100%', padding: '6px 8px', fontSize: 13, borderRadius: 6,
                border: `1px solid ${theme.colors.gray[3]}`,
                background: !isNew ? theme.colors.gray[1] : theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff',
                color: 'inherit',
              }}
            />
          </div>

          <div style={{ marginBottom: 12 }}>
            <Text size="sm" weight={600} mb={4}>Description</Text>
            <textarea
              value={mcpForm.description}
              onChange={(e) => setMcpForm((prev) => ({ ...prev, description: e.target.value }))}
              placeholder="Describe what this MCP server provides to the agent..."
              rows={2}
              style={{
                width: '100%', padding: '6px 8px', fontSize: 13, borderRadius: 6,
                border: `1px solid ${theme.colors.gray[3]}`,
                background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff',
                color: 'inherit', resize: 'vertical', fontFamily: 'inherit',
              }}
            />
          </div>

          <div style={{ marginBottom: 12 }}>
            <Text size="sm" weight={600} mb={4}>Instructions <Text span size="xs" color="dimmed">(optional — prepended to the generated SKILL.md)</Text></Text>
            <textarea
              value={mcpForm.instructions}
              onChange={(e) => setMcpForm((prev) => ({ ...prev, instructions: e.target.value }))}
              placeholder="Custom instructions for how the agent should use this MCP server and its tools..."
              rows={3}
              style={{
                width: '100%', padding: '6px 8px', fontSize: 13, borderRadius: 6,
                border: `1px solid ${theme.colors.gray[3]}`,
                background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff',
                color: 'inherit', resize: 'vertical', fontFamily: 'inherit',
              }}
            />
          </div>

          <div style={{ marginBottom: 12 }}>
            <Text size="sm" weight={600} mb={4}>Type</Text>
            <select
              value={mcpForm.type}
              onChange={(e) => setMcpForm((prev) => ({ ...prev, type: e.target.value }))}
              style={{
                width: '100%', padding: '6px 8px', fontSize: 13, borderRadius: 6,
                border: `1px solid ${theme.colors.gray[3]}`,
                background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff',
                color: 'inherit',
              }}
            >
              <option value="stdio">stdio</option>
              <option value="streamable-http">streamable-http</option>
              <option value="sse">sse</option>
            </select>
          </div>

          {isStdio ? (
            <>
              <div style={{ marginBottom: 12 }}>
                <Text size="sm" weight={600} mb={4}>Command</Text>
                <input
                  type="text"
                  value={mcpForm.command}
                  onChange={(e) => setMcpForm((prev) => ({ ...prev, command: e.target.value }))}
                  placeholder="e.g. uv, uvx, node"
                  style={{
                    width: '100%', padding: '6px 8px', fontSize: 13, borderRadius: 6,
                    border: `1px solid ${theme.colors.gray[3]}`,
                    background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff',
                    color: 'inherit',
                  }}
                />
              </div>
              <div style={{ marginBottom: 12 }}>
                <Text size="sm" weight={600} mb={4}>Args (one per line)</Text>
                <textarea
                  value={mcpForm.args}
                  onChange={(e) => setMcpForm((prev) => ({ ...prev, args: e.target.value }))}
                  rows={4}
                  style={{
                    width: '100%', padding: '6px 8px', fontSize: 13, borderRadius: 6, fontFamily: 'monospace',
                    border: `1px solid ${theme.colors.gray[3]}`,
                    background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff',
                    color: 'inherit', resize: 'vertical',
                  }}
                />
              </div>
              {renderKeyValueEditor('env', 'Environment Variables')}
            </>
          ) : (
            <>
              <div style={{ marginBottom: 12 }}>
                <Text size="sm" weight={600} mb={4}>URL</Text>
                <input
                  type="text"
                  value={mcpForm.url}
                  onChange={(e) => setMcpForm((prev) => ({ ...prev, url: e.target.value }))}
                  placeholder="https://..."
                  style={{
                    width: '100%', padding: '6px 8px', fontSize: 13, borderRadius: 6,
                    border: `1px solid ${theme.colors.gray[3]}`,
                    background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff',
                    color: 'inherit',
                  }}
                />
              </div>
              {renderKeyValueEditor('headers', 'Headers')}
            </>
          )}

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={mcpForm.disabled}
                onChange={(e) => setMcpForm((prev) => ({ ...prev, disabled: e.target.checked }))}
              />
              Disabled
            </label>
          </div>

          <Text size="xs" color="dimmed" mb={10}>
            The server <strong>Name</strong> is used as the agent skill name and the <strong>Description</strong> as the agent skill description.
            The name must be unique across all agent skills.
          </Text>

          <button
            type="button"
            onClick={() => void mcpSave()}
            disabled={mcpSaving}
            style={{
              padding: '6px 20px', fontSize: 13, borderRadius: 8, cursor: mcpSaving ? 'not-allowed' : 'pointer',
              border: `1px solid ${theme.colors.blue[5]}`, background: theme.colors.blue[6], color: '#fff',
            }}
          >
            {mcpSaving ? 'Saving...' : 'Save'}
          </button>
        </div>
      );
    }

    return (
      <div style={{ padding: 16 }}>
        <Group position="apart" mb={12}>
          <Text size="lg" weight={700}>MCP Servers</Text>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              type="button"
              onClick={mcpStartAdd}
              style={{
                border: `1px solid ${theme.colors.blue[5]}`, borderRadius: 8, padding: '4px 10px',
                background: theme.colors.blue[6], color: '#fff', fontSize: 12, cursor: 'pointer',
              }}
            >
              Add Server
            </button>
            <button
              type="button"
              onClick={() => void fetchMcpServers()}
              style={{
                border: `1px solid ${theme.colors.gray[3]}`, borderRadius: 8, padding: '4px 10px',
                background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff', fontSize: 12, cursor: 'pointer',
              }}
            >
              Refresh
            </button>
          </div>
        </Group>

        {mcpError && <Text size="xs" color="red" mb={8}>{mcpError}</Text>}

        {mcpServers.length === 0 && (
          <Text size="sm" color="dimmed" mb={12}>No MCP servers configured.</Text>
        )}

        {mcpServers.map((server) => (
          <div
            key={server.name}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              border: `1px solid ${theme.colors.gray[3]}`, borderRadius: 8, padding: '8px 10px', marginBottom: 8,
              background: theme.colorScheme === 'dark' ? theme.colors.dark[7] : '#fff',
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Text size="sm" weight={600}>{server.name}</Text>
                <span style={{
                  fontSize: 10, padding: '1px 6px', borderRadius: 4, fontWeight: 600,
                  background: server.type === 'stdio' ? theme.colors.blue[1] : theme.colors.grape[1],
                  color: server.type === 'stdio' ? theme.colors.blue[7] : theme.colors.grape[7],
                }}>
                  {server.type}
                </span>
                {server.system && (
                  <span style={{
                    fontSize: 10, padding: '1px 6px', borderRadius: 4, fontWeight: 600,
                    background: theme.colors.orange[1], color: theme.colors.orange[7],
                  }}>
                    system
                  </span>
                )}
                {server.disabled && (
                  <span style={{
                    fontSize: 10, padding: '1px 6px', borderRadius: 4, fontWeight: 600,
                    background: theme.colors.gray[2], color: theme.colors.gray[6],
                  }}>
                    disabled
                  </span>
                )}
              </div>
              {server.description && (
                <Text size="xs" color="dimmed" mt={2}>{server.description}</Text>
              )}
              <Text size="xs" color="dimmed" mt={2}>
                {server.type === 'stdio'
                  ? `${server.command || ''} ${(server.args || []).join(' ')}`.trim()
                  : server.url || ''}
              </Text>
            </div>
            {!server.system && (
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  type="button"
                  onClick={() => mcpStartEdit(server)}
                  style={{
                    border: `1px solid ${theme.colors.gray[3]}`, borderRadius: 8, padding: '5px 10px',
                    background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff', fontSize: 12, cursor: 'pointer',
                  }}
                >
                  Edit
                </button>
                <button
                  type="button"
                  onClick={() => void mcpDelete(server.name)}
                  style={{
                    border: `1px solid ${theme.colors.red[5]}`, color: theme.colors.red[6],
                    borderRadius: 8, padding: '5px 10px', background: 'transparent', fontSize: 12, cursor: 'pointer',
                  }}
                >
                  Delete
                </button>
              </div>
            )}
          </div>
        ))}

        <div style={{ marginTop: 24, borderTop: `1px solid ${theme.colors.gray[3]}`, paddingTop: 16 }}>
          <Group position="right" mb={8}>
            <button
              type="button"
              onClick={() => void mcpSync()}
              disabled={mcpSyncing}
              style={{
                border: `1px solid ${theme.colors.gray[3]}`, borderRadius: 8, padding: '4px 12px',
                background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff', fontSize: 12,
                cursor: mcpSyncing ? 'not-allowed' : 'pointer',
              }}
            >
              {mcpSyncing ? 'Syncing...' : 'Sync Skills with MCP'}
            </button>
          </Group>
          {mcpSyncOutput && (
            <pre style={{
              fontSize: 11, padding: 10, borderRadius: 6, maxHeight: 200, overflowY: 'auto',
              background: theme.colorScheme === 'dark' ? theme.colors.dark[8] : theme.colors.gray[1],
              border: `1px solid ${theme.colors.gray[3]}`, whiteSpace: 'pre-wrap', wordBreak: 'break-all',
            }}>
              {mcpSyncOutput}
            </pre>
          )}
        </div>
      </div>
    );
  };

  const startPromptExtensionSession = (prompt: string) => {
    void router.push({ pathname: '/', query: { new_session: 'true', prompt } });
  };

  const extensionInstall = (ext: ExtensionItem) => {
    if (ext.type === 'prompt') {
      const promptBase = (ext.prompt || '').trim();
      if (!promptBase) {
        window.alert(`Extension "${ext.name}" is missing its prompt configuration.`);
        return;
      }
      startPromptExtensionSession(`${promptBase}\n\nExtension path: extensions/${ext.dir}`);
      return;
    }

    if (ext.type === 'skill') {
      const skillName = (ext.skill || '').trim();
      if (!skillName) {
        window.alert(`Extension "${ext.name}" is missing its skill configuration.`);
        return;
      }
      startPromptExtensionSession(`Use agent skill ${skillName} to install extension "${ext.name}" in extensions/${ext.dir}.`);
      return;
    }

    window.alert(`Unsupported extension type for install: ${ext.type}`);
  };

  const runScriptExtensionAction = async (ext: ExtensionItem, action: 'install' | 'update' | 'uninstall') => {
    const actionKey = `${ext.dir}:${action}`;
    setExtensionActionLoading((prev) => ({ ...prev, [ext.dir]: action }));
    try {
      const res = await axios.post(`${API_BASE_URL}/config/extensions/action`, { dir: ext.dir, action });
      const output = String(res.data?.output || '').trim();
      setExtensionActionOutput((prev) => ({
        ...prev,
        [ext.dir]: output || `${action} completed successfully.`,
      }));
      setExtensionsError('');
      void fetchExtensions();
    } catch (err: any) {
      const output = String(err?.response?.data?.output || err?.response?.data?.error || `${action} failed.`);
      setExtensionActionOutput((prev) => ({ ...prev, [ext.dir]: output }));
    } finally {
      setExtensionActionLoading((prev) => {
        const next = { ...prev };
        if (next[ext.dir] === action) delete next[ext.dir];
        return next;
      });
    }
  };

  const renderExtensionsView = () => (
    <div style={{ padding: 16 }}>
      <Text size="lg" weight={700} mb={12}>Extensions</Text>
      <Text size="xs" color="dimmed" mb={12}>
        Extension entries are loaded from subfolders under <code>extensions/</code> that contain <code>extension.json5</code>.
      </Text>
      {extensionsError && (
        <Text size="sm" color="red" mb={12}>{extensionsError}</Text>
      )}
      {extensionsLoading && (
        <Text size="sm" color="dimmed" mb={12}>Loading extensions...</Text>
      )}
      {!extensionsLoading && extensions.length === 0 && !extensionsError && (
        <Text size="sm" color="dimmed">No extensions found.</Text>
      )}
      {extensions.map((ext) => (
        <div
          key={ext.dir}
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            border: `1px solid ${theme.colors.gray[3]}`, borderRadius: 8, padding: '10px 12px', marginBottom: 8,
            background: theme.colorScheme === 'dark' ? theme.colors.dark[7] : '#fff',
            gap: 12,
          }}
        >
          <div style={{ minWidth: 0, flex: 1 }}>
            <Text size="sm" weight={600}>{ext.name}</Text>
            <Text size="xs" color="dimmed">{ext.description}</Text>
            <Text size="xs" color="dimmed">Type: {ext.type}</Text>
            {ext.version && (
              <Text size="xs" color="dimmed">Version: {ext.version}</Text>
            )}
            {ext.license && (
              <Text size="xs" color="dimmed">License: {ext.license}</Text>
            )}
            {ext.type === 'prompt' && ext.prompt && (
              <Text size="xs" color="dimmed">Prompt: configured</Text>
            )}
            {ext.type === 'skill' && ext.skill && (
              <Text size="xs" color="dimmed">Skill: {ext.skill}</Text>
            )}
            {ext.type === 'script' && (
              <Text size="xs" color="dimmed">Script: {ext.script || 'extension.py'}</Text>
            )}
            {extensionActionOutput[ext.dir] && (
              <pre style={{
                fontSize: 11, padding: 10, borderRadius: 6, maxHeight: 180, overflowY: 'auto',
                background: theme.colorScheme === 'dark' ? theme.colors.dark[8] : theme.colors.gray[1],
                border: `1px solid ${theme.colors.gray[3]}`, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                marginTop: 8,
              }}>
                {extensionActionOutput[ext.dir]}
              </pre>
            )}
          </div>
          <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
            {ext.installed && ext.entrypoint && ext.entrypoint.endsWith('.html') && (
              <button
                type="button"
                onClick={() => {
                  const staticUrl = `${API_BASE_URL}/config/extensions/${encodeURIComponent(ext.dir)}/static/`;
                  window.open(staticUrl, '_blank');
                }}
                style={{
                  padding: '5px 14px', fontSize: 12, fontWeight: 600, borderRadius: 8, cursor: 'pointer',
                  border: `1px solid ${theme.colors.teal[5]}`, background: theme.colors.teal[6], color: '#fff',
                }}
              >
                View
              </button>
            )}
            {ext.type === 'script' ? (
              ext.installed ? (
                <>
                  {(['update', 'uninstall'] as const).map((action) => {
                    const activeAction = extensionActionLoading[ext.dir];
                    const busy = activeAction === action;
                    const anyBusy = Boolean(activeAction);
                    return (
                      <button
                        key={action}
                        type="button"
                        onClick={() => void runScriptExtensionAction(ext, action)}
                        disabled={anyBusy}
                        style={{
                          padding: '5px 14px', fontSize: 12, fontWeight: 600, borderRadius: 8,
                          cursor: anyBusy ? 'not-allowed' : 'pointer',
                          border: `1px solid ${theme.colors.blue[5]}`, background: theme.colors.blue[6], color: '#fff',
                        }}
                      >
                        {busy ? `${action[0].toUpperCase()}${action.slice(1)}...` : `${action[0].toUpperCase()}${action.slice(1)}`}
                      </button>
                    );
                  })}
                </>
              ) : (
                (() => {
                  const activeAction = extensionActionLoading[ext.dir];
                  const busy = activeAction === 'install';
                  const anyBusy = Boolean(activeAction);
                  return (
                    <button
                      type="button"
                      onClick={() => void runScriptExtensionAction(ext, 'install')}
                      disabled={anyBusy}
                      style={{
                        padding: '5px 14px', fontSize: 12, fontWeight: 600, borderRadius: 8,
                        cursor: anyBusy ? 'not-allowed' : 'pointer',
                        border: `1px solid ${theme.colors.blue[5]}`, background: theme.colors.blue[6], color: '#fff',
                      }}
                    >
                      {busy ? 'Installing...' : 'Install'}
                    </button>
                  );
                })()
              )
            ) : (
              <button
                type="button"
                onClick={() => extensionInstall(ext)}
                style={{
                  padding: '5px 14px', fontSize: 12, fontWeight: 600, borderRadius: 8, cursor: 'pointer',
                  border: `1px solid ${theme.colors.blue[5]}`, background: theme.colors.blue[6], color: '#fff',
                }}
              >
                Install
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );

  const renderAiSecurityView = () => {
    const sec = securitySettings.security || {
      schedules: { sandbox: true, auto: true, network: true },
      newSession: { sandbox: false, auto: false, network: true },
      remoteBot: { sandbox: true, auto: true, network: false },
      devSwarm: { sandbox: true, auto: true, network: true },
      skillAgent: {},
    };
    const getSkillAgentFlags = (providerId: string): SecurityFlags => ({
      sandbox: sec.skillAgent?.[providerId]?.sandbox ?? true,
      auto: sec.skillAgent?.[providerId]?.auto ?? true,
      network: sec.skillAgent?.[providerId]?.network ?? true,
    });

    const updateSec = (section: FixedSecuritySection, field: keyof SecurityFlags, value: boolean) => {
      setSecuritySettings((prev) => ({
        ...prev,
        security: {
          ...prev.security,
          [section]: {
            ...prev.security[section],
            [field]: value,
          },
        },
      }));
    };
    const updateSkillAgent = (providerId: string, field: keyof SecurityFlags, value: boolean) => {
      setSecuritySettings((prev) => ({
        ...prev,
        security: {
          ...prev.security,
          skillAgent: {
            ...(prev.security.skillAgent || {}),
            [providerId]: {
              sandbox: prev.security.skillAgent?.[providerId]?.sandbox ?? true,
              auto: prev.security.skillAgent?.[providerId]?.auto ?? true,
              network: prev.security.skillAgent?.[providerId]?.network ?? true,
              [field]: value,
            },
          },
        },
      }));
    };

    const saveSecurity = async () => {
      setSecuritySaving(true);
      try {
        await axios.post(`${API_BASE_URL}/config/settings`, securitySettings);
        setNewSessionSandbox(securitySettings.security.newSession.sandbox);
        setNewSessionAuto(securitySettings.security.newSession.auto);
        setNewSessionNetwork(securitySettings.security.newSession.network);
      } catch (err) {
        console.error('Failed to save security settings:', err);
      } finally {
        setSecuritySaving(false);
      }
    };

    const enableEnvSafeguard = async () => {
      setEnvSafeguardBusy(true);
      setEnvSafeguardMessage('');
      try {
        const statusRes = await axios.get(`${API_BASE_URL}/config/env-safeguard-status`);
        const status: EnvSafeguardStatus = statusRes.data || { enabled: false, exists: false };

        if (status.enabled) {
          setEnvSafeguardEnabled(true);
          setEnvSafeguardMessage('Safe guard already enabled for config/.env.');
          return;
        }
        if (!status.exists) {
          setEnvSafeguardEnabled(false);
          setEnvSafeguardMessage('config/.env not found. Create it before enabling safe guard.');
          return;
        }

        const command = 'bash -c core/bin/keys-safe-guard';

        const res = await axios.post(`${API_BASE_URL}/terminal/tmux/create`, { command });
        const sessionName = String(res.data?.session?.name || '');
        if (sessionName) {
          window.open(`/terminal?session=${encodeURIComponent(sessionName)}`, '_blank');
          setEnvSafeguardMessage('Opened terminal for key safe guard. Complete sudo prompts there.');
        } else {
          setEnvSafeguardMessage('Failed to open terminal for key safe guard.');
        }
      } catch (err: any) {
        setEnvSafeguardMessage(err?.response?.data?.error || 'Failed to enable key safe guard.');
      } finally {
        setEnvSafeguardBusy(false);
        await fetchEnvSafeguardStatus();
      }
    };

    const flagLabels: { key: keyof SecurityFlags; label: string }[] = [
      { key: 'sandbox', label: 'Sandbox' },
      { key: 'auto', label: 'Auto Run (Yolo)' },
      { key: 'network', label: 'Network Access' },
    ];

    return (
      <div style={{ padding: 16 }}>
        <Text size="lg" weight={700} mb={4}>AI & Security Settings</Text>

        <div
          style={{
            border: `1px solid ${theme.colors.gray[3]}`,
            borderRadius: 8,
            padding: '12px 16px',
            marginBottom: 12,
            background: theme.colorScheme === 'dark' ? theme.colors.dark[7] : '#fff',
          }}
        >
          <Text size="sm" weight={700}>Key Safe Guard</Text>
          <Text size="xs" color="dimmed" mt={4}>
            Protect `config/.env` by making it root-owned with `600` permissions.
            If not enabled, this opens a terminal and runs `bash -c core/bin/keys-safe-guard`
            so you can enter your sudo password interactively.
          </Text>
          <Group spacing="xs" mt={8}>
            <button
              type="button"
              onClick={() => void enableEnvSafeguard()}
              disabled={envSafeguardBusy}
              style={{
                padding: '6px 14px',
                fontSize: 12,
                fontWeight: 600,
                borderRadius: 8,
                cursor: envSafeguardBusy ? 'not-allowed' : 'pointer',
                border: `1px solid ${envSafeguardEnabled ? theme.colors.teal[6] : theme.colors.blue[5]}`,
                background: envSafeguardEnabled ? theme.colors.teal[6] : theme.colors.blue[6],
                color: '#fff',
              }}
            >
              {envSafeguardBusy ? 'Checking...' : envSafeguardEnabled ? 'Safe Guard Enabled' : 'Enable Safe Guard'}
            </button>
            {envSafeguardMessage && <Text size="xs" color="dimmed">{envSafeguardMessage}</Text>}
          </Group>
        </div>

        <div style={{ marginBottom: 16 }}>
          <Select
            label="Default AI Provider"
            placeholder="Select default provider"
            value={defaultLlmProvider || null}
            onChange={(value) => { if (value) void handleDefaultProviderChange(value); }}
            data={llmProviders.map((p) => ({ value: p.id, label: p.name }))}
            size="xs"
            style={{ maxWidth: 300 }}
          />
        </div>

        <div style={{ marginBottom: 16 }}>
          <Select
            label="Default AI Doctor Provider"
            placeholder="Select default doctor provider"
            value={defaultDoctorProvider || null}
            onChange={(value) => { if (value) void handleDefaultProviderChange(value, 'doctor'); }}
            data={llmProviders.map((p) => ({ value: p.id, label: p.name }))}
            size="xs"
            style={{ maxWidth: 300 }}
          />
        </div>

        <Text size="sm" weight={700} mb={8}>Permissions</Text>

        {llmProviders.map((provider) => (
          <div
            key={provider.id}
            style={{
              border: `1px solid ${theme.colors.gray[3]}`,
              borderRadius: 8,
              padding: '12px 16px',
              marginBottom: 12,
              background: theme.colorScheme === 'dark' ? theme.colors.dark[7] : '#fff',
            }}
          >
            <Text size="sm" weight={700} mb={8}>{provider.name} ({provider.id})</Text>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                {SECURITY_SECTION_DEFS.map((section) => (
                  <div key={`${provider.id}-${section.key}`}>
                    <Text size="xs" weight={600} color="dimmed" mb={4}>{section.label}</Text>
                    <Group spacing="md">
                      {flagLabels.map((f) => (
                        <Checkbox
                          key={`${section.key}-${provider.id}-${f.key}`}
                          label={f.label}
                          checked={sec[section.key]?.[f.key] ?? section.defaults[f.key]}
                          onChange={(e) => updateSec(section.key, f.key, e.currentTarget.checked)}
                          size="xs"
                        />
                      ))}
                    </Group>
                  </div>
                ))}
              </div>
              <div>
                <Text size="xs" weight={600} color="dimmed" mb={4}>Skill Agent</Text>
                <Group spacing="md">
                  {flagLabels.map((f) => (
                    <Checkbox
                      key={`skill-agent-${provider.id}-${f.key}`}
                      label={f.label}
                      checked={getSkillAgentFlags(provider.id)[f.key]}
                      onChange={(e) => updateSkillAgent(provider.id, f.key, e.currentTarget.checked)}
                      size="xs"
                    />
                  ))}
                </Group>
              </div>
            </div>

            {provider.id === 'opencode' && (
              <Text size="xs" color="dimmed" mt={8} italic>
                Yolo mode uses OPENCODE_CONFIG environment variable
              </Text>
            )}
          </div>
        ))}

        <button
          type="button"
          onClick={() => void saveSecurity()}
          disabled={securitySaving}
          style={{
            padding: '8px 24px',
            fontSize: 13,
            fontWeight: 600,
            borderRadius: 8,
            cursor: securitySaving ? 'not-allowed' : 'pointer',
            border: `1px solid ${theme.colors.blue[5]}`,
            background: theme.colors.blue[6],
            color: '#fff',
            marginTop: 8,
          }}
        >
          {securitySaving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    );
  };

  const PROFILE_KNOWN_FIELDS: { key: string; label: string; type: 'select' | 'text'; options?: string[] }[] = [
    { key: 'name', label: 'Name', type: 'text' },
    { key: 'age', label: 'Age', type: 'text' },
    { key: 'gender', label: 'Gender', type: 'select', options: ['male', 'female', 'undisclosed'] },
    { key: 'country', label: 'Country', type: 'text' },
    { key: 'state', label: 'State', type: 'text' },
    { key: 'city', label: 'City', type: 'text' },
    { key: 'school', label: 'School', type: 'text' },
    { key: 'department', label: 'Department', type: 'text' },
    { key: 'grade', label: 'Grade', type: 'text' },
    { key: 'timezone', label: 'Timezone', type: 'text' },
  ];

  const profileKnownKeys = new Set(PROFILE_KNOWN_FIELDS.map((f) => f.key));

  const profileSave = async () => {
    setProfileSaving(true);
    setProfileError('');
    try {
      const cleaned: Record<string, string> = {};
      for (const [k, v] of Object.entries(profileData)) {
        if (v.trim()) cleaned[k] = v.trim();
      }
      await axios.post(`${API_BASE_URL}/config/profile`, cleaned);
    } catch (err: any) {
      const msg = err?.response?.data?.error || 'Failed to save profile';
      setProfileError(msg);
      console.error('Failed to save profile:', err);
    } finally {
      setProfileSaving(false);
    }
  };

  const profileSetField = (key: string, value: string) => {
    setProfileData((prev) => ({ ...prev, [key]: value }));
  };

  const profileRemoveField = (key: string) => {
    setProfileData((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
  };

  const profileAddKnownField = (key: string) => {
    if (key && !(key in profileData)) {
      setProfileData((prev) => ({ ...prev, [key]: '' }));
    }
  };

  const profileAddCustomField = () => {
    const key = profileAddField.trim().toLowerCase().replace(/\s+/g, '_');
    if (key && !(key in profileData)) {
      setProfileData((prev) => ({ ...prev, [key]: '' }));
      setProfileAddField('');
    }
  };

  const renderProfileView = () => {
    const activeKeys = Object.keys(profileData).filter((k) => k !== 'intro' && k !== 'timezone');
    const availableKnown = PROFILE_KNOWN_FIELDS.filter((f) => f.key !== 'timezone' && !(f.key in profileData));
    const customKeys = activeKeys.filter((k) => !profileKnownKeys.has(k));

    const inputStyle = {
      width: '100%', padding: '6px 8px', fontSize: 13, borderRadius: 6,
      border: `1px solid ${theme.colors.gray[3]}`,
      background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff',
      color: 'inherit',
    };

    return (
      <div style={{ padding: 16, maxWidth: 600 }}>
        <Text size="lg" weight={700} mb={16}>Profile</Text>

        {activeKeys.map((key) => {
          const known = PROFILE_KNOWN_FIELDS.find((f) => f.key === key);
          const label = known?.label || key;
          return (
            <div key={key} style={{ marginBottom: 12 }}>
              <Group position="apart" mb={4}>
                <Text size="sm" weight={600}>{label}</Text>
                <button
                  type="button"
                  onClick={() => profileRemoveField(key)}
                  style={{
                    border: 'none', background: 'transparent', cursor: 'pointer',
                    color: theme.colors.red[5], fontSize: 12, padding: 0,
                  }}
                >
                  Remove
                </button>
              </Group>
              {known?.type === 'select' && known.options ? (
                <select
                  value={profileData[key] || ''}
                  onChange={(e) => profileSetField(key, e.target.value)}
                  style={inputStyle}
                >
                  <option value="">-- Select --</option>
                  {known.options.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  value={profileData[key] || ''}
                  onChange={(e) => profileSetField(key, e.target.value)}
                  placeholder={label}
                  style={inputStyle}
                />
              )}
            </div>
          );
        })}

        <div style={{
          marginBottom: 16, padding: '10px 12px', borderRadius: 8,
          border: `1px dashed ${theme.colors.gray[4]}`,
          background: theme.colorScheme === 'dark' ? theme.colors.dark[8] : theme.colors.gray[0],
        }}>
          <Text size="xs" weight={600} color="dimmed" mb={6}>Add Field</Text>
          {availableKnown.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
              {availableKnown.map((f) => (
                <button
                  key={f.key}
                  type="button"
                  onClick={() => profileAddKnownField(f.key)}
                  style={{
                    padding: '3px 10px', fontSize: 12, borderRadius: 6, cursor: 'pointer',
                    border: `1px solid ${theme.colors.gray[4]}`,
                    background: theme.colorScheme === 'dark' ? theme.colors.dark[5] : '#fff',
                    color: 'inherit',
                  }}
                >
                  + {f.label}
                </button>
              ))}
            </div>
          )}
          <div style={{ display: 'flex', gap: 6 }}>
            <input
              type="text"
              value={profileAddField}
              onChange={(e) => setProfileAddField(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') profileAddCustomField(); }}
              placeholder="Custom field name..."
              style={{ ...inputStyle, flex: 1 }}
            />
            <button
              type="button"
              onClick={profileAddCustomField}
              disabled={!profileAddField.trim()}
              style={{
                padding: '4px 12px', fontSize: 12, borderRadius: 6, cursor: !profileAddField.trim() ? 'not-allowed' : 'pointer',
                border: `1px solid ${theme.colors.blue[5]}`, background: theme.colors.blue[6], color: '#fff',
                opacity: !profileAddField.trim() ? 0.5 : 1,
              }}
            >
              Add
            </button>
          </div>
        </div>

        {(() => {
          const tzValue = profileData.timezone || '';
          const query = tzValue.toLowerCase();
          const filtered = query
            ? timezoneList.filter((tz) => tz.toLowerCase().includes(query))
            : [];
          const exactMatch = timezoneList.includes(tzValue);
          const showDropdown = timezoneFocused && query.length > 0 && filtered.length > 0 && !exactMatch;
          return (
            <div style={{ marginBottom: 12, position: 'relative' }}>
              <Text size="sm" weight={600} mb={4}>Timezone</Text>
              <input
                type="text"
                value={tzValue}
                onChange={(e) => { profileSetField('timezone', e.target.value); setProfileError(''); }}
                onFocus={() => setTimezoneFocused(true)}
                onBlur={() => setTimeout(() => setTimezoneFocused(false), 150)}
                placeholder="Type to search timezones... e.g. Tokyo, New_York"
                style={{
                  ...inputStyle,
                  borderColor: tzValue && !exactMatch ? theme.colors.orange[5] : theme.colors.gray[3],
                }}
              />
              {tzValue && !exactMatch && !timezoneFocused && (
                <Text size="xs" color="orange" mt={2}>Unknown timezone — type to search or enter a valid IANA timezone</Text>
              )}
              {showDropdown && (
                <div style={{
                  position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 10,
                  maxHeight: 200, overflowY: 'auto', borderRadius: 6, marginTop: 2,
                  border: `1px solid ${theme.colors.gray[3]}`,
                  background: theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                }}>
                  {filtered.map((tz) => {
                    const idx = tz.toLowerCase().indexOf(query);
                    return (
                      <div
                        key={tz}
                        onMouseDown={() => { profileSetField('timezone', tz); setProfileError(''); }}
                        style={{
                          padding: '6px 10px', fontSize: 13, cursor: 'pointer',
                          background: tz === tzValue
                            ? (theme.colorScheme === 'dark' ? theme.colors.dark[4] : theme.colors.blue[0])
                            : 'transparent',
                        }}
                      >
                        {idx >= 0 ? (
                          <>{tz.slice(0, idx)}<strong>{tz.slice(idx, idx + query.length)}</strong>{tz.slice(idx + query.length)}</>
                        ) : tz}
                      </div>
                    );
                  })}
                </div>
              )}
              <Text size="xs" color="dimmed" mt={2}>
                Used for scheduling. Auto-detected from your browser if empty.
              </Text>
            </div>
          );
        })()}

        <div style={{ marginBottom: 16 }}>
          <Text size="sm" weight={600} mb={4}>About Yourself</Text>
          <textarea
            value={profileData.intro || ''}
            onChange={(e) => profileSetField('intro', e.target.value)}
            placeholder="Tell us about yourself, your interests, learning goals..."
            rows={5}
            style={{
              ...inputStyle,
              fontFamily: 'inherit', resize: 'vertical', lineHeight: 1.5,
            }}
          />
        </div>

        {profileError && <Text size="xs" color="red" mb={8}>{profileError}</Text>}

        <button
          type="button"
          onClick={() => void profileSave()}
          disabled={profileSaving}
          style={{
            padding: '8px 24px', fontSize: 13, fontWeight: 600, borderRadius: 8,
            cursor: profileSaving ? 'not-allowed' : 'pointer',
            border: `1px solid ${theme.colors.blue[5]}`, background: theme.colors.blue[6], color: '#fff',
          }}
        >
          {profileSaving ? 'Saving...' : 'Save Profile'}
        </button>

        <Text size="xs" color="dimmed" mt={16} style={{ lineHeight: 1.5 }}>
          Your profile helps personalize course creation, real-time feedback, and AI interactions.
          Information like your school, grade, and department allows the AI to tailor content
          to your level, as if you were receiving guidance from a tutor in your own classroom.
        </Text>
      </div>
    );
  };

  const renderMainContent = () => {
    switch (activeView) {
      case 'explore':
        return <ExploreView />;
      case 'home':
        return renderHomeView();
      case 'live-terminal':
        return renderLiveTerminalView();
      case 'learning':
        return renderPlaceholder('Learning');
      case 'projects':
        return renderPlaceholder('Projects');
      case 'research':
        return renderPlaceholder('Research');
      case 'tasks':
        return renderPlaceholder('Tasks');
      case 'media':
        return renderPlaceholder('Media');
      case 'development':
        return renderPlaceholder('Development');
      case 'processes':
        return renderProcessesView();
      case 'discord-bot':
        return renderDiscordBotView();
      case 'skills':
        return renderSkillsView();
      case 'mcp-servers':
        return renderMcpServersView();
      case 'schedule':
        return renderScheduleView();
      case 'extensions':
        return renderExtensionsView();
      case 'ai-security':
        return renderAiSecurityView();
      case 'profile':
        return renderProfileView();
      default:
        return <ExploreView />;
    }
  };

  return (
    <AppShell
      padding={0}
      styles={{
        main: {
          background: theme.colorScheme === 'dark' ? theme.colors.dark[8] : theme.colors.gray[0],
        },
      }}
      navbarOffsetBreakpoint="sm"
      navbar={
        <Navbar
          p="xs"
          hiddenBreakpoint="sm"
          hidden={!opened}
          width={{ sm: 240 }}
        >
          <Navbar.Section grow component={ScrollArea}>
            {renderNavItems()}
          </Navbar.Section>
        </Navbar>
      }
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
                <Burger
                  opened={opened}
                  onClick={() => setOpened((o) => !o)}
                  size="sm"
                  color={theme.colors.gray[6]}
                  mr="xl"
                />
              </MediaQuery>
              <a href="/" style={{ display: 'flex', alignItems: 'center' }}>
                <img className="h-10" src="/images/skill-pilot-2.png" alt="Skill Pilot" />
              </a>
            </div>

            <Group spacing="xs">
              <Select
                placeholder="LLM"
                value={llmProvider}
                disabled={Boolean(newSessionWorkflow)}
                onChange={(value) => {
                  if (!value) return;
                  setLlmProvider(value);
                  setSelectedProvider(value);
                  const provider = llmProviders.find((p) => p.id === value);
                  setSelectedModel(provider?.models?.[0] || null);
                  setSelectedEffort(null);
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
        <title>Skill Pilot</title>
      </Head>

      <div style={{ height: 'calc(100vh - 60px)', overflowY: 'auto', overflowX: 'hidden' }}>
        {renderMainContent()}
      </div>
    </AppShell>
  );
}

export const getStaticProps = async (context: GetStaticPropsContext) => {
  return {
    props: {
      ...(await serverSideTranslations(context.locale ?? 'en', [
        'common',
      ]))
    }
  }
}
