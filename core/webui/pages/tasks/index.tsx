import React, { useEffect, useMemo, useState } from 'react';
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
  IconFileText,
  IconFolder,
  IconPlayerPlay,
  IconPlus,
  IconRefresh,
  IconSortAscending,
} from '@tabler/icons-react';
import { apiUrl } from '../../libs/api-base';
import { getSelectedProvider, setSelectedProvider } from '../../libs/llm';

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

const detectTaskKind = (path: string): TaskKind => {
  const lower = (path || '').toLowerCase();
  if (lower.endsWith('.md') || lower.endsWith('.markdown')) return 'markdown';
  if (lower.endsWith('.png') || lower.endsWith('.jpg') || lower.endsWith('.jpeg') || lower.endsWith('.gif') || lower.endsWith('.webp') || lower.endsWith('.bmp') || lower.endsWith('.svg')) return 'image';
  if (lower.endsWith('.mp3') || lower.endsWith('.wav') || lower.endsWith('.ogg') || lower.endsWith('.m4a') || lower.endsWith('.aac') || lower.endsWith('.flac')) return 'audio';
  if (lower.endsWith('.mp4') || lower.endsWith('.mov') || lower.endsWith('.webm') || lower.endsWith('.m4v') || lower.endsWith('.avi') || lower.endsWith('.mkv')) return 'video';
  return 'text';
};

