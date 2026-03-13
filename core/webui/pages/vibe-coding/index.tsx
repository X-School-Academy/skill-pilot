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
import { resolveSelectedProvider, setSelectedProvider } from '../../libs/llm';

const API_BASE_URL = apiUrl('/api');
axios.defaults.withCredentials = true;

type FileKind = 'markdown' | 'text' | 'image' | 'audio' | 'video';
type RequestMode = 'update' | 'issue';
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

interface VibeAction {
  label: string;
  defaultSkill: string;
  skillPromptSuffix: string;
}

const detectFileKind = (path: string): FileKind => {
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

const workflowProjectPath = (name: string): string => `core/workflows/${name}.json`;

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
  const [executeOpened, setExecuteOpened] = useState(false);
  const [executeMode, setExecuteMode] = useState<ExecuteMode>('skill');
  const [skillOptions, setSkillOptions] = useState<string[]>([]);
  const [workflowOptions, setWorkflowOptions] = useState<string[]>([]);
  const [selectedSkill, setSelectedSkill] = useState<string | null>(null);
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<VibeAction | null>(null);
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
        setNotice('');
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
      const serverDefault: string = res.data.default || '';
      const defaultId = resolveSelectedProvider(providers, serverDefault, 'gemini');
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

  const openExecuteModal = (action: VibeAction) => {
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

    const workspacePath = currentProject ? vibeProjectPath(currentProject) : 'workspace/vibe-coding';
    const projectLabel = currentProject ? `\nVibe coding project name: ${currentProject}` : '';
    const prompt = executeMode === 'skill'
      ? `Use agent skill ${target} ${pendingAction.skillPromptSuffix}${projectLabel}`
      : `Execute workflow ${workflowProjectPath(target)}. ${pendingAction.skillPromptSuffix.charAt(0).toUpperCase()}${pendingAction.skillPromptSuffix.slice(1)}\n\nYour Workspace path: ${workspacePath}${projectLabel}\n\nIf you create any intermediate files, save them inside the project workspace above.`;

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
          defaultSkill: 'vibe-coding-project-refine',
          skillPromptSuffix: `to refine the ${currentInstructionPath}`,
        },
        {
          label: 'Brainstorm',
          defaultSkill: 'vibe-coding-project-brainstorm',
          skillPromptSuffix: `to brainstorm ideas and alternatives for the ${currentInstructionPath}`,
        },
        {
          label: 'Initial',
          defaultSkill: 'vibe-coding-project-initial',
          skillPromptSuffix: `to init the project defined at ${currentInstructionPath}`,
        },
        {
          label: 'Plan',
          defaultSkill: 'vibe-coding-project-plan',
          skillPromptSuffix: `to make a development plan for requirement ${currentInstructionPath}`,
        },
      ];
    }
    if (currentFileName === 'plan.md') {
      return [
        {
          label: 'Implement',
          defaultSkill: 'vibe-coding-project-implement',
          skillPromptSuffix: `to implement the code as the ${currentInstructionPath}`,
        },
      ];
    }
    if (currentFileName === 'implement.md') {
      return [
        {
          label: 'Review',
          defaultSkill: 'vibe-coding-project-review',
          skillPromptSuffix: `to review the code of the implementation of the ${currentInstructionPath}`,
        },
        {
          label: 'Test',
          defaultSkill: 'vibe-coding-project-test',
          skillPromptSuffix: `to test the code of the implementation of the ${currentInstructionPath}`,
        },
        {
          label: 'Deploy',
          defaultSkill: 'vibe-coding-project-deploy',
          skillPromptSuffix: `to deploy the code of the implementation of the ${currentInstructionPath}`,
        },
      ];
    }
    if (currentFileName === 'update.md') {
      return [
        {
          label: 'Update Code',
          defaultSkill: 'vibe-coding-project-update',
          skillPromptSuffix: `to update the code based on the update request defined in ${currentInstructionPath}`,
        },
      ];
    }
    if (currentFileName === 'brainstorm.md') {
      return [
        {
          label: 'Apply to Requirements',
          defaultSkill: 'vibe-coding-project-apply-brainstorm',
          skillPromptSuffix: `to merge brainstorm ideas from ${currentInstructionPath} into the project requirements`,
        },
      ];
    }
    if (currentFileName === 'issues.md') {
      return [
        {
          label: 'Fix Issues',
          defaultSkill: 'vibe-coding-project-fix-issues',
          skillPromptSuffix: `to fix the issues defined in ${currentInstructionPath}`,
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
            onClick={() => openExecuteModal(action)}
          >
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
                Vibe Coding Workspace
              </Text>
              <Text size={28} weight={800} mt={10}>
                Start your first project
              </Text>
              <Text size="sm" color="dimmed" mt={12} style={{ maxWidth: 420, margin: '12px auto 0 auto', lineHeight: 1.6 }}>
                Create a project requirement, then refine, plan, implement, review, test, and deploy from the same workspace.
              </Text>
              <Group position="center" mt="xl">
                <Button onClick={openProjectModal}>New Project</Button>
              </Group>
            </div>
          </div>
        );
      }
      return <Text align="center" py="xl" color="dimmed">Select a project file from the sidebar to begin.</Text>;
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
              <Button
                key={action.label}
                size="xs"
                variant="default"
                onClick={() => openExecuteModal(action)}
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

      <Modal
        opened={executeOpened}
        onClose={() => setExecuteOpened(false)}
        title={pendingAction ? pendingAction.label : 'Run Action'}
        centered
        size="lg"
      >
        <Stack spacing="md">
          <div>
            <Text size="sm" weight={700} mb={4}>Run By</Text>
            <Group mt="xs">
              <Radio
                value="skill"
                checked={executeMode === 'skill'}
                onChange={() => setExecuteMode('skill')}
                label="Skill"
              />
              <Radio
                value="workflow"
                checked={executeMode === 'workflow'}
                onChange={() => setExecuteMode('workflow')}
                label="Workflow"
              />
            </Group>
          </div>

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

          <div>
            <Text size="sm" weight={700} mb={4}>Instruction File</Text>
            <Text size="sm">{currentInstructionPath || '(no file selected)'}</Text>
          </div>
        </Stack>
        <Group position="right" mt="md">
          <Button variant="default" onClick={() => setExecuteOpened(false)}>Cancel</Button>
          <Button
            onClick={() => void runAction()}
            disabled={!currentTask || (executeMode === 'skill' ? !selectedSkill : !selectedWorkflow)}
          >
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
