import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Badge,
  Box,
  Button,
  Checkbox,
  Divider,
  Group,
  Loader,
  Modal,
  Stack,
  Text,
  Tooltip,
  useMantineTheme,
} from '@mantine/core';
import {
  IconArrowRight,
  IconArrowLeft,
  IconCopy,
  IconExternalLink,
  IconFile,
  IconFolderOpen,
  IconGripHorizontal,
  IconPlayerPlay,
  IconRobot,
  IconSchool,
  IconSparkles,
  IconStar,
  IconTrendingUp,
  IconVideo,
  IconX,
} from '@tabler/icons-react';

import { apiUrl } from '../../libs/api-base';

type ExploreMode = 'category' | 'popularity' | 'level';

interface ShowcaseLink {
  name: string;
  url: string;
}

interface ShowcaseRelated {
  slug: string;
  caption: string;
}

interface ShowcaseVariant {
  slug: string;
  caption: string;
}

interface ShowcaseSequenceLink {
  slug_id: string;
  title: string;
}

interface ShowcaseResolvedItem {
  label: string;
  path: string | null;
}

interface ShowcaseSample {
  id: string;
  title: string;
  description: string;
  thumbnail: string | null;
  thumbnail_url: string | null;
  video: string | null;
  video_url: string | null;
  tutorial: string | null;
  tutorial_url: string | null;
  tutorial_is_media: boolean;
  request: string | null;
  request_url: string | null;
  request_is_media: boolean;
  prompt: string;
  workflow: string | null;
  directory: string | null;
  'zip-files-url'?: string | null;
  in_mode: 'dev' | 'prod';
  git_tag: string | null;
  use_worktree: boolean;
  skills: string[];
  skill_items?: ShowcaseResolvedItem[];
  subagents?: string[];
  subagent_items?: ShowcaseResolvedItem[];
  extensions: string[];
  tools: string[];
  tool_items?: ShowcaseResolvedItem[];
  files: string[];
  file_items?: ShowcaseResolvedItem[];
  prompt_items?: ShowcaseResolvedItem[];
  links: ShowcaseLink[];
  related: ShowcaseRelated[];
  variants: ShowcaseVariant[];
  previous_showcase: ShowcaseSequenceLink | null;
  next_showcase: ShowcaseSequenceLink | null;
  goals: string | null;
  terms: string[];
  term_urls?: Record<string, string>;
  popularity: number;
  level: number;
  rate: number;
}

interface ShowcaseCategory {
  category: string;
  description: string;
  thumbnail: string | null;
  thumbnail_url: string | null;
  samples: ShowcaseSample[];
  subcategories?: ShowcaseCategory[];
}

interface LaunchResponse {
  status: 'launched' | 'pending' | 'needs_existing_worktree_action' | 'monitor_dev_and_continue' | 'relaunching_current_dev' | 'error';
  target_url?: string;
  monitor_url?: string;
  launch_id?: string;
  worktree_path?: string;
  reused_running_dev?: boolean;
  error?: string;
}

const API_BASE_URL = apiUrl('/api');

const TILE_COLORS: Array<[string, string]> = [
  ['#0d9488', '#5eead4'],
  ['#2563eb', '#93c5fd'],
  ['#7c3aed', '#c4b5fd'],
  ['#0891b2', '#67e8f9'],
  ['#059669', '#6ee7b7'],
  ['#6366f1', '#a5b4fc'],
];

function pickColor(seed: string): [string, string] {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = ((hash << 5) - hash) + seed.charCodeAt(i);
    hash |= 0;
  }
  return TILE_COLORS[Math.abs(hash) % TILE_COLORS.length];
}

function initialsFromText(value: string): string {
  const parts = value.split(/\s+/).filter(Boolean).slice(0, 3);
  return parts.map((item) => item[0]?.toUpperCase() || '').join('') || '?';
}

function openFileManager(path: string) {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  window.open(`/file-manager?path=${encodeURIComponent(normalized)}`, '_blank', 'noopener,noreferrer');
}

function promptToMarkdown(prompt: string, resolvedPaths?: Map<string, string>): string {
  return prompt.replace(/@([A-Za-z0-9_./-]+)/g, (_match, pathValue) => {
    const rawPath = String(pathValue);
    const punctuation = rawPath.match(/[.,;:!?]+$/)?.[0] || '';
    const displayPath = punctuation ? rawPath.slice(0, -punctuation.length) : rawPath;
    const normalizedPath = displayPath.replace(/^\/+/, '');
    const resolvedPath = resolvedPaths?.get(normalizedPath);
    if (resolvedPaths && !resolvedPath) {
      return `@${displayPath}${punctuation}`;
    }
    const path = `/${resolvedPath || normalizedPath}`;
    return `[@${displayPath}](/file-manager?path=${encodeURIComponent(path)})${punctuation}`;
  });
}

function isMarkdownUrl(value: string | null | undefined): boolean {
  const raw = String(value || '').trim();
  if (!raw) return false;
  if (/^https?:\/\//i.test(raw)) {
    try {
      return new URL(raw).pathname.toLowerCase().endsWith('.md');
    } catch {
      return false;
    }
  }
  const [withoutHash] = raw.split('#');
  const [withoutQuery] = withoutHash.split('?');
  return withoutQuery.toLowerCase().endsWith('.md');
}

