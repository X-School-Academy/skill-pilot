import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
  Badge,
  Box,
  Button,
  Group,
  Header,
  LoadingOverlay,
  Menu,
  Modal,
  Navbar,
  NavLink,
  ScrollArea,
  SegmentedControl,
  Tabs,
  Text,
  Textarea,
  TextInput,
  Tooltip,
  useMantineTheme,
} from '@mantine/core';
import { DatePickerInput } from '@mantine/dates';
import {
  IconBrandLinkedin,
  IconBrandX,
  IconBrandWechat,
  IconPlus,
  IconDotsVertical,
  IconEdit,
  IconEye,
  IconSend,
  IconRefresh,
  IconTrash,
  IconCalendar,
  IconFileText,
} from '@tabler/icons-react';

import { apiUrl } from '../../libs/api-base';

const API_BASE_URL = apiUrl('/api');

// --- types ---

type Platform = 'linkedin' | 'x' | 'xiaohongshu';

interface FileItem {
  name: string;
  path: string;
  type: 'file' | 'dir';
  children?: FileItem[];
  mtime?: number;
  size?: number;
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

interface HistoryPost {
  platform: string;
  url?: string;
  date?: string;
  title?: string;
}

const PLATFORMS: Platform[] = ['linkedin', 'x', 'xiaohongshu'];

const PLATFORM_LABELS: Record<Platform, string> = {
  linkedin: 'LinkedIn',
  x: 'X',
  xiaohongshu: 'Xiaohongshu',
};

const PLATFORM_ICONS: Record<Platform, React.ReactNode> = {
  linkedin: <IconBrandLinkedin size="1rem" />,
  x: <IconBrandX size="1rem" />,
  xiaohongshu: <IconBrandWechat size="1rem" />,
};

const PLATFORM_HINTS: Record<Platform, { title: string; tips: string[] }> = {
  linkedin: {
    title: 'LinkedIn Writing Tips',
    tips: [
      'Start with a strong hook in the first 2 lines',
      'Use bullet points for key takeaways',
      'End with a CTA question to drive engagement',
      '3-5 relevant hashtags at the end',
    ],
  },
  x: {
    title: 'X Writing Tips',
    tips: [
      'Numbered thread format (1/n) for longer content',
      'Keep it punchy and opinionated',
      'Hot takes perform better than neutral takes',
      'One key insight per tweet in a thread',
    ],
  },
  xiaohongshu: {
    title: 'Xiaohongshu Writing Tips',
    tips: [
      'Start with 【topic】 in the title',
      'Use emojis generously throughout',
      'Focus on 干货 (substance) — actionable tips',
      '5-10 relevant tags at the end',
    ],
  },
};

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

// --- helpers ---

const socialProjectPath = (p: string) => p.replace(/^\/+/, '');
const socialRelativePath = (pp: string) => pp;

// --- API calls ---

async function fetchTree(): Promise<FileItem[]> {
  const { data } = await axios.get(`${API_BASE_URL}/social/tree`);
  return data.items || [];
}

async function fetchContent(p: string): Promise<{ path: string; content: string }> {
  const { data } = await axios.get(`${API_BASE_URL}/social/content`, { params: { path: socialProjectPath(p) } });
  return data;
}

async function saveContent(p: string, content: string): Promise<void> {
  await axios.post(`${API_BASE_URL}/social/save`, { path: socialProjectPath(p), content });
}

async function createDraft(platform: Platform, title: string): Promise<string> {
  const { data } = await axios.post(`${API_BASE_URL}/social/create`, { platform, title });
  return data.path;
}

async function deleteDraft(p: string): Promise<void> {
  await axios.post(`${API_BASE_URL}/social/delete`, { path: socialProjectPath(p) });
}

async function fetchHistory(): Promise<{ posts: HistoryPost[] }> {
  const { data } = await axios.get(`${API_BASE_URL}/social/history`);
  return data;
}

async function fetchCalendar(p?: Platform): Promise<CalendarItem[]> {
  const params: Record<string, string> = {};
  if (p) params.platform = p;
  const { data } = await axios.get(`${API_BASE_URL}/social/calendar`, { params });
  return data.items || [];
}

async function createCalendarItem(item: Partial<CalendarItem>): Promise<CalendarItem> {
  const { data } = await axios.post(`${API_BASE_URL}/social/calendar`, item);
  return data.item;
}

async function updateCalendarItem(id: string, updates: Partial<CalendarItem>): Promise<CalendarItem> {
  const { data } = await axios.patch(`${API_BASE_URL}/social/calendar/${id}`, updates);
  return data.item;
}

async function deleteCalendarItem(id: string): Promise<void> {
  await axios.delete(`${API_BASE_URL}/social/calendar/${id}`);
}

// --- component ---

export default function SocialMediaPage() {
  const router = useRouter();
  const theme = useMantineTheme();

  const [treeData, setTreeData] = useState<FileItem[]>([]);
  const [selectedPlatform, setSelectedPlatform] = useState<Platform>('linkedin');
  const [currentFile, setCurrentFile] = useState<string | null>(null);
  const [editorContent, setEditorContent] = useState('');
  const [markdownView, setMarkdownView] = useState<'edit' | 'preview'>('edit');
  const [loading, setLoading] = useState(false);
  const [editorSaving, setEditorSaving] = useState(false);
  const [editorError, setEditorError] = useState('');
  const [notice, setNotice] = useState('');

  // history
  const [historyData, setHistoryData] = useState<HistoryPost[]>([]);

  // calendar
  const [calendarItems, setCalendarItems] = useState<CalendarItem[]>([]);
  const [calendarModalOpened, setCalendarModalOpened] = useState(false);
  const [calendarEditItem, setCalendarEditItem] = useState<CalendarItem | null>(null);
  const [calTopic, setCalTopic] = useState('');
  const [calPlatform, setCalPlatform] = useState<Platform>('linkedin');
  const [calDate, setCalDate] = useState<Date | null>(null);
  const [calStatus, setCalStatus] = useState<string>('idea');
  const [calDraftPath, setCalDraftPath] = useState('');
  const [calNotes, setCalNotes] = useState('');

  // auto-save
  const editorContentRef = useRef(editorContent);
  const lastLoadedContentRef = useRef('');
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => { editorContentRef.current = editorContent; }, [editorContent]);

