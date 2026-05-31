import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Head from "next/head";
import dynamic from "next/dynamic";
import { useRouter } from "next/router";
import { GetStaticPropsContext } from "next";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { serverSideTranslations } from "next-i18next/serverSideTranslations";
import {
  Button,
  Checkbox,
  Group,
  Header,
  Loader,
  ScrollArea,
  Select,
  Stack,
  Text,
  Textarea,
  Title,
  Tooltip,
  useMantineTheme,
} from "@mantine/core";
import { IconArrowLeft, IconFolder, IconFolderOpen, IconGripHorizontal, IconPlayerPlay, IconPlus, IconRefresh } from "@tabler/icons-react";

import { apiUrl } from "../../libs/api-base";
import { resolveSelectedProvider, setSelectedProvider } from "../../libs/llm";

const API_BASE_URL = apiUrl("/api");
const SPLIT_HANDLE_SIZE = 12;
const FileManagerContent = dynamic(
  () => import("../../components/FileManagerContent"),
  {
    ssr: false,
    loading: () => (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "#868e96", fontSize: 14 }}>
        Loading file manager...
      </div>
    ),
  },
);

interface LlmProvider {
  id: string;
  name: string;
}

interface AgentSessionSummary {
  id: string;
  file: string;
  category: string;
  title: string;
  agent: string;
  model: string;
  session_id: string;
  time: string;
  resume_supported: boolean;
}

interface AgentSessionCategory {
  name: string;
  time: string;
  sessions: AgentSessionSummary[];
}

interface AgentSessionPayload {
  session: AgentSessionSummary;
  markdown: string;
}