function toCourseParam(value: string): string {
  const raw = value.trim();
  if (/^https?:\/\//i.test(raw)) return raw;
  if (raw.startsWith('/api/files/download')) {
    try {
      const path = new URL(raw, window.location.origin).searchParams.get('path') || '';
      return path.replace(/^\/+/, '').replace(/^workspace\/learning\//, '');
    } catch {
      return raw;
    }
  }
  return raw.replace(/^\/+/, '').replace(/^workspace\/learning\//, '').replace(/^learning\//, '');
}

function coursePopupUrl(value: string): string {
  return `/courses?course=${encodeURIComponent(toCourseParam(value))}&popup=1`;
}

function FloatingPopup({
  title,
  onClose,
  children,
  initialWidth = 880,
  initialHeight = 560,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  initialWidth?: number;
  initialHeight?: number;
}) {
  const popupRef = useRef<HTMLDivElement | null>(null);
  const dragRef = useRef<{ startX: number; startY: number; left: number; top: number } | null>(null);
  const resizeRef = useRef<{ startX: number; startY: number; width: number; height: number } | null>(null);
  const [position, setPosition] = useState({ left: 80, top: 80 });
  const [size, setSize] = useState({ width: initialWidth, height: initialHeight });
  const [isDraggingPopup, setIsDraggingPopup] = useState(false);
  const [isResizingPopup, setIsResizingPopup] = useState(false);

  const stopPointerAction = (event?: React.PointerEvent<HTMLElement>) => {
    if (event?.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    dragRef.current = null;
    resizeRef.current = null;
    setIsDraggingPopup(false);
    setIsResizingPopup(false);
  };

  const startDrag = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!popupRef.current) return;
    if (event.button !== 0) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    const bounds = popupRef.current.getBoundingClientRect();
    dragRef.current = {
      startX: event.clientX,
      startY: event.clientY,
      left: bounds.left,
      top: bounds.top,
    };
    setIsDraggingPopup(true);
    event.preventDefault();
  };

  const dragPopup = (event: React.PointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    if (!drag) return;
    const width = popupRef.current?.offsetWidth || initialWidth;
    const height = popupRef.current?.offsetHeight || initialHeight;
    setPosition({
      left: Math.max(8, Math.min(window.innerWidth - Math.min(120, width), drag.left + event.clientX - drag.startX)),
      top: Math.max(8, Math.min(window.innerHeight - Math.min(80, height), drag.top + event.clientY - drag.startY)),
    });
  };

  const startResize = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!popupRef.current) return;
    if (event.button !== 0) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    resizeRef.current = {
      startX: event.clientX,
      startY: event.clientY,
      width: popupRef.current.offsetWidth,
      height: popupRef.current.offsetHeight,
    };
    setIsResizingPopup(true);
    event.preventDefault();
    event.stopPropagation();
  };

  const resizePopup = (event: React.PointerEvent<HTMLDivElement>) => {
    const resizing = resizeRef.current;
    if (!resizing) return;
    setSize({
      width: Math.max(360, Math.min(window.innerWidth - position.left - 8, resizing.width + event.clientX - resizing.startX)),
      height: Math.max(260, Math.min(window.innerHeight - position.top - 8, resizing.height + event.clientY - resizing.startY)),
    });
  };

  return (
    <div
      ref={popupRef}
      style={{
        position: 'fixed',
        left: position.left,
        top: position.top,
        width: `min(${size.width}px, calc(100vw - 24px))`,
        height: `min(${size.height}px, calc(100vh - 24px))`,
        minWidth: 360,
        minHeight: 260,
        maxWidth: 'calc(100vw - 16px)',
        maxHeight: 'calc(100vh - 16px)',
        overflow: 'hidden',
        zIndex: 1000,
        background: '#ffffff',
        border: '1px solid #cbd5e1',
        borderRadius: 12,
        boxShadow: '0 24px 70px rgba(15, 23, 42, 0.28)',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div
        style={{
          height: 42,
          padding: '0 10px 0 12px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 10,
          borderBottom: '1px solid #e2e8f0',
          background: '#ffffff',
          userSelect: 'none',
          flexShrink: 0,
        }}
      >
        <Group
          spacing={8}
          noWrap
          onPointerDown={startDrag}
          onPointerMove={dragPopup}
          onPointerUp={stopPointerAction}
          onPointerCancel={stopPointerAction}
          style={{ minWidth: 0, flex: 1, alignSelf: 'stretch', cursor: isDraggingPopup ? 'grabbing' : 'grab' }}
        >
          <IconGripHorizontal size="1rem" color={isDraggingPopup ? '#2563eb' : '#64748b'} />
          <Text size="sm" weight={700} lineClamp={1}>{title}</Text>
        </Group>
        <Button size="xs" variant="subtle" compact onClick={onClose} leftIcon={<IconX size="0.9rem" />}>
          Close
        </Button>
      </div>
      <div style={{ flex: 1, minHeight: 0, overflow: 'auto', background: '#ffffff' }}>
        {children}
      </div>
      <div
        onPointerDown={startResize}
        onPointerMove={resizePopup}
        onPointerUp={stopPointerAction}
        onPointerCancel={stopPointerAction}
        title="Resize"
        style={{
          position: 'absolute',
          right: 0,
          bottom: 0,
          width: 28,
          height: 28,
          cursor: 'nwse-resize',
          background: 'transparent',
          display: 'flex',
          alignItems: 'flex-end',
          justifyContent: 'flex-end',
          padding: 5,
          zIndex: 2,
        }}
      >
        <div
          aria-hidden="true"
          style={{
            width: 13,
            height: 13,
            background:
              `repeating-linear-gradient(135deg, transparent 0 4px, ${isResizingPopup ? '#2563eb' : '#64748b'} 4px 6px, transparent 6px 8px)`,
            opacity: 0.85,
          }}
        />
      </div>
    </div>
  );
}

function PopupVideoPlayer({ src, title }: { src: string; title: string }) {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
  }, [src]);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', minHeight: 220, background: '#000' }}>
      <video
        src={src}
        controls
        autoPlay
        aria-label={title}
        onLoadStart={() => setLoading(true)}
        onWaiting={() => setLoading(true)}
        onCanPlay={() => setLoading(false)}
        onPlaying={() => setLoading(false)}
        onError={() => setLoading(false)}
        style={{ width: '100%', height: '100%', display: 'block', background: '#000' }}
      />
      {loading && (
        <div
          aria-label="Loading video"
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            pointerEvents: 'none',
            background: 'rgba(0, 0, 0, 0.18)',
          }}
        >
          <Loader size="lg" color="blue" />
        </div>
      )}
    </div>
  );
}

function toKebabCase(term: string): string {
  return term
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-');
}

function isVideoLike(value: string | null | undefined): boolean {
  const lower = String(value || '').toLowerCase();
  return ['.mp4', '.mov', '.webm', '.m4v', '.avi', '.mkv'].some((suffix) => lower.includes(suffix));
}

function isAudioLike(value: string | null | undefined): boolean {
  const lower = String(value || '').toLowerCase();
  return ['.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac'].some((suffix) => lower.includes(suffix));
}

function LoadingThumbnailImage({
  src,
  alt,
  isDark,
  style,
}: {
  src: string;
  alt: string;
  isDark?: boolean;
  style?: React.CSSProperties;
}) {
  const [status, setStatus] = useState<'loading' | 'loaded' | 'error'>('loading');

  useEffect(() => {
    setStatus('loading');
  }, [src]);

  return (
    <>
      <img
        src={src}
        alt={alt}
        onLoad={() => setStatus('loaded')}
        onError={() => setStatus('error')}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          display: 'block',
          opacity: status === 'loaded' ? 1 : 0,
          transition: 'opacity 0.18s ease',
          ...style,
        }}
      />
      {status === 'loading' && (
        <div
          aria-label={`Loading ${alt} thumbnail`}
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: isDark ? 'rgba(15, 23, 42, 0.72)' : 'rgba(248, 250, 252, 0.72)',
            color: isDark ? '#cbd5e1' : '#475569',
            pointerEvents: 'none',
          }}
        >
          <Loader size="sm" />
        </div>
      )}
      {status === 'error' && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 10,
            background: isDark ? '#111827' : '#f1f5f9',
            color: isDark ? '#cbd5e1' : '#64748b',
            fontSize: 12,
            fontWeight: 700,
            textAlign: 'center',
          }}
        >
          Thumbnail unavailable
        </div>
      )}
    </>
  );
}

function TileThumb({ label, src, seed, isDark, size = 64 }: { label: string; src?: string | null; seed: string; isDark?: boolean; size?: number }) {
  const [bg, fg] = pickColor(seed);
  const radius = Math.round(size * 0.22);
  if (src) {
    return (
      <div style={{ position: 'relative', width: size, height: size, borderRadius: radius, overflow: 'hidden', background: isDark ? '#374151' : '#e5e7eb', flexShrink: 0 }}>
        <LoadingThumbnailImage src={src} alt={label} isDark={isDark} />
      </div>
    );
  }
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: radius,
        background: `linear-gradient(135deg, ${bg}, ${isDark ? bg : fg})`,
        color: '#fff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: Math.round(size * 0.34),
        fontWeight: 800,
        letterSpacing: 1,
        flexShrink: 0,
      }}
    >
      {initialsFromText(label)}
    </div>
  );
}

