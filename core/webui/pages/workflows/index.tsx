import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { GetStaticPropsContext } from 'next';
import axios from 'axios';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';
import {
  AppShell,
  Header,
  Text,
  MediaQuery,
  Burger,
  ScrollArea,
  Group,
  ActionIcon,
  Tooltip,
  NavLink,
  Box,
  Button,
  TextInput,
  Textarea,
  Select,
  Stack,
  Paper,
  Badge,
  Divider,
} from '@mantine/core';
import {
  IconFolder,
  IconFileText,
  IconRefresh,
  IconSortAscending,
  IconClock,
  IconArrowLeft,
  IconPlus,
  IconDeviceFloppy,
  IconTrash,
  IconChevronsLeft,
  IconChevronsRight,
} from '@tabler/icons-react';
import { apiUrl } from '../../libs/api-base';

const API_BASE_URL = apiUrl('/api');

type NodeType = 'start' | 'agent' | 'end';

type WorkflowNode = {
  id: number;
  type: NodeType;
  position: { x: number; y: number };
  data?: {
    title?: string;
    provider_id?: string;
    skill?: string;
    responsibility?: string;
  };
};

type WorkflowEdge = {
  id: string;
  source: number;
  target: number;
  source_anchor?: AnchorSide;
  target_anchor?: AnchorSide;
};

type WorkflowDoc = {
  version: string;
  name: string;
  updated_at: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
};

type FileItem = {
  name: string;
  path: string;
  type: 'dir' | 'file';
  mtime: number;
  children?: FileItem[];
};

type LlmProvider = {
  id: string;
  name: string;
};

type ValidationError = {
  rule: string;
  message: string;
  node_ids?: number[];
  edge_ids?: string[];
};
type ConnectionDragState = {
  sourceNodeId: number;
  sourceKind: AnchorKind;
  sourceSide: AnchorSide;
  sourcePoint: { x: number; y: number };
  mousePoint: { x: number; y: number };
};
type HoverAnchorState = {
  nodeId: number;
  side: AnchorSide;
  kind: AnchorKind;
};

const CANVAS_WIDTH = 2600;
const CANVAS_HEIGHT = 1600;

type AnchorKind = 'in' | 'out' | 'both';
type AnchorSide = 'top' | 'right' | 'bottom' | 'left';

type NodeAnchor = {
  key: string;
  side: AnchorSide;
  kind: AnchorKind;
};

function nowIsoUtc(): string {
  return new Date().toISOString();
}

function createDefaultWorkflow(providerId: string): WorkflowDoc {
  return {
    version: '1.0',
    name: 'new-workflow',
    updated_at: nowIsoUtc(),
    nodes: [
      { id: 0, type: 'start', position: { x: 120, y: 300 } },
      {
        id: 1,
        type: 'agent',
        position: { x: 420, y: 280 },
        data: {
          title: 'Agent 1',
          provider_id: providerId,
          skill: '',
          responsibility: '',
        },
      },
      { id: -1, type: 'end', position: { x: 760, y: 300 } },
    ],
    edges: [
      { id: '0->1', source: 0, target: 1 },
      { id: '1->-1', source: 1, target: -1 },
    ],
  };
}

function edgeId(source: number, target: number): string {
  return `${source}->${target}`;
}

function workflowBaseName(path: string): string {
  const file = path.split('/').pop() || path;
  return file.replace(/\.json$/i, '');
}

function getNodeLabel(node: WorkflowNode): string {
  if (node.type === 'start') return 'Start';
  if (node.type === 'end') return 'End';
  return node.data?.title || `Agent ${node.id}`;
}

function normalizeNodeName(value: string): string {
  const normalized = String(value || '').trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  return normalized || 'node';
}

function canSource(node: WorkflowNode): boolean {
  return node.type !== 'end';
}

function canTarget(node: WorkflowNode): boolean {
  return node.type !== 'start';
}

function isInteractiveNodeTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return Boolean(
    target.closest(
      'input,textarea,select,button,[role="textbox"],[role="combobox"],[contenteditable="true"],[data-node-interactive],.anchor-btn',
    ),
  );
}

