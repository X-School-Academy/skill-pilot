import React, { useEffect, useMemo, useState } from "react";
import Head from "next/head";

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
    <>
      <Head>
        <title>Terminal History</title>
      </Head>
      <main className="h-screen bg-[#0b0f19] text-[#d7e2ff] flex flex-col overflow-hidden">
        <div className="h-[42px] border-b border-[#2f3645] px-4 flex items-center bg-[#121826] flex-shrink-0">
          <div className="text-sm font-medium whitespace-nowrap overflow-hidden text-ellipsis">
            {topBarText}
          </div>
        </div>
        <div className="flex-1 min-h-0 overflow-auto bg-[#0b0f19]">
          {loading ? (
            <div className="h-full flex items-center justify-center text-sm text-[#9fb0d9]">
              Loading tmux history...
            </div>
          ) : error ? (
            <div className="h-full flex items-center justify-center p-6 text-sm text-[#ff9ca8]">
              {error}
            </div>
          ) : (
            <pre className="min-h-full w-full p-4 m-0 whitespace-pre-wrap break-words font-mono text-[13px] leading-5 text-[#d7e2ff] select-text">
              {historyContent || "\n"}
            </pre>
          )}
        </div>
      </main>
    </>
  );
};

export default TerminalHistoryPage;
