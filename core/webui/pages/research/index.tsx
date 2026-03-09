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
  IconPlus,
  IconRefresh,
  IconSortAscending,
} from '@tabler/icons-react';
import { apiUrl } from '../../libs/api-base';
import { getSelectedProvider, setSelectedProvider } from '../../libs/llm';

const API_BASE_URL = apiUrl('/api');
axios.defaults.withCredentials = true;

type FileKind = 'markdown' | 'text' | 'image' | 'audio' | 'video' | 'pdf';
type ExecuteMode = 'skill' | 'workflow';

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

interface ResearchAction {
  label: string;
  defaultSkill: string;
  skillPromptSuffix: string;
}

const detectFileKind = (path: string): FileKind => {
  const lower = (path || '').toLowerCase();
  if (lower.endsWith('.md') || lower.endsWith('.markdown')) return 'markdown';
  if (lower.endsWith('.pdf')) return 'pdf';
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

const researchProjectPath = (path: string): string => {
  const trimmed = path.replace(/^\/+/, '');
  return trimmed ? `workspace/research/${trimmed}` : 'workspace/research';
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

export default function ResearchPage() {
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
  const [topicModalOpened, setTopicModalOpened] = useState(false);
  const [topicNameInput, setTopicNameInput] = useState('');
  const [topicRequirementsInput, setTopicRequirementsInput] = useState('');
  const [creatingTopic, setCreatingTopic] = useState(false);
  const [deletingFile, setDeletingFile] = useState(false);
  const [executeOpened, setExecuteOpened] = useState(false);
  const [executeMode, setExecuteMode] = useState<ExecuteMode>('skill');
  const [skillOptions, setSkillOptions] = useState<string[]>([]);
  const [workflowOptions, setWorkflowOptions] = useState<string[]>([]);
  const [selectedSkill, setSelectedSkill] = useState<string | null>(null);
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<ResearchAction | null>(null);
  const [navbarWidth, setNavbarWidth] = useState(300);
  const [isResizing, setIsResizing] = useState(false);

  const currentTask = typeof task === 'string' ? task : '';
  const currentTopic = currentTask.includes('/') ? currentTask.split('/')[0] : '';
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
      const res = await axios.get(`${API_BASE_URL}/research/tree`);
      setTreeData(res.data.items || []);
    } catch (err) {
      console.error('Failed to fetch research tree:', err);
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

    if (nextKind === 'image' || nextKind === 'audio' || nextKind === 'video' || nextKind === 'pdf') {
      setEditorContent('');
      setLoading(false);
      return;
    }

    try {
      const res = await axios.get(`${API_BASE_URL}/research/content`, { params: { path } });
      setSelectedKind((res.data.kind as FileKind) || nextKind);
      setEditorContent(String(res.data.content || ''));
    } catch (err: any) {
      console.error('Failed to fetch research content:', err);
      setEditorError(err?.response?.data?.error || 'Failed to load file content.');
      setEditorContent('');
    } finally {
      setLoading(false);
    }
  };

  const fetchLatest = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/research/latest`);
      if (res.data.path) {
        router.push(`/research?task=${encodeURIComponent(res.data.path)}`, undefined, { shallow: true });
      } else {
        setEditorContent('');
        setNotice('');
      }
    } catch (err) {
      console.error('Failed to fetch latest research file:', err);
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
    if (!currentTask || selectedKind === 'image' || selectedKind === 'audio' || selectedKind === 'video' || selectedKind === 'pdf') {
      return true;
    }
    setEditorSaving(true);
    setEditorError('');
    setNotice('');
    try {
      await axios.post(`${API_BASE_URL}/research/save`, {
        path: currentTask,
        content: editorContent,
      });
      setNotice('Saved.');
      await fetchTree();
      await fetchContent(currentTask);
      return true;
    } catch (err: any) {
      console.error('Failed to save research content:', err);
      setEditorError(err?.response?.data?.error || 'Failed to save content.');
      return false;
    } finally {
      setEditorSaving(false);
    }
  };

  const openTopicModal = () => {
    setTopicNameInput(currentTopic || '');
    setTopicRequirementsInput('');
    setTopicModalOpened(true);
    setEditorError('');
    setNotice('');
  };

  const createTopic = async () => {
    setCreatingTopic(true);
    setEditorError('');
    setNotice('');
    try {
      const res = await axios.post(`${API_BASE_URL}/research/create-topic`, {
        topic_name: topicNameInput,
        requirements: topicRequirementsInput,
      });
      const createdPath = String(res.data.path || '');
      setTopicModalOpened(false);
      await fetchTree();
      if (createdPath) {
        router.push(`/research?task=${encodeURIComponent(createdPath)}`, undefined, { shallow: true });
      }
    } catch (err: any) {
      console.error('Failed to create research topic:', err);
      setEditorError(err?.response?.data?.error || 'Failed to create topic.');
    } finally {
      setCreatingTopic(false);
    }
  };

  const deleteCurrentFile = async () => {
    if (!currentTask) return;

    let confirmText = '';
    if (currentFileName === 'requirements.md') {
      const typed = window.prompt(`Deleting ${currentTask} will remove the full topic folder. Type delete to confirm.`);
      if (typed === null) return;
      confirmText = typed;
    } else if (!window.confirm(`Delete ${currentTask}?`)) {
      return;
    }

    setDeletingFile(true);
    setEditorError('');
    setNotice('');
    try {
      await axios.post(`${API_BASE_URL}/research/delete`, {
        path: currentTask,
        confirm_text: confirmText,
      });
      await fetchTree();
      router.push('/research', undefined, { shallow: true });
    } catch (err: any) {
      console.error('Failed to delete research file:', err);
      setEditorError(err?.response?.data?.error || 'Failed to delete file.');
    } finally {
      setDeletingFile(false);
    }
  };

  const openExecuteModal = (action: ResearchAction) => {
    setPendingAction(action);
    setExecuteMode('skill');
    setSelectedSkill(action.defaultSkill);
    setSelectedWorkflow(null);
    setExecuteOpened(true);
  };

  const runAction = async () => {
    if (!currentTask || !pendingAction) return;
    const target = executeMode === 'skill' ? selectedSkill : selectedWorkflow;
    if (!target) return;

    const saved = await saveCurrentContent();
    if (!saved) return;

    const workspacePath = currentTopic ? researchProjectPath(currentTopic) : 'workspace/research';
    const prompt = executeMode === 'skill'
      ? `Use agent skill ${target} ${pendingAction.skillPromptSuffix}`
      : `Execute workflow ${workflowProjectPath(target)}. ${pendingAction.skillPromptSuffix.charAt(0).toUpperCase()}${pendingAction.skillPromptSuffix.slice(1)}\n\nYour Workspace path: ${workspacePath}\n\nIf you create any intermediate files, save them inside the project workspace above.`;

    setExecuteOpened(false);
    if (executeMode === 'workflow') {
      void router.push(
        `/?new_session=true&prompt=${encodeURIComponent(prompt)}&workflow=${encodeURIComponent(`${target}.json`)}&next_node_trigger=${encodeURIComponent('auto_continue')}&resume=false&resume_available=false`,
      );
      return;
    }
    void router.push(`/?new_session=true&prompt=${encodeURIComponent(prompt)}`);
  };

  useEffect(() => {
    fetchTree();
    fetchLlmProviders();
    fetchExecuteOptions();
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
          router.push(`/research?task=${encodeURIComponent(item.path)}`, undefined, { shallow: true });
          setOpened(false);
        }}
      />
    );
  });

  const currentInstructionPath = currentTask ? researchProjectPath(currentTask) : '';
  const fileActions = useMemo<ResearchAction[]>(() => {
    if (currentFileName !== 'requirements.md' || !currentInstructionPath) return [];
    return [
      {
        label: 'Refine',
        defaultSkill: 'refine-research-requirement',
        skillPromptSuffix: `to refine the research requirement ${currentInstructionPath}`,
      },
      {
        label: 'Research',
        defaultSkill: 'deep-research',
        skillPromptSuffix: `to make a research as the requirement file defined at ${currentInstructionPath}`,
      },
    ];
  }, [currentFileName, currentInstructionPath]);

  const mediaUrl = currentTask ? `${API_BASE_URL}/research/file?path=${encodeURIComponent(currentTask)}` : '';
  const isMarkdownEditor = selectedKind === 'markdown';
  const isTextEditor = selectedKind === 'text';

  const renderActionButtons = () => {
    if (fileActions.length === 0) return null;
    return (
      <Group spacing="xs" mb="md" noWrap={false}>
        {fileActions.map((action) => (
          <Button key={action.label} size="xs" variant="default" onClick={() => openExecuteModal(action)}>
            {action.label}
          </Button>
        ))}
      </Group>
    );
  };

  const renderMainContent = () => {
    if (!currentTask) {
      if (loading) return null;
      if (treeData.length === 0) {
        return (
          <div
            style={{
              minHeight: '60vh',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
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
                Research Workspace
              </Text>
              <Text size={28} weight={800} mt={10}>
                Start your first topic
              </Text>
              <Text size="sm" color="dimmed" mt={12} style={{ maxWidth: 420, margin: '12px auto 0 auto', lineHeight: 1.6 }}>
                Create a topic folder with a research requirement, then refine it or run deep research with a skill or workflow.
              </Text>
              <Group position="center" mt="xl">
                <Button onClick={openTopicModal}>New Topic</Button>
              </Group>
            </div>
          </div>
        );
      }
      return <Text align="center" py="xl" color="dimmed">Select a research file from the sidebar to begin.</Text>;
    }

    if (selectedKind === 'pdf' && currentTask) {
      return (
        <>
          <div style={{ height: '75vh', borderRadius: 8, overflow: 'hidden', border: `1px solid ${theme.colors.gray[3]}` }}>
            <iframe title={currentFileName} src={mediaUrl} style={{ width: '100%', height: '100%', border: 'none' }} />
          </div>
          <Group position="right" mt="md">
            <Button color="red" variant="light" onClick={() => void deleteCurrentFile()} loading={deletingFile}>Delete</Button>
          </Group>
        </>
      );
    }

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
              <Button key={action.label} size="xs" variant="default" onClick={() => openExecuteModal(action)}>
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

    return !loading ? <Text align="center" py="xl" color="dimmed">Select a research file from the sidebar to begin.</Text> : null;
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
        <title>Skill Pilot - Research</title>
      </Head>

      <Modal opened={topicModalOpened} onClose={() => setTopicModalOpened(false)} title="New Topic" centered>
        <div>
          <Text size="sm" weight={700} mb={4}>Topic Name</Text>
          <TextInput
            placeholder="topic-name"
            value={topicNameInput}
            onChange={(e) => setTopicNameInput(e.currentTarget.value)}
            description="A topic folder will be created in kebab-case. Duplicates get _1, _2, and so on."
          />
        </div>
        <div style={{ marginTop: 16 }}>
          <Text size="sm" weight={700} mb={4}>Requirements of Research</Text>
          <Textarea
            value={topicRequirementsInput}
            onChange={(e) => setTopicRequirementsInput(e.currentTarget.value)}
            minRows={10}
            autosize
          />
        </div>
        <Group position="right" mt="md">
          <Button variant="default" onClick={() => setTopicModalOpened(false)}>Cancel</Button>
          <Button onClick={() => void createTopic()} loading={creatingTopic} disabled={!topicNameInput.trim()}>
            Create
          </Button>
        </Group>
      </Modal>

      <Modal
        opened={executeOpened}
        onClose={() => setExecuteOpened(false)}
        title={pendingAction ? pendingAction.label : 'Run Action'}
        centered
        size="lg"
      >
        <div>
          <Text size="sm" weight={700} mb={4}>Run By</Text>
          <Group mt="xs">
            <Radio value="skill" checked={executeMode === 'skill'} onChange={() => setExecuteMode('skill')} label="Skill" />
            <Radio value="workflow" checked={executeMode === 'workflow'} onChange={() => setExecuteMode('workflow')} label="Workflow" />
          </Group>
        </div>
        <div style={{ marginTop: 16 }}>
          {executeMode === 'skill' ? (
            <Select
              label="Skill"
              placeholder="Select a skill"
              value={selectedSkill}
              onChange={setSelectedSkill}
              data={skillOptions.map((item) => ({ value: item, label: item }))}
              searchable
              clearable={false}
            />
          ) : (
            <Select
              label="Workflow"
              placeholder="Select a workflow"
              value={selectedWorkflow}
              onChange={setSelectedWorkflow}
              data={workflowOptions.map((item) => ({ value: item, label: item }))}
              searchable
              clearable
            />
          )}
        </div>
        <div style={{ marginTop: 16 }}>
          <Text size="sm" weight={700} mb={4}>Instruction File</Text>
          <Text size="sm">{currentInstructionPath || '(no file selected)'}</Text>
        </div>
        <Group position="right" mt="md">
          <Button variant="default" onClick={() => setExecuteOpened(false)}>Cancel</Button>
          <Button onClick={() => void runAction()} disabled={!currentTask || (executeMode === 'skill' ? !selectedSkill : !selectedWorkflow)}>
            Run
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
          style={{ position: 'relative', transition: isResizing ? 'none' : 'width 200ms ease', height: '100%' }}
        >
          <Navbar.Section mb="md">
            <Group position="apart" align="center">
              <Text weight={700} size="lg">Topics</Text>
              <Group spacing={4}>
                <Tooltip label="New Topic">
                  <ActionIcon variant="subtle" onClick={openTopicModal}>
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

        <main style={{ flex: 1, display: 'flex', justifyContent: 'center', overflowY: 'auto', padding: '20px' }}>
          <div className="w-full max-w-4xl bg-white p-6 rounded-lg shadow-sm relative" style={{ height: 'fit-content', minHeight: '100%', marginTop: 24 }}>
            <LoadingOverlay visible={loading} overlayBlur={2} />
            {currentFileName ? <h1 className="mb-4">{currentFileName}</h1> : null}
            {currentTopic ? <Text size="sm" color="dimmed" mb="sm">Topic: {currentTopic}</Text> : null}
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