export default function ExploreView() {
  const router = useRouter();
  const theme = useMantineTheme();
  const isDark = theme.colorScheme === 'dark';
  const [categories, setCategories] = useState<ShowcaseCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [runtimeMode, setRuntimeMode] = useState('production');
  const [canUseTemplate, setCanUseTemplate] = useState(true);
  const [copiedPromptId, setCopiedPromptId] = useState('');
  const [mediaModal, setMediaModal] = useState<{ url: string; title: string; type: 'image' | 'video' | 'audio' } | null>(null);
  const [coursePopup, setCoursePopup] = useState<{ url: string; title: string } | null>(null);
  const [templateSample, setTemplateSample] = useState<ShowcaseSample | null>(null);
  const [templateOpened, setTemplateOpened] = useState(false);
  const [templateUseWorktree, setTemplateUseWorktree] = useState(false);
  const [templateCheckoutTag, setTemplateCheckoutTag] = useState(true);
  const [templateBusy, setTemplateBusy] = useState(false);
  const [templateError, setTemplateError] = useState('');
  const [launchState, setLaunchState] = useState('');
  const [existingAction, setExistingAction] = useState<'continue' | 'remove' | null>(null);
  const [templateMonitorUrl, setTemplateMonitorUrl] = useState('');
  const [templateContinueUrl, setTemplateContinueUrl] = useState('');
  const [templateMonitorLaunchId, setTemplateMonitorLaunchId] = useState('');
  const [templateMonitorReady, setTemplateMonitorReady] = useState(false);
  const [templateMonitorStatus, setTemplateMonitorStatus] = useState('');

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      setLoading(true);
      try {
        const res = await axios.get(`${API_BASE_URL}/explore/showcases`);
        if (cancelled) return;
        setCategories(res.data.categories || []);
        setRuntimeMode(String(res.data.runtime_mode || 'production'));
        setCanUseTemplate(Boolean(res.data.can_use_template));
        setError('');
      } catch (err: any) {
        if (cancelled) return;
        setError(err?.response?.data?.error || 'Failed to load showcase data.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void run();
    return () => { cancelled = true; };
  }, []);

  const mode: ExploreMode = useMemo(() => {
    const queryMode = typeof router.query.explore_mode === 'string' ? router.query.explore_mode : '';
    return queryMode === 'popularity' || queryMode === 'level' ? queryMode : 'category';
  }, [router.query.explore_mode]);

  const selectedCategoryName = typeof router.query.category === 'string' ? router.query.category : '';
  const selectedSampleId = typeof router.query.sample === 'string' ? router.query.sample : '';

  const categoryByName = useMemo(() => {
    const map = new Map<string, ShowcaseCategory>();
    const enqueue = (catList: ShowcaseCategory[]) => {
      catList.forEach((c) => {
        map.set(c.category, c);
        if (c.subcategories) {
          enqueue(c.subcategories);
        }
      });
    };
    enqueue(categories);
    return map;
  }, [categories]);

  const selectedCategory = categoryByName.get(selectedCategoryName) || null;

  const allSamples = useMemo(() => {
    const samples: Array<ShowcaseSample & { __category: string }> = [];
    const enqueue = (catList: ShowcaseCategory[]) => {
      catList.forEach((c) => {
        c.samples.forEach((s) => samples.push({ ...s, __category: c.category }));
        if (c.subcategories) {
          enqueue(c.subcategories);
        }
      });
    };
    enqueue(categories);
    return samples;
  }, [categories]);

  const selectedSample = useMemo(
    () => allSamples.find((sample) => sample.id === selectedSampleId) || null,
    [allSamples, selectedSampleId],
  );

  const sortedSamples = useMemo(() => {
    const base = [...allSamples];
    if (mode === 'popularity') {
      return base.sort((a, b) => b.popularity - a.popularity || a.title.localeCompare(b.title));
    }
    if (mode === 'level') {
      return base.sort((a, b) => a.level - b.level || b.popularity - a.popularity);
    }
    return base;
  }, [allSamples, mode]);

  const updateQuery = (patch: Record<string, string | undefined>, options?: { history?: 'replace' | 'push' }) => {
    const nextQuery: Record<string, string> = {};
    const current = router.query;
    Object.entries(current).forEach(([key, value]) => {
      if (typeof value === 'string') nextQuery[key] = value;
    });
    nextQuery.view = 'explore';
    Object.entries(patch).forEach(([key, value]) => {
      if (value === undefined || value === '') {
        delete nextQuery[key];
      } else {
        nextQuery[key] = value;
      }
    });
    const nextRoute = { pathname: '/', query: nextQuery };
    if (options?.history === 'push') {
      void router.push(nextRoute, undefined, { shallow: true });
      return;
    }
    void router.replace(nextRoute, undefined, { shallow: true });
  };

  const openMode = (nextMode: ExploreMode) => {
    if (nextMode === 'category') {
      updateQuery({ explore_mode: undefined, category: undefined, sample: undefined });
      return;
    }
    updateQuery({ explore_mode: nextMode, category: undefined, sample: undefined });
  };

  const openCategory = (category: ShowcaseCategory) => {
    updateQuery({ explore_mode: 'category', category: category.category, sample: undefined });
  };

  const openSample = (sample: ShowcaseSample, categoryName?: string) => {
    updateQuery({
      explore_mode: mode === 'category' ? 'category' : mode,
      category: categoryName || selectedCategoryName || undefined,
      sample: sample.id,
    });
  };

  const openSampleBySlug = (slug: string) => {
    const target = allSamples.find((sample) => sample.id === slug);
    if (target) {
      updateQuery({
        explore_mode: mode === 'category' ? 'category' : mode,
        category: target.__category || selectedCategoryName || undefined,
        sample: target.id,
      }, { history: 'push' });
      return;
    }
    updateQuery({ sample: slug }, { history: 'push' });
  };

  const goBackFromSample = () => {
    updateQuery({ sample: undefined });
  };

  const goBackFromCategory = () => {
    updateQuery({ category: undefined, sample: undefined });
  };

  const copyPrompt = async (sample: ShowcaseSample) => {
    await navigator.clipboard.writeText(sample.prompt);
    setCopiedPromptId(sample.id);
    window.setTimeout(() => setCopiedPromptId((current) => (current === sample.id ? '' : current)), 1500);
  };

  const openMedia = (url: string, title: string, type: 'image' | 'video' | 'audio') => {
    setMediaModal({ url, title, type });
  };

  const openCoursePopup = (url: string, title: string) => {
    setCoursePopup({ url: coursePopupUrl(url), title });
  };

  const openShowcaseResource = (url: string, title: string) => {
    if (isMarkdownUrl(url)) {
      openCoursePopup(url, title);
      return;
    }
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const openTermVideo = (term: string, url: string) => {
    openMedia(url, term, 'video');
  };

  const maybeOpenTutorial = (sample: ShowcaseSample) => {
    if (!sample.tutorial_url) return;
    if (sample.tutorial_is_media) {
      openMedia(sample.tutorial_url, `${sample.title} tutorial`, isAudioLike(sample.tutorial) ? 'audio' : 'video');
      return;
    }
    openShowcaseResource(sample.tutorial_url, `${sample.title} tutorial`);
  };

  const linkKind = (url: string): 'video' | 'course' | 'external' => {
    if (isVideoLike(url)) return 'video';
    if (isMarkdownUrl(url)) return 'course';
    return 'external';
  };

  const openLinkResource = (link: ShowcaseLink) => {
    const kind = linkKind(link.url);
    if (kind === 'video') {
      openMedia(link.url, link.name, 'video');
      return;
    }
    if (kind === 'course') {
      openCoursePopup(link.url, link.name);
      return;
    }
    window.open(link.url, '_blank', 'noopener,noreferrer');
  };

  const openTemplateSettings = (sample: ShowcaseSample, forceWorktree = false) => {
    setTemplateSample(sample);
    setTemplateUseWorktree(runtimeMode === 'development' ? false : (forceWorktree || sample.use_worktree));
    setTemplateCheckoutTag(runtimeMode === 'development' ? false : Boolean(sample.git_tag));
    setTemplateError('');
    setLaunchState('');
    setExistingAction(null);
    setTemplateMonitorUrl('');
    setTemplateContinueUrl('');
    setTemplateMonitorLaunchId('');
    setTemplateMonitorReady(false);
    setTemplateMonitorStatus('');
    setTemplateOpened(true);
  };

  useEffect(() => {
    if (!templateOpened || !templateMonitorLaunchId || templateMonitorReady) return undefined;
    let cancelled = false;
    const deadline = Date.now() + 120000;
    const poll = async () => {
      while (!cancelled && Date.now() < deadline) {
        await new Promise((resolve) => window.setTimeout(resolve, 1500));
        try {
          const statusRes = await axios.get(`${API_BASE_URL}/explore/template/status`, { params: { launch_id: templateMonitorLaunchId } });
          const statusPayload = statusRes.data as LaunchResponse;
          if (cancelled) return;
          if (statusPayload.status === 'launched') {
            setTemplateMonitorReady(true);
            setTemplateMonitorStatus('Dev instance is ready for live monitoring.');
            if (statusPayload.monitor_url) {
              setTemplateMonitorUrl(statusPayload.monitor_url);
            }
            return;
          }
          if (statusPayload.status === 'error') {
            setTemplateMonitorStatus('');
            setTemplateError(statusPayload.error || 'Failed to start the dev instance for monitoring.');
            return;
          }
        } catch (err: any) {
          if (cancelled) return;
          setTemplateMonitorStatus('');
          setTemplateError(err?.response?.data?.error || 'Failed to check dev instance status.');
          return;
        }
      }
      if (!cancelled) {
        setTemplateMonitorStatus('');
        setTemplateError('Timed out waiting for the dev instance to become ready for monitoring.');
      }
    };
    void poll();
    return () => {
      cancelled = true;
    };
  }, [templateMonitorLaunchId, templateMonitorReady, templateOpened]);

  const handleTemplateResponse = async (sample: ShowcaseSample, response: LaunchResponse) => {
    if (response.status === 'launched' && response.target_url) {
      window.location.assign(response.target_url);
      return;
    }
    if (response.status === 'relaunching_current_dev' && response.target_url) {
      setLaunchState('Restarting the current dev instance from the new project directory...');
      const deadline = Date.now() + 180000;
      while (Date.now() < deadline) {
        await new Promise((resolve) => window.setTimeout(resolve, 1500));
        try {
          const healthRes = await axios.get(`${window.location.origin}/api/health`, { timeout: 1500, withCredentials: true });
          if (healthRes.data?.status === 'ok') {
            window.location.assign(response.target_url);
            return;
          }
        } catch {
          // Dev engine is expected to be temporarily unavailable while tmux restarts it.
        }
      }
      setLaunchState('');
      setTemplateError('Timed out waiting for the current dev instance to restart.');
      return;
    }
    if (response.status === 'monitor_dev_and_continue' && response.target_url) {
      setLaunchState('');
      setTemplateError('');
      setTemplateMonitorUrl(response.monitor_url || '');
      setTemplateContinueUrl(response.target_url);
      setTemplateMonitorLaunchId(response.launch_id || '');
      const ready = !response.launch_id || Boolean(response.reused_running_dev);
      setTemplateMonitorReady(ready);
      setTemplateMonitorStatus(
        ready
          ? 'Dev instance is ready for live monitoring.'
          : 'Dev instance is starting or relaunching. Continue in the current instance, then launch the dev instance for monitoring when it is ready.',
      );
      return;
    }
    if (response.status === 'needs_existing_worktree_action') {
      setTemplateError(`Worktree already exists at ${response.worktree_path}. Choose whether to continue or remove it.`);
      return;
    }
    if (response.status === 'pending' && response.launch_id) {
      setLaunchState('Starting worktree dev mode...');
      const deadline = Date.now() + 120000;
      while (Date.now() < deadline) {
        await new Promise((resolve) => window.setTimeout(resolve, 1500));
        try {
          const statusRes = await axios.get(`${API_BASE_URL}/explore/template/status`, { params: { launch_id: response.launch_id } });
          const statusPayload = statusRes.data as LaunchResponse;
          if (statusPayload.status === 'launched' && statusPayload.target_url) {
            window.location.assign(statusPayload.target_url);
            return;
          }
          if (statusPayload.status === 'error') {
            setLaunchState('');
            setTemplateError(statusPayload.error || 'Failed to start the template.');
            return;
          }
        } catch (err: any) {
          setLaunchState('');
          setTemplateError(err?.response?.data?.error || 'Failed to check template status.');
          return;
        }
      }
      setLaunchState('');
      setTemplateError('Timed out waiting for the worktree WebUI to become ready.');
      return;
    }
    setTemplateError(response.error || 'Unexpected template launch response.');
  };

  const startTemplate = async () => {
    if (!templateSample) return;
    const effectiveUseWorktree = runtimeMode === 'development' ? false : templateUseWorktree;
    const effectiveCheckoutTag = runtimeMode === 'development' ? false : (templateSample.git_tag ? templateCheckoutTag : false);
    const startInDevMode = effectiveUseWorktree || templateSample.in_mode === 'dev';
    setTemplateBusy(true);
    setTemplateError('');
    setLaunchState('');
    setTemplateMonitorLaunchId('');
    setTemplateMonitorReady(false);
    setTemplateMonitorStatus('');
    setTemplateMonitorUrl('');
    setTemplateContinueUrl('');
    try {
      const res = await axios.post(`${API_BASE_URL}/explore/template/start`, {
        sample_id: templateSample.id,
        use_worktree: effectiveUseWorktree,
        checkout_tag: effectiveCheckoutTag,
        start_in_dev_mode: startInDevMode,
        existing_worktree_action: existingAction || undefined,
      });
      await handleTemplateResponse(templateSample, res.data as LaunchResponse);
    } catch (err: any) {
      const responseData = err?.response?.data as LaunchResponse | undefined;
      if (responseData) {
        await handleTemplateResponse(templateSample, responseData);
      } else {
        setTemplateError(err?.response?.data?.error || 'Failed to start template.');
      }
    } finally {
      setTemplateBusy(false);
    }
  };

  const cardBg = isDark ? theme.colors.dark[6] : '#ffffff';
  const cardBorder = isDark ? `1px solid ${theme.colors.dark[4]}` : '1px solid #dbe3f0';
  const cardShadow = isDark ? '0 4px 12px rgba(0, 0, 0, 0.3)' : '0 2px 8px rgba(15, 23, 42, 0.06)';
  const promptBg = isDark ? theme.colors.dark[7] : '#f8fafc';
  const promptBorder = isDark ? `1px solid ${theme.colors.dark[4]}` : '1px solid #e2e8f0';
  const promptText = isDark ? theme.colors.dark[0] : '#1e293b';
  const linkColor = isDark ? theme.colors.blue[4] : '#2563eb';
  const promptResolvedPaths = useMemo(() => {
    const paths = new Map<string, string>();
    (selectedSample?.prompt_items || []).forEach((item) => {
      if (item.path) paths.set(item.label.replace(/^\/+/, ''), item.path.replace(/^\/+/, ''));
    });
    return paths;
  }, [selectedSample?.prompt_items]);

  const markdownLinkComponents = {
    a: ({ href, children }: { href?: string; children?: React.ReactNode }) => {
      const target = String(href || '');
      if (target.startsWith('/file-manager?path=')) {
        return (
          <a
            href={target}
            onClick={(event) => {
              event.preventDefault();
              const params = new URL(target, window.location.origin).searchParams;
              const path = params.get('path') || '';
              openFileManager(path);
            }}
            style={{ color: linkColor, fontWeight: 600 }}
          >
            {children}
          </a>
        );
      }
      return (
        <a href={target} target="_blank" rel="noreferrer" style={{ color: linkColor, fontWeight: 600 }}>
          {children}
        </a>
      );
    },
  };

  const renderMarkdown = (text: string) => (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownLinkComponents}>
      {promptToMarkdown(text || '')}
    </ReactMarkdown>
  );

  const renderResolvedItem = (item: ShowcaseResolvedItem, icon: React.ReactNode, displayLabel?: string) => {
    const label = displayLabel || item.label;
    if (item.path) {
      return (
        <Button
          key={`${item.label}-${item.path}`}
          variant="subtle"
          compact
          styles={{ inner: { justifyContent: 'flex-start' }, label: { textAlign: 'left' } }}
          leftIcon={icon}
          onClick={() => openFileManager(item.path as string)}
        >
          {label}
        </Button>
      );
    }
    return (
      <Group
        key={item.label}
        spacing={8}
        noWrap
        style={{
          minHeight: 30,
          padding: '4px 10px',
          color: isDark ? theme.colors.dark[2] : '#64748b',
        }}
      >
        {icon}
        <Text size="sm" style={{ flex: 1, minWidth: 0, lineHeight: 1.35, wordBreak: 'break-word' }}>{label}</Text>
      </Group>
    );
  };

  const renderSequenceLink = (label: string, link: ShowcaseSequenceLink, direction: 'previous' | 'next') => (
    <button
      type="button"
      onClick={() => openSampleBySlug(link.slug_id)}
      style={{
        flex: 1,
        minWidth: 220,
        border: isDark ? `1px solid ${theme.colors.dark[4]}` : '1px solid #bfdbfe',
        borderRadius: 10,
        background: isDark ? theme.colors.dark[6] : '#eff6ff',
        color: isDark ? theme.colors.blue[2] : '#1d4ed8',
        cursor: 'pointer',
        padding: '10px 12px',
        textAlign: 'left',
        fontSize: 13,
        fontWeight: 600,
        lineHeight: 1.45,
        whiteSpace: 'normal',
        overflowWrap: 'anywhere',
      }}
    >
      <Group spacing={8} noWrap>
        {direction === 'previous' && <IconArrowLeft size="0.9rem" />}
        <div style={{ minWidth: 0, flex: 1 }}>
          <Text size="xs" weight={700} color={isDark ? 'blue.2' : 'blue.7'}>{label}</Text>
          <Text size="sm" weight={700} style={{ lineHeight: 1.35 }}>{link.title}</Text>
        </div>
        {direction === 'next' && <IconArrowRight size="0.9rem" />}
      </Group>
    </button>
  );

  const renderSampleActions = (sample: ShowcaseSample) => {
    const subagents = sample.subagents || [];
    const pathGroups: Array<{ title: string; items: ShowcaseResolvedItem[]; icon: React.ReactNode }> = [
      ...(sample.workflow ? [{
        title: 'Workflow',
        items: [{ label: sample.workflow, path: null }],
        icon: <IconFile size="0.9rem" />,
      }] : []),
      ...(sample.directory ? [{
        title: 'Directory',
        items: [{ label: sample.directory, path: null }],
        icon: <IconFolderOpen size="0.9rem" />,
      }] : []),
      ...(sample.skills.length > 0 ? [{
        title: 'Skills',
        items: sample.skill_items || sample.skills.map((skill) => ({ label: skill, path: null })),
        icon: <IconFolderOpen size="0.9rem" />,
      }] : []),
      ...(subagents.length > 0 ? [{
        title: 'Subagents',
        items: sample.subagent_items || subagents.map((subagent) => ({ label: subagent, path: null })),
        icon: <IconRobot size="0.9rem" />,
      }] : []),
      ...(sample.tools.length > 0 ? [{
        title: 'Tools',
        items: sample.tool_items || sample.tools.map((tool) => ({ label: tool, path: null })),
        icon: <IconFile size="0.9rem" />,
      }] : []),
    ];

    return (
      <Stack spacing="md">
        <div style={{ padding: 18, borderRadius: 18, border: cardBorder, background: cardBg }}>
          <Text size="sm" weight={700} mb={10}>Template</Text>
          <Stack spacing="xs">
            <Tooltip label="Use this sample as a template">
              <div>
                <Button
                  fullWidth
                  leftIcon={<IconSparkles size="1rem" />}
                  onClick={() => openTemplateSettings(sample)}
                  disabled={!canUseTemplate}
                >
                  Use Template
                </Button>
              </div>
            </Tooltip>
            {sample.use_worktree && (
              <Tooltip label="Open this sample in a worktree">
                <div>
                  <Button
                    fullWidth
                    variant="light"
                    leftIcon={<IconFolderOpen size="1rem" />}
                    onClick={() => openTemplateSettings(sample, true)}
                    disabled={!canUseTemplate}
                  >
                    Open in Worktree
                  </Button>
                </div>
              </Tooltip>
            )}
            <Text size="xs" color="dimmed">Runtime: {runtimeMode}</Text>
            <Text size="xs" color="dimmed">Use in mode: {sample.in_mode}</Text>
            <Text size="xs" color="dimmed">Git tag: {sample.git_tag || 'Current branch'}</Text>
            <Text size="xs" color="dimmed">Use worktree: {sample.use_worktree ? 'Yes' : 'No'}</Text>
          </Stack>
        </div>

        {pathGroups.map((group) => (
          <div key={group.title} style={{ padding: 18, borderRadius: 18, border: cardBorder, background: cardBg }}>
            <Text size="sm" weight={700} mb={10}>{group.title}</Text>
            <Stack spacing={6}>
              {group.items.map((item) => renderResolvedItem(item, group.icon))}
            </Stack>
          </div>
        ))}

        {sample.files.length > 0 && (
          <div style={{ padding: 18, borderRadius: 18, border: cardBorder, background: cardBg }}>
            <Text size="sm" weight={700} mb={10}>Files</Text>
            <Stack spacing={6}>
              {(sample.file_items || sample.files.map((filePath) => ({ label: filePath, path: null }))).map((item) => {
                const fileName = item.label.split('/').pop() || item.label;
                return renderResolvedItem(item, <IconFile size="0.9rem" />, fileName);
              })}
            </Stack>
          </div>
        )}

        {sample.extensions.length > 0 && (
          <div style={{ padding: 18, borderRadius: 18, border: cardBorder, background: cardBg }}>
            <Text size="sm" weight={700} mb={10}>Extensions</Text>
            <Stack spacing={6}>
              {sample.extensions.map((ext) => {
                const extName = ext.replace(/^extensions\//, '');
                return (
                  <Group
                    key={ext}
                    spacing={8}
                    noWrap
                    style={{
                      minHeight: 30,
                      padding: '4px 10px',
                      color: isDark ? theme.colors.dark[2] : '#64748b',
                    }}
                  >
                    <IconFolderOpen size="0.9rem" />
                    <Text size="sm" style={{ flex: 1, minWidth: 0, lineHeight: 1.35, wordBreak: 'break-word' }}>{extName}</Text>
                  </Group>
                );
              })}
            </Stack>
          </div>
        )}

        {sample.links.length > 0 && (
          <div style={{ padding: 18, borderRadius: 18, border: cardBorder, background: cardBg }}>
            <Text size="sm" weight={700} mb={10}>Links</Text>
            <Stack spacing={8}>
              {sample.links.map((link) => {
                const kind = linkKind(link.url);
                return (
                  <Button
                    key={link.url}
                    variant="subtle"
                    compact
                    leftIcon={
                      kind === 'video'
                        ? <IconVideo size="0.9rem" />
                        : kind === 'course'
                          ? <IconSchool size="0.9rem" />
                          : <IconExternalLink size="0.9rem" />
                    }
                    styles={{ inner: { justifyContent: 'flex-start' } }}
                    onClick={() => openLinkResource(link)}
                  >
                    {link.name}
                  </Button>
                );
              })}
            </Stack>
          </div>
        )}
      </Stack>
    );
  };

  const renderSampleDetail = () => {
    if (!selectedSample) return null;
    const sample = selectedSample;
    const linkedPrompt = promptToMarkdown(sample.prompt, promptResolvedPaths);

    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 2fr) minmax(280px, 360px)', gap: 20, padding: 20 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <Group spacing="xs">
            <Button variant="subtle" leftIcon={<IconArrowLeft size="1rem" />} onClick={goBackFromSample}>
              Back
            </Button>
            <Badge variant="light">{sample.__category}</Badge>
            <Badge color="orange" variant="light">Level {sample.level}</Badge>
            <Badge color="yellow" variant="light">Rate {sample.rate.toFixed(1)}</Badge>
            <Badge color="grape" variant="light">Popularity {sample.popularity}</Badge>
          </Group>

          <div style={{ borderRadius: 22, border: cardBorder, background: cardBg, boxShadow: cardShadow, overflow: 'hidden' }}>
            {sample.thumbnail_url && (
              <button
                type="button"
                onClick={() => {
                  if (sample.video_url) {
                    openMedia(sample.video_url as string, sample.title, isAudioLike(sample.video) ? 'audio' : 'video');
                  } else {
                    openMedia(sample.thumbnail_url as string, sample.title, 'image');
                  }
                }}
                style={{
                  position: 'relative',
                  width: '100%',
                  aspectRatio: '16 / 9',
                  background: isDark ? '#0f172a' : '#e5e7eb',
                  padding: 0,
                  border: 'none',
                  cursor: sample.video_url ? 'pointer' : 'zoom-in',
                  display: 'block',
                  overflow: 'hidden',
                }}
              >
                <LoadingThumbnailImage src={sample.thumbnail_url} alt={sample.title} isDark={isDark} />
                <div
                  style={{
                    position: 'absolute',
                    inset: 0,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    pointerEvents: 'none',
                    zIndex: 1,
                  }}
                >
                  <div
                    style={{
                      width: 96,
                      height: 96,
                      borderRadius: '50%',
                      background: 'rgba(0, 0, 0, 0.45)',
                      backdropFilter: 'blur(2px)',
                      border: '2px solid rgba(255, 255, 255, 0.85)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      boxShadow: '0 6px 20px rgba(0, 0, 0, 0.35)',
                    }}
                  >
                    <IconPlayerPlay size={44} color="#fff" fill="#fff" style={{ marginLeft: 6 }} />
                  </div>
                </div>
              </button>
            )}
            <div style={{ padding: 24 }}>
            <div style={{ display: 'flex', gap: 18, alignItems: 'flex-start', marginBottom: 18 }}>
              {!sample.thumbnail_url && (
                <TileThumb label={sample.title} src={sample.thumbnail_url} seed={sample.id} isDark={isDark} />
              )}
              <div style={{ flex: 1 }}>
                <Text size={28} weight={800} style={{ lineHeight: 1.15 }}>{sample.title}</Text>
                <Box
                  mt={8}
                  sx={{
                    fontSize: 14,
                    color: isDark ? theme.colors.dark[1] : '#475569',
                    lineHeight: 1.55,
                    '& p': { margin: '0 0 8px' },
                    '& p:last-child': { marginBottom: 0 },
                    '& ul, & ol': { paddingLeft: 20, margin: '4px 0 8px' },
                    '& code': {
                      background: isDark ? theme.colors.dark[5] : '#eef2f7',
                      padding: '1px 5px',
                      borderRadius: 4,
                      fontSize: '0.9em',
                    },
                    '& pre': {
                      background: isDark ? theme.colors.dark[7] : '#f1f5f9',
                      padding: 10,
                      borderRadius: 8,
                      overflowX: 'auto',
                    },
                    '& blockquote': {
                      borderLeft: `3px solid ${isDark ? theme.colors.dark[4] : '#cbd5e1'}`,
                      margin: '6px 0',
                      padding: '2px 10px',
                      color: isDark ? theme.colors.dark[2] : '#64748b',
                    },
                  }}
                >
                  {renderMarkdown(sample.description)}
                </Box>
                <Group spacing="xs" mt={14}>
                  {sample.video_url && (
                    <Button
                      size="xs"
                      leftIcon={<IconPlayerPlay size="0.9rem" />}
                      onClick={() => openMedia(sample.video_url as string, sample.title, isAudioLike(sample.video) ? 'audio' : 'video')}
                    >
                      Video
                    </Button>
                  )}
                  {sample.tutorial_url && (
                    <Button
                      size="xs"
                      variant="light"
                      leftIcon={<IconExternalLink size="0.9rem" />}
                      onClick={() => maybeOpenTutorial(sample)}
                    >
                      Tutorial
                    </Button>
                  )}
                </Group>
              </div>
            </div>

            {sample.request_url && (
              <Group spacing="xs" mt={14}>
                <Button
                  size="xs"
                  variant="light"
                  leftIcon={sample.request_is_media ? <IconPlayerPlay size="0.9rem" /> : <IconExternalLink size="0.9rem" />}
                  onClick={() => {
                    if (sample.request_is_media) {
                      openMedia(sample.request_url as string, `${sample.title} request`, isAudioLike(sample.request) ? 'audio' : 'video');
                    } else {
                      openShowcaseResource(sample.request_url as string, `${sample.title} requirement`);
                    }
                  }}
                >
                  {sample.request_is_media ? 'Click to view the request video' : 'Click to view the requirement'}
                </Button>
              </Group>
            )}

            <Divider my="md" />

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <Text size="sm" weight={700}>Prompt</Text>
              <Button size="xs" variant="subtle" leftIcon={<IconCopy size="0.9rem" />} onClick={() => void copyPrompt(sample)}>
                {copiedPromptId === sample.id ? 'Copied' : 'Copy'}
              </Button>
            </div>

            <Box
              sx={{
                borderRadius: 16,
                border: promptBorder,
                background: promptBg,
                padding: 18,
                color: promptText,
                overflowX: 'auto',
                fontSize: 14,
                lineHeight: 1.6,
                '& p': { margin: '0 0 10px' },
                '& p:last-child': { marginBottom: 0 },
                '& h1, & h2, & h3, & h4': { margin: '14px 0 8px', lineHeight: 1.25 },
                '& h1': { fontSize: 22 },
                '& h2': { fontSize: 19 },
                '& h3': { fontSize: 16 },
                '& ul, & ol': { paddingLeft: 22, margin: '6px 0 10px' },
                '& li': { margin: '2px 0' },
                '& code': {
                  background: isDark ? theme.colors.dark[5] : '#eef2f7',
                  padding: '1px 6px',
                  borderRadius: 4,
                  fontSize: '0.9em',
                  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
                },
                '& pre': {
                  background: isDark ? theme.colors.dark[8] : '#0f172a',
                  color: isDark ? theme.colors.dark[0] : '#e2e8f0',
                  padding: 12,
                  borderRadius: 10,
                  overflowX: 'auto',
                  margin: '8px 0',
                },
                '& pre code': {
                  background: 'transparent',
                  color: 'inherit',
                  padding: 0,
                },
                '& blockquote': {
                  borderLeft: `3px solid ${isDark ? theme.colors.dark[4] : '#cbd5e1'}`,
                  margin: '8px 0',
                  padding: '4px 12px',
                  color: isDark ? theme.colors.dark[2] : '#64748b',
                },
                '& table': {
                  borderCollapse: 'collapse',
                  margin: '8px 0',
                  width: '100%',
                },
                '& th, & td': {
                  border: `1px solid ${isDark ? theme.colors.dark[4] : '#e2e8f0'}`,
                  padding: '6px 10px',
                  textAlign: 'left',
                },
                '& hr': {
                  border: 0,
                  borderTop: `1px solid ${isDark ? theme.colors.dark[4] : '#e2e8f0'}`,
                  margin: '12px 0',
                },
              }}
            >
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownLinkComponents}>
                {linkedPrompt}
              </ReactMarkdown>
            </Box>

            {(sample.previous_showcase || sample.next_showcase) && (
              <>
                <Divider my="md" />
                <Group spacing={10} align="stretch">
                  {sample.previous_showcase && renderSequenceLink('Previous showcase', sample.previous_showcase, 'previous')}
                  {sample.next_showcase && renderSequenceLink('Next showcase', sample.next_showcase, 'next')}
                </Group>
              </>
            )}

            {sample.goals && (
              <>
                <Divider my="md" />
                <Text size="sm" weight={700} mb={10}>Goals</Text>
                <Box
                  sx={{
                    fontSize: 14,
                    color: isDark ? theme.colors.dark[1] : '#475569',
                    lineHeight: 1.6,
                    '& p': { margin: '0 0 8px' },
                    '& p:last-child': { marginBottom: 0 },
                    '& ul, & ol': { paddingLeft: 20, margin: '4px 0 8px' },
                    '& li': { margin: '2px 0' },
                  }}
                >
                  {renderMarkdown(sample.goals)}
                </Box>
              </>
            )}

            {sample.terms.length > 0 && (
              <>
                <Divider my="md" />
                <Text size="sm" weight={700} mb={10}>Terms</Text>
                <Group spacing={8}>
                  {sample.terms.map((term) => {
                    const termUrl = sample.term_urls?.[term] || '';
                    return (
                      <Badge
                        key={term}
                        variant="light"
                        color={termUrl ? undefined : 'gray'}
                        style={{ cursor: termUrl ? 'pointer' : 'default' }}
                        onClick={termUrl ? () => openTermVideo(term, termUrl) : undefined}
                      >
                        {term}
                      </Badge>
                    );
                  })}
                </Group>
              </>
            )}

            {sample.variants.length > 0 && (
              <>
                <Divider my="md" />
                <Text size="sm" weight={700} mb={10}>Variants</Text>
                <Stack spacing={8}>
                  {sample.variants.map((variant) => (
                    <button
                      type="button"
                      key={`${variant.slug}-${variant.caption}`}
                      onClick={() => openSampleBySlug(variant.slug)}
                      style={{
                        width: '100%',
                        border: isDark ? `1px solid ${theme.colors.dark[4]}` : '1px solid #ccfbf1',
                        borderRadius: 10,
                        background: isDark ? theme.colors.dark[6] : '#f0fdfa',
                        color: isDark ? theme.colors.teal[2] : '#0f766e',
                        cursor: 'pointer',
                        padding: '10px 12px',
                        textAlign: 'left',
                        fontSize: 13,
                        fontWeight: 600,
                        lineHeight: 1.45,
                        whiteSpace: 'normal',
                        overflowWrap: 'anywhere',
                      }}
                    >
                      {variant.caption}
                    </button>
                  ))}
                </Stack>
              </>
            )}

            {sample.related.length > 0 && (
              <>
                <Divider my="md" />
                <Text size="sm" weight={700} mb={10}>Related</Text>
                <Stack spacing={8}>
                  {sample.related.map((related) => (
                    <button
                      type="button"
                      key={`${related.slug}-${related.caption}`}
                      onClick={() => openSampleBySlug(related.slug)}
                      style={{
                        width: '100%',
                        border: isDark ? `1px solid ${theme.colors.dark[4]}` : '1px solid #dbeafe',
                        borderRadius: 10,
                        background: isDark ? theme.colors.dark[6] : '#eff6ff',
                        color: isDark ? theme.colors.blue[2] : '#1d4ed8',
                        cursor: 'pointer',
                        padding: '10px 12px',
                        textAlign: 'left',
                        fontSize: 13,
                        fontWeight: 600,
                        lineHeight: 1.45,
                        whiteSpace: 'normal',
                        overflowWrap: 'anywhere',
                      }}
                    >
                      {related.caption}
                    </button>
                  ))}
                </Stack>
              </>
            )}

            </div>
          </div>
        </div>

        <div>
          {renderSampleActions(sample)}
        </div>
      </div>
    );
  };

  const renderTile = (
    title: string,
    description: string,
    seed: string,
    onClick: () => void,
    src?: string | null,
    meta?: React.ReactNode,
    thumbSize = 64,
    horizontal = false,
    landscape = false,
  ) => {
    const [bg, fg] = pickColor(seed);
    return (
      <Tooltip label={description} multiline width={280}>
        <button
          type="button"
          onClick={onClick}
          style={{
            border: cardBorder,
            borderRadius: 20,
            background: cardBg,
            padding: landscape ? 0 : 18,
            textAlign: horizontal ? 'center' : 'left',
            cursor: 'pointer',
            display: 'flex',
            flexDirection: 'column',
            gap: landscape ? 0 : 14,
            minHeight: landscape ? 240 : (thumbSize > 96 ? 220 : 182),
            overflow: 'hidden',
            boxShadow: cardShadow,
            transition: 'box-shadow 0.2s ease, transform 0.2s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.boxShadow = isDark ? '0 8px 24px rgba(0, 0, 0, 0.5)' : '0 8px 24px rgba(15, 23, 42, 0.12)';
            e.currentTarget.style.transform = 'translateY(-2px)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.boxShadow = cardShadow;
            e.currentTarget.style.transform = 'translateY(0)';
          }}
        >
          {landscape ? (
            <>
              <div style={{ position: 'relative', width: '100%', aspectRatio: '16 / 9', background: src ? (isDark ? '#0f172a' : '#e5e7eb') : `linear-gradient(135deg, ${bg}, ${isDark ? bg : fg})`, display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden', flexShrink: 0 }}>
                {src ? (
                  <LoadingThumbnailImage src={src} alt={title} isDark={isDark} />
                ) : (
                  <span style={{ color: '#fff', fontSize: 36, fontWeight: 800, letterSpacing: 1 }}>{initialsFromText(title)}</span>
                )}
              </div>
              <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 10, textAlign: 'left', flex: 1 }}>
                <Text size="sm" weight={700} style={{ lineHeight: 1.35 }}>{title}</Text>
                <Text size="xs" color="dimmed" lineClamp={2}>{description}</Text>
                {meta && <div style={{ marginTop: 'auto' }}>{meta}</div>}
              </div>
            </>
          ) : horizontal ? (
            <>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
                <TileThumb label={title} src={src} seed={seed} isDark={isDark} size={thumbSize} />
                <Text size="lg" weight={800} style={{ lineHeight: 1.25, textAlign: 'center' }}>{title}</Text>
              </div>
              <Text size="xs" color="dimmed" style={{ textAlign: 'left' }} lineClamp={2}>{description}</Text>
              {meta && <div style={{ textAlign: 'left' }}>{meta}</div>}
            </>
          ) : (
            <>
              <TileThumb label={title} src={src} seed={seed} isDark={isDark} size={thumbSize} />
              <div>
                <Text size="sm" weight={700} style={{ lineHeight: 1.35 }}>{title}</Text>
                <Text size="xs" color="dimmed" mt={6} lineClamp={2}>{description}</Text>
              </div>
              {meta && <div>{meta}</div>}
            </>
          )}
        </button>
      </Tooltip>
    );
  };

  const renderCategoryGrid = () => (
    <div style={{ padding: 20 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 18 }}>
        {categories.map((category) => renderTile(
          category.category,
          category.description,
          category.category,
          () => openCategory(category),
          category.thumbnail_url,
          <Text size="xs" color="dimmed">
            {(category.samples?.length || 0) + (category.subcategories?.length || 0)} items
          </Text>,
          120,
          true,
        ))}
      </div>
    </div>
  );

  const renderSampleGrid = (samples: Array<ShowcaseSample & { __category?: string }>, title: string, onBack?: () => void) => (
    <div style={{ padding: 20 }}>
      <Group position="apart" mb={18}>
        <div>
          <Text size={26} weight={800}>{title}</Text>
          <Text size="sm" color="dimmed">Browse samples and open one to see the prompt, assets, and template actions.</Text>
        </div>
        {onBack && (
          <Button variant="subtle" leftIcon={<IconArrowLeft size="1rem" />} onClick={onBack}>
            Back
          </Button>
        )}
      </Group>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 18 }}>
        {samples.map((sample) => renderTile(
          sample.title,
          sample.description,
          sample.id,
          () => openSample(sample, sample.__category || selectedCategoryName),
          sample.thumbnail_url,
          <Group spacing={8}>
            <Badge leftSection={<IconTrendingUp size="0.7rem" />} variant="light">{sample.popularity}</Badge>
            <Badge variant="light">Level {sample.level}</Badge>
            <Badge leftSection={<IconStar size="0.7rem" />} color="yellow" variant="light">{sample.rate.toFixed(1)}</Badge>
          </Group>,
          64,
          false,
          true,
        ))}
      </div>
    </div>
  );

  let content: React.ReactNode;
  if (loading) {
    content = (
      <div style={{ padding: 28, display: 'flex', alignItems: 'center', gap: 12 }}>
        <Loader size="sm" />
        <Text size="sm" color="dimmed">Loading Explore showcase data...</Text>
      </div>
    );
  } else if (error) {
    content = <Text color="red" size="sm" style={{ padding: 24 }}>{error}</Text>;
  } else if (selectedSample) {
    content = renderSampleDetail();
  } else if (mode === 'category' && selectedCategory) {
    const hasSubs = selectedCategory.subcategories && selectedCategory.subcategories.length > 0;
    const hasSamps = selectedCategory.samples && selectedCategory.samples.length > 0;

    content = (
      <div style={{ padding: 20 }}>
        <Group position="apart" mb={18}>
          <div>
            <Text size={26} weight={800}>{selectedCategory.category}</Text>
            <Text size="sm" color="dimmed">Browse subcategories and samples</Text>
          </div>
          <Button variant="subtle" leftIcon={<IconArrowLeft size="1rem" />} onClick={goBackFromCategory}>
            Back
          </Button>
        </Group>

        <Stack spacing={32}>
          {hasSubs && (
            <div>
              {hasSamps && <Text size="lg" weight={700} mb={14}>Subcategories</Text>}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 18 }}>
                {selectedCategory.subcategories!.map((sub) => renderTile(
                  sub.category,
                  sub.description,
                  sub.category,
                  () => openCategory(sub),
                  sub.thumbnail_url,
                  <Text size="xs" color="dimmed">
                    {(sub.samples?.length || 0) + (sub.subcategories?.length || 0)} items
                  </Text>,
                  120,
                  true,
                ))}
              </div>
            </div>
          )}

          {hasSamps && (
            <div>
              {hasSubs && <Text size="lg" weight={700} mb={14}>Samples</Text>}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 18 }}>
                {selectedCategory.samples.map((sample) => renderTile(
                  sample.title,
                  sample.description,
                  sample.id,
                  () => openSample(sample, selectedCategory.category),
                  sample.thumbnail_url,
                  <Group spacing={8}>
                    <Badge leftSection={<IconTrendingUp size="0.7rem" />} variant="light">{sample.popularity}</Badge>
                    <Badge variant="light">Level {sample.level}</Badge>
                    <Badge leftSection={<IconStar size="0.7rem" />} color="yellow" variant="light">{sample.rate.toFixed(1)}</Badge>
                  </Group>,
                  64,
                  false,
                  true,
                ))}
              </div>
            </div>
          )}

          {!hasSubs && !hasSamps && (
            <Text size="sm" color="dimmed">No content available in this category.</Text>
          )}
        </Stack>
      </div>
    );
  } else if (mode === 'popularity') {
    content = renderSampleGrid(sortedSamples, 'Popular Samples');
  } else if (mode === 'level') {
    content = renderSampleGrid(sortedSamples, 'Samples By Level');
  } else {
    content = renderCategoryGrid();
  }

  return (
    <>
      <div style={{ minHeight: '100%', background: isDark ? theme.colors.dark[8] : 'linear-gradient(180deg, #f7fbff 0%, #eef4ff 100%)' }}>
        <div style={{ padding: '24px 20px 0' }}>
          <div style={{ padding: 32, borderRadius: 24, background: isDark ? 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)' : 'linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #2563eb 100%)', color: '#fff', boxShadow: isDark ? '0 8px 24px rgba(0, 0, 0, 0.4)' : '0 20px 40px -15px rgba(37, 99, 235, 0.35)', position: 'relative', overflow: 'hidden', border: isDark ? '1px solid rgba(51, 65, 85, 0.6)' : 'none' }}>
            {/* Background decoration */}
            <div style={{ position: 'absolute', top: -50, right: -50, width: 250, height: 250, background: isDark ? 'rgba(59, 130, 246, 0.1)' : 'rgba(96, 165, 250, 0.15)', filter: 'blur(60px)', borderRadius: '50%' }} />
            <div style={{ position: 'absolute', bottom: -80, left: -40, width: 200, height: 200, background: isDark ? 'rgba(99, 102, 241, 0.08)' : 'rgba(99, 102, 241, 0.1)', filter: 'blur(50px)', borderRadius: '50%' }} />

            <Group position="apart" align="flex-start" style={{ position: 'relative', zIndex: 1 }}>
              <div style={{ maxWidth: 800 }}>
                <Group spacing="sm" mb={4}>
                  <Badge variant="filled" color="blue" size="md" radius="xl" style={{ textTransform: 'none', fontWeight: 700, padding: '0 12px' }}>Skill Pilot</Badge>
                  <Text size="xs" style={{ color: '#bfdbfe', letterSpacing: 0.5, fontWeight: 700, textTransform: 'uppercase' }}>A Codeware of AI agent</Text>
                </Group>

                <Text size={38} weight={900} style={{ lineHeight: 1.15, letterSpacing: '-0.02em', marginTop: 12, display: 'flex', alignItems: 'center', gap: '12px' }}>
                  Do first, <span style={{ color: '#60a5fa' }}>learn afterwards.</span>
                  <IconSparkles size="2.2rem" style={{ color: '#60a5fa', opacity: 0.8 }} />
                </Text>

                <Text size="md" style={{ color: 'rgba(255,255,255,0.85)', marginTop: 16, lineHeight: 1.6 }}>
                  This is the <strong>learning method in the age of AI</strong>. Welcome to <strong>Codeware</strong>—the new software form where AI and humans use code as software. AI uses and updates code dynamically to fit any demand you have. Dive into these templates to launch your ideas instantly, and learn how they work along the way.
                </Text>
              </div>
              <Badge size="lg" variant="gradient" gradient={{ from: runtimeMode === 'production' ? 'teal' : 'orange', to: runtimeMode === 'production' ? 'green' : 'red', deg: 105 }} style={{ border: 'none' }}>
                {runtimeMode === 'production' ? 'Prod Mode' : 'Dev Mode'}
              </Badge>
            </Group>
            <Group spacing="xs" mt={32} style={{ position: 'relative', zIndex: 1 }}>
              {(['category', 'popularity', 'level'] as ExploreMode[]).map((m) => {
                const isActive = mode === m;
                const label = m === 'category' ? 'By Category' : m === 'popularity' ? 'By Popularity' : 'By Level';
                return (
                  <Button
                    key={m}
                    variant={isActive ? 'white' : 'default'}
                    onClick={() => openMode(m)}
                    style={isActive
                      ? { color: '#0f172a', fontWeight: 700 }
                      : { background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', fontWeight: 500 }
                    }
                  >
                    {label}
                  </Button>
                );
              })}
            </Group>
          </div>
        </div>
        {content}
      </div>

      <Modal opened={templateOpened} onClose={() => !templateBusy && setTemplateOpened(false)} title="Use Template" centered>
        {templateSample && (
          <Stack spacing="sm">
            <Text size="sm" color="dimmed">{templateSample.title}</Text>
            <Checkbox
              label="Using worktree"
              checked={templateUseWorktree}
              onChange={(event) => setTemplateUseWorktree(event.currentTarget.checked)}
              disabled={templateSample.use_worktree || templateSample.git_tag !== null || runtimeMode === 'development'}
            />
            {templateSample.git_tag && (
              <Checkbox
                label={`Checkout tag: ${templateSample.git_tag}`}
                checked={templateCheckoutTag}
                onChange={(event) => setTemplateCheckoutTag(event.currentTarget.checked)}
                disabled={runtimeMode === 'development'}
              />
            )}
            <Checkbox
              label="Start in dev mode"
              checked={templateUseWorktree || templateSample.in_mode === 'dev'}
              disabled
            />
            <Text
              size="xs"
              color={runtimeMode === 'development' ? 'orange' : 'dimmed'}
              weight={runtimeMode === 'development' ? 700 : 400}
            >
              {runtimeMode === 'development'
                ? 'Warning: use in development mode only if you are experienced with Skill Pilot AI agent development.'
                : 'Warning: update the default settings only if you are experienced with Skill Pilot AI agent development.'}
            </Text>

            {templateError && (
              <Box style={{ padding: 12, borderRadius: 12, border: isDark ? '1px solid #7f1d1d' : '1px solid #fecaca', background: isDark ? '#450a0a' : '#fff1f2' }}>
                <Text size="sm" color="red">{templateError}</Text>
                {templateError.includes('Worktree already exists') && (
                  <Group mt={10} spacing="xs">
                    <Button size="xs" variant={existingAction === 'continue' ? 'filled' : 'light'} onClick={() => setExistingAction('continue')}>
                      Continue Existing
                    </Button>
                    <Button size="xs" color="red" variant={existingAction === 'remove' ? 'filled' : 'light'} onClick={() => setExistingAction('remove')}>
                      Remove And Recreate
                    </Button>
                  </Group>
                )}
              </Box>
            )}

            {launchState && (
              <Group spacing="xs">
                <Loader size="sm" />
                <Text size="sm">{launchState}</Text>
              </Group>
            )}

            {templateContinueUrl && (
              <Box style={{ padding: 14, borderRadius: 14, border: isDark ? '1px solid #1d4ed8' : '1px solid #bfdbfe', background: isDark ? '#172554' : '#eff6ff' }}>
                <Stack spacing={10}>
                  <Group spacing={8}>
                    <IconFolderOpen size="1rem" />
                    <Text size="sm" weight={700}>Work In This Instance, Monitor In Dev</Text>
                  </Group>
                  <Text size="sm">
                    Keep doing the work in the current instance so the web terminal stays stable. Use the dev instance only to monitor live updates from `core/webui` or `core/engine`.
                  </Text>
                  <Box style={{ padding: 10, borderRadius: 10, background: isDark ? 'rgba(15, 23, 42, 0.55)' : 'rgba(255, 255, 255, 0.72)', border: isDark ? '1px solid rgba(148, 163, 184, 0.2)' : '1px solid rgba(148, 163, 184, 0.28)' }}>
                    <Text size="xs" weight={700} style={{ letterSpacing: 0.2, textTransform: 'uppercase' }}>
                      Recommended Flow
                    </Text>
                    <Text size="sm" mt={6}>
                      1. Click the button below to launch the dev instance for monitoring if you have not opened it yet.
                    </Text>
                    <Text size="sm" mt={4}>
                      2. Press Continue to start the template in the current instance.
                    </Text>
                  </Box>
                  {templateMonitorStatus && (
                    <Group spacing="xs" align="center">
                      {!templateMonitorReady && <Loader size="xs" />}
                      <Text size="sm" color={templateMonitorReady ? (isDark ? 'blue.2' : 'blue.8') : undefined}>
                        {templateMonitorStatus}
                      </Text>
                    </Group>
                  )}
                  <Group spacing="xs" position="right">
                    <Button
                      size="sm"
                      variant="light"
                      leftIcon={<IconExternalLink size="0.9rem" />}
                      component={templateMonitorReady && templateMonitorUrl ? 'a' : 'button'}
                      href={templateMonitorReady && templateMonitorUrl ? templateMonitorUrl : undefined}
                      target={templateMonitorReady && templateMonitorUrl ? '_blank' : undefined}
                      rel={templateMonitorReady && templateMonitorUrl ? 'noopener noreferrer' : undefined}
                      disabled={!templateMonitorReady || !templateMonitorUrl}
                    >
                      {templateMonitorReady ? 'Launch Dev Instance For Monitoring' : 'Waiting For Dev Instance'}
                    </Button>
                    <Button size="sm" leftIcon={<IconPlayerPlay size="0.9rem" />} onClick={() => window.location.assign(templateContinueUrl)}>
                      Continue In Current Instance
                    </Button>
                  </Group>
                </Stack>
              </Box>
            )}

            <Group position="right" mt="sm">
              <Button variant="default" onClick={() => setTemplateOpened(false)} disabled={templateBusy}>Cancel</Button>
              {!templateContinueUrl && (
                <Button onClick={() => void startTemplate()} loading={templateBusy}>Start Template</Button>
              )}
            </Group>
          </Stack>
        )}
      </Modal>

      {mediaModal && (
        <FloatingPopup
          title={mediaModal.title || 'Media'}
          onClose={() => setMediaModal(null)}
          initialWidth={mediaModal.type === 'audio' ? 520 : 920}
          initialHeight={mediaModal.type === 'audio' ? 180 : 560}
        >
          {mediaModal.type === 'image' && (
            <img src={mediaModal.url} alt={mediaModal.title} style={{ width: '100%', display: 'block' }} />
          )}
          {mediaModal.type === 'video' && (
            <PopupVideoPlayer src={mediaModal.url} title={mediaModal.title} />
          )}
          {mediaModal.type === 'audio' && (
            <div style={{ padding: 18 }}>
              <audio src={mediaModal.url} controls autoPlay style={{ width: '100%' }} />
            </div>
          )}
        </FloatingPopup>
      )}

      {coursePopup && (
        <FloatingPopup title={coursePopup.title || 'Markdown course'} onClose={() => setCoursePopup(null)} initialWidth={980} initialHeight={660}>
          <iframe
            src={coursePopup.url}
            title={coursePopup.title || 'Markdown course'}
            style={{ width: '100%', height: '100%', border: 0, display: 'block' }}
          />
        </FloatingPopup>
      )}

    </>
  );
}
