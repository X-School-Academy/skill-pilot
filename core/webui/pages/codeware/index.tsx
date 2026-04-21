import React, { useEffect, useRef, useState } from 'react';
import { GetStaticPropsContext } from 'next';
import axios from 'axios';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';
import {
  Anchor,
  Box,
  Button,
  Checkbox,
  Code,
  Divider,
  Group,
  Loader,
  LoadingOverlay,
  Stack,
  Tabs,
  Text,
  TextInput,
  Title,
  useMantineTheme,
} from '@mantine/core';
import {
  IconExternalLink,
  IconGitBranch,
  IconHammer,
  IconInfoCircle,
  IconFolder,
  IconPlayerPlay,
  IconRefresh,
  IconTrash,
} from '@tabler/icons-react';
import MainLayout from '../../components/main-layout';
import EmbeddedSessionPanel, { WorkflowExecuteStatus } from '../../components/EmbeddedSessionPanel';
import { apiUrl } from '../../libs/api-base';
import { getSelectedProvider } from '../../libs/llm';

const API_BASE_URL = apiUrl('/api');
axios.defaults.withCredentials = true;

interface AboutInfo {
  version: string;
  build: number | null;
  path: string;
  runtime_mode?: string;
}

interface WorkspaceRemote {
  url: string;
  is_sample: boolean;
  sample_url: string;
}

interface WorktreeEntry {
  path: string;
  name: string;
  branch: string;
  head: string;
  is_main: boolean;
  detached: boolean;
}

type CoreTab = 'codeware' | 'workspace' | 'worktree' | 'about';

interface CodewareAction {
  key: 'update' | 'restore' | 'add remote' | 'contribute';
  label: string;
  description: string;
  variant?: 'filled' | 'light' | 'default';
  color?: string;
}

const CODEWARE_ACTIONS: CodewareAction[] = [
  {
    key: 'update',
    label: 'Update',
    description: 'Pull the latest official codeware into your user branch and apply any pending upgrade notices.',
  },
  {
    key: 'restore',
    label: 'Restore',
    description: 'Reset your user branch back to the official codeware, backing up local work first.',
    variant: 'light',
    color: 'orange',
  },
  {
    key: 'add remote',
    label: 'Link to My Repos',
    description: 'Attach your personal GitHub fork as the origin remote so your changes have a home.',
    variant: 'default',
  },
  {
    key: 'contribute',
    label: 'Contribute',
    description: 'Create a clean contribution branch, push to your fork, and open a pull request upstream.',
    variant: 'default',
  },
];

const CODEWARE_PROMPTS: Record<CodewareAction['key'], string> = {
  update:
    'Use the codeware-management agent skill to update the codeware: merge the latest official upstream/codeware into the local user branch, then walk and apply any pending upgrade notices.',
  restore:
    'Use the codeware-management agent skill to restore the user branch from the official codeware branch, backing up local work first, then walk and apply any pending upgrade notices.',
  'add remote':
    'Use the codeware-management agent skill to add or fix my personal GitHub fork as the origin remote (add remote flow). Ask me for the fork URL if you do not already have it.',
  contribute:
    'Use the codeware-management agent skill to create a clean contribution branch from upstream/contrib, push it to my fork, and open a pull request. Ask me which feature or fix I want to contribute and include a brief description in the PR.',
};

