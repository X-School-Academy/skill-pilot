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
import { apiUrl } from '../../libs/api-base';
import { getSelectedProvider, setSelectedProvider } from '../../libs/llm';

const API_BASE_URL = apiUrl('/api');
axios.defaults.withCredentials = true;

type FileKind = 'markdown' | 'text' | 'image' | 'audio' | 'video';
type RequestMode = 'update' | 'issue';

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
  prompt: string;
}

const detectFileKind = (path: string): FileKind => {
  const lower = (path || '').toLowerCase();
  if (lower.endsWith('.md') || lower.endsWith('.markdown')) return 'markdown';
  if (lower.endsWith('.png') || lower.endsWith('.jpg') || lower.endsWith('.jpeg') || lower.endsWith('.gif') || lower.endsWith('.webp') || lower.endsWith('.bmp') || lower.endsWith('.svg')) return 'image';
  if (lower.endsWith('.mp3') || lower.endsWith('.wav') || lower.endsWith('.ogg') || lower.endsWith('.m4a') || lower.endsWith('.aac') || lower.endsWith('.flac')) return 'audio';
  if (lower.endsWith('.mp4') || lower.endsWith('.mov') || lower.endsWith('.webm') || lower.endsWith('.m4v') || lower.endsWith('.avi') || lower.endsWith('.mkv')) return 'video';
  return 'text';
};