export default function TasksPage() {
  const router = useRouter();
  const { task } = router.query;
  const theme = useMantineTheme();
  const [opened, setOpened] = useState(false);
  const [treeData, setTreeData] = useState<FileItem[]>([]);
  const [selectedKind, setSelectedKind] = useState<TaskKind>('text');
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
  const [addTaskOpened, setAddTaskOpened] = useState(false);
  const [newTaskPath, setNewTaskPath] = useState('');
  const [taskTitle, setTaskTitle] = useState('');
  const [creatingTask, setCreatingTask] = useState(false);
  const [navbarWidth, setNavbarWidth] = useState(300);
  const [isResizing, setIsResizing] = useState(false);

  const currentTask = typeof task === 'string' ? task : '';

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
        setNotice('No task files available. Use + to create one.');
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
      const stored = getSelectedProvider();
      const defaultId = stored || providers[0]?.id || null;
      if (defaultId) {
        setSelectedProvider(defaultId);
      }
      setLlmProvider(defaultId);
    } catch (err) {
      console.error('Failed to fetch LLM providers:', err);
    }
  };

  const saveContent = async () => {
    if (!currentTask || selectedKind === 'image' || selectedKind === 'audio' || selectedKind === 'video') return;
    setEditorSaving(true);
    setEditorError('');
    setNotice('');
    try {
      await axios.post(`${API_BASE_URL}/tasks/save`, { path: currentTask, content: editorContent });
      setNotice('Saved.');
      await fetchTree();
      await fetchContent(currentTask);
    } catch (err: any) {
      console.error('Failed to save task content:', err);
      setEditorError(err?.response?.data?.error || 'Failed to save task content.');
    } finally {
      setEditorSaving(false);
    }
  };

  const createTask = async () => {
    const trimmed = newTaskPath.trim();
    if (!trimmed) return;
    setCreatingTask(true);
    setEditorError('');
    setNotice('');
    try {
      const res = await axios.post(`${API_BASE_URL}/tasks/create`, { path: trimmed });
      const createdPath = String(res.data.path || trimmed);
      setAddTaskOpened(false);
      setNewTaskPath('');
      await fetchTree();
      router.push(`/tasks?task=${encodeURIComponent(createdPath)}`, undefined, { shallow: true });
    } catch (err: any) {
      console.error('Failed to create task:', err);
      setEditorError(err?.response?.data?.error || 'Failed to create task.');
    } finally {
      setCreatingTask(false);
    }
  };

  useEffect(() => {
    fetchTree();
    fetchLlmProviders();
  }, []);

  useEffect(() => {
    if (currentTask) {
      fetchContent(currentTask);
    } else if (router.isReady) {
      fetchLatest();
    }
  }, [currentTask, router.isReady]);

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
          defaultOpened={currentTask.startsWith(item.path)}
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

  const renderMainContent = () => {
    if (selectedKind === 'image' && currentTask) {
      return (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 480 }}>
          <img src={mediaUrl} alt={taskTitle} style={{ maxWidth: '100%', maxHeight: '70vh', objectFit: 'contain', borderRadius: 8 }} />
        </div>
      );
    }

    if (selectedKind === 'audio' && currentTask) {
      return (
        <div style={{ paddingTop: 40 }}>
          <audio controls src={mediaUrl} style={{ width: '100%' }}>
            Your browser does not support audio playback.
          </audio>
        </div>
      );
    }

    if (selectedKind === 'video' && currentTask) {
      return (
        <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 8 }}>
          <video controls src={mediaUrl} style={{ width: '100%', maxHeight: '70vh', borderRadius: 8 }}>
            Your browser does not support video playback.
          </video>
        </div>
      );
    }

    if (isMarkdownEditor) {
      return (
        <div>
          <Group spacing="xs" mb="md">
            <Button size="xs" variant={markdownView === 'editor' ? 'filled' : 'default'} onClick={() => setMarkdownView('editor')}>
              Edit
            </Button>
            <Button size="xs" variant={markdownView === 'preview' ? 'filled' : 'default'} onClick={() => setMarkdownView('preview')}>
              Preview
            </Button>
            <Button
              size="xs"
              variant="default"
              leftIcon={<IconPlayerPlay size="1rem" />}
              onClick={() => {
                setNotice('Execute is a placeholder for now.');
                setEditorError('');
              }}
            >
              Execute
            </Button>
          </Group>
          {markdownView === 'editor' ? (
            <>
              <Textarea
                value={editorContent}
                onChange={(e) => {
                  setEditorContent(e.currentTarget.value);
                  if (editorError) setEditorError('');
                  if (notice) setNotice('');
                }}
                minRows={24}
                autosize
                styles={{ input: { fontFamily: 'Menlo, Monaco, Consolas, monospace' } }}
              />
              <Group position="right" mt="md">
                <Button onClick={() => void saveContent()} loading={editorSaving}>Save</Button>
              </Group>
            </>
          ) : (
            <div className="doc-markdown">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{editorContent}</ReactMarkdown>
            </div>
          )}
        </div>
      );
    }

    if (isTextEditor) {
      return (
        <>
          <Textarea
            value={editorContent}
            onChange={(e) => {
              setEditorContent(e.currentTarget.value);
              if (editorError) setEditorError('');
              if (notice) setNotice('');
            }}
            minRows={24}
            autosize
            styles={{ input: { fontFamily: 'Menlo, Monaco, Consolas, monospace' } }}
          />
          <Group position="right" mt="md">
            <Button onClick={() => void saveContent()} loading={editorSaving}>Save</Button>
          </Group>
        </>
      );
    }

    return !loading ? <Text align="center" py="xl" color="dimmed">Select a task file from the sidebar to begin.</Text> : null;
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
          height: '100vh',
        },
      }}
      navbarOffsetBreakpoint="sm"
      header={
        <Header height={{ base: 60 }} p="md">
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
        <TextInput
          placeholder="project-a/new-task.md"
          value={newTaskPath}
          onChange={(e) => setNewTaskPath(e.currentTarget.value)}
          description="Relative to workspace/tasks. Missing extensions default to .md."
        />
        <Group position="right" mt="md">
          <Button variant="default" onClick={() => setAddTaskOpened(false)}>Cancel</Button>
          <Button onClick={() => void createTask()} disabled={!newTaskPath.trim()} loading={creatingTask}>Create Task</Button>
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
              <Text weight={700} size="lg">Tasks</Text>
              <Group spacing={4}>
                <Tooltip label="Add Task">
                  <ActionIcon
                    variant="subtle"
                    onClick={() => {
                      const baseDir = currentTask.includes('/') ? currentTask.slice(0, currentTask.lastIndexOf('/') + 1) : '';
                      setNewTaskPath(`${baseDir}new-task.md`);
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
            {taskTitle ? <h1 className="mb-4">{taskTitle}</h1> : null}
            {editorError && <Text color="red" size="sm" mb="sm">{editorError}</Text>}
            {notice && !editorError && <Text color="green" size="sm" mb="sm">{notice}</Text>}
            {renderMainContent()}
          </div>
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
