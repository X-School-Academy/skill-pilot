import React, { useEffect, useMemo, useState } from "react";
import { GetStaticPropsContext } from "next";
import { serverSideTranslations } from "next-i18next/serverSideTranslations";

import MainLayout from "../../components/main-layout";
import TerminalHistoryViewer from "../../components/TerminalHistoryViewer";
import { getApiBase } from "../../libs/api-base";

type SavedHistoryResponse = {
  id: string;
  session: string;
  command: string;
  content: string;
  title: string;
  saved_at: string;
};

const readHistoryIdFromUrl = (): string => {
  if (typeof window === "undefined") return "";
  const params = new URLSearchParams(window.location.search);
  return (params.get("id") || "").trim();
};

const formatSavedAt = (value: string): string => {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
};

const SavedTerminalHistoryPage = () => {
  const [historyId, setHistoryId] = useState("");
  const [historyTitle, setHistoryTitle] = useState("");
  const [historyCommand, setHistoryCommand] = useState("");
  const [historyContent, setHistoryContent] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const id = readHistoryIdFromUrl();
    setHistoryId(id);

    if (!id) {
      setError("saved history id is required");
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    const apiBase = getApiBase();
    const historyUrl = `${apiBase}/api/terminal/tmux/saved-history?id=${encodeURIComponent(id)}`;

    void fetch(historyUrl, { signal: controller.signal })
      .then(async (response) => {
        const payload = await response.json().catch(() => null);
        if (!response.ok) {
          throw new Error(String(payload?.error || "failed to load saved terminal history"));
        }
        return payload as SavedHistoryResponse;
      })
      .then((payload) => {
        setHistoryId(payload.id || id);
        setHistoryTitle(formatSavedAt(payload.saved_at) || payload.title || "");
        setHistoryCommand(payload.command || "");
        setHistoryContent(payload.content || "");
        setError("");
      })
      .catch((fetchError: unknown) => {
        if (controller.signal.aborted) return;
        setError(fetchError instanceof Error ? fetchError.message : "failed to load saved terminal history");
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, []);

  const topBarText = useMemo(() => {
    if (historyCommand && historyTitle) return `${historyTitle} · ${historyCommand}`;
    if (historyTitle) return historyTitle;
    if (historyId) return `saved terminal history: ${historyId}`;
    return "saved terminal history";
  }, [historyCommand, historyId, historyTitle]);

  return (
    <MainLayout title="Saved Terminal History">
      <div style={{ height: "calc(100vh - 60px)", overflow: "hidden" }}>
        <TerminalHistoryViewer
          pageTitle="Saved Terminal History"
          topBarText={topBarText}
          loading={loading}
          loadingText="Loading saved terminal history..."
          error={error}
          content={historyContent}
          fitParent
        />
      </div>
    </MainLayout>
  );
};

export default SavedTerminalHistoryPage;

export const getStaticProps = async (context: GetStaticPropsContext) => {
  return {
    props: {
      ...(await serverSideTranslations(context.locale ?? "en", [
        "common",
      ])),
    },
  };
};
