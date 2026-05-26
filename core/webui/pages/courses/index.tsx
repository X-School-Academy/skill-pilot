import React, { useEffect, useMemo, useRef, useState } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { GetStaticPropsContext } from 'next';
import axios from 'axios';
import YAML from 'js-yaml';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';
import {
  AppShell,
  Navbar,
  Header,
  Text,
  MediaQuery,
  Burger,
  useMantineTheme,
  ScrollArea,
  Group,
  ActionIcon,
  Tooltip,
  NavLink,
  Box,
  LoadingOverlay,
  Button,
  Select,
  Modal,
  Textarea,
} from '@mantine/core';
import {
  IconFolder,
  IconFileText,
  IconRefresh,
  IconSortAscending,
  IconClock,
  IconArrowLeft,
  IconPlayerStop,
  IconBolt,
  IconPlus,
} from '@tabler/icons-react';
import CourseBlock from '../../components/blocks/course.block';
import MarkdownRenderer from '../../components/blocks/MarkdownRenderer';
import EmbeddedSessionPanel from '../../components/EmbeddedSessionPanel';
import { apiUrl } from '../../libs/api-base';
import { dispatchLlmStatus, getClientId, resolveSelectedProvider, setSelectedProvider } from '../../libs/llm';

const API_BASE_URL = apiUrl('/api');

type CourseRenderMode = 'guided_challenge' | 'interactive_tutorial' | 'markdown';

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

const parseYaml = (source: string): Record<string, any> => {
  try {
    const parsed = YAML.load(source);
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed as Record<string, any> : {};
  } catch {
    return {};
  }
};

const detectCourseRenderMode = (content: string): CourseRenderMode => {
  const normalized = content.replace(/^\uFEFF/, '');
  const yamlFence = normalized.match(/^```\s*yaml[^\n]*\n([\s\S]*?)\n```/i);
  if (yamlFence) {
    const meta = parseYaml(yamlFence[1]);
    if (meta.type === 'guided_challenge') return 'guided_challenge';
  }

  const frontmatter = normalized.match(/^---\s*\n([\s\S]*?)\n---(?:\s*\n|$)/);
  if (frontmatter) {
    const meta = parseYaml(frontmatter[1]);
    if (meta.type === 'interactive_tutorial') return 'interactive_tutorial';
  }

  return 'markdown';
};