const vibeProjectPath = (path: string): string => {
  const trimmed = path.replace(/^\/+/, '');
  return trimmed ? `workspace/vibe-coding/${trimmed}` : 'workspace/vibe-coding';
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

export default function VibeCodingPage() {
  const router = useRouter();
  const { task } = router.query;
  const theme = useMantineTheme();
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
  const [projectModalOpened, setProjectModalOpened] = useState(false);
  const [requestModalOpened, setRequestModalOpened] = useState(false);
  const [projectNameInput, setProjectNameInput] = useState('');
  const [projectRequirementsInput, setProjectRequirementsInput] = useState('');
  const [requestMode, setRequestMode] = useState<RequestMode>('update');
  const [requestProject, setRequestProject] = useState('');
  const [requestContent, setRequestContent] = useState('');
  const [creatingEntry, setCreatingEntry] = useState(false);
  const [deletingFile, setDeletingFile] = useState(false);
  const [navbarWidth, setNavbarWidth] = useState(300);
  const [isResizing, setIsResizing] = useState(false);

  const currentTask = typeof task === 'string' ? task : '';
  const currentProject = currentTask.includes('/') ? currentTask.split('/')[0] : '';
  const currentFileName = currentTask.split('/').pop() || '';

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
      setEditorContent(String(res.data.content || ''));
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
        router.push(`/vibe-coding?task=${encodeURIComponent(res.data.path)}`, undefined, { shallow: true });
      } else {
        setEditorContent('');
        setNotice('No projects available. Use New to create one.');
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
      const stored = getSelectedProvider();
      const defaultId = stored || providers[0]?.id || null;
      if (defaultId) setSelectedProvider(defaultId);
      setLlmProvider(defaultId);
    } catch (err) {
      console.error('Failed to fetch LLM providers:', err);
    }
  };

  const saveCurrentContent = async (): Promise<boolean> => {
    if (!currentTask || selectedKind === 'image' || selectedKind === 'audio' || selectedKind === 'video') {
      return true;
    }
    setEditorSaving(true);
    setEditorError('');
    setNotice('');
    try {
      await axios.post(`${API_BASE_URL}/vibe-coding/save`, {
        path: currentTask,
        content: editorContent,
      });
      setNotice('Saved.');
      await fetchTree();
      await fetchContent(currentTask);
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
      setProjectModalOpened(false);
      await fetchTree();
      if (createdPath) {
        router.push(`/vibe-coding?task=${encodeURIComponent(createdPath)}`, undefined, { shallow: true });
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
      if (createdPath) {
        router.push(`/vibe-coding?task=${encodeURIComponent(createdPath)}`, undefined, { shallow: true });
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
    if (currentFileName === 'requirements.md') {
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
      router.push('/vibe-coding', undefined, { shallow: true });
    } catch (err: any) {
      console.error('Failed to delete vibe coding file:', err);
      setEditorError(err?.response?.data?.error || 'Failed to delete file.');
    } finally {
      setDeletingFile(false);
    }
  };

  const runAction = async (action: VibeAction) => {
    if (!currentTask) return;
    const saved = await saveCurrentContent();
    if (!saved) return;
    void router.push(`/?new_session=true&prompt=${encodeURIComponent(action.prompt)}`);
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
                title={`New update or bug request for ${item.name}`}
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
          router.push(`/vibe-coding?task=${encodeURIComponent(item.path)}`, undefined, { shallow: true });
          setOpened(false);
        }}
      />
    );
  });

  const currentInstructionPath = currentTask ? vibeProjectPath(currentTask) : '';
  const fileActions = useMemo<VibeAction[]>(() => {
    if (!currentInstructionPath) return [];
    if (currentFileName === 'requirements.md') {
      return [
        {
          label: 'Refine',
          prompt: `Use agent skill vibe-coding-project-refine to refine the ${currentInstructionPath}`,
        },
        {
          label: 'Initial',
          prompt: `Use agent skill vibe-coding-project-initial to init the project defined at ${currentInstructionPath}`,
        },
        {
          label: 'Plan',
          prompt: `Use agent skill vibe-coding-project-plan to make a development plan for requirement ${currentInstructionPath}`,
        },
      ];
    }
    if (currentFileName === 'plan.md') {
      return [
        {
          label: 'Implement',
          prompt: `Use agent skill vibe-coding-project-implement to implement the code as the ${currentInstructionPath}`,
        },
      ];
    }
    if (currentFileName === 'implement.md') {
      return [
        {
          label: 'Review',
          prompt: `Use agent skill vibe-coding-project-review to review the code of the implementation of the ${currentInstructionPath}`,
        },
        {
          label: 'Test',
          prompt: `Use agent skill vibe-coding-project-test to test the code of the implementation of the ${currentInstructionPath}`,
        },
        {
          label: 'Deploy',
          prompt: `Use agent skill vibe-coding-project-deploy to deploy the code of the implementation of the ${currentInstructionPath}`,
        },
      ];
    }
    if (currentFileName === 'update.md') {
      return [
        {
          label: 'Update Code',
          prompt: `Use agent skill vibe-coding-project-update to update the code based on the update request defined in ${currentInstructionPath}`,
        },
      ];
    }
    if (currentFileName === 'issues.md') {
      return [
        {
          label: 'Fix Issues',
          prompt: `Use agent skill vibe-coding-project-fix-issues to fix the issues defined in ${currentInstructionPath}`,
        },
      ];
    }
    return [];
  }, [currentFileName, currentInstructionPath]);

  const mediaUrl = currentTask ? `${API_BASE_URL}/vibe-coding/file?path=${encodeURIComponent(currentTask)}` : '';
  const isMarkdownEditor = selectedKind === 'markdown';
  const isTextEditor = selectedKind === 'text';

  const renderActionButtons = () => {
    if (fileActions.length === 0) return null;
    return (
      <Group spacing="xs" mb="md" noWrap={false}>
        {fileActions.map((action) => (
          <Button
            key={action.label}
            size="xs"
            variant="default"
            onClick={() => void runAction(action)}
          >
            {action.label}
          </Button>
        ))}
      </Group>
    );
  };

  const renderMainContent = () => {
    if (selectedKind === 'image' && currentTask) {
      return (
        <>
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 480 }}>
            <img src={mediaUrl} alt={currentFileName} style={{ maxWidth: '100%', maxHeight: '70vh', objectFit: 'contain', borderRadius: 8 }} />
          </div>
          <Group position="right" mt="md">
            <Button color="red" variant="light" onClick={() => void deleteCurrentFile()} loading={deletingFile}>Delete</Button>
          </Group>
        </>
      );
    }

    if (selectedKind === 'audio' && currentTask) {
      return (
        <>
          <div style={{ paddingTop: 40 }}>
            <audio controls src={mediaUrl} style={{ width: '100%' }}>
              Your browser does not support audio playback.
            </audio>
          </div>
          <Group position="right" mt="md">
            <Button color="red" variant="light" onClick={() => void deleteCurrentFile()} loading={deletingFile}>Delete</Button>
          </Group>
        </>
      );
    }

    if (selectedKind === 'video' && currentTask) {
      return (
        <>
          <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 8 }}>
            <video controls src={mediaUrl} style={{ width: '100%', maxHeight: '70vh', borderRadius: 8 }}>
              Your browser does not support video playback.
            </video>
          </div>
          <Group position="right" mt="md">
            <Button color="red" variant="light" onClick={() => void deleteCurrentFile()} loading={deletingFile}>Delete</Button>
          </Group>
        </>
      );
    }

    if (isMarkdownEditor) {
      return (
        <div>
          <Group spacing="xs" mb="md" noWrap={false}>
            <Button size="xs" variant={markdownView === 'editor' ? 'filled' : 'default'} onClick={() => setMarkdownView('editor')}>
              Edit
            </Button>
            <Button size="xs" variant={markdownView === 'preview' ? 'filled' : 'default'} onClick={() => setMarkdownView('preview')}>
              Preview
            </Button>
            {fileActions.map((action) => (
              <Button
                key={action.label}
                size="xs"
                variant="default"
                onClick={() => void runAction(action)}
              >
                {action.label}
              </Button>
            ))}
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
                <Button onClick={() => void saveCurrentContent()} loading={editorSaving}>Save</Button>
                <Button color="red" variant="light" onClick={() => void deleteCurrentFile()} loading={deletingFile}>Delete</Button>
              </Group>
            </>
          ) : (
            <>
              <div className="doc-markdown">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{editorContent}</ReactMarkdown>
              </div>
              <Group position="right" mt="md">
                <Button color="red" variant="light" onClick={() => void deleteCurrentFile()} loading={deletingFile}>Delete</Button>
              </Group>
            </>
          )}
        </div>
      );
    }

    if (isTextEditor) {
      return (
        <>
          {renderActionButtons()}
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
            <Button onClick={() => void saveCurrentContent()} loading={editorSaving}>Save</Button>
            <Button color="red" variant="light" onClick={() => void deleteCurrentFile()} loading={deletingFile}>Delete</Button>
          </Group>
        </>
      );
    }

    return !loading ? <Text align="center" py="xl" color="dimmed">Select a project file from the sidebar to begin.</Text> : null;
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
        <title>Skill Pilot - Vibe Coding</title>
      </Head>

      <Modal opened={projectModalOpened} onClose={() => setProjectModalOpened(false)} title="New Project" centered>
        <Stack spacing="md">
          <div>
            <Text size="sm" weight={700} mb={4}>Project Name</Text>
            <TextInput
              placeholder="project-name"
              value={projectNameInput}
              onChange={(e) => setProjectNameInput(e.currentTarget.value)}
              description="A project folder will be created in kebab-case. Duplicates get _1, _2, and so on."
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
              <Text weight={700} size="lg">Projects</Text>
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
            {currentFileName ? <h1 className="mb-4">{currentFileName}</h1> : null}
            {currentProject ? <Text size="sm" color="dimmed" mb="sm">Project: {currentProject}</Text> : null}
            {editorError && <Text color="red" size="sm" mb="sm">{editorError}</Text>}
            {notice && !editorError && <Text color="green" size="sm" mb="sm">{notice}</Text>}
            {renderMainContent()}
          </div>
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
