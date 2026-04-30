import React, { useEffect, useMemo, useState } from "react";

import TerminalHistoryViewer from "../../components/TerminalHistoryViewer";
import { getApiBase } from "../../libs/api-base";

type HistoryResponse = {
  session: string;
  pane_target: string;
  command: string;
  content: string;
};

const readSessionFromUrl = (): string => {
  if (typeof window === "undefined") return "";
  const params = new URLSearchParams(window.location.search);
  return (params.get("session") || "").trim();
};

const TerminalHistoryPage = () => {
  const [sessionName, setSessionName] = useState("");
  const [historyCommand, setHistoryCommand] = useState("");
  const [historyContent, setHistoryContent] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const session = readSessionFromUrl();
    setSessionName(session);

    if (!session) {
      setError("tmux session name is required");
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    const apiBase = getApiBase();
    const historyUrl = `${apiBase}/api/terminal/tmux/history?session=${encodeURIComponent(session)}`;

    void fetch(historyUrl, { signal: controller.signal })
      .then(async (response) => {
        const payload = await response.json().catch(() => null);
        if (!response.ok) {
          throw new Error(String(payload?.error || "failed to load tmux history"));
        }
        return payload as HistoryResponse;
      })
      .then((payload) => {
        setSessionName(payload.session || session);
        setHistoryCommand(payload.command || "");
        setHistoryContent(payload.content || "");
        setError("");
      })
      .catch((fetchError: unknown) => {
        if (controller.signal.aborted) return;
        setError(fetchError instanceof Error ? fetchError.message : "failed to load tmux history");
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, []);

  const topBarText = useMemo(() => {
    if (historyCommand) return `comand: ${historyCommand}`;
    if (sessionName) return `comand: tmux capture-pane -pJ -S - -E - -t ${sessionName}:0.0`;
    return "comand: tmux capture-pane -pJ -S - -E - -t";
  }, [historyCommand, sessionName]);

  return (
    <TerminalHistoryViewer
      pageTitle="Terminal History"
      topBarText={topBarText}
      loading={loading}
      loadingText="Loading tmux history..."
      error={error}
      content={historyContent}
    />
  );
};

export default TerminalHistoryPage;