const stripFrontmatter = (content: string): string => {
  const normalized = content.replace(/^\uFEFF/, '');
  return normalized.replace(/^---\s*\n[\s\S]*?\n---(?:\s*\n|$)/, '');
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

const buildCourseCreatorPrompt = (requestText: string): string => `Use agent skill \`course-creator\` to create a tutorial based on the learner requirement below.

Learner requirement:
${requestText}

If \`config/profile.json5\` exists, tailor the tutorial to the learner profile in that file.`;

export default function CoursesPage() {
  const router = useRouter();
  const { course } = router.query;
  const theme = useMantineTheme();
  const isDevMode = process.env.NODE_ENV === 'development';
  const [opened, setOpened] = useState(false);
  const [treeData, setTreeData] = useState<FileItem[]>([]);
  const [courseContent, setCourseContent] = useState<string>('');
  const [assignment, setAssignment] = useState<{ title: string; last_step: number } | null>(null);
  const [loading, setLoading] = useState(false);
  const [treeLoading, setTreeLoading] = useState(false);
  const [sortByTime, setSortByTime] = useState(true);
  const [llmProviders, setLlmProviders] = useState<LlmProvider[]>([]);
  const [llmProvider, setLlmProvider] = useState<string | null>(null);
  const [llmRunning, setLlmRunning] = useState(false);

  const [courseRenderMode, setCourseRenderMode] = useState<CourseRenderMode>('markdown');

  const [addSessionOpened, setAddSessionOpened] = useState(false);
  const [sessionPrompt, setSessionPrompt] = useState('');
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
  const [workflowExecuteStatus, setWorkflowExecuteStatus] = useState<any>(null);
  const [continuingWorkflow, setContinuingWorkflow] = useState(false);

  const [navbarWidth, setNavbarWidth] = useState(300);
  const [isResizing, setIsResizing] = useState(false);
  const rightPaneRef = useRef<HTMLDivElement | null>(null);

  const startResizing = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  };

  const stopResizing = () => {
    setIsResizing(false);
  };

  const resize = (e: MouseEvent) => {
    if (isResizing) {
      const newWidth = e.clientX;
      if (newWidth > 150 && newWidth < 600) {
        setNavbarWidth(newWidth);
      }
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

  const fetchTree = async () => {
    setTreeLoading(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/courses/tree`);
      setTreeData(res.data.items);
    } catch (err) {
      console.error('Failed to fetch tree:', err);
    } finally {
      setTreeLoading(false);
    }
  };

  const fetchContent = async (path: string) => {
    setLoading(true);
    setCourseContent('');
    setAssignment({ title: '', last_step: 0 });
    setCourseRenderMode('markdown');
    try {
      const res = await axios.get(`${API_BASE_URL}/courses/content`, {
        params: { course: path },
      });
      const raw = String(res.data.content || '');
      const meta = res.data.meta || {};
      const renderMode = detectCourseRenderMode(raw);

      setCourseContent(raw);
      setCourseRenderMode(renderMode);
      setAssignment({
        title: meta.title || path.split('/').pop() || path,
        last_step: Number(meta.last_step ?? 0),
      });
    } catch (err) {
      console.error('Failed to fetch content:', err);
      setCourseContent('# Error\nFailed to load course content.');
      setAssignment(null);
      setCourseRenderMode('markdown');
    } finally {
      setLoading(false);
    }
  };

  const fetchLatest = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/courses/latest`);
      if (res.data.path) {
        router.push(`/courses?course=${res.data.path}`, undefined, { shallow: true });
      } else {
        setCourseContent('# No learning sessions available\nPlease create a learning file first.');
        setAssignment(null);
      }
    } catch (err) {
      console.error('Failed to fetch latest:', err);
    }
  };

  const resetCourseProgress = async () => {
    if (!course || courseRenderMode !== 'guided_challenge') return;
    setLoading(true);
    try {
      await axios.post(`${API_BASE_URL}/courses/reset`, { course });
      await fetchContent(course as string);
    } catch (err) {
      console.error('Failed to reset progress:', err);
    } finally {
      setLoading(false);
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

  const handleStopLlm = async () => {
    try {
      const clientId = getClientId();
      await axios.post(`${API_BASE_URL}/llm/stop`, { client_id: clientId });
    } catch (err) {
      console.error('Failed to stop LLM:', err);
    } finally {
      dispatchLlmStatus(false);
      setLlmRunning(false);
    }
  };

  const handleCreateSession = () => {
    const request = sessionPrompt.trim();
    if (!request) return;
    const prompt = buildCourseCreatorPrompt(request);
    setAddSessionOpened(false);
    setSessionPrompt('');
    setSessionPromptText(prompt);
    setNewSessionWorkflow(null);
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
      console.error('Failed to start learning session:', err);
    } finally {
      setStartingSession(false);
    }
  };

  useEffect(() => {
    fetchTree();
    fetchLlmProviders();
    void axios.get(`${API_BASE_URL}/config/settings`).then((res) => {
      const security = res.data?.security?.newSession;
      if (!security) return;
      setNewSessionSandbox(Boolean(security.sandbox));
      setNewSessionAuto(Boolean(security.auto));
      setNewSessionNetwork(security.network !== false);
    }).catch((err) => {
      console.error('Failed to fetch learning session settings:', err);
    });
  }, []);

  useEffect(() => {
    const handler = (event: any) => {
      setLlmRunning(Boolean(event?.detail?.running));
    };
    window.addEventListener('llm:status', handler);
    return () => window.removeEventListener('llm:status', handler);
  }, []);

  useEffect(() => {
    if (course) {
      fetchContent(course as string);
    } else if (router.isReady) {
      fetchLatest();
    }
  }, [course, router.isReady]);

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

  const renderTree = (items: FileItem[]) => {
    return items.map((item) => {
      const isSelected = course === item.path;
      if (item.type === 'dir') {
        return (
          <NavLink
            key={item.path}
            label={item.name}
            icon={<IconFolder size="1.2rem" stroke={1.5} color={theme.colors.blue[6]} />}
            childrenOffset={16}
            defaultOpened={course?.toString().startsWith(item.path)}
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
            router.push(`/courses?course=${item.path}`, undefined, { shallow: true });
            setOpened(false);
          }}
        />
      );
    });
  };

  const isGuidedChallenge = courseRenderMode === 'guided_challenge';
  const markdownContent = courseRenderMode === 'interactive_tutorial' ? stripFrontmatter(courseContent) : courseContent;
  const isRemoteCourse = typeof course === 'string' && /^https:\/\//i.test(course);

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
                <Burger
                  opened={opened}
                  onClick={() => setOpened((o) => !o)}
                  size="sm"
                  color={theme.colors.gray[6]}
                  mr="xl"
                />
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
              <Tooltip label={llmRunning ? 'Stop LLM' : 'LLM Idle'}>
                <ActionIcon
                  variant={llmRunning ? 'filled' : 'subtle'}
                  color={llmRunning ? 'red' : 'gray'}
                  onClick={() => {
                    if (llmRunning) handleStopLlm();
                  }}
                >
                  {llmRunning ? <IconPlayerStop size="1rem" /> : <IconBolt size="1rem" />}
                </ActionIcon>
              </Tooltip>
              {isGuidedChallenge && !isRemoteCourse && (
                <Button
                  variant="subtle"
                  leftIcon={<IconRefresh size="1rem" />}
                  onClick={() => void resetCourseProgress()}
                  loading={loading}
                >
                  Reset Progress
                </Button>
              )}
            </Group>
          </div>
        </Header>
      }
    >
      <Head>
        <title>Skill Pilot - Learning</title>
      </Head>

      <Modal
        opened={addSessionOpened}
        onClose={() => setAddSessionOpened(false)}
        title="Add Learning Session"
        centered
      >
        <Textarea
          placeholder="Describe what you want to learn, your current level, target outcome, constraints, and preferred style (examples, exercises, project-based, etc.)."
          value={sessionPrompt}
          onChange={(e) => setSessionPrompt(e.currentTarget.value)}
          minRows={10}
          autosize
        />
        <Group position="right" mt="md">
          <Button variant="default" onClick={() => setAddSessionOpened(false)}>Cancel</Button>
          <Button onClick={handleCreateSession} disabled={!sessionPrompt.trim()}>Create Session</Button>
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
                  <Text weight={700} size="lg">Learning</Text>
                </Group>
                <Group spacing={4}>
                  <Tooltip label="Add Session">
                    <ActionIcon variant="subtle" onClick={() => setAddSessionOpened(true)}>
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
                  {typeof course === 'string' && course ? course : 'Select a learning file from the sidebar'}
                </div>
              </div>
              <div style={{ flex: 1, minHeight: 0, overflow: 'hidden', position: 'relative', display: 'flex', flexDirection: 'column' }}>
                <LoadingOverlay visible={loading} overlayBlur={2} />
                {courseContent ? (
                  <>
                    {isGuidedChallenge ? (
                      <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: '16px' }}>
                        <CourseBlock
                          key={`${course as string}-${assignment?.last_step ?? 0}`}
                          courseData={courseContent}
                          token={isRemoteCourse ? undefined : course as string}
                          lastStep={assignment?.last_step ?? 0}
                          fromIndex={0}
                        />
                      </div>
                    ) : (
                      <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: '20px 24px' }}>
                        <div className="doc-markdown" style={{ maxWidth: 'none', margin: 0, minHeight: '100%', padding: '18px 20px 24px', border: 'none', borderRadius: 0, boxShadow: 'none', background: '#ffffff' }}>
                          <MarkdownRenderer markdown={markdownContent} />
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  !loading && <Text align="center" py="xl" color="dimmed">Select a learning file from the sidebar to begin.</Text>
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
                <span style={{ fontSize: 16, lineHeight: 1 }}>⋯</span>
              </div>
              <div style={{ minHeight: 0, overflow: 'hidden' }}>
                <EmbeddedSessionPanel
                  currentLabel={course?.toString() || 'Learning session'}
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
                  onContinueWorkflow={() => {}}
                />
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
      ...(await serverSideTranslations(context.locale ?? 'en', [
        'common',
      ])),
    },
  };
};
