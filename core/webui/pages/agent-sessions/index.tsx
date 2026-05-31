import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Head from "next/head";
import { useRouter } from "next/router";
import { GetStaticPropsContext } from "next";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { serverSideTranslations } from "next-i18next/serverSideTranslations";
import {
  Button,
  Group,
  Header,
  Loader,
  ScrollArea,
  Stack,
  Text,
  Title,
  useMantineTheme,
} from "@mantine/core";
import { IconArrowLeft, IconFolder, IconPlayerPlay, IconRefresh } from "@tabler/icons-react";

import { apiUrl } from "../../libs/api-base";

const API_BASE_URL = apiUrl("/api");

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
  const [error, setError] = useState("");
  const initialLoadRef = useRef(false);

  const goHome = useCallback(() => {
    void router.push("/?view=home");
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

  useEffect(() => {
    if (!router.isReady || initialLoadRef.current) return;
    initialLoadRef.current = true;
    const queryId = typeof router.query.id === "string" ? router.query.id : "";
    void fetchSessions(queryId, true);
  }, [fetchSessions, router.isReady, router.query.id]);

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
          <a href="/?view=home" style={{ display: "flex", alignItems: "center" }}>
            <img className="h-10" src="/images/skill-pilot-2.png" alt="Logo" />
          </a>
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
                    {category.sessions.map((session) => {
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
                          <Text size="sm" weight={600} truncate>{session.title}</Text>
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
          <Group
            position="apart"
            px="lg"
            py="sm"
            style={{ borderBottom: `1px solid ${theme.colors.gray[3]}`, background: theme.colorScheme === "dark" ? theme.colors.dark[7] : "#fff" }}
          >
            <div style={{ minWidth: 0 }}>
              <Title order={3} style={{ fontSize: 18 }}>Agent Session</Title>
              {selectedSummary && (
                <Text size="xs" color="dimmed" truncate>
                  {selectedSummary.agent || "agent"} · {selectedSummary.session_id || selectedSummary.id}
                </Text>
              )}
            </div>
            {renderResumeButton("top")}
          </Group>

          {error && <Text size="sm" color="red" px="lg" pt="sm">{error}</Text>}

          <ScrollArea style={{ flex: 1 }}>
            {loadingSession ? (
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
