"use client";

import ReactMarkdown from "react-markdown";
import { useRouter } from "next/router";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  ConsoleEvent,
  ConsoleEventCategory,
  DocumentPayload,
  Stage,
  Toast,
} from "../../libs/dev-swarm/types";
import { getStageConfig } from "../../libs/dev-swarm/stages";
import type { StageConfig } from "../../libs/dev-swarm/stages";
import {
  syncProject,
  readDocument,
  writeDocument,
  deleteDocument,
  toggleSkip,
  startAgentRun,
  stopAgentRun,
  createEventSource,
  fetchAgents,
} from "../../libs/dev-swarm/api";
import * as prompts from "../../libs/dev-swarm/prompts";
import { apiUrl } from "../../libs/api-base";
import {
  RefreshCw,
  Play,
  Square,
  Trash2,
  Save,
  Folder,
  FileText,
  FileCode,
  Terminal,
  CheckCircle2,
  AlertCircle,
  Archive,
  Layers,
  Layout,
  Settings,
  Database,
  Globe,
  Code2,
  Box,
  ChevronLeft,
  Search,
  PenTool,
  Rocket,
  Cpu,
  Eraser,
  ExternalLink,
  Eye,
  Edit3,
  Clock,
  SkipForward,
  File,
  XCircle,
  Menu,
  ChevronRight,
  ArrowRight
} from "../../libs/dev-swarm/icons";

const STATUS_ICONS: Record<Stage["status"], React.ElementType> = {
  "not-started": Clock,
  "in-progress": Play,
  completed: CheckCircle2,
  skipped: SkipForward,
  error: XCircle,
};

const STATUS_STYLES: Record<Stage["status"], string> = {
  "not-started": "text-[var(--color-text-secondary)]",
  "in-progress": "text-[var(--color-accent-cyan)]",
  completed: "text-[var(--color-success)]",
  skipped: "text-[var(--color-warning)]",
  error: "text-[var(--color-error)]",
};

const STAGE_GROUPS = [
  { title: "Discovery & Planning", stageIds: ["00", "01", "02"], icon: Search },
  { title: "Product Definition", stageIds: ["03", "04", "05"], icon: Box },
  { title: "Design", stageIds: ["06"], icon: PenTool },
  { title: "Technical Planning", stageIds: ["07", "08"], icon: Database },
  { title: "Implementation", stageIds: ["09", "10"], icon: Code2 },
  { title: "Deployment", stageIds: ["11"], icon: Rocket },
  { title: "Archive", stageIds: ["99"], icon: Archive },
];

