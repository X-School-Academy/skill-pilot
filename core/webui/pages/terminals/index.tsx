import React, { useCallback, useEffect, useRef, useState } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { GetStaticPropsContext } from 'next';
import axios from 'axios';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';
import {
  AppShell,
  Header,
  Navbar,
  NavLink,
  Divider,
  Select,
  Group,
  Text,
  useMantineTheme,
  MediaQuery,
  Burger,
  ScrollArea,
} from '@mantine/core';
import { apiUrl } from '../../libs/api-base';
import { resolveSelectedProvider, setSelectedProvider } from '../../libs/llm';
import { MAIN_NAV_ITEMS } from '../../libs/main-nav';

const API_BASE_URL = apiUrl('/api');

interface LlmProvider {
  id: string;
  name: string;
}

interface TmuxLiveSession {
  name: string;
  attached: boolean;
  created_at: number;
  windows: number;
}

interface NavItem {
  label: string;
  icon: React.ReactNode;
  dividerBefore?: string;
  active?: boolean;
  action?: () => void;
}

export default function TerminalsPage() {
  const router = useRouter();
  const theme = useMantineTheme();
  const isDevMode = process.env.NODE_ENV === 'development';
  const [opened, setOpened] = useState(false);
  const [llmProviders, setLlmProviders] = useState<LlmProvider[]>([]);
  const [llmProvider, setLlmProvider] = useState<string | null>(null);
  const [liveSessions, setLiveSessions] = useState<TmuxLiveSession[]>([]);
  const [activeSessionName, setActiveSessionName] = useState<string | null>(null);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [busyAction, setBusyAction] = useState<'create' | 'close' | null>(null);
  const [busySessionName, setBusySessionName] = useState<string | null>(null);
  const [sessionError, setSessionError] = useState<string>('');
  const queryBootstrappedRef = useRef(false);

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

  const fetchTmuxSessions = useCallback(async (quiet: boolean = false) => {
    if (!quiet) setLoadingSessions(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/terminal/tmux/sessions`);
      const sessions: TmuxLiveSession[] = res.data?.sessions || [];
      setLiveSessions(sessions);
      setActiveSessionName((prev) => {
        if (prev && sessions.some((session) => session.name === prev)) return prev;
        return null;
      });
      setSessionError('');
    } catch (err: any) {
      const message = err?.response?.data?.error || 'Failed to load live tmux sessions.';
      setSessionError(String(message));
    } finally {
      if (!quiet) setLoadingSessions(false);
    }
  }, []);

  const createTmuxSession = useCallback(async (command: string) => {
    setBusyAction('create');
    try {
      const res = await axios.post(`${API_BASE_URL}/terminal/tmux/create`, { command });
      const sessionName: string | undefined = res.data?.session?.name;
      if (sessionName) {
        setActiveSessionName(sessionName);
      }
      await fetchTmuxSessions(true);
      if (sessionName) {
        setActiveSessionName(sessionName);
      }
      setSessionError('');
    } catch (err: any) {
      const message = err?.response?.data?.error || 'Failed to create tmux session.';
      setSessionError(String(message));
    } finally {
      setBusyAction(null);
    }
  }, [fetchTmuxSessions]);

  const closeTmuxSession = useCallback(async (sessionName: string) => {
    setBusyAction('close');
    setBusySessionName(sessionName);
    try {
      await axios.post(`${API_BASE_URL}/terminal/tmux/kill`, { session: sessionName });
      await fetchTmuxSessions(true);
      setSessionError('');
    } catch (err: any) {
      const message = err?.response?.data?.error || 'Failed to close tmux session.';
      setSessionError(String(message));
    } finally {
      setBusyAction(null);
      setBusySessionName(null);
    }
  }, [fetchTmuxSessions]);

  useEffect(() => {
    fetchLlmProviders();
    void fetchTmuxSessions();
    const intervalId = window.setInterval(() => {
      void fetchTmuxSessions(true);
    }, 5000);
    return () => {
      window.clearInterval(intervalId);
    };
  }, [fetchTmuxSessions]);

  useEffect(() => {
    if (!router.isReady || queryBootstrappedRef.current) return;
    queryBootstrappedRef.current = true;
    const queryCommand = typeof router.query.command === 'string' ? router.query.command.trim() : '';
    if (queryCommand) {
      void createTmuxSession(queryCommand);
    }
  }, [createTmuxSession, router.isReady, router.query.command]);

  useEffect(() => {
    if (!router.isReady) return;
    const querySession = typeof router.query.session === 'string' ? router.query.session.trim() : '';
    if (!querySession) return;
    if (liveSessions.some((session) => session.name === querySession)) {
      setActiveSessionName(querySession);
    }
  }, [liveSessions, router.isReady, router.query.session]);

  const navItems: NavItem[] = MAIN_NAV_ITEMS.map((item) => {
    if (item.href === '/terminals') {
      return {
        ...item,
        active: true,
        action: () => {
          if (activeSessionName) {
            setActiveSessionName(null);
          }
        },
      };
    }

    return {
      ...item,
      action: () => { void router.push(item.href); },
    };
  });

  const renderNavItems = () => navItems.map((item, idx) => {
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

    elements.push(
      <NavLink
        key={item.label}
        label={item.label}
        icon={item.icon}
        active={Boolean(item.active)}
        onClick={() => {
          if (item.action) item.action();
          setOpened(false);
        }}
      />
    );

    return elements;
  });

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
                  onClick={() => setOpened((state) => !state)}
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
                onChange={(value) => {
                  if (!value) return;
                  setLlmProvider(value);
                  setSelectedProvider(value);
                }}
                data={llmProviders.map((provider) => ({ value: provider.id, label: provider.name }))}
                size="xs"
                style={{ width: 200 }}
              />
            </Group>
          </div>
        </Header>
      }
    >
      <Head>
        <title>Skill Pilot - Live Sessions</title>
      </Head>

      <div style={{ height: 'calc(100vh - 60px)', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {liveSessions.length === 0 && !loadingSessions ? (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Text size="sm" color="dimmed">No live sessions. Click &quot;New Session&quot; to create one.</Text>
          </div>
        ) : activeSessionName ? (
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '12px 16px 16px 16px' }}>
            <Group position="apart" mb={8}>
              <Text size="sm" weight={700}>Viewing: {activeSessionName}</Text>
              <button
                type="button"
                onClick={() => setActiveSessionName(null)}
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
            <div style={{ flex: 1, minHeight: 0, overflow: 'hidden', position: 'relative' }}>
              <iframe
                key={activeSessionName}
                src={`/terminal?session=${encodeURIComponent(activeSessionName)}`}
                style={{
                  width: '100%',
                  height: '100%',
                  display: 'block',
                  border: 'none',
                  borderRadius: 8,
                }}
              />
            </div>
          </div>
        ) : (
          <>
            <div style={{ borderBottom: `1px solid ${theme.colors.gray[3]}`, padding: 12, background: theme.colorScheme === 'dark' ? theme.colors.dark[7] : '#fff', overflowY: 'auto', maxHeight: 220 }}>
              <Group position="apart" mb={8}>
                <Text size="sm" weight={700}>Live Sessions</Text>
                <button
                  type="button"
                  onClick={() => void fetchTmuxSessions()}
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

              {sessionError && (
                <Text size="xs" color="red" mb={8}>{sessionError}</Text>
              )}

              {loadingSessions && liveSessions.length === 0 && (
                <Text size="sm" color="dimmed">Loading sessions...</Text>
              )}

              {liveSessions.map((session) => (
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
                    background: activeSessionName === session.name
                      ? (theme.colorScheme === 'dark' ? theme.colors.dark[6] : theme.colors.gray[0])
                      : (theme.colorScheme === 'dark' ? theme.colors.dark[7] : '#fff'),
                  }}
                >
                  <div>
                    <Text size="sm" weight={600}>{session.name}</Text>
                    <Text size="xs" color="dimmed">
                      {session.attached ? 'Attached' : 'Detached'} · windows {session.windows}
                    </Text>
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button
                      type="button"
                      onClick={(e) => {
                        if (e.shiftKey) {
                          window.open(`/terminal?session=${encodeURIComponent(session.name)}`, '_blank');
                        } else {
                          setActiveSessionName(session.name);
                        }
                      }}
                      disabled={activeSessionName === session.name}
                      style={{
                        border: `1px solid ${theme.colors.gray[3]}`,
                        borderRadius: 8,
                        padding: '5px 10px',
                        background: activeSessionName === session.name
                          ? (theme.colorScheme === 'dark' ? theme.colors.dark[5] : theme.colors.gray[1])
                          : (theme.colorScheme === 'dark' ? theme.colors.dark[6] : '#fff'),
                        fontSize: 12,
                        cursor: activeSessionName === session.name ? 'not-allowed' : 'pointer',
                      }}
                    >
                      Connect
                    </button>
                    <button
                      type="button"
                      onClick={() => void closeTmuxSession(session.name)}
                      disabled={busyAction === 'close' && busySessionName === session.name}
                      style={{
                        border: `1px solid ${theme.colors.red[5]}`,
                        color: theme.colors.red[6],
                        borderRadius: 8,
                        padding: '5px 10px',
                        background: 'transparent',
                        fontSize: 12,
                        cursor: (busyAction === 'close' && busySessionName === session.name) ? 'not-allowed' : 'pointer',
                      }}
                    >
                      Close
                    </button>
                  </div>
                </div>
              ))}
              <Text size="xs" color="dimmed" mt={4}>Shift+Click &quot;Connect&quot; to open in a new window.</Text>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}

export const getStaticProps = async (context: GetStaticPropsContext) => {
  return {
    props: {
      ...(await serverSideTranslations(context.locale ?? 'en', [
        'common',
      ])),
    },
  };
};