function getNodeAnchors(node: WorkflowNode): NodeAnchor[] {
  if (node.type === 'start') {
    return [{ key: 'start-out', side: 'right', kind: 'out' }];
  }
  if (node.type === 'end') {
    return [{ key: 'end-in', side: 'left', kind: 'in' }];
  }
  return [
    { key: 'top', side: 'top', kind: 'both' },
    { key: 'right', side: 'right', kind: 'both' },
    { key: 'bottom', side: 'bottom', kind: 'both' },
    { key: 'left', side: 'left', kind: 'both' },
  ];
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function isSafeWorkflowDoc(value: unknown): value is WorkflowDoc {
  if (!value || typeof value !== 'object') return false;
  const doc = value as Partial<WorkflowDoc>;
  if (!Array.isArray(doc.nodes) || !Array.isArray(doc.edges)) return false;

  for (const node of doc.nodes) {
    if (!node || typeof node !== 'object') return false;
    const n = node as WorkflowNode;
    if (typeof n.id !== 'number') return false;
    if (n.type !== 'start' && n.type !== 'agent' && n.type !== 'end') return false;
    if (!n.position || typeof n.position !== 'object') return false;
    if (!isFiniteNumber(n.position.x) || !isFiniteNumber(n.position.y)) return false;
  }

  for (const edge of doc.edges) {
    if (!edge || typeof edge !== 'object') return false;
    const e = edge as WorkflowEdge;
    if (typeof e.id !== 'string' || !e.id.trim()) return false;
    if (typeof e.source !== 'number' || typeof e.target !== 'number') return false;
  }
  return true;
}

export default function WorkflowsPage() {
  const router = useRouter();

  const [opened, setOpened] = useState(false);
  const [treeData, setTreeData] = useState<FileItem[]>([]);
  const [treeLoading, setTreeLoading] = useState(false);
  const [sortByTime, setSortByTime] = useState(true);

  const [providers, setProviders] = useState<LlmProvider[]>([]);
  const [skills, setSkills] = useState<string[]>([]);
  const [defaultProviderId, setDefaultProviderId] = useState('');

  const [workflowPath, setWorkflowPath] = useState<string | null>(null);
  const [filenameInput, setFilenameInput] = useState('new-workflow');
  const [workflow, setWorkflow] = useState<WorkflowDoc>(() => createDefaultWorkflow(''));

  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [connectionDrag, setConnectionDrag] = useState<ConnectionDragState | null>(null);
  const [hoverAnchor, setHoverAnchor] = useState<HoverAnchorState | null>(null);
  const [errors, setErrors] = useState<ValidationError[]>([]);
  const [saving, setSaving] = useState(false);
  const [inspectorVisible, setInspectorVisible] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [editingNodeId, setEditingNodeId] = useState<number | null>(null);
  const [editingNodeTitle, setEditingNodeTitle] = useState('');

  const [isResizing, setIsResizing] = useState(false);
  const [navbarWidth, setNavbarWidth] = useState(320);
  const [inspectorWidth, setInspectorWidth] = useState(320);
  const [isInspectorResizing, setIsInspectorResizing] = useState(false);
  const [nodeSizes, setNodeSizes] = useState<Record<number, { width: number; height: number }>>({});

  const canvasScrollRef = useRef<HTMLDivElement | null>(null);
  const canvasInnerRef = useRef<HTMLDivElement | null>(null);
  const nodeRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  const dragRef = useRef<{ nodeId: number; dx: number; dy: number } | null>(null);
  const skipNextDraftWriteRef = useRef(false);
  const hasUnsavedChangesRef = useRef(false);
  const isInitialMountRef = useRef(true);
  const pendingNewNodeSelectRef = useRef<number | null>(null);

  const beginProgrammaticStateUpdate = () => {
    skipNextDraftWriteRef.current = true;
  };

  const startResizing = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  };

  useEffect(() => {
    if (typeof ResizeObserver === 'undefined') return;
    const observers: ResizeObserver[] = [];
    for (const node of workflow.nodes) {
      const el = nodeRefs.current.get(node.id);
      if (!el) continue;
      const applySize = () => {
        const rect = el.getBoundingClientRect();
        setNodeSizes((prev) => {
          const prevSize = prev[node.id];
          const nextSize = { width: rect.width, height: rect.height };
          if (prevSize && prevSize.width === nextSize.width && prevSize.height === nextSize.height) {
            return prev;
          }
          return { ...prev, [node.id]: nextSize };
        });
      };
      applySize();
      const obs = new ResizeObserver(applySize);
      obs.observe(el);
      observers.push(obs);
    }
    return () => {
      observers.forEach((obs) => obs.disconnect());
    };
  }, [workflow.nodes]);

  useEffect(() => {
    const resize = (e: MouseEvent) => {
      if (!isResizing) return;
      const newWidth = e.clientX;
      if (newWidth > 220 && newWidth < 640) setNavbarWidth(newWidth);
    };
    const stop = () => setIsResizing(false);
    window.addEventListener('mousemove', resize);
    window.addEventListener('mouseup', stop);
    return () => {
      window.removeEventListener('mousemove', resize);
      window.removeEventListener('mouseup', stop);
    };
  }, [isResizing]);

  useEffect(() => {
    const resize = (e: MouseEvent) => {
      if (!isInspectorResizing) return;
      const newWidth = window.innerWidth - e.clientX;
      if (newWidth > 240 && newWidth < 700) setInspectorWidth(newWidth);
    };
    const stop = () => setIsInspectorResizing(false);
    window.addEventListener('mousemove', resize);
    window.addEventListener('mouseup', stop);
    return () => {
      window.removeEventListener('mousemove', resize);
      window.removeEventListener('mouseup', stop);
    };
  }, [isInspectorResizing]);

  const sortItems = useCallback((items: FileItem[]): FileItem[] => {
    const sorted = [...items].sort((a, b) => {
      if (a.type === 'dir' && b.type !== 'dir') return -1;
      if (a.type !== 'dir' && b.type === 'dir') return 1;
      if (sortByTime) return b.mtime - a.mtime;
      return a.name.localeCompare(b.name);
    });
    return sorted.map((item) => (item.children ? { ...item, children: sortItems(item.children) } : item));
  }, [sortByTime]);

  const sortedTreeData = useMemo(() => sortItems(treeData), [treeData, sortItems]);

  const fetchTree = useCallback(async () => {
    setTreeLoading(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/workflows/tree`);
      setTreeData(res.data.items || []);
    } catch (err) {
      console.error('Failed to fetch workflows tree:', err);
    } finally {
      setTreeLoading(false);
    }
  }, []);

  const fetchProviders = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/llm/providers`);
      const items: LlmProvider[] = res.data.providers || [];
      const fallback = items[0]?.id || '';
      const selected = res.data.default || fallback;
      setProviders(items);
      setDefaultProviderId(selected || '');
      beginProgrammaticStateUpdate();
      setWorkflow((prev) => {
        const updatedNodes = prev.nodes.map((n) => {
          if (n.type !== 'agent') return n;
          const provider = n.data?.provider_id || selected || fallback;
          return { ...n, data: { ...n.data, provider_id: provider } };
        });
        return { ...prev, nodes: updatedNodes };
      });
    } catch (err) {
      console.error('Failed to fetch providers:', err);
    }
  }, []);

  const fetchSkills = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/config/skills`);
      const categories = res.data.categories || [];
      const names: string[] = [];
      for (const cat of categories) {
        for (const skill of cat.skills || []) {
          if (skill?.name) names.push(String(skill.name));
        }
      }
      setSkills(names);
    } catch (err) {
      console.error('Failed to fetch skills:', err);
    }
  }, []);

  const loadWorkflow = useCallback(async (path: string, skipUnsavedCheck = false) => {
    if (!skipUnsavedCheck && hasUnsavedChangesRef.current) {
      const ok = window.confirm('You have unsaved changes. Discard and open another workflow?');
      if (!ok) return;
    }
    try {
      const res = await axios.get(`${API_BASE_URL}/workflows/content`, { params: { workflow: path } });
      const content = res.data.content;
      if (!isSafeWorkflowDoc(content)) {
        setErrors([{ rule: 'LOAD_INVALID', message: 'Loaded workflow document has invalid shape.', node_ids: [], edge_ids: [] }]);
        setInspectorVisible(true);
        return;
      }
      beginProgrammaticStateUpdate();
      setWorkflow(content);
      setWorkflowPath(path);
      setFilenameInput(workflowBaseName(path));
      setSelectedNodeId(null);
      setSelectedEdgeId(null);
      setConnectionDrag(null);
      setHoverAnchor(null);
      pendingNewNodeSelectRef.current = null;
      setErrors([]);
      setHasUnsavedChanges(false);
      setEditingNodeId(null);
      setEditingNodeTitle('');
    } catch (err: any) {
      console.error('Failed to load workflow:', err);
      const apiErrors = err?.response?.data?.errors;
      if (Array.isArray(apiErrors)) {
        setErrors(apiErrors);
      } else {
        const message = err?.response?.data?.error || err?.response?.data?.detail || err?.message || 'Failed to load workflow.';
        setErrors([{ rule: 'LOAD_FAILED', message, node_ids: [], edge_ids: [] }]);
      }
      setInspectorVisible(true);
    }
  }, []);

  const loadLatest = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/workflows/latest`);
      const latestPath: string | null = res.data.path || null;
      if (!latestPath) {
        const fresh = createDefaultWorkflow(defaultProviderId);
        beginProgrammaticStateUpdate();
        setWorkflow(fresh);
        setFilenameInput(fresh.name);
        setWorkflowPath(null);
        pendingNewNodeSelectRef.current = null;
        setErrors([]);
        setHasUnsavedChanges(false);
        return;
      }
      await loadWorkflow(latestPath, true);
    } catch (err) {
      console.error('Failed to load latest workflow:', err);
    }
  }, [defaultProviderId, loadWorkflow]);

  useEffect(() => {
    void fetchTree();
    void fetchProviders();
    void fetchSkills();
  }, [fetchTree, fetchProviders, fetchSkills]);

  useEffect(() => {
    if (!defaultProviderId) return;
    void loadLatest();
  }, [defaultProviderId, loadLatest]);

  useEffect(() => {
    hasUnsavedChangesRef.current = hasUnsavedChanges;
  }, [hasUnsavedChanges]);

  useEffect(() => {
    if (isInitialMountRef.current) {
      isInitialMountRef.current = false;
      return;
    }
    if (skipNextDraftWriteRef.current) {
      skipNextDraftWriteRef.current = false;
      return;
    }
    setHasUnsavedChanges(true);
  }, [workflow, filenameInput, workflowPath]);

  // Warn before closing/refreshing the browser tab with unsaved changes
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChangesRef.current) {
        e.preventDefault();
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, []);

  // Warn before navigating to another page within the app
  useEffect(() => {
    const handleRouteChangeStart = () => {
      if (hasUnsavedChangesRef.current) {
        if (!window.confirm('You have unsaved changes. Leave without saving?')) {
          router.events.emit('routeChangeError');
          // eslint-disable-next-line @typescript-eslint/no-throw-literal
          throw 'routeChangeAborted';
        }
      }
    };
    router.events.on('routeChangeStart', handleRouteChangeStart);
    return () => router.events.off('routeChangeStart', handleRouteChangeStart);
  }, [router.events]);

  useEffect(() => {
    const pendingId = pendingNewNodeSelectRef.current;
    if (pendingId === null) return;
    const exists = workflow.nodes.some((n) => n.id === pendingId);
    if (!exists) return;
    setSelectedNodeId(pendingId);
    pendingNewNodeSelectRef.current = null;
  }, [workflow.nodes]);

  useEffect(() => {
    if (editingNodeId === null) return;
    const stillExists = workflow.nodes.some((node) => node.id === editingNodeId && node.type === 'agent');
    if (!stillExists) {
      setEditingNodeId(null);
      setEditingNodeTitle('');
    }
  }, [editingNodeId, workflow.nodes]);

  const renderTree = (items: FileItem[]) => items.map((item) => {
    if (item.type === 'dir') {
      return (
        <NavLink
          key={item.path}
          label={item.name}
          icon={<IconFolder size="1rem" />}
          childrenOffset={16}
          defaultOpened={true}
        >
          {item.children ? renderTree(item.children) : null}
        </NavLink>
      );
    }
    return (
      <NavLink
        key={item.path}
        label={item.name}
        icon={<IconFileText size="1rem" />}
        active={workflowPath === item.path}
        onClick={() => {
          void loadWorkflow(item.path);
          setOpened(false);
        }}
      />
    );
  });

  const handleNewWorkflow = () => {
    if (hasUnsavedChangesRef.current) {
      const ok = window.confirm('You have unsaved changes. Discard and create a new workflow?');
      if (!ok) return;
    }
    const fresh = createDefaultWorkflow(defaultProviderId);
    beginProgrammaticStateUpdate();
    setWorkflow(fresh);
    setWorkflowPath(null);
    setFilenameInput('new-workflow');
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    setConnectionDrag(null);
    setHoverAnchor(null);
    pendingNewNodeSelectRef.current = null;
    setErrors([]);
    setHasUnsavedChanges(false);
    setEditingNodeId(null);
    setEditingNodeTitle('');
  };

  const handleAddAgent = (position?: { x: number; y: number }) => {
    setWorkflow((prev) => {
      const ids = prev.nodes.filter((n) => n.type === 'agent').map((n) => n.id);
      const nextId = ids.length === 0 ? 1 : Math.max(...ids) + 1;
      pendingNewNodeSelectRef.current = nextId;
      const node: WorkflowNode = {
        id: nextId,
        type: 'agent',
        position: position || { x: 360 + (nextId % 5) * 180, y: 180 + (nextId % 6) * 120 },
        data: {
          title: `Agent ${nextId}`,
          provider_id: defaultProviderId,
          skill: '',
          responsibility: '',
        },
      };
      return { ...prev, nodes: [...prev.nodes, node] };
    });
    setSelectedEdgeId(null);
  };

  const getViewportAddPosition = useCallback(() => {
    const scrollLeft = canvasScrollRef.current?.scrollLeft || 0;
    const scrollTop = canvasScrollRef.current?.scrollTop || 0;
    return {
      x: Math.max(10, Math.min(CANVAS_WIDTH - 210, scrollLeft + 120)),
      y: Math.max(10, Math.min(CANVAS_HEIGHT - 170, scrollTop + 80)),
    };
  }, []);

  const findNode = useCallback((id: number) => workflow.nodes.find((n) => n.id === id) || null, [workflow.nodes]);

  const getNodeSize = useCallback((node: WorkflowNode): { width: number; height: number } => {
    const measured = nodeSizes[node.id];
    if (measured) return measured;
    if (node.type === 'agent') return { width: 190, height: 170 };
    return { width: 96, height: 96 };
  }, [nodeSizes]);

  const getAnchorOffset = useCallback((node: WorkflowNode, side: AnchorSide): { x: number; y: number } => {
    const size = getNodeSize(node);
    if (side === 'top') return { x: size.width / 2, y: 0 };
    if (side === 'right') return { x: size.width, y: size.height / 2 };
    if (side === 'bottom') return { x: size.width / 2, y: size.height };
    return { x: 0, y: size.height / 2 };
  }, [getNodeSize]);

  const nodeAnchorPosition = useCallback((node: WorkflowNode) => {
    const size = getNodeSize(node);
    return {
      x: node.position.x + size.width / 2,
      y: node.position.y + size.height / 2,
    };
  }, [getNodeSize]);

  const edgeGeometry = useCallback((edge: WorkflowEdge) => {
    const src = findNode(edge.source);
    const dst = findNode(edge.target);
    if (!src || !dst) return null;
    const pickAutoSide = (from: WorkflowNode, to: WorkflowNode): AnchorSide => {
      const dx = to.position.x - from.position.x;
      const dy = to.position.y - from.position.y;
      if (Math.abs(dx) >= Math.abs(dy)) {
        return dx >= 0 ? 'right' : 'left';
      }
      return dy >= 0 ? 'bottom' : 'top';
    };
    const sourceSide = edge.source_anchor || pickAutoSide(src, dst);
    const targetSide = edge.target_anchor || pickAutoSide(dst, src);
    const sourceOffset = getAnchorOffset(src, sourceSide);
    const targetOffset = getAnchorOffset(dst, targetSide);
    const s = { x: src.position.x + sourceOffset.x, y: src.position.y + sourceOffset.y };
    const t = { x: dst.position.x + targetOffset.x, y: dst.position.y + targetOffset.y };
    const dx = Math.max(60, Math.abs(t.x - s.x) * 0.45);
    const c1x = s.x + (t.x >= s.x ? dx : -dx);
    const c2x = t.x - (t.x >= s.x ? dx : -dx);
    const path = `M ${s.x} ${s.y} C ${c1x} ${s.y}, ${c2x} ${t.y}, ${t.x} ${t.y}`;
    return {
      path,
      midX: (s.x + t.x) / 2,
      midY: (s.y + t.y) / 2,
    };
  }, [findNode, getAnchorOffset]);

  const setAgentField = useCallback((nodeId: number, key: 'title' | 'provider_id' | 'skill' | 'responsibility', value: string) => {
    setWorkflow((prev) => ({
      ...prev,
      nodes: prev.nodes.map((node) => {
        if (node.id !== nodeId || node.type !== 'agent') return node;
        return { ...node, data: { ...node.data, [key]: value } };
      }),
    }));
  }, []);

  const startEditingNodeTitle = useCallback((node: WorkflowNode) => {
    if (node.type !== 'agent') return;
    setSelectedNodeId(node.id);
    setSelectedEdgeId(null);
    setEditingNodeId(node.id);
    setEditingNodeTitle(node.data?.title || `Agent ${node.id}`);
  }, []);

  const commitEditingNodeTitle = useCallback(() => {
    if (editingNodeId === null) return;
    const nextTitle = editingNodeTitle.trim() || `Agent ${editingNodeId}`;
    setAgentField(editingNodeId, 'title', nextTitle);
    setEditingNodeId(null);
    setEditingNodeTitle('');
  }, [editingNodeId, editingNodeTitle, setAgentField]);

  const cancelEditingNodeTitle = useCallback(() => {
    setEditingNodeId(null);
    setEditingNodeTitle('');
  }, []);

  const resolveDirectedEdge = useCallback(
    (sourceNodeId: number, sourceKind: AnchorKind, targetNodeId: number, targetKind: AnchorKind): { source: number; target: number; fromFirst: boolean } | null => {
      const sourceNode = findNode(sourceNodeId);
      const targetNode = findNode(targetNodeId);
      if (!sourceNode || !targetNode) return null;
      if (sourceNodeId === targetNodeId) return null;

      const firstCanSource = sourceKind !== 'in' && canSource(sourceNode);
      const firstCanTarget = sourceKind !== 'out' && canTarget(sourceNode);
      const secondCanSource = targetKind !== 'in' && canSource(targetNode);
      const secondCanTarget = targetKind !== 'out' && canTarget(targetNode);

      if (firstCanSource && secondCanTarget) {
        return { source: sourceNodeId, target: targetNodeId, fromFirst: true };
      }
      if (secondCanSource && firstCanTarget) {
        return { source: targetNodeId, target: sourceNodeId, fromFirst: false };
      }
      return null;
    },
    [findNode],
  );

  const handleAnchorMouseDown = (e: React.MouseEvent, nodeId: number, kind: AnchorKind, side: AnchorSide) => {
    e.stopPropagation();
    e.preventDefault();
    const node = findNode(nodeId);
    if (!node || !canvasInnerRef.current || !canvasScrollRef.current) return;
    const anchorOffset = getAnchorOffset(node, side);
    const rect = canvasInnerRef.current.getBoundingClientRect();
    const scrollLeft = canvasScrollRef.current.scrollLeft;
    const scrollTop = canvasScrollRef.current.scrollTop;
    const sourcePoint = {
      x: node.position.x + anchorOffset.x,
      y: node.position.y + anchorOffset.y,
    };
    const mousePoint = {
      x: e.clientX - rect.left + scrollLeft,
      y: e.clientY - rect.top + scrollTop,
    };
    setConnectionDrag({ sourceNodeId: nodeId, sourceKind: kind, sourceSide: side, sourcePoint, mousePoint });
  };

  const handleAnchorMouseUp = (e: React.MouseEvent, targetNodeId: number, targetKind: AnchorKind, targetSide: AnchorSide) => {
    e.stopPropagation();
    e.preventDefault();
    if (!connectionDrag) return;
    const resolved = resolveDirectedEdge(connectionDrag.sourceNodeId, connectionDrag.sourceKind, targetNodeId, targetKind);
    if (resolved) {
      const newEdge: WorkflowEdge = {
        id: edgeId(resolved.source, resolved.target),
        source: resolved.source,
        target: resolved.target,
        source_anchor: resolved.fromFirst ? connectionDrag.sourceSide : targetSide,
        target_anchor: resolved.fromFirst ? targetSide : connectionDrag.sourceSide,
      };
      setWorkflow((prev) => {
        const exists = prev.edges.some((edge) => edge.source === newEdge.source && edge.target === newEdge.target);
        if (exists) return prev;
        return { ...prev, edges: [...prev.edges, newEdge] };
      });
    }
    setConnectionDrag(null);
    setHoverAnchor(null);
  };

  const onNodeMouseDown = (e: React.MouseEvent, node: WorkflowNode) => {
    if (!canvasInnerRef.current || !canvasScrollRef.current) return;
    const rect = canvasInnerRef.current.getBoundingClientRect();
    const scrollLeft = canvasScrollRef.current.scrollLeft;
    const scrollTop = canvasScrollRef.current.scrollTop;
    dragRef.current = {
      nodeId: node.id,
      dx: e.clientX - rect.left + scrollLeft - node.position.x,
      dy: e.clientY - rect.top + scrollTop - node.position.y,
    };
    setSelectedNodeId(node.id);
    setSelectedEdgeId(null);
  };

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!canvasInnerRef.current || !canvasScrollRef.current) return;
      const rect = canvasInnerRef.current.getBoundingClientRect();
      const scrollLeft = canvasScrollRef.current.scrollLeft;
      const scrollTop = canvasScrollRef.current.scrollTop;

      if (connectionDrag) {
        setConnectionDrag((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            mousePoint: {
              x: e.clientX - rect.left + scrollLeft,
              y: e.clientY - rect.top + scrollTop,
            },
          };
        });
      }

      if (dragRef.current) {
        const x = e.clientX - rect.left + scrollLeft - dragRef.current.dx;
        const y = e.clientY - rect.top + scrollTop - dragRef.current.dy;

        setWorkflow((prev) => ({
          ...prev,
          nodes: prev.nodes.map((n) => {
            if (n.id !== dragRef.current?.nodeId) return n;
            const size = getNodeSize(n);
            return {
              ...n,
              position: {
                x: Math.max(10, Math.min(CANVAS_WIDTH - size.width - 10, x)),
                y: Math.max(10, Math.min(CANVAS_HEIGHT - size.height - 10, y)),
              },
            };
          }),
        }));
      }
    };

    const onUp = () => {
      dragRef.current = null;
      setConnectionDrag((prev) => (prev ? null : prev));
      setHoverAnchor((prev) => (prev ? null : prev));
    };

    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [connectionDrag, getNodeSize]);

  const removeSelectedEdge = () => {
    if (!selectedEdgeId) return;
    setWorkflow((prev) => ({ ...prev, edges: prev.edges.filter((e) => e.id !== selectedEdgeId) }));
    setSelectedEdgeId(null);
  };

  const removeSelectedNode = () => {
    if (selectedNodeId === null) return;
    const node = findNode(selectedNodeId);
    if (!node || node.type === 'start' || node.type === 'end') return;
    setWorkflow((prev) => ({
      ...prev,
      nodes: prev.nodes.filter((n) => n.id !== selectedNodeId),
      edges: prev.edges.filter((e) => e.source !== selectedNodeId && e.target !== selectedNodeId),
    }));
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
  };

  const handleSave = async () => {
    const localErrors: ValidationError[] = [];
    const normalizedNameToIds = new Map<string, number[]>();
    for (const node of workflow.nodes) {
      const nodeLabel = getNodeLabel(node);
      const normalizedName = normalizeNodeName(nodeLabel);
      normalizedNameToIds.set(normalizedName, [...(normalizedNameToIds.get(normalizedName) || []), node.id]);
      if (node.type !== 'agent') continue;
      if (!(node.data?.title || '').trim()) {
        localErrors.push({
          rule: 'SUBAGENT_FIELD',
          message: 'Agent requires non-empty `title`.',
          node_ids: [node.id],
          edge_ids: [],
        });
      }
      if (!(node.data?.provider_id || '').trim()) {
        localErrors.push({
          rule: 'SUBAGENT_FIELD',
          message: 'Agent requires non-empty `provider_id`.',
          node_ids: [node.id],
          edge_ids: [],
        });
      }
      if (!(node.data?.skill || '').trim() && !(node.data?.responsibility || '').trim()) {
        localErrors.push({
          rule: 'SUBAGENT_FIELD',
          message: 'Agent requires non-empty `skill` or `responsibility`.',
          node_ids: [node.id],
          edge_ids: [],
        });
      }
    }
    const duplicateNameIds = Array.from(normalizedNameToIds.values())
      .filter((ids) => ids.length > 1)
      .flat()
      .sort((a, b) => a - b);
    if (duplicateNameIds.length > 0) {
      localErrors.push({
        rule: 'NODE_NAME_DUPLICATE',
        message: 'Node names must be unique after normalization.',
        node_ids: duplicateNameIds,
        edge_ids: [],
      });
    }
    if (localErrors.length > 0) {
      setErrors(localErrors);
      setInspectorVisible(true);
      return;
    }

    setSaving(true);
    setErrors([]);
    try {
      const payload = {
        path: workflowPath,
        filename: filenameInput,
        workflow: {
          ...workflow,
          updated_at: nowIsoUtc(),
        },
      };
      const res = await axios.post(`${API_BASE_URL}/workflows/save`, payload);
      const path = res.data?.path as string;
      if (path) {
        beginProgrammaticStateUpdate();
        setWorkflowPath(path);
        setFilenameInput(workflowBaseName(path));
      }
      setHasUnsavedChanges(false);
      await fetchTree();
    } catch (err: any) {
      console.error('Failed to save workflow:', err);
      const apiErrors = err?.response?.data?.errors;
      if (Array.isArray(apiErrors)) {
        setErrors(apiErrors);
        setInspectorVisible(true);
      } else {
        const message = err?.response?.data?.detail || err?.message || 'Failed to save workflow.';
        setErrors([{ rule: 'SAVE_FAILED', message, node_ids: [], edge_ids: [] }]);
        setInspectorVisible(true);
      }
    } finally {
      setSaving(false);
    }
  };

  const selectedNode = workflow.nodes.find((n) => n.id === selectedNodeId) || null;
  const selectedNodeHasMissingSkill = Boolean(
    selectedNode?.type === 'agent' &&
    !(selectedNode.data?.skill || '').trim() &&
    !(selectedNode.data?.responsibility || '').trim(),
  );

  return (
    <AppShell
      styles={{
        main: {
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
          <Group position="apart" style={{ height: '100%' }}>
            <Group>
              <MediaQuery largerThan="sm" styles={{ display: 'none' }}>
                <Burger opened={opened} onClick={() => setOpened((o) => !o)} size="sm" mr="xl" />
              </MediaQuery>
              <a href="/"><img className="h-10" src="/images/skill-pilot-2.png" alt="Logo" /></a>
              <Text fw={700}>Workflows</Text>
            </Group>
            <Group />
          </Group>
        </Header>
      }
    >
      <Head>
        <title>Skill Pilot - Workflows</title>
      </Head>

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
      <div style={{ padding: 10, borderBottom: '1px solid #e5e7eb', background: '#fff' }}>
        <Group position="apart">
          <Group spacing="xs">
            <Badge variant="light">Path: {workflowPath || '(new workflow)'}</Badge>
            {connectionDrag !== null && <Badge color="orange">Connecting... drag to another anchor</Badge>}
          </Group>
          <Group spacing="xs">
            <TextInput
              value={filenameInput}
              onChange={(e) => setFilenameInput(e.currentTarget.value)}
              placeholder="workflow-file-name"
              size="xs"
              style={{ width: 220 }}
              styles={{ input: { border: 'none', background: 'transparent', boxShadow: 'none', paddingLeft: 4, paddingRight: 4 } }}
            />
            <Button leftIcon={<IconDeviceFloppy size="1rem" />} onClick={() => { void handleSave(); }} loading={saving}>
              Save Workflow
            </Button>
          </Group>
        </Group>
      </div>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <div
          style={{
            width: navbarWidth,
            minWidth: navbarWidth,
            position: 'relative',
            transition: isResizing ? 'none' : 'width 200ms ease',
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            borderRight: '1px solid #e5e7eb',
            background: '#fff',
            overflow: 'hidden',
          }}
        >
          <div style={{ padding: '8px 16px' }}>
            <Stack spacing="xs">
              <Button leftIcon={<IconPlus size="1rem" />} onClick={handleNewWorkflow}>
                Create Workflow
              </Button>
              <Group position="apart">
                <Text fw={700}>Workflow Files</Text>
                <Group spacing={4}>
                  <Tooltip label="Refresh">
                    <ActionIcon variant="subtle" onClick={() => { void fetchTree(); }}>
                      <IconRefresh size="1rem" />
                    </ActionIcon>
                  </Tooltip>
                  <Tooltip label={sortByTime ? 'Sorted by Time' : 'Sorted Alpha'}>
                    <ActionIcon variant="subtle" onClick={() => setSortByTime((v) => !v)}>
                      {sortByTime ? <IconClock size="1rem" /> : <IconSortAscending size="1rem" />}
                    </ActionIcon>
                  </Tooltip>
                </Group>
              </Group>
            </Stack>
          </div>
          <ScrollArea style={{ flex: 1 }} px="md" pb="md">
            {treeLoading && treeData.length === 0 ? (
              <Box py="xl" style={{ textAlign: 'center' }}><Text size="sm" c="dimmed">Loading...</Text></Box>
            ) : (
              <Box style={{ display: 'flex', flexDirection: 'column', justifyContent: 'flex-start' }}>
                {renderTree(sortedTreeData)}
              </Box>
            )}
          </ScrollArea>

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
                backgroundColor: isResizing ? '#228be6' : 'transparent',
                zIndex: 100,
              }}
            />
          </MediaQuery>
        </div>

        <main style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <div ref={canvasScrollRef} style={{ flex: 1, overflow: 'auto', background: '#f8fafc' }}>
              <div
                ref={canvasInnerRef}
                style={{
                  width: CANVAS_WIDTH,
                  height: CANVAS_HEIGHT,
                  position: 'relative',
                  backgroundImage: 'linear-gradient(#e2e8f0 1px, transparent 1px), linear-gradient(90deg, #e2e8f0 1px, transparent 1px)',
                  backgroundSize: '24px 24px',
                }}
                onClick={() => {
                  setSelectedNodeId(null);
                  setSelectedEdgeId(null);
                  setConnectionDrag(null);
                  setHoverAnchor(null);
                }}
                onDoubleClick={(e) => {
                  const target = e.target as HTMLElement;
                  if (target.closest('.workflow-node, .anchor-btn')) return;
                  if (!canvasInnerRef.current || !canvasScrollRef.current) return;
                  const rect = canvasInnerRef.current.getBoundingClientRect();
                  const scrollLeft = canvasScrollRef.current.scrollLeft;
                  const scrollTop = canvasScrollRef.current.scrollTop;
                  const x = e.clientX - rect.left + scrollLeft;
                  const y = e.clientY - rect.top + scrollTop;
                  handleAddAgent({
                    x: Math.max(10, Math.min(CANVAS_WIDTH - 210, x - 95)),
                    y: Math.max(10, Math.min(CANVAS_HEIGHT - 170, y - 85)),
                  });
                }}
              >
                <div style={{ position: 'absolute', top: 12, left: 12, zIndex: 30 }}>
                  <Tooltip label="Add New Node">
                    <Button
                      size="xs"
                      leftIcon={<IconPlus size="0.95rem" />}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleAddAgent(getViewportAddPosition());
                      }}
                    >
                      Node
                    </Button>
                  </Tooltip>
                </div>
                <svg width={CANVAS_WIDTH} height={CANVAS_HEIGHT} style={{ position: 'absolute', inset: 0 }}>
                  <defs>
                    <marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="strokeWidth">
                      <path d="M0,0 L8,4 L0,8 z" fill="#64748b" />
                    </marker>
                  </defs>
                  {workflow.edges.map((edge) => {
                    const geo = edgeGeometry(edge);
                    if (!geo) return null;
                    const isSelected = selectedEdgeId === edge.id;
                    return (
                      <g key={edge.id}>
                        <path
                          d={geo.path}
                          fill="none"
                          stroke={isSelected ? '#2563eb' : '#64748b'}
                          strokeWidth={isSelected ? 3 : 2}
                          markerEnd="url(#arrow)"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedEdgeId(edge.id);
                            setSelectedNodeId(null);
                          }}
                          style={{ cursor: 'pointer' }}
                        />
                        {isSelected && (
                          <g>
                            <rect x={geo.midX - 10} y={geo.midY - 10} width={20} height={20} rx={5} fill="#fff" stroke="#ef4444" />
                            <text
                              x={geo.midX}
                              y={geo.midY + 4}
                              textAnchor="middle"
                              fill="#ef4444"
                              fontSize={13}
                              style={{ cursor: 'pointer', userSelect: 'none' }}
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedEdgeId(edge.id);
                                removeSelectedEdge();
                              }}
                            >
                              ×
                            </text>
                          </g>
                        )}
                      </g>
                    );
                  })}
                  {connectionDrag ? (
                    <path
                      d={`M ${connectionDrag.sourcePoint.x} ${connectionDrag.sourcePoint.y} C ${connectionDrag.sourcePoint.x + 80} ${connectionDrag.sourcePoint.y}, ${connectionDrag.mousePoint.x - 80} ${connectionDrag.mousePoint.y}, ${connectionDrag.mousePoint.x} ${connectionDrag.mousePoint.y}`}
                      fill="none"
                      stroke="#f59e0b"
                      strokeWidth={2}
                      strokeDasharray="6 4"
                    />
                  ) : null}
                </svg>

                {workflow.nodes.map((node) => {
                  const isSelected = selectedNodeId === node.id;
                  const isRoundNode = node.type !== 'agent';
                  const circleBg = node.type === 'start' ? '#dcfce7' : '#ede9fe';
                  const circleBorder = node.type === 'start' ? '#22c55e' : '#8b5cf6';
                  return (
                    <Paper
                      key={node.id}
                      className="workflow-node"
                      ref={(el) => {
                        if (el) nodeRefs.current.set(node.id, el);
                        else nodeRefs.current.delete(node.id);
                      }}
                      shadow="xs"
                      p="xs"
                      radius="md"
                      withBorder
                      style={{
                        position: 'absolute',
                        left: node.position.x,
                        top: node.position.y,
                        width: isRoundNode ? 96 : 190,
                        minHeight: isRoundNode ? 96 : 100,
                        zIndex: isSelected ? 10 : 4,
                        borderColor: isSelected ? '#2563eb' : (isRoundNode ? circleBorder : undefined),
                        background: isRoundNode ? circleBg : '#fff',
                        cursor: 'grab',
                        overflow: 'visible',
                        borderRadius: isRoundNode ? 999 : undefined,
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'center',
                      }}
                      onMouseDown={(e) => {
                        if (isInteractiveNodeTarget(e.target)) return;
                        onNodeMouseDown(e, node);
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedNodeId(node.id);
                        setSelectedEdgeId(null);
                      }}
	                      onDoubleClick={(e) => {
	                        e.stopPropagation();
	                      }}
	                    >
	                      <Group position="apart" mb={isRoundNode ? 0 : 4}>
	                        {node.type === 'agent' && editingNodeId === node.id ? (
	                          <TextInput
	                            size="xs"
	                            value={editingNodeTitle}
	                            onChange={(e) => setEditingNodeTitle(e.currentTarget.value)}
	                            onBlur={commitEditingNodeTitle}
	                            onKeyDown={(e) => {
	                              if (e.key === 'Enter') {
	                                e.preventDefault();
	                                commitEditingNodeTitle();
	                              } else if (e.key === 'Escape') {
	                                e.preventDefault();
	                                cancelEditingNodeTitle();
	                              }
	                            }}
	                            autoFocus
	                            styles={{ input: { fontWeight: 700 } }}
	                            style={{ flex: 1 }}
	                          />
	                        ) : (
	                          <Text
	                            fw={700}
	                            size="sm"
	                            ta={isRoundNode ? 'center' : 'left'}
	                            style={{
	                              width: isRoundNode ? '100%' : undefined,
	                              flex: isRoundNode ? undefined : 1,
	                              cursor: node.type === 'agent' ? 'text' : 'default',
	                            }}
	                            onClick={(e) => {
	                              e.stopPropagation();
	                              if (node.type === 'agent') startEditingNodeTitle(node);
	                            }}
	                          >
	                            {getNodeLabel(node)}
	                          </Text>
	                        )}
	                        {!isRoundNode ? (
	                          <Badge size="xs" color={node.type === 'agent' ? 'blue' : node.type === 'start' ? 'green' : 'grape'}>
	                            {node.type}
	                          </Badge>
	                        ) : null}
                      </Group>

	                      {node.type === 'agent' ? (
	                        <Stack spacing={6}>
                            <div
                              data-node-interactive
                              onMouseDown={(e) => e.stopPropagation()}
                              onClick={(e) => e.stopPropagation()}
                            >
	                          <Select
	                            size="xs"
	                            value={node.data?.provider_id || ''}
	                            onChange={(value) => setAgentField(node.id, 'provider_id', value || '')}
                              data={providers.map((p) => ({ value: p.id, label: p.name }))}
                              placeholder="Provider"
                              searchable
                            />
                          </div>
                          <div
                            data-node-interactive
                            onMouseDown={(e) => e.stopPropagation()}
                            onClick={(e) => e.stopPropagation()}
                          >
                            <TextInput
                              size="xs"
                              value={node.data?.skill || ''}
                              onChange={(e) => setAgentField(node.id, 'skill', e.currentTarget.value)}
                              placeholder="Skill"
                              list="workflow-skills-list"
                            />
                          </div>
                          <div
                            data-node-interactive
                            onMouseDown={(e) => e.stopPropagation()}
                            onClick={(e) => e.stopPropagation()}
                          >
                            <Textarea
                              size="xs"
                              value={node.data?.responsibility || ''}
                              onChange={(e) => setAgentField(node.id, 'responsibility', e.currentTarget.value)}
                              placeholder="Describe the role and focus of this agent"
                              minRows={2}
                              autosize
                              maxRows={4}
                            />
                          </div>
                        </Stack>
                      ) : null}

                      {getNodeAnchors(node).map((anchor) => {
                        const pos = getAnchorOffset(node, anchor.side);
                        const isHoveredAnchor =
                          hoverAnchor?.nodeId === node.id && hoverAnchor.side === anchor.side;
                        const isValidDropTarget = Boolean(
                          connectionDrag &&
                          isHoveredAnchor &&
                          resolveDirectedEdge(
                            connectionDrag.sourceNodeId,
                            connectionDrag.sourceKind,
                            node.id,
                            anchor.kind,
                          ),
                        );
                        const anchorBg = isValidDropTarget
                          ? '#22c55e'
                          : (connectionDrag?.sourceNodeId === node.id ? '#fbbf24' : '#ffffff');
                        return (
                        <button
                          key={anchor.key}
                          type="button"
                          className="anchor-btn"
                          onMouseDown={(e) => {
                            handleAnchorMouseDown(e, node.id, anchor.kind, anchor.side);
                          }}
                          onMouseUp={(e) => {
                            handleAnchorMouseUp(e, node.id, anchor.kind, anchor.side);
                          }}
                          onMouseEnter={() => {
                            if (!connectionDrag) return;
                            setHoverAnchor({ nodeId: node.id, side: anchor.side, kind: anchor.kind });
                          }}
                          onMouseLeave={() => {
                            setHoverAnchor((prev) => {
                              if (!prev) return prev;
                              if (prev.nodeId === node.id && prev.side === anchor.side) return null;
                              return prev;
                            });
                          }}
                          style={{
                            position: 'absolute',
                            width: 28,
                            height: 28,
                            borderRadius: '50%',
                            border: 'none',
                            background: 'transparent',
                            left: pos.x - 14,
                            top: pos.y - 14,
                            padding: 0,
                            cursor: 'crosshair',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                          }}
                        >
                          <span
                            style={{
                              width: 14,
                              height: 14,
                              borderRadius: '50%',
                              border: isValidDropTarget ? '2px solid #166534' : '1px solid #64748b',
                              background: anchorBg,
                              display: 'block',
                              pointerEvents: 'none',
                            }}
                          />
                        </button>
                        );
                      })}
                    </Paper>
                  );
                })}
              </div>
            </div>
          </div>

          {inspectorVisible ? (
          <aside style={{ width: inspectorWidth, minWidth: inspectorWidth, borderLeft: '1px solid #e5e7eb', overflowY: 'auto', position: 'relative', transition: isInspectorResizing ? 'none' : 'width 150ms ease' }}>
            <div
              onMouseDown={(e) => { e.preventDefault(); setIsInspectorResizing(true); }}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: 4,
                height: '100%',
                cursor: 'col-resize',
                backgroundColor: isInspectorResizing ? '#228be6' : 'transparent',
                zIndex: 100,
              }}
            />
            <div style={{ padding: 12 }}>
            <Group position="apart" mb={8}>
              <Text fw={700}>Inspector</Text>
              <Tooltip label="Hide Inspector">
                <ActionIcon variant="light" onClick={() => setInspectorVisible(false)}>
                  <IconChevronsRight size="1rem" />
                </ActionIcon>
              </Tooltip>
            </Group>
            {selectedNode ? (
              <Stack spacing={8}>
                <Text size="sm">Node ID: {selectedNode.id}</Text>
                <Text size="sm">Type: {selectedNode.type}</Text>
                <Text size="sm">Position: ({Math.round(selectedNode.position.x)}, {Math.round(selectedNode.position.y)})</Text>
	                {selectedNode.type === 'agent' ? (
	                  <>
	                    <Divider />
	                    <TextInput
	                      label="Name"
	                      size="sm"
	                      value={selectedNode.data?.title || ''}
	                      onChange={(e) => setAgentField(selectedNode.id, 'title', e.currentTarget.value)}
	                    />
	                    <Select
	                      label="AI Provider"
	                      size="sm"
                      value={selectedNode.data?.provider_id || ''}
                      onChange={(value) => setAgentField(selectedNode.id, 'provider_id', value || '')}
                      data={providers.map((p) => ({ value: p.id, label: p.name }))}
                      searchable
                    />
                    <TextInput
                      label="Skill"
                      size="sm"
                      value={selectedNode.data?.skill || ''}
                      onChange={(e) => setAgentField(selectedNode.id, 'skill', e.currentTarget.value)}
                      list="workflow-skills-list"
                    />
                    <Textarea
                      label="Responsibility"
                      size="sm"
                      value={selectedNode.data?.responsibility || ''}
                      onChange={(e) => setAgentField(selectedNode.id, 'responsibility', e.currentTarget.value)}
                      placeholder="Describe the role and focus of this agent"
                      minRows={3}
                      autosize
                      style={{ width: '100%' }}
                    />
                    {selectedNodeHasMissingSkill ? (
                      <Paper p="xs" withBorder style={{ borderColor: '#ef4444', background: '#fef2f2' }}>
                        <Text size="xs" c="red" fw={700}>Validation Error: skill or responsibility is required</Text>
                      </Paper>
                    ) : null}
                    <Button
                      color="red"
                      variant="light"
                      leftIcon={<IconTrash size="0.9rem" />}
                      onClick={removeSelectedNode}
                    >
                      Delete Node
                    </Button>
                  </>
                ) : null}
              </Stack>
            ) : (
              <Text size="sm" c="dimmed">Select a node or edge.</Text>
            )}

            <Divider my="md" />
            <Group position="apart" mb={6}>
              <Text fw={700}>Validation</Text>
              {selectedEdgeId ? (
                <ActionIcon color="red" variant="light" onClick={removeSelectedEdge} title="Delete selected edge">
                  <IconTrash size="0.95rem" />
                </ActionIcon>
              ) : null}
            </Group>
            {errors.length === 0 ? (
              <Text size="sm" c="dimmed">No validation errors.</Text>
            ) : (
              <Stack spacing={8}>
                {errors.map((err, idx) => (
                  <Paper key={`${err.rule}-${idx}`} p="xs" withBorder>
                    <Text size="xs" fw={700}>{err.rule}</Text>
                    <Text size="xs">{err.message}</Text>
                    {(err.node_ids && err.node_ids.length > 0) ? <Text size="xs" c="dimmed">Nodes: {err.node_ids.join(', ')}</Text> : null}
                    {(err.edge_ids && err.edge_ids.length > 0) ? <Text size="xs" c="dimmed">Edges: {err.edge_ids.join(', ')}</Text> : null}
                  </Paper>
                ))}
              </Stack>
            )}
            </div>
          </aside>
          ) : null}
          {!inspectorVisible ? (
            <Tooltip label="Show Inspector">
              <ActionIcon
                variant="filled"
                color="blue"
                onClick={() => setInspectorVisible(true)}
                style={{ position: 'absolute', top: 10, right: 10, zIndex: 20 }}
              >
                <IconChevronsLeft size="1rem" />
              </ActionIcon>
            </Tooltip>
          ) : null}
        </main>
      </div>

      <datalist id="workflow-skills-list">
        {skills.map((s) => (
          <option key={s} value={s} />
        ))}
      </datalist>
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
