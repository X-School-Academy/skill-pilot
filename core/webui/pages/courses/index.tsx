import React, { useEffect, useMemo, useState } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { GetStaticPropsContext } from 'next';
import axios from 'axios';
import YAML from 'js-yaml';
import JSON5 from 'json5';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
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
import { apiUrl } from '../../libs/api-base';
import { dispatchLlmStatus, getClientId, resolveSelectedProvider, setSelectedProvider } from '../../libs/llm';

const API_BASE_URL = apiUrl('/api');

type FileType = 'markdown' | 'yaml' | 'json' | 'json5' | 'other';

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

const detectFileType = (path: string): FileType => {
  const lower = (path || '').toLowerCase();
  if (lower.endsWith('.md') || lower.endsWith('.markdown')) return 'markdown';
  if (lower.endsWith('.yaml') || lower.endsWith('.yml')) return 'yaml';
  if (lower.endsWith('.json5')) return 'json5';
  if (lower.endsWith('.json')) return 'json';
  return 'other';
};

const hasFirstYamlFence = (content: string): boolean => {
  const firstFence = content.match(/^\s*```\s*([a-zA-Z0-9_-]+)[^\n]*\n/);
  return (firstFence?.[1] || '').toLowerCase() === 'yaml';
};

const normalizeEditorContent = (content: string, type: FileType): string => {
  try {
    if (type === 'json') {
      return `${JSON.stringify(JSON.parse(content), null, 2)}\n`;
    }
    if (type === 'json5') {
      return `${JSON.stringify(JSON5.parse(content), null, 2)}\n`;
    }
    if (type === 'yaml') {
      const parsed = YAML.load(content);
      return `${YAML.dump(parsed, { lineWidth: -1 })}`;
    }
  } catch {
    return content;
  }
  return content;
};

const validateEditorContent = (content: string, type: FileType): string | null => {
  try {
    if (type === 'json') {
      JSON.parse(content);
    } else if (type === 'json5') {
      JSON5.parse(content);
    } else if (type === 'yaml') {
      YAML.load(content);
    }
    return null;
  } catch (err: any) {
    const details = typeof err?.message === 'string' ? err.message : 'Invalid format';
    if (type === 'json') return `Invalid JSON: ${details}`;
    if (type === 'json5') return `Invalid JSON5: ${details}`;
    if (type === 'yaml') return `Invalid YAML: ${details}`;
    return details;
  }
};

const buildCourseCreatorPrompt = (requestText: string): string => `Use agent skill \`course-creator\` to create a tutorial based on the learner requirement below.

Learner requirement:
${requestText}

If \`config/profile.json5\` exists, tailor the tutorial to the learner profile in that file.`;

export default function CoursesPage() {
  const router = useRouter();
  const { course } = router.query;
  const theme = useMantineTheme();
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
  const [editorSaving, setEditorSaving] = useState(false);
  const [editorError, setEditorError] = useState<string>('');

  const [editorContent, setEditorContent] = useState('');
  const [fileType, setFileType] = useState<FileType>('other');
  const [isCourseTutorial, setIsCourseTutorial] = useState(false);
  const [markdownView, setMarkdownView] = useState<'editor' | 'preview'>('editor');

  const [addSessionOpened, setAddSessionOpened] = useState(false);
  const [sessionPrompt, setSessionPrompt] = useState('');

  const [navbarWidth, setNavbarWidth] = useState(300);
  const [isResizing, setIsResizing] = useState(false);

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
    setEditorContent('');
    setAssignment({ title: '', last_step: 0 });
    setIsCourseTutorial(false);
    try {
      const res = await axios.get(`${API_BASE_URL}/courses/content`, {
        params: { course: path },
      });
      const raw = String(res.data.content || '');
      const meta = res.data.meta || {};
      const nextType = detectFileType(path);
      const tutorial = nextType === 'markdown' && hasFirstYamlFence(raw);

      setFileType(nextType);
      setCourseContent(raw);
      setEditorContent(normalizeEditorContent(raw, nextType));
      setIsCourseTutorial(tutorial);
      setAssignment({
        title: meta.title || path.split('/').pop() || path,
        last_step: Number(meta.last_step ?? 0),
      });
      setMarkdownView('editor');
    } catch (err) {
      console.error('Failed to fetch content:', err);
      setCourseContent('# Error\nFailed to load course content.');
      setEditorContent('# Error\nFailed to load course content.');
      setAssignment(null);
      setFileType('markdown');
      setIsCourseTutorial(false);
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
        setEditorContent('# No learning sessions available\nPlease create a learning file first.');
        setAssignment(null);
      }
    } catch (err) {
      console.error('Failed to fetch latest:', err);
    }
  };

  const resetCourseProgress = async () => {
    if (!course || !isCourseTutorial) return;
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

  const saveContent = async () => {
    if (!course) return;
    const validationError = validateEditorContent(editorContent, fileType);
    if (validationError) {
      setEditorError(validationError);
      return;
    }
    setEditorError('');
    setEditorSaving(true);
    try {
      await axios.post(`${API_BASE_URL}/courses/save`, {
        course,
        content: editorContent,
      });
      await fetchContent(course as string);
      await fetchTree();
    } catch (err) {
      console.error('Failed to save content:', err);
    } finally {
      setEditorSaving(false);
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
    void router.push(`/?new_session=true&prompt=${encodeURIComponent(prompt)}`);
  };

  useEffect(() => {
    fetchTree();
    fetchLlmProviders();
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

  const isMarkdownEditor = fileType === 'markdown' && !isCourseTutorial;
  const isDataEditor = fileType === 'yaml' || fileType === 'json' || fileType === 'json5';

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
          height: '100vh',
        },
      }}
      navbarOffsetBreakpoint="sm"
      header={
        <Header height={{ base: 60 }} p="md">
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
              {isCourseTutorial && (
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

      <div className="shrink-0 border-b border-[#d6def8] bg-white/60 px-6 py-2">
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

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <Navbar
          p="md"
          hiddenBreakpoint="sm"
          hidden={!opened}
          width={{ sm: navbarWidth }}
          style={{
            position: 'relative',
            transition: isResizing ? 'none' : 'width 200ms ease',
            height: '100%',
          }}
        >
          <Navbar.Section mb="md">
            <Group position="apart" align="center">
              <Text weight={700} size="lg">Learning</Text>
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
          </Navbar.Section>
          <Navbar.Section grow component={ScrollArea} mx="-md" px="md">
            {treeLoading && treeData.length === 0 ? (
              <Box py="xl" sx={{ textAlign: 'center' }}><Text size="sm" color="dimmed">Loading...</Text></Box>
            ) : (
              renderTree(sortedTreeData)
            )}
          </Navbar.Section>

          <MediaQuery smallerThan="sm" styles={{ display: 'none' }}>
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
          </MediaQuery>
        </Navbar>

        <main
          style={{
            flex: 1,
            display: 'flex',
            justifyContent: 'center',
            overflowY: 'auto',
            padding: '20px',
          }}
        >
          <div className="w-full max-w-4xl bg-white p-6 rounded-lg shadow-sm relative" style={{ height: 'fit-content', minHeight: '100%', marginTop: 24 }}>
            <LoadingOverlay visible={loading} overlayBlur={2} />
            {courseContent ? (
              <>
                {assignment?.title ? <h1 className="mb-4">{assignment.title}</h1> : null}
                {isCourseTutorial ? (
                  <CourseBlock
                    key={`${course as string}-${assignment?.last_step ?? 0}`}
                    courseData={courseContent}
                    token={course as string}
                    lastStep={assignment?.last_step ?? 0}
                    fromIndex={0}
                  />
                ) : isMarkdownEditor ? (
                  <div>
                    <Group spacing="xs" mb="md">
                      <Button
                        size="xs"
                        variant={markdownView === 'editor' ? 'filled' : 'default'}
                        onClick={() => setMarkdownView('editor')}
                      >
                        Editor
                      </Button>
                      <Button
                        size="xs"
                        variant={markdownView === 'preview' ? 'filled' : 'default'}
                        onClick={() => setMarkdownView('preview')}
                      >
                        Preview
                      </Button>
                    </Group>
                    {markdownView === 'editor' ? (
                      <>
                        <Textarea
                          value={editorContent}
                          onChange={(e) => {
                            setEditorContent(e.currentTarget.value);
                            if (editorError) setEditorError('');
                          }}
                          minRows={24}
                          autosize
                          styles={{ input: { fontFamily: 'Menlo, Monaco, Consolas, monospace' } }}
                        />
                        {editorError && (
                          <Text color="red" size="sm" mt="xs">
                            {editorError}
                          </Text>
                        )}
                        <Group position="right" mt="md">
                          <Button onClick={() => void saveContent()} loading={editorSaving}>
                            Save
                          </Button>
                        </Group>
                      </>
                    ) : (
                      <div className="doc-markdown">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{editorContent}</ReactMarkdown>
                      </div>
                    )}
                  </div>
                ) : (
                  <>
                    <Textarea
                      value={editorContent}
                      onChange={(e) => {
                        setEditorContent(e.currentTarget.value);
                        if (editorError) setEditorError('');
                      }}
                      minRows={24}
                      autosize
                      styles={{ input: { fontFamily: 'Menlo, Monaco, Consolas, monospace' } }}
                    />
                    {editorError && (
                      <Text color="red" size="sm" mt="xs">
                        {editorError}
                      </Text>
                    )}
                    <Group position="right" mt="md">
                      <Button onClick={() => void saveContent()} loading={editorSaving}>
                        Save
                      </Button>
                    </Group>
                  </>
                )}
              </>
            ) : (
              !loading && <Text align="center" py="xl" color="dimmed">Select a learning file from the sidebar to begin.</Text>
            )}
          </div>
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