export default function Home() {
  const router = useRouter();
  // --- Core state ---
  const [stages, setStages] = useState<Stage[]>([]);
  const [selectedStageId, setSelectedStageId] = useState<string>("00");
  const [loading, setLoading] = useState(true);
  const [activeProgressStep, setActiveProgressStep] = useState<string>("");
  const [agents, setAgents] = useState<{ id: string; name: string }[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string>("");

  // --- Document state ---
  const [currentPath, setCurrentPath] = useState<string>("");
  const [folderStack, setFolderStack] = useState<string[]>([]);
  const [selectedSprintFolder, setSelectedSprintFolder] = useState<string>("");
  const [documentPayload, setDocumentPayload] = useState<DocumentPayload | null>(null);
  const [editorContent, setEditorContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [markdownView, setMarkdownView] = useState<"editor" | "preview">("editor");

  // --- AI Agent log state ---
  const [consoleEvents, setConsoleEvents] = useState<ConsoleEvent[]>([]);
  const [runId, setRunId] = useState<string | null>(null);
  const [agentRunning, setAgentRunning] = useState(false);
  const [isPinned, setIsPinned] = useState(true);
  const consoleRef = useRef<HTMLDivElement>(null);

  // --- Toast ---
  const [toast, setToast] = useState<Toast | null>(null);

  const showToast = useCallback((message: string, variant: Toast["variant"] = "error") => {
    setToast({ message, variant });
  }, []);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 4000);
    return () => clearTimeout(t);
  }, [toast]);

  // --- Selected stage & config ---
  const selectedStage = useMemo(
    () => stages.find((s) => s.stageId === selectedStageId),
    [stages, selectedStageId]
  );
  const stageConfig = useMemo(
    () => getStageConfig(selectedStageId),
    [selectedStageId]
  );

  // --- Sync / Fetch ---
  const doSync = useCallback(async () => {
    setLoading(true);
    try {
      const data = await syncProject();
      setStages(data.stages);
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    void doSync();
    void fetchAgents().then((list) => {
      setAgents(list);
      if (list.length > 0 && !selectedAgent) {
        setSelectedAgent(list[0].id);
      }
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doSync]);

  // --- Auto-detect progress step ---
  const detectProgressStep = useCallback(
    (stage: Stage | undefined, config: StageConfig | undefined) => {
      if (!stage || !config) return "";
      const files = stage.files;
      const folder = config.folder;

      if (config.type === "init-ideas") {
        const hasReadme = files.some((f) => f === `${folder}/README.md`);
        const hasOtherFiles = files.some(
          (f) => f.startsWith(`${folder}/`) && f !== `${folder}/README.md` && !f.endsWith("SKIP.md")
        );
        if (hasOtherFiles) return "stage-files";
        if (hasReadme) return "proposal";
        return "init";
      }

      if (config.type === "sprints") {
        const hasReadme = files.some((f) => f === `${folder}/README.md`);
        const hasPlan = files.some((f) => f === `${folder}/development-plan.md`);
        const hasSprintFolders = files.some(
          (f) =>
            f.startsWith(`${folder}/`) &&
            f.split("/").length > 2 &&
            !f.endsWith("SKIP.md")
        );
        if (hasSprintFolders) return "backlogs";
        if (hasPlan) return "plan";
        if (hasReadme) return "proposal";
        return "proposal";
      }

      // Standard, research, ux, devops
      const hasReadme = files.some((f) => f === `${folder}/README.md`);
      const hasOtherFiles = files.some(
        (f) =>
          f.startsWith(`${folder}/`) &&
          f !== `${folder}/README.md` &&
          !f.endsWith("SKIP.md")
      );
      if (hasOtherFiles) return "stage-files";
      if (hasReadme) return "proposal";
      return "proposal";
    },
    []
  );

  useEffect(() => {
    const step = detectProgressStep(selectedStage, stageConfig);
    setActiveProgressStep(step);
  }, [selectedStage, stageConfig, detectProgressStep]);

  // --- File helpers ---
  const stageFiles = useMemo(() => {
    if (!selectedStage || !stageConfig) return [];
    const folder = stageConfig.folder;
    return selectedStage.files
      .filter((f) => f.startsWith(`${folder}/`) && !f.endsWith("SKIP.md"))
      .map((f) => f.slice(folder.length + 1)); // relative to stage folder
  }, [selectedStage, stageConfig]);

  // Check if stage folder has no stage files to display (only README.md or no .md files at all)
  const hasOnlyReadme = useMemo(() => {
    if (!selectedStage || !stageConfig) return true;
    const folder = stageConfig.folder;
    const mdFiles = selectedStage.files.filter(
      (f) =>
        f.startsWith(`${folder}/`) &&
        f.endsWith(".md") &&
        !f.endsWith("SKIP.md")
    );
    // Disable if no .md files, or only README.md
    return mdFiles.length === 0 || (mdFiles.length === 1 && mdFiles[0] === `${folder}/README.md`);
  }, [selectedStage, stageConfig]);

  // Check if README.md exists in stage folder (for init-ideas Proposal step)
  const hasReadme = useMemo(() => {
    if (!selectedStage || !stageConfig) return false;
    const folder = stageConfig.folder;
    return selectedStage.files.some((f) => f === `${folder}/README.md`);
  }, [selectedStage, stageConfig]);

  // Check if development-plan.md exists (for Sprints Plan step)
  const hasDevelopmentPlan = useMemo(() => {
    if (!selectedStage || !stageConfig) return false;
    const folder = stageConfig.folder;
    return selectedStage.files.some((f) => f === `${folder}/development-plan.md`);
  }, [selectedStage, stageConfig]);

  // Check if sprint folders exist (for Sprints Backlogs step)
  const hasSprintFolders = useMemo(() => {
    if (!stageConfig || stageConfig.type !== "sprints") return false;
    const folder = stageConfig.folder;
    for (const f of selectedStage?.files || []) {
      if (!f.startsWith(`${folder}/`)) continue;
      const rel = f.slice(folder.length + 1);
      if (rel === "README.md" || rel === "development-plan.md") continue;
      if (rel.includes("/")) return true;
    }
    return false;
  }, [selectedStage, stageConfig]);

  // Get items in current browsing folder (files + subfolders)
  const currentFolderItems = useMemo(() => {
    const prefix = folderStack.length > 0 ? folderStack.join("/") + "/" : "";
    const items: { name: string; isFolder: boolean; fullPath: string; relativePath: string }[] = [];
    const seenFolders = new Set<string>();

    for (const rel of stageFiles) {
      if (!rel.startsWith(prefix)) continue;
      const rest = rel.slice(prefix.length);
      const slashIdx = rest.indexOf("/");
      if (slashIdx === -1) {
        // It's a file in this directory
        items.push({
          name: rest,
          isFolder: false,
          fullPath: `${stageConfig!.folder}/${rel}`,
          relativePath: rel,
        });
      } else {
        // It's in a subfolder
        const folderName = rest.slice(0, slashIdx);
        if (!seenFolders.has(folderName)) {
          seenFolders.add(folderName);
          items.push({
            name: folderName,
            isFolder: true,
            fullPath: "", // folders don't have a single path
            relativePath: `${prefix}${folderName}`,
          });
        }
      }
    }

    // Sort: README.md first, then folders, then files
    items.sort((a, b) => {
      if (a.name === "README.md") return -1;
      if (b.name === "README.md") return 1;
      if (a.isFolder && !b.isFolder) return -1;
      if (!a.isFolder && b.isFolder) return 1;
      return a.name.localeCompare(b.name);
    });

    return items;
  }, [stageFiles, folderStack, stageConfig]);

  // Get research subfolders (for Tech Research stage)
  const researchFolders = useMemo(() => {
    if (!stageConfig || stageConfig.type !== "research") return [];
    const folder = stageConfig.folder;
    const folders = new Set<string>();
    for (const f of selectedStage?.files || []) {
      if (!f.startsWith(`${folder}/`)) continue;
      const rel = f.slice(folder.length + 1);
      const slashIdx = rel.indexOf("/");
      if (slashIdx !== -1) {
        const sub = rel.slice(0, slashIdx);
        if (sub !== "README.md" && !sub.endsWith(".md") && !sub.endsWith(".html")) {
          folders.add(sub);
        }
      }
    }
    return Array.from(folders).sort();
  }, [selectedStage, stageConfig]);

  // Get UX mockup subfolder
  const uxMockupFolder = useMemo(() => {
    if (!stageConfig || stageConfig.type !== "ux") return null;
    const folder = stageConfig.folder;
    const folders = new Set<string>();
    for (const f of selectedStage?.files || []) {
      if (!f.startsWith(`${folder}/`)) continue;
      const rel = f.slice(folder.length + 1);
      const slashIdx = rel.indexOf("/");
      if (slashIdx !== -1) {
        folders.add(rel.slice(0, slashIdx));
      }
    }
    // Look for a mockup folder (common patterns)
    for (const sub of folders) {
      if (sub.toLowerCase().includes("mockup") || sub.toLowerCase().includes("ui-preview")) {
        return sub;
      }
    }
    return folders.size > 0 ? Array.from(folders)[0] : null;
  }, [selectedStage, stageConfig]);

  // Sprint folders for Sprints stage
  const sprintFolders = useMemo(() => {
    if (!stageConfig || stageConfig.type !== "sprints") return [];
    const folder = stageConfig.folder;
    const folders = new Set<string>();
    for (const f of selectedStage?.files || []) {
      if (!f.startsWith(`${folder}/`)) continue;
      const rel = f.slice(folder.length + 1);
      if (rel === "README.md" || rel === "development-plan.md") continue;
      const slashIdx = rel.indexOf("/");
      if (slashIdx !== -1) {
        folders.add(rel.slice(0, slashIdx));
      }
    }
    return Array.from(folders).sort();
  }, [selectedStage, stageConfig]);

  // Dynamic progress steps (for research/ux/sprints)
  const dynamicProgressSteps = useMemo(() => {
    if (!stageConfig) return [];
    const base = [...stageConfig.progressSteps];

    if (stageConfig.type === "research" && researchFolders.length > 0) {
      for (const rf of researchFolders) {
        base.push({ key: `research:${rf}`, label: rf });
      }
    }

    if (stageConfig.type === "ux" && uxMockupFolder) {
      base.push({ key: "ui-mockup", label: "UI Mockup" });
    }

    return base;
  }, [stageConfig, researchFolders, uxMockupFolder]);

  // --- Document loading ---
  const loadDocument = useCallback(
    async (path: string) => {
      try {
        const doc = await readDocument(path);
        setDocumentPayload(doc);
        setCurrentPath(path);
        if (doc.contentType === "text/markdown") {
          setEditorContent(doc.content);
        }
      } catch (err) {
        showToast(err instanceof Error ? err.message : "Failed to load document");
      }
    },
    [showToast]
  );

  // Auto-load README.md when stage files are shown
  useEffect(() => {
    if (!stageConfig || !selectedStage) return;
    const folder = stageConfig.folder;

    // Only auto-load on stage-files, research, or ui-mockup steps
    if (
      activeProgressStep === "stage-files" ||
      activeProgressStep.startsWith("research:") ||
      activeProgressStep === "ui-mockup"
    ) {
      const readmePath = `${folder}/README.md`;
      if (selectedStage.files.includes(readmePath)) {
        void loadDocument(readmePath);
      }
    } else if (activeProgressStep === "init") {
      void loadDocument("ideas.md");
    } else if (activeProgressStep === "backlogs") {
      if (selectedSprintFolder) {
        const sprintReadme = `${stageConfig.folder}/${selectedSprintFolder}/README.md`;
        if (selectedStage.files.includes(sprintReadme)) {
          void loadDocument(sprintReadme);
        } else {
          setDocumentPayload(null);
          setCurrentPath("");
          setEditorContent("");
        }
      } else {
        setDocumentPayload(null);
        setCurrentPath("");
        setEditorContent("");
      }
    } else if (activeProgressStep === "proposal") {
      const readmePath = `${folder}/README.md`;
      if (selectedStage.files.includes(readmePath)) {
        void loadDocument(readmePath);
      } else {
        setDocumentPayload(null);
        setCurrentPath("");
        setEditorContent("");
      }
    } else if (activeProgressStep === "plan") {
      const planPath = `${stageConfig.folder}/development-plan.md`;
      if (selectedStage.files.includes(planPath)) {
        void loadDocument(planPath);
      }
    } else {
      setDocumentPayload(null);
      setCurrentPath("");
      setEditorContent("");
    }
    setFolderStack([]);
    if (activeProgressStep !== "backlogs") {
      setSelectedSprintFolder("");
    }
  }, [activeProgressStep, selectedStage, stageConfig, loadDocument, selectedSprintFolder]);

  // --- Stage change: reset ---
  useEffect(() => {
    setDocumentPayload(null);
    setCurrentPath("");
    setEditorContent("");
    setFolderStack([]);
    setSelectedSprintFolder("");
  }, [selectedStageId]);

  // --- Save document ---
  const handleSave = useCallback(async () => {
    if (!documentPayload || documentPayload.contentType !== "text/markdown") return;
    setSaving(true);
    try {
      const doc = await writeDocument(documentPayload.path, editorContent);
      setDocumentPayload(doc);
      showToast("Saved successfully", "success");
      await doSync();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }, [documentPayload, editorContent, showToast, doSync]);

  // --- Delete document ---
  const handleDelete = useCallback(async () => {
    if (!documentPayload) return;
    if (documentPayload.path.endsWith("README.md")) return;
    try {
      await deleteDocument(documentPayload.path);
      setDocumentPayload(null);
      setCurrentPath("");
      setEditorContent("");
      showToast("Deleted successfully", "success");
      await doSync();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Failed to delete");
    }
  }, [documentPayload, showToast, doSync]);

  // --- AI Agent execution ---
  const hasAgent = useMemo(
    () => agents.some((agent) => agent.id === selectedAgent),
    [agents, selectedAgent]
  );

  const runAgent = useCallback(
    async (prompt: string) => {
      if (!selectedStage) return;
      if (!hasAgent) {
        showToast("No agent configured. Please add an agent in agents.json.");
        return;
      }
      setConsoleEvents([]);
      setAgentRunning(true);
      setIsPinned(true);
      try {
        const data = await startAgentRun(selectedStage.stageId, prompt, selectedAgent);
        setRunId(data.runId);
      } catch (err) {
        showToast(err instanceof Error ? err.message : "Failed to start agent");
        setAgentRunning(false);
      }
    },
    [selectedStage, selectedAgent, hasAgent, showToast]
  );

  const handleInterrupt = useCallback(async () => {
    try {
      await stopAgentRun();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Failed to stop agent");
    }
  }, [showToast]);

  // --- SSE streaming ---
  useEffect(() => {
    if (!runId) return;
    const source = createEventSource(runId);

    const handle = (category: ConsoleEventCategory) => {
      source.addEventListener(category, (event: Event) => {
        const me = event as MessageEvent;
        if (!me.data) return;
        try {
          const payload = JSON.parse(me.data) as {
            timestamp: string;
            category: ConsoleEventCategory;
            message: string;
          };
          setConsoleEvents((prev) => [
            ...prev,
            {
              id: `${payload.timestamp}-${prev.length}`,
              timestamp: payload.timestamp,
              category,
              message: payload.message,
            },
          ]);
          // Check if run ended
          if (
            category === "status" &&
            ["succeeded", "failed", "stopped"].includes(payload.message)
          ) {
            setAgentRunning(false);
            // Auto-sync after agent completes
            void doSync();
          }
        } catch {
          // ignore parse errors
        }
      });
    };

    handle("system");
    handle("output");
    handle("stderr");
    handle("status");

    source.onerror = () => {
      source.close();
      setAgentRunning(false);
    };

    return () => source.close();
  }, [runId, doSync]);

  // Auto-scroll console
  useEffect(() => {
    if (isPinned && consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
    }
  }, [consoleEvents, isPinned]);

  // --- Render helpers ---
  const isSkipped = selectedStage?.hasSkipFile;

  const renderActionButton = (
    label: string,
    prompt: string,
    variant: "primary" | "secondary" | "danger" | "success" = "primary",
    icon: React.ElementType = Play
  ) => {
    const Icon = icon;
    const baseClass =
      variant === "primary"
        ? "bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white shadow-md shadow-[var(--color-accent)]/20"
        : variant === "danger"
          ? "bg-[var(--color-error)] hover:brightness-110 text-white shadow-md shadow-[var(--color-error)]/20"
          : variant === "success"
            ? "bg-[var(--color-success)] hover:brightness-110 text-slate-900 shadow-md shadow-[var(--color-success)]/20"
          : "border border-[var(--color-border)] text-[var(--color-text-primary)] hover:border-[var(--color-accent)] hover:text-[var(--color-accent)] bg-[var(--color-surface-alt)]";
    return (
        <button
          type="button"
          onClick={() => void runAgent(prompt)}
          disabled={agentRunning || !hasAgent}
          className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition disabled:opacity-50 disabled:cursor-not-allowed ${baseClass}`}
        >
          <Icon className="h-4 w-4" />
          <span>{label}</span>
        </button>
    );
  };

  // --- Stage content renderer ---
  const renderStageContent = () => {
    if (!selectedStage || !stageConfig) return null;

    // --- Skip state ---
    if (isSkipped) {
      return (
        <div className="flex flex-col items-center justify-center py-20 gap-6">
          <div className="rounded-full bg-[var(--color-surface-alt)] p-4">
             <SkipForward className="h-10 w-10 text-[var(--color-text-secondary)]" />
          </div>
          <div className="text-center">
             <p className="text-[var(--color-text-secondary)] text-lg font-medium">This stage is skipped</p>
             <p className="text-[var(--color-text-secondary)] text-sm opacity-60">You can unskip it to resume work</p>
          </div>
          <button
            type="button"
            onClick={async () => {
              await toggleSkip(selectedStage.stageId, false);
              await doSync();
            }}
            className="flex items-center gap-2 rounded-lg bg-[var(--color-accent)] px-6 py-3 text-sm font-semibold text-white hover:bg-[var(--color-accent-hover)] transition shadow-lg shadow-[var(--color-accent)]/20"
          >
            <Play className="h-4 w-4" />
            Unskip Stage
          </button>
        </div>
      );
    }

    // --- Archive ---
    if (stageConfig.type === "archive") {
      return (
        <div className="flex flex-col items-center justify-center py-20 gap-6">
          <div className="rounded-full bg-[var(--color-surface-alt)] p-4">
             <Archive className="h-10 w-10 text-[var(--color-text-secondary)]" />
          </div>
          <p className="text-[var(--color-text-secondary)] text-center max-w-md">
            Archive the current project to save its state and start fresh. This action cannot be easily undone via the UI.
          </p>
          {renderActionButton("Archive Project", prompts.archivePrompt(), "primary", Archive)}
        </div>
      );
    }

    // --- Init Ideas ---
    if (stageConfig.type === "init-ideas") {
      if (activeProgressStep === "init") {
        return (
          <div className="flex flex-1 min-h-0 flex-col gap-4">
            {renderEditor()}
            <div className="mt-auto flex gap-3 pt-4 border-t border-[var(--color-border)]">
              {renderActionButton("Refine Ideas", prompts.refineIdeasPrompt(), "secondary", Edit3)}
              {renderActionButton("Create Proposal", prompts.createProposalPrompt_InitIdeas(), "primary", FileText)}
            </div>
          </div>
        );
      }
      if (activeProgressStep === "proposal") {
        return (
          <div className="flex flex-1 min-h-0 flex-col gap-4">
            {renderEditor()}
            <div className="mt-auto flex gap-3 pt-4 border-t border-[var(--color-border)]">
              {markdownView === "editor" && (
                <button
                  type="button"
                  onClick={() => void handleSave()}
                  disabled={saving || !documentPayload}
                  className="flex items-center gap-2 rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm font-semibold text-white hover:bg-[var(--color-accent-hover)] transition disabled:opacity-50 shadow-md shadow-[var(--color-accent)]/20"
                >
                  <Save className="h-4 w-4" />
                  {saving ? "Saving..." : "Update"}
                </button>
              )}
              {renderActionButton("Create Files", prompts.createFilesPrompt_InitIdeas(), "primary", Folder)}
            </div>
          </div>
        );
      }
      // stage-files
      return (
        <div className="flex flex-1 min-h-0 flex-col gap-4">
          {renderFileBrowser()}
          {renderEditor()}
          <div className="mt-auto flex items-center justify-between gap-3 pt-4 border-t border-[var(--color-border)]">
            <div className="flex gap-3">{renderSaveDeleteButtons()}</div>
            {renderActionButton("Finalize Stage", prompts.finalizePrompt_InitIdeas(), "success", CheckCircle2)}
          </div>
        </div>
      );
    }

    // --- Standard stages ---
    if (stageConfig.type === "standard") {
      if (activeProgressStep === "proposal") {
        const hasReadme = selectedStage.files.includes(`${stageConfig.folder}/README.md`);
        return (
          <div className="flex flex-1 min-h-0 flex-col gap-4">
            {hasReadme && renderEditor()}
            <div className="mt-auto flex gap-3 pt-4 border-t border-[var(--color-border)]">
              {hasReadme && markdownView === "editor" && (
                <button
                  type="button"
                  onClick={() => void handleSave()}
                  disabled={saving || !documentPayload}
                  className="flex items-center gap-2 rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm font-semibold text-white hover:bg-[var(--color-accent-hover)] transition disabled:opacity-50 shadow-md shadow-[var(--color-accent)]/20"
                >
                  <Save className="h-4 w-4" />
                  {saving ? "Saving..." : "Update"}
                </button>
              )}
              {!hasReadme &&
                renderActionButton("Create Proposal", prompts.createProposalPrompt(stageConfig), "primary", FileText)}
              {hasReadme &&
                renderActionButton("Create Files", prompts.createFilesPrompt(stageConfig), "primary", Folder)}
            </div>
          </div>
        );
      }
      // stage-files
      return (
        <div className="flex flex-1 min-h-0 flex-col gap-4">
          {renderFileBrowser()}
          {renderEditor()}
          <div className="mt-auto flex items-center justify-between gap-3 pt-4 border-t border-[var(--color-border)]">
            <div className="flex gap-3">{renderSaveDeleteButtons()}</div>
            {renderActionButton("Finalize Stage", prompts.finalizePrompt(stageConfig), "success", CheckCircle2)}
          </div>
        </div>
      );
    }

    // --- Research (Tech Research) ---
    if (stageConfig.type === "research") {
      if (activeProgressStep === "proposal") {
        const hasReadme = selectedStage.files.includes(`${stageConfig.folder}/README.md`);
        return (
          <div className="flex flex-1 min-h-0 flex-col gap-4">
            {hasReadme && renderEditor()}
            <div className="mt-auto flex gap-3 pt-4 border-t border-[var(--color-border)]">
              {hasReadme && markdownView === "editor" && (
                <button
                  type="button"
                  onClick={() => void handleSave()}
                  disabled={saving || !documentPayload}
                  className="flex items-center gap-2 rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm font-semibold text-white hover:bg-[var(--color-accent-hover)] transition disabled:opacity-50 shadow-md shadow-[var(--color-accent)]/20"
                >
                  <Save className="h-4 w-4" />
                  {saving ? "Saving..." : "Update"}
                </button>
              )}
              {!hasReadme &&
                renderActionButton("Create Proposal", prompts.createProposalPrompt(stageConfig), "primary", FileText)}
              {hasReadme &&
                renderActionButton("Create Files", prompts.createFilesPrompt(stageConfig), "primary", Folder)}
            </div>
          </div>
        );
      }
      if (activeProgressStep === "stage-files") {
        return (
          <div className="flex flex-1 min-h-0 flex-col gap-4">
            {renderFileBrowser()}
            {renderEditor()}
            <div className="mt-auto flex gap-3 pt-4 border-t border-[var(--color-border)]">
              {renderSaveDeleteButtons()}
            </div>
          </div>
        );
      }
      if (activeProgressStep.startsWith("research:")) {
        const researchName = activeProgressStep.replace("research:", "");
        const isLast = researchFolders[researchFolders.length - 1] === researchName;
        return (
          <div className="flex flex-1 min-h-0 flex-col gap-4">
            {renderSubfolderBrowser(researchName)}
            {renderEditor()}
            <div className="mt-auto flex items-center justify-between gap-3 pt-4 border-t border-[var(--color-border)]">
              <div className="flex gap-3">
                {renderSaveDeleteButtons()}
                {renderActionButton("Run Research", prompts.researchPrompt(researchName), "primary", Search)}
              </div>
              {isLast && renderActionButton("Finalize Stage", prompts.finalizeResearchPrompt(), "success", CheckCircle2)}
            </div>
          </div>
        );
      }
    }

    // --- UX ---
    if (stageConfig.type === "ux") {
      if (activeProgressStep === "proposal") {
        const hasReadme = selectedStage.files.includes(`${stageConfig.folder}/README.md`);
        return (
          <div className="flex flex-1 min-h-0 flex-col gap-4">
            {hasReadme && renderEditor()}
            <div className="mt-auto flex gap-3 pt-4 border-t border-[var(--color-border)]">
              {hasReadme && markdownView === "editor" && (
                <button
                  type="button"
                  onClick={() => void handleSave()}
                  disabled={saving || !documentPayload}
                  className="flex items-center gap-2 rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm font-semibold text-white hover:bg-[var(--color-accent-hover)] transition disabled:opacity-50 shadow-md shadow-[var(--color-accent)]/20"
                >
                  <Save className="h-4 w-4" />
                  {saving ? "Saving..." : "Update"}
                </button>
              )}
              {!hasReadme &&
                renderActionButton("Create Proposal", prompts.createProposalPrompt(stageConfig), "primary", FileText)}
              {hasReadme &&
                renderActionButton("Create Files", prompts.createFilesPrompt(stageConfig), "primary", Folder)}
            </div>
          </div>
        );
      }
      if (activeProgressStep === "stage-files") {
        return (
          <div className="flex flex-1 min-h-0 flex-col gap-4">
            {renderFileBrowser()}
            {renderEditor()}
            <div className="mt-auto flex gap-3 pt-4 border-t border-[var(--color-border)]">
              {renderSaveDeleteButtons()}
            </div>
          </div>
        );
      }
      if (activeProgressStep === "ui-mockup") {
        return (
          <div className="flex flex-1 min-h-0 flex-col gap-4">
            {uxMockupFolder && renderSubfolderBrowser(uxMockupFolder)}
            {renderEditor()}
            <div className="mt-auto flex items-center justify-between gap-3 pt-4 border-t border-[var(--color-border)]">
              <div className="flex gap-3">
                {renderSaveDeleteButtons()}
                {renderActionButton("Generate Mockup", prompts.createMockupPrompt(), "primary", Layout)}
              </div>
              {renderActionButton("Finalize Stage", prompts.finalizeUxPrompt(), "success", CheckCircle2)}
            </div>
          </div>
        );
      }
    }

    // --- DevOps ---
    if (stageConfig.type === "devops") {
      if (activeProgressStep === "proposal") {
        const hasReadme = selectedStage.files.includes(`${stageConfig.folder}/README.md`);
        return (
          <div className="flex flex-1 min-h-0 flex-col gap-4">
            {hasReadme && renderEditor()}
            <div className="mt-auto flex gap-3 pt-4 border-t border-[var(--color-border)]">
              {hasReadme && markdownView === "editor" && (
                <button
                  type="button"
                  onClick={() => void handleSave()}
                  disabled={saving || !documentPayload}
                  className="flex items-center gap-2 rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm font-semibold text-white hover:bg-[var(--color-accent-hover)] transition disabled:opacity-50 shadow-md shadow-[var(--color-accent)]/20"
                >
                  <Save className="h-4 w-4" />
                  {saving ? "Saving..." : "Update"}
                </button>
              )}
              {!hasReadme &&
                renderActionButton("Create Proposal", prompts.createProposalPrompt(stageConfig), "primary", FileText)}
              {hasReadme &&
                renderActionButton("Create Files", prompts.createFilesPrompt(stageConfig), "primary", Folder)}
            </div>
          </div>
        );
      }
      // stage-files with Execute + Finalize
      return (
        <div className="flex flex-1 min-h-0 flex-col gap-4">
          {renderFileBrowser()}
          {renderEditor()}
          <div className="mt-auto flex items-center justify-between gap-3 pt-4 border-t border-[var(--color-border)]">
            <div className="flex gap-3">
              {renderSaveDeleteButtons()}
              {renderActionButton("ExecuteOps", prompts.executeDevOpsPrompt(stageConfig), "secondary", Terminal)}
            </div>
            {renderActionButton("Finalize Stage", prompts.finalizePrompt(stageConfig), "success", CheckCircle2)}
          </div>
        </div>
      );
    }

    // --- Sprints ---
    if (stageConfig.type === "sprints") {
      if (activeProgressStep === "proposal") {
        const hasReadme = selectedStage.files.includes(`${stageConfig.folder}/README.md`);
        return (
          <div className="flex flex-1 min-h-0 flex-col gap-4">
            {hasReadme && renderEditor()}
            <div className="mt-auto flex gap-3 pt-4 border-t border-[var(--color-border)]">
              {hasReadme && markdownView === "editor" && (
                <button
                  type="button"
                  onClick={() => void handleSave()}
                  disabled={saving || !documentPayload}
                  className="flex items-center gap-2 rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm font-semibold text-white hover:bg-[var(--color-accent-hover)] transition disabled:opacity-50 shadow-md shadow-[var(--color-accent)]/20"
                >
                  <Save className="h-4 w-4" />
                  {saving ? "Saving..." : "Update"}
                </button>
              )}
              {!hasReadme &&
                renderActionButton(
                  "Create Proposal",
                  prompts.createProposalPrompt(stageConfig),
                  "primary",
                  FileText
                )}
              {hasReadme &&
                renderActionButton("Create Plan", prompts.createSprintPlanPrompt(), "primary", Layers)}
            </div>
          </div>
        );
      }
      if (activeProgressStep === "plan") {
        return (
          <div className="flex flex-1 min-h-0 flex-col gap-4">
            {renderEditor()}
            <div className="mt-auto flex gap-3 pt-4 border-t border-[var(--color-border)]">
              {markdownView === "editor" && (
                <button
                  type="button"
                  onClick={() => void handleSave()}
                  disabled={saving || !documentPayload}
                  className="flex items-center gap-2 rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm font-semibold text-white hover:bg-[var(--color-accent-hover)] transition disabled:opacity-50 shadow-md shadow-[var(--color-accent)]/20"
                >
                  <Save className="h-4 w-4" />
                  {saving ? "Saving..." : "Update"}
                </button>
              )}
              {renderActionButton("Create Backlogs", prompts.createBacklogsPrompt(), "primary", Layers)}
            </div>
          </div>
        );
      }
      if (activeProgressStep === "backlogs") {
        return (
          <div className="flex flex-1 min-h-0 flex-col gap-4">
            {!selectedSprintFolder && (
              <div className="mb-2">
                {renderActionButton("Develop all sprints", prompts.developAllSprintsPrompt(), "secondary", Rocket)}
              </div>
            )}
            {selectedSprintFolder ? renderSprintFileBrowser() : renderSprintFolderList()}
            {selectedSprintFolder && renderEditor()}
            {selectedSprintFolder && (
              <div className="mt-auto flex gap-3 pt-4 border-t border-[var(--color-border)]">{renderSprintButtons()}</div>
            )}
          </div>
        );
      }
    }

    return null;
  };

  // --- Sub-renderers ---

  const renderEditor = () => {
    if (!documentPayload) {
      return (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-[var(--color-border)] bg-[var(--color-surface-alt)]/50 px-4 py-20 text-center text-sm text-[var(--color-text-secondary)]">
          <FileText className="h-10 w-10 mb-3 opacity-20" />
          <p>No document loaded.</p>
        </div>
      );
    }

    if (documentPayload.contentType === "text/html") {
      return (
        <div className="rounded-lg border border-[var(--color-border)] overflow-hidden bg-white shadow-sm">
          <div className="flex items-center justify-between bg-gray-100 px-3 py-1.5 border-b border-gray-200">
             <span className="text-xs text-gray-500 font-mono">{documentPayload.path}</span>
             <ExternalLink className="h-3 w-3 text-gray-400" />
          </div>
          <iframe
            title={`HTML preview: ${documentPayload.path}`}
            sandbox="allow-same-origin"
            className="h-[520px] w-full"
            src={`${apiUrl("/api/dev-swarm/html")}/${documentPayload.path
              .split("/")
              .map((seg) => encodeURIComponent(seg))
              .join("/")}`}
          />
        </div>
      );
    }

    return (
      <div className="flex flex-1 flex-col gap-3 min-h-0">
        <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 bg-[var(--color-surface-alt)] rounded-lg p-1 border border-[var(--color-border)]">
              <button
                type="button"
                onClick={() => setMarkdownView("editor")}
                className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest transition ${
                  markdownView === "editor"
                    ? "bg-[var(--color-surface)] text-[var(--color-accent)] shadow-sm"
                    : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
                }`}
              >
                <Edit3 className="h-3 w-3" />
                Editor
              </button>
              <button
                type="button"
                onClick={() => setMarkdownView("preview")}
                className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest transition ${
                  markdownView === "preview"
                    ? "bg-[var(--color-surface)] text-[var(--color-accent)] shadow-sm"
                    : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
                }`}
              >
                <Eye className="h-3 w-3" />
                Preview
              </button>
            </div>
            <span className="text-xs font-mono text-[var(--color-text-secondary)] opacity-50">{documentPayload.path}</span>
        </div>

        {markdownView === "editor" ? (
          <div className="flex flex-1 flex-col min-h-0 relative group">
            <textarea
              value={editorContent}
              onChange={(e) => setEditorContent(e.target.value)}
              className="min-h-0 flex-1 w-full resize-none rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-alt)] px-4 py-3 text-sm text-[var(--color-text-primary)] font-mono outline-none focus:border-[var(--color-focus)] focus:ring-1 focus:ring-[var(--color-focus)] transition shadow-inner"
            />
          </div>
        ) : (
          <div className="min-h-0 flex-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-alt)] p-6 overflow-auto shadow-inner">
            <div className="doc-markdown">
              <ReactMarkdown
                components={{
                  code: ({ className, children, ...props }) => {
                    const content = String(children).trim();
                    // Basic heuristic: check if it looks like a relative file path
                    // We only want to intercept if it matches a file/folder in the current stage
                    // or ends with .md/.html
                    
                    const isFileLike = content.match(/^[\w\-. /]+\.(md|html)$/) || (content.match(/^[\w\-. /]+$/) && !content.includes('\n'));

                    if (!isFileLike || !documentPayload?.path) {
                        return (
                            <code className={className} {...props}>
                                {children}
                            </code>
                        );
                    }

                    const currentDir = documentPayload.path.substring(0, documentPayload.path.lastIndexOf("/"));
                    let targetPath = content.startsWith("/") ? content.slice(1) : `${currentDir}/${content}`;
                    if (content.startsWith("./")) {
                        targetPath = `${currentDir}/${content.slice(2)}`;
                    }

                    // Check if file exists in stageFiles (which are relative to stage folder)
                    // stageConfig.folder e.g. "06-ux"
                    // targetPath e.g. "06-ux/README.md"
                    
                    if (stageConfig && targetPath.startsWith(stageConfig.folder + "/")) {
                        const relPath = targetPath.slice(stageConfig.folder.length + 1); // e.g. "README.md"
                        
                        // Check exact file match
                        const isFile = stageFiles.includes(relPath);
                        // Check folder match (does relPath/index.html exist?)
                        const isFolder = stageFiles.includes(`${relPath}/index.html`);

                        if (isFile) {
                            if (relPath.endsWith(".md")) {
                                return (
                                    <code 
                                        className={`${className} cursor-pointer hover:underline hover:text-[var(--color-accent)] transition-colors`}
                                        onClick={() => void loadDocument(targetPath)}
                                        title={`Open ${relPath}`}
                                        {...props}
                                    >
                                        {children}
                                    </code>
                                );
                            }
                            if (relPath.endsWith(".html")) {
                                return (
                                    <code 
                                        className={`${className} cursor-pointer hover:underline hover:text-[var(--color-accent)] transition-colors`}
                                        onClick={() => openStaticSite(relPath)}
                                        title={`Preview ${relPath}`}
                                        {...props}
                                    >
                                        {children}
                                    </code>
                                );
                            }
                        }
                        
                        if (isFolder) {
                             return (
                                <code 
                                    className={`${className} cursor-pointer hover:underline hover:text-[var(--color-accent)] transition-colors`}
                                    onClick={() => openStaticSite(`${relPath}/index.html`)}
                                    title={`Preview ${relPath}`}
                                    {...props}
                                >
                                    {children}
                                </code>
                            );
                        }
                    }

                    return (
                        <code className={className} {...props}>
                            {children}
                        </code>
                    );
                  },
                  a: ({ href, children }) => {
                    if (!href) return <span>{children}</span>;
                    const isExternal = href.startsWith("http") || href.startsWith("https");
                    
                    if (isExternal) {
                      return (
                        <a href={href} target="_blank" rel="noopener noreferrer">
                          {children}
                        </a>
                      );
                    }

                    // Handle internal file links
                    return (
                      <a
                        href={href}
                        onClick={(e) => {
                          e.preventDefault();
                          // Resolve path relative to current document location if possible
                          // But here we might just have simple filenames or relative paths
                          
                          // Heuristic:
                          // 1. If it ends with .html, openStaticSite
                          // 2. If it ends with .md, loadDocument
                          // 3. If it has no extension, assume folder -> openStaticSite(path/index.html)
                          
                          // We need to resolve against the current document's directory
                          // documentPayload.path e.g. "06-ux/README.md"
                          if (!documentPayload?.path) return;
                          
                          const currentDir = documentPayload.path.substring(0, documentPayload.path.lastIndexOf("/"));
                          // Simple resolve: strictly supports "./" or just filename, no ".." yet for simplicity
                          // or just basic concatenation
                          let targetPath = href.startsWith("/") ? href.slice(1) : `${currentDir}/${href}`;
                          
                          // Handle ./ prefix
                          if (href.startsWith("./")) {
                             targetPath = `${currentDir}/${href.slice(2)}`;
                          }

                          if (targetPath.toLowerCase().endsWith(".html")) {
                             // openStaticSite expects path relative to stage folder
                             // stageConfig.folder e.g. "06-ux"
                             // targetPath e.g. "06-ux/design-ui-preview.html"
                             if (stageConfig && targetPath.startsWith(stageConfig.folder + "/")) {
                                 const relPath = targetPath.slice(stageConfig.folder.length + 1);
                                 openStaticSite(relPath);
                             }
                          } else if (targetPath.toLowerCase().endsWith(".md")) {
                             void loadDocument(targetPath);
                          } else {
                             // Assume folder, append /index.html
                             // Check if it looks like a folder (no dot usually, or explicitly ends in /)
                             // For "html folder" case
                             let folderPath = targetPath;
                             if (!folderPath.endsWith("/")) folderPath += "/";
                             
                             if (stageConfig && folderPath.startsWith(stageConfig.folder + "/")) {
                                 const relPath = folderPath.slice(stageConfig.folder.length + 1) + "index.html";
                                 openStaticSite(relPath);
                             }
                          }
                        }}
                      >
                        {children}
                      </a>
                    );
                  },
                }}
              >
                {editorContent}
              </ReactMarkdown>
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderSaveDeleteButtons = () => {
    if (!documentPayload || documentPayload.contentType !== "text/markdown" || markdownView === "preview") return null;
    const isReadme = documentPayload.path.endsWith("README.md");
    return (
      <>
        <button
          type="button"
          onClick={() => void handleSave()}
          disabled={saving}
          className="flex items-center gap-2 rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm font-semibold text-white hover:bg-[var(--color-accent-hover)] transition disabled:opacity-50 shadow-md shadow-[var(--color-accent)]/20"
        >
          <Save className="h-4 w-4" />
          {saving ? "Saving..." : "Update"}
        </button>
        {!isReadme && (
          <button
            type="button"
            onClick={() => void handleDelete()}
            className="flex items-center gap-2 rounded-lg bg-[var(--color-surface-alt)] border border-[var(--color-error)] text-[var(--color-error)] px-4 py-2 text-sm font-semibold hover:bg-[var(--color-error)] hover:text-white transition"
          >
            <Trash2 className="h-4 w-4" />
            Delete
          </button>
        )}
      </>
    );
  };

  const openStaticSite = (relativePath: string) => {
    if (!stageConfig) return;
    const fullPath = `${stageConfig.folder}/${relativePath}`;
    const url = `${apiUrl("/api/dev-swarm/static")}/${fullPath
      .split("/")
      .map((seg) => encodeURIComponent(seg))
      .join("/")}`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  const renderFileBrowser = () => (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-3">
      {folderStack.length > 0 && (
        <button
          type="button"
          onClick={() => setFolderStack((prev) => prev.slice(0, -1))}
          className="mb-3 text-xs flex items-center gap-1 text-[var(--color-text-secondary)] hover:text-[var(--color-accent-cyan)] transition"
        >
          <ChevronLeft className="h-3 w-3" />
          Back
        </button>
      )}
      <div className="flex flex-wrap gap-2">
        {currentFolderItems.map((item) => {
          const isStaticFolder = item.isFolder && stageFiles.includes(`${item.relativePath}/index.html`);
          return (
            <button
              key={item.name}
              type="button"
              onClick={() => {
                if (item.isFolder) {
                  const indexPath = `${item.relativePath}/index.html`;
                  if (stageFiles.includes(indexPath)) {
                    openStaticSite(`${item.relativePath}/index.html`);
                  } else {
                    setFolderStack((prev) => [...prev, item.name]);
                  }
                } else if (item.name.toLowerCase().endsWith(".html")) {
                  openStaticSite(item.relativePath);
                } else {
                  void loadDocument(item.fullPath);
                }
              }}
              className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition border ${
                currentPath === item.fullPath
                  ? "bg-[var(--color-accent)] text-white border-[var(--color-accent)] shadow-md shadow-[var(--color-accent)]/10"
                  : item.isFolder
                    ? "bg-[var(--color-surface-alt)] text-[var(--color-text-primary)] border-[var(--color-border)] hover:border-[var(--color-accent)] hover:shadow-sm"
                    : "bg-transparent text-[var(--color-text-secondary)] border-transparent hover:bg-[var(--color-surface-alt)] hover:text-[var(--color-text-primary)]"
              }`}
            >
              {isStaticFolder ? (
                <Globe className={`h-4 w-4 ${currentPath === item.fullPath ? "text-white" : "text-[var(--color-accent-cyan)]"}`} />
              ) : item.isFolder ? (
                <Folder className={`h-4 w-4 ${currentPath === item.fullPath ? "text-white" : "text-[var(--color-accent-cyan)]"}`} />
              ) : item.name.toLowerCase().endsWith(".md") ? (
                <FileText className="h-4 w-4 opacity-70" />
              ) : item.name.toLowerCase().endsWith(".html") ? (
                <Globe className="h-4 w-4 text-[var(--color-accent-cyan)] opacity-70" />
              ) : (
                <File className="h-4 w-4 opacity-70" />
              )}
              <span className="truncate max-w-[140px]">{item.name}</span>
            </button>
          );
        })}
      </div>
    </div>
  );

  const renderSubfolderBrowser = (subfolder: string) => {
    if (!stageConfig || !selectedStage) return null;
    const prefix = `${stageConfig.folder}/${subfolder}/`;
    const items = selectedStage.files
      .filter((f) => f.startsWith(prefix) && (f.endsWith(".md") || f.endsWith(".html")))
      .map((f) => ({ name: f.slice(prefix.length), fullPath: f, relativePath: `${subfolder}/${f.slice(prefix.length)}` }));

    return (
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-3">
        <div className="mb-2 text-xs font-mono text-[var(--color-text-secondary)] uppercase tracking-wider flex items-center gap-2">
            <Folder className="h-3 w-3" />
            {subfolder}
        </div>
        <div className="flex flex-wrap gap-2">
            {items.map((item) => (
            <button
                key={item.fullPath}
                type="button"
                onClick={() => {
                  if (item.name.toLowerCase().endsWith(".html")) {
                    openStaticSite(item.relativePath);
                  } else {
                    void loadDocument(item.fullPath);
                  }
                }}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm border transition ${
                currentPath === item.fullPath
                    ? "bg-[var(--color-accent)] text-white border-[var(--color-accent)] shadow-md"
                    : "bg-[var(--color-surface-alt)] text-[var(--color-text-primary)] border-[var(--color-border)] hover:border-[var(--color-accent)] hover:shadow-sm"
                }`}
            >
                {item.name.toLowerCase().endsWith(".md") ? (
                    <FileText className="h-4 w-4" />
                ) : (
                    <Globe className="h-4 w-4 text-[var(--color-accent-cyan)]" />
                )}
                <span>{item.name}</span>
            </button>
            ))}
        </div>
      </div>
    );
  };

  const renderSprintFolderList = () => {
    if (!stageConfig || !selectedStage) return null;

    return (
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-3">
        <p className="mb-3 text-xs text-[var(--color-text-secondary)] uppercase tracking-wider">Sprints</p>
        <div className="flex flex-wrap gap-2">
            {sprintFolders.map((sf) => (
            <button
                key={sf}
                type="button"
                onClick={() => {
                setSelectedSprintFolder(sf);
                setFolderStack([]);
                }}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs border transition ${
                selectedSprintFolder === sf
                    ? "bg-[var(--color-accent)] text-white border-[var(--color-accent)] shadow-md"
                    : "bg-[var(--color-surface-alt)] text-[var(--color-text-primary)] border-[var(--color-border)] hover:border-[var(--color-accent)] hover:shadow-sm"
                }`}
            >
                <Layers className="h-3.5 w-3.5" />
                {sf}
            </button>
            ))}
        </div>
      </div>
    );
  };

  const renderSprintFileBrowser = () => {
    if (!stageConfig || !selectedStage || !selectedSprintFolder) return null;
    const folder = stageConfig.folder;
    const sprintPrefix = `${selectedSprintFolder}/`;
    const basePrefix =
      folderStack.length > 0 ? `${sprintPrefix}${folderStack.join("/")}/` : sprintPrefix;

    const items: { name: string; isFolder: boolean; fullPath: string; relativePath: string }[] = [];
    const seenFolders = new Set<string>();

    for (const f of selectedStage.files) {
      if (!f.startsWith(`${folder}/${basePrefix}`)) continue;
      const rel = f.slice(folder.length + 1);
      if (!rel.startsWith(basePrefix)) continue;
      const rest = rel.slice(basePrefix.length);
      const slashIdx = rest.indexOf("/");
      if (slashIdx === -1) {
        items.push({
          name: rest,
          isFolder: false,
          fullPath: `${folder}/${rel}`,
          relativePath: rel,
        });
      } else {
        const folderName = rest.slice(0, slashIdx);
        if (!seenFolders.has(folderName)) {
          seenFolders.add(folderName);
          items.push({
            name: folderName,
            isFolder: true,
            fullPath: "",
            relativePath: `${basePrefix}${folderName}`,
          });
        }
      }
    }

    items.sort((a, b) => {
      if (a.name === "README.md") return -1;
      if (b.name === "README.md") return 1;
      if (a.isFolder && !b.isFolder) return -1;
      if (!a.isFolder && b.isFolder) return 1;
      return a.name.localeCompare(b.name);
    });

    return (
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-3">
        <button
          type="button"
          onClick={() => {
            if (folderStack.length > 0) {
              setFolderStack((prev) => prev.slice(0, -1));
            } else {
              setSelectedSprintFolder("");
              setDocumentPayload(null);
              setCurrentPath("");
              setEditorContent("");
            }
          }}
          className="mb-3 text-xs flex items-center gap-1 text-[var(--color-text-secondary)] hover:text-[var(--color-accent-cyan)] transition"
        >
          <ChevronLeft className="h-3 w-3" />
          {folderStack.length > 0 ? "Up Directory" : "Back to sprints"}
        </button>
        <div className="flex flex-wrap gap-2">
          {items.map((item) => {
            const isStaticFolder = item.isFolder && stageFiles.includes(`${item.relativePath}/index.html`);
            return (
              <button
                key={item.name}
                type="button"
                onClick={() => {
                  if (item.isFolder) {
                    const indexPath = `${item.relativePath}/index.html`;
                    if (stageFiles.includes(indexPath)) {
                      openStaticSite(`${item.relativePath}/index.html`);
                    } else {
                      setFolderStack((prev) => [...prev, item.name]);
                    }
                  } else if (item.name.toLowerCase().endsWith(".html")) {
                    openStaticSite(item.relativePath);
                  } else {
                    void loadDocument(item.fullPath);
                  }
                }}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition border ${
                  currentPath === item.fullPath
                    ? "bg-[var(--color-accent)] text-white border-[var(--color-accent)] shadow-md"
                    : item.isFolder
                      ? "bg-[var(--color-surface-alt)] text-[var(--color-text-primary)] border-[var(--color-border)] hover:border-[var(--color-accent)]"
                      : "bg-transparent text-[var(--color-text-secondary)] border-transparent hover:bg-[var(--color-surface-alt)] hover:text-[var(--color-text-primary)]"
                }`}
              >
                {isStaticFolder ? (
                  <Globe className={`h-4 w-4 ${currentPath === item.fullPath ? "text-white" : "text-[var(--color-accent-cyan)]"}`} />
                ) : item.isFolder ? (
                  <Folder className={`h-4 w-4 ${currentPath === item.fullPath ? "text-white" : "text-[var(--color-accent-cyan)]"}`} />
                ) : item.name.toLowerCase().endsWith(".md") ? (
                  <FileText className="h-4 w-4 opacity-70" />
                ) : item.name.toLowerCase().endsWith(".html") ? (
                  <Globe className="h-4 w-4 text-[var(--color-accent-cyan)] opacity-70" />
                ) : (
                  <File className="h-4 w-4 opacity-70" />
                )}
                <span>{item.name}</span>
              </button>
            );
          })}
        </div>
      </div>
    );
  };

  const renderSprintButtons = () => {
    if (!documentPayload || !currentPath || documentPayload.contentType !== "text/markdown") return null;
    if (!stageConfig || stageConfig.type !== "sprints") return null;

    const folder = stageConfig.folder;
    const rel = currentPath.startsWith(`${folder}/`) ? currentPath.slice(folder.length + 1) : "";
    const parts = rel.split("/");

    if (parts.length !== 2) return null;

    const sprintFolder = parts[0];
    const fileName = parts[1];
    const isReadme = fileName === "README.md";

    return (
      <>
        <button
          type="button"
          onClick={() => void handleSave()}
          disabled={saving}
          className="flex items-center gap-2 rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm font-semibold text-white hover:bg-[var(--color-accent-hover)] transition disabled:opacity-50 shadow-md shadow-[var(--color-accent)]/20"
        >
          <Save className="h-4 w-4" />
          {saving ? "Saving..." : "Update"}
        </button>
        {isReadme
          ? renderActionButton("Develop this sprint", prompts.developSprintPrompt(sprintFolder), "primary", Rocket)
          : renderActionButton(
              "Develop this backlog",
              prompts.developBacklogPrompt(fileName.replace(".md", "")),
              "primary",
              Code2
            )}
      </>
    );
  };

  // --- Main render ---
  return (
    <div className="dev-swarm-root flex h-screen flex-col bg-[var(--color-background)] text-[var(--color-text-primary)] font-[var(--font-sans)]">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-surface)]/80 backdrop-blur-md px-6 py-3 shrink-0 z-20">
        <div className="flex items-center gap-3">
          <div className="bg-gradient-to-tr from-[var(--color-accent)] to-[var(--color-accent-cyan)] h-8 w-8 rounded-lg flex items-center justify-center shadow-lg shadow-[var(--color-accent)]/20">
             <Menu className="text-white h-5 w-5" />
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-[0.2em] text-[var(--color-text-secondary)] font-bold">
              Skill Pilot
            </p>
            <h1 className="text-lg font-bold font-[var(--font-display)] leading-none">Dev Swarm</h1>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => void doSync()}
            disabled={loading}
            className="group flex items-center gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-alt)] px-4 py-2 text-sm font-semibold text-[var(--color-text-primary)] hover:border-[var(--color-accent)] hover:bg-[var(--color-surface)] transition disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 transition-transform ${loading ? "animate-spin" : "group-hover:rotate-180"}`} />
            <span>Sync</span>
          </button>
          
          <div className="relative">
             <div className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none">
                <Cpu className="h-4 w-4 text-[var(--color-text-secondary)]" />
             </div>
            <select
                value={selectedAgent}
                onChange={(e) => setSelectedAgent(e.target.value)}
                disabled={agents.length === 0}
                className="appearance-none rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-alt)] pl-9 pr-8 py-2 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-focus)] focus:ring-1 focus:ring-[var(--color-focus)] transition cursor-pointer hover:bg-[var(--color-surface)]"
            >
                {agents.length === 0 ? (
                <option value="">No agents</option>
                ) : (
                agents.map((a) => (
                    <option key={a.id} value={a.id}>
                    {a.name}
                    </option>
                ))
                )}
            </select>
            <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
                 <div className="h-1.5 w-1.5 rounded-full bg-[var(--color-success)] shadow-[0_0_5px_var(--color-success)]"></div>
            </div>
          </div>
        </div>
      </header>

      <div className="shrink-0 border-b border-[var(--color-border)] bg-[var(--color-surface)]/60 px-6 py-2">
        <button
          type="button"
          onClick={() => { void router.push('/'); }}
          className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-semibold text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-alt)] hover:text-[var(--color-text-primary)] transition"
          title="Back to Home"
        >
          <ChevronLeft className="h-4 w-4" />
          <span>Back to Home</span>
        </button>
      </div>

      {/* Toast */}
      {toast && (
        <div className="fixed right-6 top-20 z-50 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 text-sm shadow-xl flex items-center gap-3 animate-in slide-in-from-right-10 fade-in duration-200">
           {toast.variant === "error" ? <AlertCircle className="text-[var(--color-error)] h-5 w-5" /> : <CheckCircle2 className="text-[var(--color-success)] h-5 w-5" />}
          <p
            className={`font-semibold ${
              toast.variant === "error"
                ? "text-[var(--color-error)]"
                : "text-[var(--color-success)]"
            }`}
          >
            {toast.message}
          </p>
        </div>
      )}

      {/* Main 3-panel layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Menu */}
        <aside className="w-64 shrink-0 border-r border-[var(--color-border)] bg-[var(--color-surface)] overflow-y-auto custom-scrollbar">
          <div className="px-4 py-6">
            <h2 className="text-xs font-bold uppercase tracking-widest text-[var(--color-text-secondary)] mb-4 pl-2 flex items-center gap-2">
                <Layers className="h-3 w-3" />
                Project Stages
            </h2>
            {loading ? (
              <div className="flex flex-col gap-2 p-2">
                 <div className="h-8 w-full bg-[var(--color-surface-alt)] rounded animate-pulse"></div>
                 <div className="h-8 w-full bg-[var(--color-surface-alt)] rounded animate-pulse delay-75"></div>
                 <div className="h-8 w-full bg-[var(--color-surface-alt)] rounded animate-pulse delay-150"></div>
              </div>
            ) : (
              <div className="space-y-6">
                {STAGE_GROUPS.map((group) => {
                  const groupStages = stages.filter((stage) =>
                    group.stageIds.includes(stage.stageId)
                  );
                  if (groupStages.length === 0) return null;
                  const GroupIcon = group.icon;
                  return (
                    <div key={group.title} className="space-y-2">
                      <p className="px-2 text-[10px] font-bold uppercase tracking-[0.1em] text-[var(--color-text-secondary)] opacity-70 flex items-center gap-2">
                        <GroupIcon className="h-3 w-3" />
                        {group.title}
                      </p>
                      <ul className="space-y-0.5">
                        {groupStages.map((stage) => {
                             const StatusIcon = STATUS_ICONS[stage.status];
                             const statusColor = STATUS_STYLES[stage.status];
                             return (
                                <li key={stage.stageId}>
                                    <button
                                    type="button"
                                    onClick={() => setSelectedStageId(stage.stageId)}
                                    className={`group flex w-full items-center justify-between rounded-lg px-2 py-2 text-left text-xs transition relative overflow-hidden ${
                                        stage.stageId === selectedStageId
                                        ? "bg-[var(--color-surface-alt)] text-white shadow-sm ring-1 ring-[var(--color-border)]"
                                        : "text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-alt)]/50 hover:text-[var(--color-text-primary)]"
                                    }`}
                                    >
                                    {stage.stageId === selectedStageId && <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-[var(--color-accent)]"></div>}
                                    <span className="flex items-center gap-3 truncate">
                                        <span
                                        className={`grid h-5 w-8 place-items-center rounded text-[9px] font-bold tracking-tighter ${
                                            stage.stageId === selectedStageId
                                            ? "bg-[var(--color-accent)] text-white"
                                            : "bg-[var(--color-surface)] text-[var(--color-text-secondary)] border border-[var(--color-border)]"
                                        }`}
                                        >
                                        {stage.stageId}
                                        </span>
                                        <span className={`truncate font-medium ${stage.stageId === selectedStageId ? "text-white" : ""}`}>{stage.name}</span>
                                    </span>
                                    <StatusIcon className={`h-3.5 w-3.5 ${statusColor}`} />
                                    </button>
                                </li>
                            );
                        })}
                      </ul>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </aside>

        {/* Middle Panel */}
        <main className="flex flex-1 flex-col overflow-hidden bg-[var(--color-background)] relative">
          
          {/* Progress Menu */}
          {stageConfig && dynamicProgressSteps.length > 0 && !isSkipped && (
            <div className="flex items-center gap-1 border-b border-[var(--color-border)] bg-[var(--color-surface)]/50 backdrop-blur-sm px-6 py-2 overflow-x-auto shrink-0 z-10">
              {dynamicProgressSteps.map((step, idx) => {
                const isStageFilesStep = step.key === "stage-files";
                const isProposalStep = step.key === "proposal";
                const isPlanStep = step.key === "plan";
                const isBacklogsStep = step.key === "backlogs";
                const isInitIdeas = stageConfig?.type === "init-ideas";
                const isSprints = stageConfig?.type === "sprints";
                const isStageFilesDisabled = isStageFilesStep && hasOnlyReadme;
                const isProposalDisabled = isProposalStep && isInitIdeas && !hasReadme;
                const isPlanDisabled = isPlanStep && isSprints && !hasDevelopmentPlan;
                const isBacklogsDisabled = isBacklogsStep && isSprints && !hasSprintFolders;
                const isDisabled = isStageFilesDisabled || isProposalDisabled || isPlanDisabled || isBacklogsDisabled;
                const disabledTooltip = isProposalDisabled
                  ? "Create proposal first"
                  : isPlanDisabled
                    ? "Create development plan first"
                    : isBacklogsDisabled
                      ? "Create sprint backlogs first"
                      : isStageFilesDisabled
                        ? "Create stage files first"
                        : undefined;
                return (
                  <div key={step.key} className="flex items-center">
                      <button
                          type="button"
                          onClick={() => !isDisabled && setActiveProgressStep(step.key)}
                          disabled={isDisabled}
                          title={disabledTooltip}
                          className={`flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-semibold transition whitespace-nowrap ${
                              step.key === activeProgressStep
                              ? "bg-[var(--color-accent)] text-white shadow-md shadow-[var(--color-accent)]/20"
                              : isDisabled
                                ? "text-[var(--color-text-secondary)] opacity-40 cursor-not-allowed"
                                : "text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-alt)] hover:text-[var(--color-text-primary)]"
                          }`}
                          >
                          <span className={`flex items-center justify-center h-4 w-4 rounded-full text-[9px] ${step.key === activeProgressStep ? "bg-white/20" : isDisabled ? "bg-[var(--color-surface-alt)] opacity-50" : "bg-[var(--color-surface-alt)]"}`}>
                              {idx + 1}
                          </span>
                          {step.label}
                      </button>
                      {idx < dynamicProgressSteps.length - 1 && (
                          <ArrowRight className="h-3 w-3 text-[var(--color-text-secondary)] mx-1" />
                      )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Stage Content */}
          <div className="flex flex-1 min-h-0 flex-col px-8 py-6 max-w-5xl mx-auto w-full">
            {/* Stage header */}
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold font-[var(--font-display)] flex items-center gap-3">
                    {selectedStage && (
                        <span className="text-[var(--color-accent-cyan)] opacity-80 text-lg font-mono tracking-tighter">
                            {selectedStage.stageId}
                        </span>
                    )}
                  {selectedStage
                    ? selectedStage.name
                    : "Select a stage"}
                </h2>
                {selectedStage && (
                  <div className="flex items-center gap-3 mt-1">
                     <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_STYLES[selectedStage.status]} bg-[var(--color-surface-alt)] border border-[var(--color-border)]`}>
                        {(() => {
                            const Icon = STATUS_ICONS[selectedStage.status];
                            return <Icon className="h-3 w-3" />;
                        })()}
                        {selectedStage.status}
                     </span>
                     <span className="text-xs text-[var(--color-text-secondary)] flex items-center gap-1">
                        <File className="h-3 w-3" />
                        {selectedStage.files.length} files
                     </span>
                  </div>
                )}
              </div>
              {selectedStage?.isSkippable && !isSkipped && (
                <button
                  type="button"
                  onClick={async () => {
                    await toggleSkip(selectedStage.stageId, true);
                    await doSync();
                  }}
                  className="flex items-center gap-2 rounded-lg border border-[var(--color-border)] px-3 py-1.5 text-xs font-medium text-[var(--color-text-secondary)] hover:border-[var(--color-warning)] hover:text-[var(--color-warning)] transition bg-[var(--color-surface-alt)]"
                >
                  <SkipForward className="h-3.5 w-3.5" />
                  Skip Stage
                </button>
              )}
            </div>

            <div className="flex-1 min-h-0 flex flex-col overflow-y-auto pr-2 custom-scrollbar">
              {renderStageContent()}
            </div>
          </div>
        </main>

        {/* Right Panel - AI Agent Log */}
        <aside className="w-96 shrink-0 border-l border-[var(--color-border)] bg-[var(--color-surface)] flex flex-col shadow-xl z-10">
          <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)] bg-[var(--color-surface-alt)]/50">
            <div className="flex items-center gap-2">
              <Terminal className="h-4 w-4 text-[var(--color-text-secondary)]" />
              <div>
                <h3 className="text-xs font-bold uppercase tracking-widest text-[var(--color-text-secondary)]">
                    Agent Console
                </h3>
              </div>
            </div>
            <div className="flex items-center gap-1">
               <div className={`h-2 w-2 rounded-full ${agentRunning ? "bg-[var(--color-success)] animate-pulse" : "bg-[var(--color-border)]"}`}></div>
               <span className="text-[10px] text-[var(--color-text-secondary)] font-mono uppercase mr-2">{agentRunning ? "Active" : "Idle"}</span>

              {agentRunning && (
                <button
                  type="button"
                  onClick={() => void handleInterrupt()}
                  className="rounded bg-[var(--color-error)]/10 border border-[var(--color-error)]/30 p-1 text-[var(--color-error)] hover:bg-[var(--color-error)] hover:text-white transition"
                  title="Interrupt"
                >
                  <Square className="h-3.5 w-3.5" />
                </button>
              )}
              <button
                type="button"
                onClick={() => setConsoleEvents([])}
                className="rounded border border-[var(--color-border)] p-1 text-[var(--color-text-secondary)] hover:border-[var(--color-accent)] hover:text-[var(--color-accent)] transition bg-[var(--color-surface)]"
                title="Clear Output"
              >
                <Eraser className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
          <div
            ref={consoleRef}
            onScroll={() => {
              const el = consoleRef.current;
              if (!el) return;
              setIsPinned(el.scrollHeight - el.scrollTop - el.clientHeight < 24);
            }}
            className="flex-1 overflow-y-auto p-4 font-mono text-xs space-y-2 bg-[var(--color-background)]"
          >
            {consoleEvents.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-[var(--color-text-secondary)] opacity-50 gap-2">
                 <Terminal className="h-8 w-8" />
                 <p>Waiting for agent output...</p>
              </div>
            ) : (
              consoleEvents.map((ev) => (
                <div
                  key={ev.id}
                  className={`border-l-2 pl-3 py-1 ${
                    ev.category === "stderr"
                      ? "border-[var(--color-error)] bg-[var(--color-error)]/5"
                      : ev.category === "system"
                        ? "border-[var(--color-accent-cyan)]"
                        : ev.category === "status"
                          ? "border-[var(--color-warning)] bg-[var(--color-warning)]/5"
                          : "border-[var(--color-border)]"
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1 opacity-50 text-[10px]">
                     <span>{new Date(ev.timestamp).toLocaleTimeString()}</span>
                     <span className="uppercase">{ev.category}</span>
                  </div>
                  <div className={`whitespace-pre-wrap break-words leading-relaxed ${
                    ev.category === "stderr"
                      ? "text-[var(--color-error)]"
                      : ev.category === "system"
                        ? "text-[var(--color-accent-cyan)] font-bold"
                        : ev.category === "status"
                          ? "text-[var(--color-warning)]"
                          : "text-[var(--color-text-primary)]"
                  }`}>
                    {ev.message}
                  </div>
                </div>
              ))
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