  // load tree
  const loadTree = useCallback(async () => {
    try {
      const items = await fetchTree();
      setTreeData(items);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => { loadTree(); }, [loadTree]);

  // load history
  useEffect(() => {
    fetchHistory().then(d => setHistoryData(d.posts || [])).catch(() => {});
  }, []);

  // load calendar
  useEffect(() => {
    fetchCalendar(selectedPlatform).then(setCalendarItems).catch(() => {});
  }, [selectedPlatform]);

  // auto-save: 900ms debounce
  const doAutoSave = useCallback(async () => {
    if (!currentFile) return;
    const c = editorContentRef.current;
    if (c === lastLoadedContentRef.current) return;
    try {
      setEditorSaving(true);
      await saveContent(currentFile, c);
      lastLoadedContentRef.current = c;
      setNotice('Saved');
      setTimeout(() => setNotice(''), 2000);
    } catch {
      setEditorError('Save failed');
    } finally {
      setEditorSaving(false);
    }
  }, [currentFile]);

  useEffect(() => {
    if (!currentFile) return;
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(doAutoSave, 900);
    return () => { if (saveTimerRef.current) clearTimeout(saveTimerRef.current); };
  }, [editorContent, currentFile, doAutoSave]);

  // open file
  const openFile = async (p: string) => {
    setLoading(true);
    setEditorError('');
    try {
      const { content } = await fetchContent(p);
      setCurrentFile(p);
      setEditorContent(content);
      lastLoadedContentRef.current = content;
    } catch (e: any) {
      setEditorError(e?.response?.data?.error || 'Failed to load');
    } finally {
      setLoading(false);
    }
  };

  // create new draft
  const handleCreate = async () => {
    const title = prompt('Draft title:')?.trim();
    if (!title) return;
    try {
      const p = await createDraft(selectedPlatform, title);
      await loadTree();
      openFile(p);
    } catch {
      setEditorError('Failed to create draft');
    }
  };

  // delete current
  const handleDelete = async () => {
    if (!currentFile) return;
    if (!confirm('Delete this draft?')) return;
    try {
      await deleteDraft(currentFile);
      setCurrentFile(null);
      setEditorContent('');
      await loadTree();
    } catch {
      setEditorError('Failed to delete');
    }
  };

  // schedule from draft context
  const openCalendarForDraft = (p: string) => {
    resetCalendarForm();
    setCalendarEditItem(null);
    setCalDraftPath(p);
    setCalPlatform(selectedPlatform);
    setCalendarModalOpened(true);
  };

  // calendar form
  const resetCalendarForm = () => {
    setCalTopic('');
    setCalPlatform(selectedPlatform);
    setCalDate(null);
    setCalStatus('idea');
    setCalDraftPath('');
    setCalNotes('');
    setCalendarEditItem(null);
  };

  const openCalendarCreate = () => {
    resetCalendarForm();
    setCalendarModalOpened(true);
  };

  const openCalendarEdit = (item: CalendarItem) => {
    setCalendarEditItem(item);
    setCalTopic(item.topic);
    setCalPlatform(item.platform);
    setCalDate(item.scheduledDate ? new Date(item.scheduledDate) : null);
    setCalStatus(item.status);
    setCalDraftPath(item.draftPath);
    setCalNotes(item.notes);
    setCalendarModalOpened(true);
  };

  const saveCalendarItem = async () => {
    if (!calTopic.trim()) return;
    const payload = {
      topic: calTopic.trim(),
      platform: calPlatform,
      status: calStatus,
      scheduledDate: calDate ? calDate.toISOString().slice(0, 10) : '',
      draftPath: calDraftPath,
      notes: calNotes,
    };
    try {
      if (calendarEditItem) {
        await updateCalendarItem(calendarEditItem.id, payload);
      } else {
        await createCalendarItem(payload);
      }
      setCalendarModalOpened(false);
      const items = await fetchCalendar(selectedPlatform);
      setCalendarItems(items);
    } catch {
      // ignore
    }
  };

  const cycleCalendarStatus = async (item: CalendarItem) => {
    const order = ['idea', 'scheduled', 'drafted', 'published'];
    const idx = order.indexOf(item.status);
    const next = order[(idx + 1) % order.length];
    try {
      await updateCalendarItem(item.id, { status: next });
      const items = await fetchCalendar(selectedPlatform);
      setCalendarItems(items);
    } catch {
      // ignore
    }
  };

  const handleDeleteCalendar = async (id: string) => {
    if (!confirm('Delete this calendar item?')) return;
    try {
      await deleteCalendarItem(id);
      const items = await fetchCalendar(selectedPlatform);
      setCalendarItems(items);
    } catch {
      // ignore
    }
  };

  // platform drafts
  const platformDrafts = useMemo(() => {
    const folder = treeData.find(f => f.name === selectedPlatform);
    return folder?.children?.filter(f => f.type === 'file' && f.name.endsWith('.md')) || [];
  }, [treeData, selectedPlatform]);

  // nav
  const navContent = (
    <ScrollArea>
      <Box p="sm">
        <SegmentedControl
          fullWidth
          size="xs"
          value={selectedPlatform}
          onChange={(v) => setSelectedPlatform(v as Platform)}
          data={PLATFORMS.map(p => ({ value: p, label: PLATFORM_LABELS[p] }))}
        />
      </Box>

      <Group px="sm" pb="xs" position="apart">
        <Text size="xs" weight={600} color="dimmed">DRAFTS</Text>
        <ActionIcon size="sm" variant="subtle" onClick={handleCreate} title="New draft">
          <IconPlus size="0.9rem" />
        </ActionIcon>
      </Group>

      {platformDrafts.map(f => (
        <NavLink
          key={f.path}
          label={f.name.replace(/\.md$/, '')}
          active={currentFile === f.path}
          onClick={() => openFile(f.path)}
          rightSection={
            <Menu shadow="md" width={160}>
              <Menu.Target>
                <ActionIcon size="xs" variant="subtle" onClick={(e: React.MouseEvent) => e.stopPropagation()}>
                  <IconDotsVertical size="0.8rem" />
                </ActionIcon>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Item icon={<IconCalendar size="0.9rem" />} onClick={(e: React.MouseEvent) => { e.stopPropagation(); openCalendarForDraft(f.path); }}>
                  Schedule
                </Menu.Item>
                <Menu.Item color="red" icon={<IconTrash size="0.9rem" />} onClick={(e: React.MouseEvent) => { e.stopPropagation(); }}>
                  Delete
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
          }
        />
      ))}

      {/* History */}
      <Box px="sm" pt="md">
        <Text size="xs" weight={600} color="dimmed" pb="xs">POST HISTORY</Text>
        {historyData.length === 0 && <Text size="xs" color="dimmed">No posts yet</Text>}
        {historyData.slice(0, 10).map((post, i) => (
          <Text key={i} size="xs" color="dimmed" py={1}>
            {post.platform}: {post.title || post.url || 'Untitled'}
          </Text>
        ))}
      </Box>

      {/* Calendar */}
      <Box px="sm" pt="md">
        <Group position="apart" pb="xs">
          <Text size="xs" weight={600} color="dimmed">CONTENT CALENDAR</Text>
          <ActionIcon size="sm" variant="subtle" onClick={openCalendarCreate} title="Add to calendar">
            <IconPlus size="0.9rem" />
          </ActionIcon>
        </Group>
        {calendarItems.length === 0 && <Text size="xs" color="dimmed">No scheduled content</Text>}
        {calendarItems.slice(0, 10).map(item => (
          <Box key={item.id} py={4} style={{ cursor: 'pointer' }} onClick={() => openCalendarEdit(item)}>
            <Group spacing={6} noWrap>
              <Badge
                size="xs"
                color={CALENDAR_STATUS_COLORS[item.status]}
                variant="light"
                style={{ cursor: 'pointer' }}
                onClick={(e: React.MouseEvent) => { e.stopPropagation(); cycleCalendarStatus(item); }}
              >
                {CALENDAR_STATUS_LABELS[item.status]}
              </Badge>
              <Text size="xs" lineClamp={1}>{item.topic}</Text>
              {item.scheduledDate && <Text size="xs" color="dimmed">{item.scheduledDate}</Text>}
            </Group>
          </Box>
        ))}
      </Box>
    </ScrollArea>
  );

  const hints = PLATFORM_HINTS[selectedPlatform];

  return (
    <>
      <Head><title>Social Media</title></Head>
      <AppShell
        styles={{
          main: {
            background: theme.colorScheme === 'dark' ? theme.colors.dark[8] : theme.colors.gray[0],
            padding: 0,
            marginTop: 48,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            height: 'calc(100vh - 48px)',
            minHeight: 0,
          },
        }}
        navbarOffsetBreakpoint="sm"
        header={
          <Header height={48} px="md">
            <Group position="apart" align="center" style={{ height: '100%' }}>
              <Group spacing="sm">
                <Text weight={700}>Social Media</Text>
                {notice && <Text size="xs" color="green">{notice}</Text>}
                {editorSaving && <Text size="xs" color="dimmed">Saving...</Text>}
                {editorError && <Text size="xs" color="red">{editorError}</Text>}
              </Group>
              <Group spacing="xs">
                <Button
                  size="xs"
                  variant="light"
                  leftIcon={<IconRefresh size="0.8rem" />}
                  disabled={!currentFile}
                >
                  Repurpose
                </Button>
                <Button
                  size="xs"
                  leftIcon={<IconSend size="0.8rem" />}
                  disabled={!currentFile}
                >
                  Publish
                </Button>
              </Group>
            </Group>
          </Header>
        }
      >
        <Box style={{ position: 'relative', display: 'flex', flex: 1, minHeight: 0 }}>
          {/* Left sidebar */}
          <Navbar width={{ base: 280 }} hiddenBreakpoint="sm" hidden={false} style={{ flexShrink: 0, height: '100%' }}>
            {navContent}
          </Navbar>

          {/* Main content */}
          <Box style={{ flex: 1, minHeight: 0, overflow: 'hidden', position: 'relative' }}>
            <LoadingOverlay visible={loading} />

            {!currentFile ? (
              <Box p="xl" style={{ textAlign: 'center', paddingTop: '20%' }}>
                <IconFileText size="3rem" color={theme.colors.gray[4]} />
                <Text color="dimmed" mt="md">Select a draft or create a new one</Text>
                <Button mt="md" variant="light" onClick={handleCreate}>Create Draft</Button>
              </Box>
            ) : (
              <Box p="md" style={{ height: '100%' }}>
                {/* Hints card */}
                <Group mb="sm" spacing="xs">
                  {PLATFORM_ICONS[selectedPlatform]}
                  <Text size="sm" weight={600}>{hints.title}</Text>
                </Group>
                <Box mb="md" p="sm" style={{ background: theme.colors.gray[0], borderRadius: 8, fontSize: '0.8rem' }}>
                  {hints.tips.map((tip, i) => (
                    <Text key={i} size="xs" color="dimmed">• {tip}</Text>
                  ))}
                </Box>

                {/* Edit/Preview tabs */}
                <Tabs value={markdownView} onTabChange={(v) => setMarkdownView(v as 'edit' | 'preview')} mb="sm">
                  <Tabs.List>
                    <Tabs.Tab value="edit" icon={<IconEdit size="0.8rem" />}>Edit</Tabs.Tab>
                    <Tabs.Tab value="preview" icon={<IconEye size="0.8rem" />}>Preview</Tabs.Tab>
                  </Tabs.List>
                </Tabs>

                {markdownView === 'edit' ? (
                  <Textarea
                    value={editorContent}
                    onChange={(e) => setEditorContent(e.currentTarget.value)}
                    minRows={20}
                    maxRows={40}
                    autosize
                    placeholder="Write your content here..."
                    styles={{
                      input: {
                        fontFamily: "'JetBrains Mono', 'Fira Mono', 'Cascadia Code', 'Consolas', monospace",
                        fontSize: '0.85rem',
                        minHeight: '400px',
                      },
                    }}
                  />
                ) : (
                  <Box
                    p="md"
                    style={{
                      background: '#fff',
                      borderRadius: 8,
                      border: '1px solid #eee',
                      minHeight: '400px',
                      maxHeight: 'calc(100vh - 350px)',
                      overflow: 'auto',
                    }}
                  >
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {editorContent || '*Nothing to preview*'}
                    </ReactMarkdown>
                  </Box>
                )}

                {/* Delete button */}
                <Group mt="sm">
                  <Button size="xs" variant="subtle" color="red" leftIcon={<IconTrash size="0.8rem" />} onClick={handleDelete}>
                    Delete Draft
                  </Button>
                </Group>
              </Box>
            )}
          </Box>
        </Box>
      </AppShell>

      {/* Calendar modal */}
      <Modal opened={calendarModalOpened} onClose={() => setCalendarModalOpened(false)} title={calendarEditItem ? 'Edit Calendar Item' : 'New Calendar Item'} size="md">
        <TextInput label="Topic" value={calTopic} onChange={e => setCalTopic(e.currentTarget.value)} mb="sm" required />
        <SegmentedControl
          fullWidth
          size="xs"
          value={calPlatform}
          onChange={(v) => setCalPlatform(v as Platform)}
          data={PLATFORMS.map(p => ({ value: p, label: PLATFORM_LABELS[p] }))}
          mb="sm"
        />
        <DatePickerInput label="Scheduled Date" value={calDate} onChange={setCalDate} clearable mb="sm" />
        <SegmentedControl
          fullWidth
          size="xs"
          value={calStatus}
          onChange={setCalStatus}
          data={['idea', 'scheduled', 'drafted', 'published'].map(s => ({ value: s, label: CALENDAR_STATUS_LABELS[s] }))}
          mb="sm"
        />
        <TextInput label="Draft Path" value={calDraftPath} onChange={e => setCalDraftPath(e.currentTarget.value)} mb="sm" />
        <Textarea label="Notes" value={calNotes} onChange={e => setCalNotes(e.currentTarget.value)} minRows={3} mb="md" />
        <Group position="apart">
          {calendarEditItem && (
            <Button size="sm" variant="subtle" color="red" onClick={() => { handleDeleteCalendar(calendarEditItem.id); setCalendarModalOpened(false); }}>
              Delete
            </Button>
          )}
          <Button size="sm" onClick={saveCalendarItem}>{calendarEditItem ? 'Update' : 'Create'}</Button>
        </Group>
      </Modal>
    </>
  );
}

export async function getStaticProps(ctx: GetStaticPropsContext) {
  return { props: { ...(await serverSideTranslations(ctx.locale || 'en', ['common'])) } };
}