export default function CodewarePage() {
  const theme = useMantineTheme();
  const [activeTab, setActiveTab] = useState<CoreTab>('codeware');

  const [aboutInfo, setAboutInfo] = useState<AboutInfo | null>(null);
  const [aboutLoading, setAboutLoading] = useState(false);
  const [aboutError, setAboutError] = useState('');
  const [runtimeMode, setRuntimeMode] = useState<string>('production');
  const isProdRuntime = runtimeMode === 'production';

  const [workspaceRemote, setWorkspaceRemote] = useState<WorkspaceRemote | null>(null);
  const [workspaceLoading, setWorkspaceLoading] = useState(false);
  const [workspaceError, setWorkspaceError] = useState('');

  const [worktrees, setWorktrees] = useState<WorktreeEntry[]>([]);
  const [worktreesLoading, setWorktreesLoading] = useState(false);
  const [worktreesError, setWorktreesError] = useState('');
  const [newWorktreeName, setNewWorktreeName] = useState('');
  const [creatingWorktree, setCreatingWorktree] = useState(false);
  const [removingPath, setRemovingPath] = useState<string | null>(null);

  const [devStarting, setDevStarting] = useState(false);
  const [devStatus, setDevStatus] = useState('');
  const [devError, setDevError] = useState('');
  const [devUrl, setDevUrl] = useState('');
  const [devReady, setDevReady] = useState(false);
  const [devPolling, setDevPolling] = useState(false);
  const devPollCancelRef = useRef<boolean>(false);
  const [restartRebuildWebui, setRestartRebuildWebui] = useState(false);
  const [restartStarting, setRestartStarting] = useState(false);
  const [restartStatus, setRestartStatus] = useState('');
  const [restartError, setRestartError] = useState('');

  const [sessionPanelOpen, setSessionPanelOpen] = useState(false);
  const [sessionPanelHeight, setSessionPanelHeight] = useState(50);
  const [isSessionPanelResizing, setIsSessionPanelResizing] = useState(false);
  const [sessionPromptText, setSessionPromptText] = useState('');
  const [sessionLabel, setSessionLabel] = useState('Codeware action');
  const [newSessionSandbox, setNewSessionSandbox] = useState(false);
  const [newSessionAuto, setNewSessionAuto] = useState(false);
  const [newSessionNetwork, setNewSessionNetwork] = useState(true);
  const [newSessionNextNodeTrigger, setNewSessionNextNodeTrigger] = useState<'auto_continue' | 'start_by_prompt'>('auto_continue');
  const [newSessionWorkflowResumeAvailable] = useState(false);
  const [newSessionWorkflowResume, setNewSessionWorkflowResume] = useState(false);
  const [startingSession, setStartingSession] = useState(false);
  const [liveSessionName, setLiveSessionName] = useState<string | null>(null);
  const [workflowExecuteStatus] = useState<WorkflowExecuteStatus | null>(null);
  const [workflowSessionActive] = useState(false);
  const [continuingWorkflow] = useState(false);

  const rightPaneRef = useRef<HTMLDivElement | null>(null);

  const fetchAbout = async () => {
    setAboutLoading(true);
    setAboutError('');
    try {
      const res = await axios.get(`${API_BASE_URL}/codeware/about`);
      const data = res.data as AboutInfo;
      setAboutInfo(data);
      if (data.runtime_mode) setRuntimeMode(String(data.runtime_mode));
    } catch (err: any) {
      console.error('Failed to fetch about info:', err);
      setAboutError(err?.response?.data?.error || 'Failed to load About info.');
    } finally {
      setAboutLoading(false);
    }
  };

  const fetchWorkspaceRemote = async () => {
    setWorkspaceLoading(true);
    setWorkspaceError('');
    try {
      const res = await axios.get(`${API_BASE_URL}/codeware/workspace/remote`);
      setWorkspaceRemote(res.data as WorkspaceRemote);
    } catch (err: any) {
      console.error('Failed to fetch workspace remote:', err);
      setWorkspaceError(err?.response?.data?.error || 'Failed to load workspace remote.');
    } finally {
      setWorkspaceLoading(false);
    }
  };

  const fetchWorktrees = async () => {
    setWorktreesLoading(true);
    setWorktreesError('');
    try {
      const res = await axios.get(`${API_BASE_URL}/codeware/worktrees`);
      setWorktrees((res.data.items || []) as WorktreeEntry[]);
    } catch (err: any) {
      console.error('Failed to fetch worktrees:', err);
      setWorktreesError(err?.response?.data?.error || 'Failed to load worktrees.');
    } finally {
      setWorktreesLoading(false);
    }
  };

  useEffect(() => {
    fetchAbout();
    fetchWorkspaceRemote();
    fetchWorktrees();
    void axios.get(`${API_BASE_URL}/config/settings`).then((res) => {
      const security = res.data?.security?.newSession;
      if (!security) return;
      setNewSessionSandbox(Boolean(security.sandbox));
      setNewSessionAuto(Boolean(security.auto));
      setNewSessionNetwork(security.network !== false);
    }).catch(() => undefined);
    return () => {
      devPollCancelRef.current = true;
    };
  }, []);

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

  const openSessionWithPrompt = (label: string, prompt: string) => {
    setSessionLabel(label);
    setSessionPromptText(prompt);
    setLiveSessionName(null);
    setNewSessionNextNodeTrigger('auto_continue');
    setNewSessionWorkflowResume(false);
    setSessionPanelHeight(50);
    setSessionPanelOpen(true);
  };

  const closeSessionPanel = () => {
    setSessionPanelOpen(false);
    setIsSessionPanelResizing(false);
    setLiveSessionName(null);
    setStartingSession(false);
  };

  const handleStartSession = async (path?: string) => {
    const trimmedPrompt = sessionPromptText.trim();
    if (!trimmedPrompt || startingSession) return;
    const provider = getSelectedProvider() || 'gemini';
    setStartingSession(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/terminal/tmux/create`, {
        provider_id: provider,
        prompt: trimmedPrompt,
        path: path || undefined,
        sandbox: newSessionSandbox,
        auto: newSessionAuto,
        network: newSessionNetwork,
      });
      const sessionName: string | undefined = res.data?.session?.name;
      if (sessionName) setLiveSessionName(sessionName);
    } catch (err) {
      console.error('Failed to start codeware session:', err);
    } finally {
      setStartingSession(false);
    }
  };

  const runCodewareAction = (operation: CodewareAction['key']) => {
    const labelMap: Record<CodewareAction['key'], string> = {
      update: 'Codeware: Update',
      restore: 'Codeware: Restore',
      'add remote': 'Codeware: Link to My Repos',
      contribute: 'Codeware: Contribute',
    };
    openSessionWithPrompt(labelMap[operation], CODEWARE_PROMPTS[operation]);
  };

  const runCreatePrivateWorkspaceRepo = () => {
    openSessionWithPrompt(
      'Workspace: Create Private Workspace Repo',
      'Use the codeware-management agent skill with the "create private workspace repo" operation to replace the sample workspace/ submodule with a new empty private GitHub repository I will provide, following the steps in workspace/README.md.',
    );
  };

  const createWorktree = async () => {
    const raw = newWorktreeName.trim();
    if (!raw) return;
    setCreatingWorktree(true);
    setWorktreesError('');
    try {
      await axios.post(`${API_BASE_URL}/codeware/worktrees/create`, { name: raw });
      setNewWorktreeName('');
      await fetchWorktrees();
    } catch (err: any) {
      console.error('Failed to create worktree:', err);
      setWorktreesError(err?.response?.data?.error || 'Failed to create worktree.');
    } finally {
      setCreatingWorktree(false);
    }
  };

  const removeWorktree = async (path: string) => {
    if (!window.confirm(`Remove worktree at ${path}?`)) return;
    setRemovingPath(path);
    setWorktreesError('');
    try {
      await axios.post(`${API_BASE_URL}/codeware/worktrees/remove`, { path });
      await fetchWorktrees();
    } catch (err: any) {
      console.error('Failed to remove worktree:', err);
      setWorktreesError(err?.response?.data?.error || 'Failed to remove worktree.');
    } finally {
      setRemovingPath(null);
    }
  };

  const pollDevReady = async (baseUrl: string) => {
    devPollCancelRef.current = false;
    setDevPolling(true);
    const deadline = Date.now() + 120000;
    try {
      while (!devPollCancelRef.current && Date.now() < deadline) {
        await new Promise((resolve) => window.setTimeout(resolve, 1500));
        if (devPollCancelRef.current) return;
        try {
          const res = await axios.get(`${API_BASE_URL}/codeware/dev/status`);
          if (res.data?.ready) {
            setDevReady(true);
            setDevUrl(String(res.data.dev_url || baseUrl));
            setDevStatus('Dev instance is ready.');
            return;
          }
        } catch (err) {
          // Engine may be momentarily unavailable while dev starts; keep polling.
        }
      }
      if (!devPollCancelRef.current) {
        setDevError('Timed out waiting for the dev instance to become ready.');
      }
    } finally {
      setDevPolling(false);
    }
  };

  const handleStartDev = async () => {
    if (devStarting || devPolling) return;
    setDevStarting(true);
    setDevError('');
    setDevReady(false);
    setDevUrl('');
    setDevStatus('Starting Skill Pilot in development mode...');
    try {
      const res = await axios.post(`${API_BASE_URL}/codeware/dev/start`, {});
      const url = String(res.data?.dev_url || '');
      setDevUrl(url);
      setDevStatus('Waiting for the dev instance to come online...');
      await pollDevReady(url);
    } catch (err: any) {
      setDevError(err?.response?.data?.error || 'Failed to start dev mode.');
      setDevStatus('');
    } finally {
      setDevStarting(false);
    }
  };

  const handleRestartProd = async () => {
    if (restartStarting || devStarting || devPolling) return;
    setRestartStarting(true);
    setRestartError('');
    setRestartStatus(
      restartRebuildWebui
        ? 'Rebuilding WebUI, then restarting Skill Pilot...'
        : 'Restarting Skill Pilot...',
    );
    try {
      const res = await axios.post(`${API_BASE_URL}/codeware/prod/restart`, {
        rebuild_webui: restartRebuildWebui,
      });
      const buildCommitMessage = String(res.data?.build_commit?.message || '').trim();
      const baseMessage = 'Restart requested. This instance will stop and the new WebUI will open when it is ready.';
      setRestartStatus(buildCommitMessage ? `${buildCommitMessage} ${baseMessage}` : baseMessage);
    } catch (err: any) {
      setRestartError(err?.response?.data?.error || 'Failed to restart Skill Pilot.');
      setRestartStatus('');
    } finally {
      setRestartStarting(false);
    }
  };

  const renderAbout = () => (
    <Box style={{ padding: '24px 28px', position: 'relative' }}>
      <LoadingOverlay visible={aboutLoading} overlayBlur={2} />
      <Title order={3} mb="md">About</Title>
      {aboutError && <Text color="red" mb="md">{aboutError}</Text>}
      <Stack spacing={18}>
        <Stack spacing={4}>
          <Title order={4}>Skill Pilot</Title>
          <Text size="sm" color="dimmed">
            An AI-first platform where humans and AI agents build, learn, and ship software together.
          </Text>
          <Anchor href="https://skill-pilot.ai" target="_blank" rel="noopener noreferrer" size="sm">
            https://skill-pilot.ai
          </Anchor>
        </Stack>

        {aboutInfo && (
          <Stack spacing={8}>
            <Group spacing={8}><Text weight={600} style={{ width: 120 }}>Version</Text><Code>{aboutInfo.version || '(unknown)'}</Code></Group>
            <Group spacing={8}><Text weight={600} style={{ width: 120 }}>Build</Text><Code>{aboutInfo.build == null ? '(unknown)' : String(aboutInfo.build)}</Code></Group>
            <Group spacing={8}><Text weight={600} style={{ width: 120 }}>Runtime mode</Text><Code>{runtimeMode}</Code></Group>
            <Group spacing={8}><Text weight={600} style={{ width: 120 }}>Source</Text><Text size="sm" color="dimmed">{aboutInfo.path}</Text></Group>
          </Stack>
        )}

        <Stack spacing={4}>
          <Title order={5}>License</Title>
          <Text size="sm">
            MIT License — Copyright (c) 2026 Frank He (
            <Anchor href="https://skill-pilot.ai" target="_blank" rel="noopener noreferrer">
              https://skill-pilot.ai
            </Anchor>
            )
          </Text>
          <Text size="xs" color="dimmed">
            Permission is hereby granted, free of charge, to any person obtaining a copy of this
            software and associated documentation files (the &quot;Software&quot;), to deal in the Software
            without restriction, including without limitation the rights to use, copy, modify, merge,
            publish, distribute, sublicense, and/or sell copies of the Software, subject to the
            conditions of the MIT License. The Software is provided &quot;as is&quot;, without warranty of any
            kind.
          </Text>
        </Stack>
      </Stack>
    </Box>
  );

  const renderCodeware = () => (
    <Box style={{ padding: '24px 28px' }}>
      <Title order={3} mb="xs">Codeware</Title>
      <Text size="sm" mb="lg">
        <Text span weight={700}>Skill Pilot Codeware</Text> — a new form of software where AI and humans read,
        write, and evolve code together. Ship new features, polish what&apos;s here, fix bugs, and
        contribute back. Every action below opens a session pre-wired to the{' '}
        <Code>codeware-management</Code> agent skill.
      </Text>

      <Stack spacing="md">
        {CODEWARE_ACTIONS.map((action) => (
          <Group key={action.key} spacing="md" align="flex-start" noWrap>
            <Button
              variant={action.variant}
              color={action.color}
              onClick={() => runCodewareAction(action.key)}
              style={{ minWidth: 180 }}
            >
              {action.label}
            </Button>
            <Text size="sm" color="dimmed" style={{ flex: 1, paddingTop: 6 }}>
              {action.description}
            </Text>
          </Group>
        ))}
      </Stack>

      {isProdRuntime && (
        <>
          <Divider my="xl" label="Local development" labelPosition="center" />
          <Stack spacing="sm">
            <Text size="sm" color="dimmed">
              Start Skill Pilot in development mode (runs <Code>./skillpilot.sh start --dev</Code>) so
              you can hot-reload edits to <Code>core/webui</Code> and <Code>core/engine</Code>. A
              separate dev instance will launch alongside this prod instance.
            </Text>
            <Group spacing="md" align="center">
              <Button
                leftIcon={<IconPlayerPlay size="0.95rem" />}
                onClick={() => void handleStartDev()}
                loading={devStarting}
                disabled={devPolling || restartStarting}
              >
                Development
              </Button>
              {devPolling && (
                <Group spacing="xs">
                  <Loader size="xs" />
                  <Text size="xs" color="dimmed">{devStatus}</Text>
                </Group>
              )}
              {!devPolling && devStatus && !devReady && !devError && (
                <Text size="xs" color="dimmed">{devStatus}</Text>
              )}
            </Group>
            <Stack spacing={6} pt={4}>
              <Group spacing="md" align="center">
                <Button
                  variant="default"
                  leftIcon={<IconRefresh size="0.95rem" />}
                  onClick={() => void handleRestartProd()}
                  loading={restartStarting}
                  disabled={devStarting || devPolling}
                >
                  Restart Skill Pilot
                </Button>
                <Checkbox
                  label="Rebuild WebUI before restart"
                  checked={restartRebuildWebui}
                  onChange={(event) => setRestartRebuildWebui(event.currentTarget.checked)}
                  disabled={restartStarting || devStarting || devPolling}
                />
              </Group>
              <Text size="sm" color="dimmed">
                Restart Skill Pilot only after you update <Code>core/engine</Code> Python code and verify the change in
                development mode. Turn on <Code>Rebuild WebUI before restart</Code> only when you changed Next.js frontend
                code in <Code>core/webui</Code>. If restart fails, run <Code>./skillpilot.sh doctor</Code> for guided
                troubleshooting when you are unsure how to debug the issue.
              </Text>
            </Stack>
            {devReady && devUrl && (
              <Button
                component="a"
                href={devUrl}
                target="_blank"
                rel="noopener noreferrer"
                variant="light"
                leftIcon={<IconExternalLink size="0.9rem" />}
                style={{ width: 'fit-content' }}
              >
                Open Dev Instance ({devUrl})
              </Button>
            )}
            {devError && <Text size="sm" color="red">{devError}</Text>}
            {restartStatus && <Text size="sm" color="dimmed">{restartStatus}</Text>}
            {restartError && (
              <Text size="sm" color="red" style={{ whiteSpace: 'pre-wrap' }}>
                {restartError}
              </Text>
            )}
          </Stack>
        </>
      )}
    </Box>
  );

  const renderWorkspace = () => (
    <Box style={{ padding: '24px 28px', position: 'relative' }}>
      <LoadingOverlay visible={workspaceLoading} overlayBlur={2} />
      <Group position="apart" mb="md">
        <Title order={3}>Workspace</Title>
        <Button size="xs" variant="default" leftIcon={<IconRefresh size="0.9rem" />} onClick={() => void fetchWorkspaceRemote()}>Refresh</Button>
      </Group>
      <Text size="sm" color="dimmed" mb="md">
        Your <Code>workspace/</Code> folder is the private, version-controlled home for everything you
        create with Skill Pilot — courses, vibe-coding projects, research notes, tasks, and more.
        Keeping it in your own Git repo means your work stays private and travels with you across
        machines.
      </Text>
      {workspaceError && <Text color="red" mb="md">{workspaceError}</Text>}
      {workspaceRemote && (
        <Stack spacing={10}>
          <Group spacing={8} align="flex-start">
            <Text weight={600} style={{ width: 140 }}>Current remote</Text>
            <Code style={{ wordBreak: 'break-all', maxWidth: 640 }}>{workspaceRemote.url || '(none)'}</Code>
          </Group>
          {workspaceRemote.is_sample ? (
            <>
              <Text size="sm" color="dimmed" mt="sm">
                This workspace still points to the public sample repo. Replace it with your own private
                GitHub repository to keep your work version-controlled and private.
              </Text>
              <Group mt="sm">
                <Button onClick={runCreatePrivateWorkspaceRepo}>Create Private Workspace Repo</Button>
              </Group>
            </>
          ) : (
            <Text size="sm" color="dimmed" mt="sm">
              Workspace is linked to a personal remote. No action needed.
            </Text>
          )}
        </Stack>
      )}
    </Box>
  );

  const renderWorktree = () => (
    <Box style={{ padding: '24px 28px', position: 'relative' }}>
      <LoadingOverlay visible={worktreesLoading} overlayBlur={2} />
      <Group position="apart" mb="md">
        <Title order={3}>Worktrees</Title>
        <Button size="xs" variant="default" leftIcon={<IconRefresh size="0.9rem" />} onClick={() => void fetchWorktrees()}>Refresh</Button>
      </Group>
      {worktreesError && <Text color="red" mb="md">{worktreesError}</Text>}

      <Stack spacing={8} mb="xl">
        {worktrees.length === 0 && !worktreesLoading && (
          <Text size="sm" color="dimmed">No worktrees found.</Text>
        )}
        {worktrees.map((wt) => (
          <Group
            key={wt.path}
            position="apart"
            spacing="sm"
            style={{
              padding: '10px 12px',
              borderRadius: 8,
              border: `1px solid ${theme.colors.gray[3]}`,
              background: wt.is_main ? theme.colors.gray[0] : '#ffffff',
            }}
          >
            <Stack spacing={2} style={{ minWidth: 0, flex: 1 }}>
              <Group spacing={8}>
                <IconFolder size="0.95rem" color={theme.colors.blue[6]} />
                <Text weight={600} size="sm">{wt.name || wt.path}</Text>
                {wt.is_main && <Text size="xs" color="blue">main</Text>}
                {wt.detached && <Text size="xs" color="orange">detached</Text>}
              </Group>
              <Text size="xs" color="dimmed" style={{ wordBreak: 'break-all' }}>{wt.path}</Text>
              {wt.branch && <Text size="xs" color="dimmed">branch: {wt.branch}</Text>}
            </Stack>
            {!wt.is_main && (
              <Button
                size="xs"
                color="red"
                variant="light"
                leftIcon={<IconTrash size="0.9rem" />}
                loading={removingPath === wt.path}
                onClick={() => void removeWorktree(wt.path)}
              >
                Remove
              </Button>
            )}
          </Group>
        ))}
      </Stack>

      <Title order={5} mb={6}>Create Worktree</Title>
      <Text size="xs" color="dimmed" mb={8}>
        A new worktree will be created at <Code>../{'{repo}'}_{'{name}'}</Code> and fail if that folder already exists.
      </Text>
      <Group spacing="sm" align="flex-end">
        <TextInput
          placeholder="feature-name"
          value={newWorktreeName}
          onChange={(e) => setNewWorktreeName(e.currentTarget.value)}
          style={{ flex: 1, maxWidth: 320 }}
          disabled={creatingWorktree}
        />
        <Button
          leftIcon={<IconHammer size="0.95rem" />}
          onClick={() => void createWorktree()}
          loading={creatingWorktree}
          disabled={!newWorktreeName.trim()}
        >
          Create
        </Button>
      </Group>
    </Box>
  );

  return (
    <MainLayout title="Codeware">
      <div
        ref={rightPaneRef}
        style={{
          height: '100%',
          minWidth: 0,
          display: 'grid',
          gridTemplateRows: sessionPanelOpen ? `${100 - sessionPanelHeight}fr 12px ${sessionPanelHeight}fr` : '1fr',
          overflow: 'hidden',
          background: '#ffffff',
        }}
      >
        <div style={{ minHeight: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column', background: '#ffffff' }}>
          <Tabs
            value={activeTab}
            onTabChange={(value) => value && setActiveTab(value as CoreTab)}
            styles={{ tabsList: { padding: '0 18px', borderBottom: `1px solid ${theme.colors.gray[2]}`, background: '#f8fafc' } }}
          >
            <Tabs.List>
              <Tabs.Tab value="codeware" icon={<IconHammer size="0.9rem" />}>Codeware</Tabs.Tab>
              <Tabs.Tab value="workspace" icon={<IconFolder size="0.9rem" />}>Workspace</Tabs.Tab>
              {isProdRuntime && (
                <Tabs.Tab value="worktree" icon={<IconGitBranch size="0.9rem" />}>Worktree</Tabs.Tab>
              )}
              <Tabs.Tab value="about" icon={<IconInfoCircle size="0.9rem" />}>About</Tabs.Tab>
            </Tabs.List>
          </Tabs>
          <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
            {activeTab === 'codeware' && renderCodeware()}
            {activeTab === 'workspace' && renderWorkspace()}
            {activeTab === 'worktree' && isProdRuntime && renderWorktree()}
            {activeTab === 'about' && renderAbout()}
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
                currentLabel={sessionLabel}
                liveSessionName={liveSessionName}
                sessionPromptText={sessionPromptText}
                setSessionPromptText={setSessionPromptText}
                newSessionWorkflow={null}
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
                onContinueWorkflow={() => undefined}
              />
            </div>
          </>
        )}
      </div>
    </MainLayout>
  );
}

export async function getStaticProps({ locale }: GetStaticPropsContext) {
  return {
    props: {
      ...(await serverSideTranslations(locale ?? 'en', ['common'])),
    },
  };
}