const formatTime = (value: string): string => {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const quoteShell = (value: string): string => `'${value.replace(/'/g, "'\\''")}'`;

const titlePreview = (value: string): string => {
  const title = String(value || "").trim();
  if (title.length <= 30) return title;
  return `${title.slice(0, 30)}...`;
};

const buildResumeCommand = (session: AgentSessionSummary): string | null => {
  const agent = String(session.agent || "").toLowerCase();
  const sessionId = String(session.session_id || "").trim();
  if (!sessionId) return null;
  const quotedSessionId = quoteShell(sessionId);
  if (agent === "codex") return `codex resume ${quotedSessionId}`;
  if (agent === "claude") return `claude --resume ${quotedSessionId}`;
  if (agent === "gemini") return `gemini --resume ${quotedSessionId}`;
  if (agent === "opencode") return `opencode --session ${quotedSessionId}`;
  return null;
};

const AgentSessionsPage = () => {
  const router = useRouter();
  const theme = useMantineTheme();
  const [categories, setCategories] = useState<AgentSessionCategory[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [payload, setPayload] = useState<AgentSessionPayload | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingSession, setLoadingSession] = useState(false);
  const [resuming, setResuming] = useState(false);
  const [creatingSession, setCreatingSession] = useState(false);
  const [creatingTerminal, setCreatingTerminal] = useState(false);
  const [newSessionMode, setNewSessionMode] = useState(false);
  const [newSessionPrompt, setNewSessionPrompt] = useState("");
  const [newSessionSandbox, setNewSessionSandbox] = useState(false);
  const [newSessionAuto, setNewSessionAuto] = useState(false);
  const [newSessionNetwork, setNewSessionNetwork] = useState(true);
  const [newSessionNativeTerminal, setNewSessionNativeTerminal] = useState(false);
  const [newSessionPath, setNewSessionPath] = useState("");
  const [newSessionShowcaseDirectory, setNewSessionShowcaseDirectory] = useState("");
  const [newSessionFileManagerPath, setNewSessionFileManagerPath] = useState("");
  const [liveSessionName, setLiveSessionName] = useState("");
  const [liveSessionFileManagerPath, setLiveSessionFileManagerPath] = useState("");
  const [fileManagerOpen, setFileManagerOpen] = useState(false);
  const [fileManagerHeight, setFileManagerHeight] = useState(44);
  const [isSplitResizing, setIsSplitResizing] = useState(false);
  const [llmProviders, setLlmProviders] = useState<LlmProvider[]>([]);
  const [llmProvider, setLlmProvider] = useState<string | null>(null);
  const [error, setError] = useState("");
  const livePaneRef = useRef<HTMLDivElement | null>(null);
  const initialLoadRef = useRef(false);

  const goHome = useCallback(() => {
    void router.push("/");
  }, [router]);

  const selectedSummary = useMemo(() => {
    if (payload?.session) return payload.session;
    for (const category of categories) {
      const match = category.sessions.find((session) => session.id === selectedId);
      if (match) return match;
    }
    return null;
  }, [categories, payload, selectedId]);

  const fetchSession = useCallback(async (id: string) => {
    if (!id) return;
    setLoadingSession(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/agent-sessions/session`, { params: { id } });
      setPayload(res.data);
      setSelectedId(id);
      setNewSessionMode(false);
      setLiveSessionName("");
      setLiveSessionFileManagerPath("");
      setFileManagerOpen(false);
      setError("");
      void router.replace(`/agent-sessions?id=${encodeURIComponent(id)}`, undefined, { shallow: true });
    } catch (err: any) {
      const message = err?.response?.data?.error || "Failed to load agent session.";
      setError(String(message));
    } finally {
      setLoadingSession(false);
    }
  }, [router]);

  const fetchSessions = useCallback(async (sessionId = "", loadContent = false) => {
    setLoadingList(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/agent-sessions`);
      const nextCategories: AgentSessionCategory[] = res.data?.categories || [];
      setCategories(nextCategories);
      const firstId = nextCategories[0]?.sessions?.[0]?.id || "";
      const nextId = sessionId || firstId;
      setError("");
      if (loadContent && nextId) {
        await fetchSession(nextId);
      } else if (loadContent) {
        setPayload(null);
        setSelectedId("");
      }
    } catch (err: any) {
      const message = err?.response?.data?.error || "Failed to load agent sessions.";
      setError(String(message));
    } finally {
      setLoadingList(false);
    }
  }, [fetchSession]);

  const resumeSession = useCallback(async () => {
    if (!selectedSummary || resuming) return;
    const command = buildResumeCommand(selectedSummary);
    if (!command) {
      setError("Resume is only supported for codex, claude, gemini, and opencode sessions.");
      return;
    }
    setResuming(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/terminal/tmux/create`, { command });
      const sessionName: string | undefined = res.data?.session?.name;
      if (sessionName) {
        await router.push(`/terminals?session=${encodeURIComponent(sessionName)}`);
      }
      setError("");
    } catch (err: any) {
      const message = err?.response?.data?.error || "Failed to resume agent session.";
      setError(String(message));
    } finally {
      setResuming(false);
    }
  }, [resuming, router, selectedSummary]);

  const showNewSession = useCallback(() => {
    setNewSessionMode(true);
    setSelectedId("");
    setPayload(null);
    setNewSessionPath("");
    setNewSessionShowcaseDirectory("");
    setNewSessionFileManagerPath("");
    setLiveSessionName("");
    setLiveSessionFileManagerPath("");
    setFileManagerOpen(false);
    setError("");
    void router.replace("/agent-sessions?new=true", undefined, { shallow: true });
  }, [router]);

  const startNewSession = useCallback(async () => {
    const prompt = newSessionPrompt.trim();
    if (!prompt || creatingSession) return;
    const provider = llmProvider || "gemini";
    const envPairs: [string, string][] = [];
    if (newSessionShowcaseDirectory) {
      envPairs.push(["SHOWCASE_SESSION_DIRECTORY", newSessionShowcaseDirectory]);
    }
    setCreatingSession(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/terminal/tmux/create`, {
        provider_id: provider,
        prompt,
        path: newSessionPath || undefined,
        sandbox: newSessionSandbox,
        auto: newSessionAuto,
        network: newSessionNetwork,
        native_terminal: newSessionNativeTerminal,
        env: envPairs.length ? envPairs : undefined,
      });
      const sessionName: string | undefined = res.data?.session?.name;
      if (sessionName) {
        setNewSessionPrompt("");
        if (newSessionNativeTerminal) {
          const nativeOpened: boolean = Boolean(res.data?.native_terminal?.opened);
          const nativeError = String(res.data?.native_terminal?.error || "");
          if (!nativeOpened) {
            const details = nativeError ? `: ${nativeError}` : "";
            window.alert(`Native terminal did not open${details}. You can attach manually with tmux session ${sessionName}.`);
          }
        } else {
          setLiveSessionName(sessionName);
          setLiveSessionFileManagerPath(newSessionFileManagerPath);
          setFileManagerOpen(Boolean(newSessionFileManagerPath));
        }
      }
      setError("");
    } catch (err: any) {
      const message = err?.response?.data?.error || "Failed to start agent session.";
      setError(String(message));
    } finally {
      setCreatingSession(false);
    }
  }, [
    creatingSession,
    llmProvider,
    newSessionAuto,
    newSessionFileManagerPath,
    newSessionNativeTerminal,
    newSessionNetwork,
    newSessionPath,
    newSessionPrompt,
    newSessionSandbox,
    newSessionShowcaseDirectory,
    router,
  ]);

  const handleNewSessionKeyDown = useCallback((event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      void startNewSession();
    }
  }, [startNewSession]);

  const startShellTerminal = useCallback(async () => {
    if (creatingTerminal) return;
    setCreatingTerminal(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/terminal/tmux/create`, {
        session_type: "shell",
      });
      const sessionName: string | undefined = res.data?.session?.name;
      if (sessionName) {
        setLiveSessionName(sessionName);
        setLiveSessionFileManagerPath("");
        setFileManagerOpen(false);
      }
      setError("");
    } catch (err: any) {
      const message = err?.response?.data?.error || "Failed to start terminal session.";
      setError(String(message));
    } finally {
      setCreatingTerminal(false);
    }
  }, [creatingTerminal]);

  useEffect(() => {
    if (!router.isReady || initialLoadRef.current) return;
    initialLoadRef.current = true;
    const queryId = typeof router.query.id === "string" ? router.query.id : "";
    const queryPrompt = typeof router.query.prompt === "string" ? router.query.prompt : "";
    const queryPath = typeof router.query.path === "string" ? router.query.path : "";
    const queryShowcaseDirectory = typeof router.query.showcaseDirectory === "string" ? router.query.showcaseDirectory : "";
    const queryFileManagerPath = typeof router.query.fileManagerPath === "string" ? router.query.fileManagerPath : "";
    if (queryPrompt) {
      setNewSessionPrompt(queryPrompt);
    }
    if (queryPath) {
      setNewSessionPath(queryPath);
    }
    if (queryShowcaseDirectory) {
      setNewSessionShowcaseDirectory(queryShowcaseDirectory);
    }
    if (queryFileManagerPath) {
      setNewSessionFileManagerPath(queryFileManagerPath);
    }
    if (!queryId || router.query.new === "true") {
      setNewSessionMode(true);
    }
    void fetchSessions(queryId, Boolean(queryId) && router.query.new !== "true");
  }, [fetchSessions, router.isReady, router.query.id]);

  useEffect(() => {
    axios.get(`${API_BASE_URL}/llm/providers`)
      .then((res) => {
        const providers: LlmProvider[] = res.data.providers || [];
        const serverDefault: string = res.data.default || "";
        setLlmProviders(providers);
        const defaultId = resolveSelectedProvider(providers, serverDefault, "gemini");
        if (defaultId) setSelectedProvider(defaultId);
        setLlmProvider(defaultId);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!isSplitResizing) return undefined;

    const previousCursor = document.body.style.cursor;
    const previousUserSelect = document.body.style.userSelect;
    document.body.style.cursor = "row-resize";
    document.body.style.userSelect = "none";

    const handlePointerMove = (event: PointerEvent) => {
      if (!livePaneRef.current) return;
      const bounds = livePaneRef.current.getBoundingClientRect();
      if (bounds.height <= 0) return;
      event.preventDefault();
      const availableHeight = Math.max(1, bounds.height - SPLIT_HANDLE_SIZE);
      const nextTopPixels = Math.max(0, Math.min(availableHeight, event.clientY - bounds.top));
      setFileManagerHeight((nextTopPixels / availableHeight) * 100);
    };

    const handlePointerUp = () => setIsSplitResizing(false);

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    window.addEventListener("pointercancel", handlePointerUp);
    return () => {
      document.body.style.cursor = previousCursor;
      document.body.style.userSelect = previousUserSelect;
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      window.removeEventListener("pointercancel", handlePointerUp);
    };
  }, [isSplitResizing]);

  const startSplitResize = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.currentTarget.setPointerCapture?.(event.pointerId);
    setIsSplitResizing(true);
  }, []);

  const renderResumeButton = (position: "top" | "bottom") => {
    const command = selectedSummary ? buildResumeCommand(selectedSummary) : null;
    return (
      <Button
        key={position}
        size="xs"
        leftIcon={<IconPlayerPlay size="1rem" />}
        disabled={!command || resuming}
        loading={resuming}
        onClick={() => void resumeSession()}
      >
        Resume
      </Button>
    );
  };

  const renderLiveTerminal = () => (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", padding: "12px 16px 16px" }}>
      <Group position="apart" mb={8}>
        <Text size="sm" weight={700}>Viewing: {liveSessionName}</Text>
        <button
          type="button"
          onClick={() => setFileManagerOpen((open) => !open)}
          title={fileManagerOpen ? "Hide file manager" : "Show file manager"}
          aria-label={fileManagerOpen ? "Hide file manager" : "Show file manager"}
          style={{
            width: 30,
            height: 28,
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            border: `1px solid ${theme.colors.gray[3]}`,
            borderRadius: 8,
            padding: 0,
            background: fileManagerOpen
              ? (theme.colorScheme === "dark" ? theme.colors.dark[5] : theme.colors.blue[0])
              : (theme.colorScheme === "dark" ? theme.colors.dark[6] : "#fff"),
            color: fileManagerOpen ? theme.colors.blue[6] : "inherit",
            cursor: "pointer",
          }}
        >
          <IconFolderOpen size={16} />
        </button>
      </Group>
      <div
        ref={livePaneRef}
        style={{
          flex: 1,
          minHeight: 0,
          overflow: "hidden",
          position: "relative",
          display: "grid",
          gridTemplateRows: fileManagerOpen ? `minmax(0, ${fileManagerHeight}fr) ${SPLIT_HANDLE_SIZE}px minmax(0, ${100 - fileManagerHeight}fr)` : "1fr",
        }}
      >
        {isSplitResizing && (
          <div
            style={{
              position: "fixed",
              inset: 0,
              zIndex: 9999,
              cursor: "row-resize",
              background: "transparent",
            }}
          />
        )}
        {fileManagerOpen && (
          <>
            <div style={{ minHeight: 0, overflow: "hidden", border: `1px solid ${theme.colors.gray[3]}`, borderRadius: 8, background: "#fff" }}>
              <div style={{ height: "100%", minHeight: 0 }}>
                <FileManagerContent
                  key={liveSessionFileManagerPath || "project-root"}
                  title="Documents"
                  initialPath={liveSessionFileManagerPath || undefined}
                  hideDirectoryTree
                  hideStandaloneHeader
                  routePathname="/agent-sessions"
                  updateRoute={false}
                />
              </div>
            </div>
            <div
              onPointerDown={startSplitResize}
              aria-label="Resize file manager and terminal"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                cursor: "row-resize",
                touchAction: "none",
                userSelect: "none",
                color: "#93a4cc",
                background: "transparent",
              }}
            >
              <IconGripHorizontal size={16} />
            </div>
          </>
        )}
        <div style={{ minHeight: 0, overflow: "hidden", position: "relative" }}>
          <iframe
            key={liveSessionName}
            src={`/terminal?session=${encodeURIComponent(liveSessionName)}`}
            style={{
              width: "100%",
              height: "100%",
              display: "block",
              border: "none",
              borderRadius: 8,
            }}
          />
        </div>
      </div>
    </div>
  );

  return (
    <>
      <Head>
        <title>Skill Pilot - Agent Sessions</title>
      </Head>
      <Header
        height={{ base: 60 }}
        p="md"
        styles={{
          root: process.env.NODE_ENV === "development" ? { borderBottom: "2px solid #228be6" } : undefined,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", height: "100%", justifyContent: "space-between" }}>
          <a href="/" style={{ display: "flex", alignItems: "center" }}>
            <img className="h-10" src="/images/skill-pilot-2.png" alt="Logo" />
          </a>
          <Group spacing="xs">
            <Select
              placeholder="LLM"
              value={llmProvider}
              onChange={(value) => {
                if (!value) return;
                setLlmProvider(value);
                setSelectedProvider(value);
              }}
              data={llmProviders.map((provider) => ({ value: provider.id, label: provider.name }))}
              size="xs"
              style={{ width: 200 }}
            />
          </Group>
        </div>
      </Header>
      <main
        style={{
          height: "calc(100vh - 60px)",
          background: theme.colorScheme === "dark" ? theme.colors.dark[8] : theme.colors.gray[0],
          display: "grid",
          gridTemplateColumns: "minmax(260px, 340px) minmax(0, 1fr)",
          overflow: "hidden",
        }}
      >
        <aside
          style={{
            borderRight: `1px solid ${theme.colors.gray[3]}`,
            background: theme.colorScheme === "dark" ? theme.colors.dark[7] : "#fff",
            minWidth: 0,
          }}
        >
          <Group position="apart" px="md" py="sm" style={{ borderBottom: `1px solid ${theme.colors.gray[3]}` }}>
            <Group spacing="xs" noWrap>
              <Button
                size="xs"
                variant="subtle"
                compact
                leftIcon={<IconArrowLeft size="0.9rem" />}
                onClick={goHome}
              >
                Back
              </Button>
              <Text size="sm" weight={700}>Agent Sessions</Text>
            </Group>
            <Button size="xs" variant="default" compact onClick={() => void fetchSessions(selectedId, !payload)} aria-label="Refresh">
              <IconRefresh size="0.9rem" />
            </Button>
          </Group>
          <ScrollArea style={{ height: "calc(100vh - 105px)" }}>
            <Stack spacing={4} p="sm">
              <button
                type="button"
                onClick={showNewSession}
                style={{
                  width: "100%",
                  border: `1px solid ${newSessionMode ? theme.colors.blue[5] : theme.colors.gray[3]}`,
                  borderRadius: 8,
                  padding: "9px 10px",
                  marginBottom: 8,
                  background: newSessionMode
                    ? (theme.colorScheme === "dark" ? theme.colors.dark[5] : theme.colors.blue[0])
                    : (theme.colorScheme === "dark" ? theme.colors.dark[6] : theme.colors.gray[0]),
                  color: "inherit",
                  cursor: "pointer",
                  textAlign: "left",
                }}
              >
                <Group spacing={8} noWrap>
                  <IconPlus size="1rem" color={theme.colors.blue[6]} />
                  <Text size="sm" weight={700}>New Session</Text>
                </Group>
              </button>
              {loadingList && categories.length === 0 ? (
                <Group py="md" position="center">
                  <Loader size="sm" />
                </Group>
              ) : categories.length === 0 ? (
                <Text size="sm" color="dimmed" p="xs">No agent sessions recorded yet.</Text>
              ) : (
                categories.map((category) => (
                  <div key={category.name}>
                    <Group spacing={5} mt="xs" mb={4} noWrap>
                      <IconFolder size="0.95rem" color={theme.colors.yellow[7]} />
                      <Text size="xs" weight={700} color="dimmed" truncate>
                        {category.name}
                      </Text>
                    </Group>
                    {category.sessions.slice(0, 10).map((session) => {
                      const active = session.id === selectedId;
                      return (
                        <button
                          key={session.id}
                          type="button"
                          onClick={() => {
                            if (!active) void fetchSession(session.id);
                          }}
                          style={{
                            width: "100%",
                            border: `1px solid ${active ? theme.colors.blue[5] : "transparent"}`,
                            borderRadius: 8,
                            padding: "8px 10px",
                            marginBottom: 4,
                            background: active
                              ? (theme.colorScheme === "dark" ? theme.colors.dark[5] : theme.colors.blue[0])
                              : "transparent",
                            color: "inherit",
                            cursor: "pointer",
                            textAlign: "left",
                          }}
                        >
                          <Tooltip label={session.title} openDelay={350} multiline width={320} disabled={session.title.length <= 30}>
                            <Text size="sm" weight={600} truncate>{titlePreview(session.title)}</Text>
                          </Tooltip>
                          <Text size="xs" color="dimmed" truncate>
                            {session.agent || "agent"} · {formatTime(session.time)}
                          </Text>
                        </button>
                      );
                    })}
                  </div>
                ))
              )}
            </Stack>
          </ScrollArea>
        </aside>

        <section style={{ minWidth: 0, overflow: "hidden", display: "flex", flexDirection: "column" }}>
          {!liveSessionName && (
            <Group
              position="apart"
              px="lg"
              py="sm"
              style={{ borderBottom: `1px solid ${theme.colors.gray[3]}`, background: theme.colorScheme === "dark" ? theme.colors.dark[7] : "#fff" }}
            >
              <div style={{ minWidth: 0 }}>
                <Title order={3} style={{ fontSize: 18 }}>{newSessionMode ? "New Session" : "Agent Session"}</Title>
                {!newSessionMode && selectedSummary && (
                  <Text size="xs" color="dimmed" truncate>
                    {selectedSummary.agent || "agent"} · {selectedSummary.session_id || selectedSummary.id}
                  </Text>
                )}
              </div>
              {!newSessionMode && renderResumeButton("top")}
            </Group>
          )}

          {error && <Text size="sm" color="red" px="lg" pt="sm">{error}</Text>}

          {liveSessionName ? (
            <div style={{ flex: 1, minHeight: 0, overflow: "hidden" }}>
              {renderLiveTerminal()}
            </div>
          ) : (
          <ScrollArea style={{ flex: 1 }}>
            {newSessionMode ? (
              <div style={{ width: "100%", maxWidth: 720, margin: "0 auto", padding: "48px 24px", position: "relative" }}>
                <div style={{ position: "absolute", top: 20, right: 24 }}>
                  <Button
                    size="sm"
                    variant="subtle"
                    leftIcon={<IconPlus size="1rem" />}
                    onClick={() => void startShellTerminal()}
                    loading={creatingTerminal}
                    aria-label="New terminal"
                  >
                    Terminal
                  </Button>
                </div>
                <Stack spacing="md">
                  <div>
                    <Title order={2} style={{ fontSize: 28 }}>Skill Pilot</Title>
                    <Text size="md" color="dimmed" italic>
                      Do first. Learn as needed.
                    </Text>
                  </div>
                  <Textarea
                    placeholder="What would you like to do?"
                    value={newSessionPrompt}
                    onChange={(event) => setNewSessionPrompt(event.currentTarget.value)}
                    onKeyDown={handleNewSessionKeyDown}
                    autosize
                    minRows={4}
                    maxRows={12}
                    size="md"
                  />
                  {(newSessionPath || newSessionShowcaseDirectory) && (
                    <Stack spacing={3}>
                      {newSessionPath && (
                        <Text size="xs" color="dimmed" truncate>
                          Start directory: {newSessionPath}
                        </Text>
                      )}
                      {newSessionShowcaseDirectory && (
                        <Text size="xs" color="dimmed" truncate>
                          Showcase directory: {newSessionShowcaseDirectory}
                        </Text>
                      )}
                    </Stack>
                  )}
                  <Group position="center" spacing="md">
                    <Checkbox
                      label="Sandbox"
                      checked={newSessionSandbox}
                      onChange={(event) => setNewSessionSandbox(event.currentTarget.checked)}
                      size="xs"
                    />
                    <Checkbox
                      label="Auto Run (Yolo)"
                      checked={newSessionAuto}
                      onChange={(event) => setNewSessionAuto(event.currentTarget.checked)}
                      size="xs"
                    />
                    <Checkbox
                      label="Network Access"
                      checked={newSessionNetwork}
                      onChange={(event) => setNewSessionNetwork(event.currentTarget.checked)}
                      size="xs"
                    />
                    <Checkbox
                      label="Native Terminal"
                      checked={newSessionNativeTerminal}
                      onChange={(event) => setNewSessionNativeTerminal(event.currentTarget.checked)}
                      size="xs"
                    />
                  </Group>
                  <Group position="center">
                    <Button
                      size="md"
                      leftIcon={<IconPlayerPlay size="1rem" />}
                      disabled={!newSessionPrompt.trim() || creatingSession}
                      loading={creatingSession}
                      onClick={() => void startNewSession()}
                    >
                      Start
                    </Button>
                  </Group>
                </Stack>
              </div>
            ) : loadingSession ? (
              <Group position="center" py="xl">
                <Loader size="sm" />
                <Text size="sm" color="dimmed">Loading session...</Text>
              </Group>
            ) : payload ? (
              <div style={{ maxWidth: 980, margin: "0 auto", padding: "20px 24px 28px" }}>
                <div className="doc-markdown" style={{ maxWidth: "none", background: "#fff", padding: 20, borderRadius: 8, border: `1px solid ${theme.colors.gray[3]}` }}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{payload.markdown}</ReactMarkdown>
                </div>
                <Group position="right" mt="md">
                  {renderResumeButton("bottom")}
                </Group>
              </div>
            ) : (
              <Text size="sm" color="dimmed" p="lg">Select an agent session.</Text>
            )}
          </ScrollArea>
          )}
        </section>
      </main>
    </>
  );
};

export default AgentSessionsPage;

export const getStaticProps = async (context: GetStaticPropsContext) => {
  return {
    props: {
      ...(await serverSideTranslations(context.locale ?? "en", [
        "common",
      ])),
    },
  };
};
