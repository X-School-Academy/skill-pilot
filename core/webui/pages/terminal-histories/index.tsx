import React, { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/router";
import { GetStaticPropsContext } from "next";
import axios from "axios";
import { serverSideTranslations } from "next-i18next/serverSideTranslations";
import {
  ActionIcon,
  Button,
  Group,
  Loader,
  Stack,
  Text,
  Title,
  Tooltip,
  useMantineTheme,
} from "@mantine/core";
import { IconEye, IconRefresh, IconTrash } from "@tabler/icons-react";

import MainLayout from "../../components/main-layout";
import { apiUrl } from "../../libs/api-base";

const API_BASE_URL = apiUrl("/api");

interface SavedTerminalHistory {
  id: string;
  session: string;
  title: string;
  saved_at: string;
  size: number;
}

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

const TerminalHistoriesPage = () => {
  const router = useRouter();
  const theme = useMantineTheme();
  const [histories, setHistories] = useState<SavedTerminalHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyHistoryId, setBusyHistoryId] = useState<string | null>(null);
  const [error, setError] = useState("");

  const fetchHistories = useCallback(async (quiet = false) => {
    if (!quiet) setLoading(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/terminal/tmux/saved-histories`);
      setHistories(res.data?.histories || []);
      setError("");
    } catch (err: any) {
      const message = err?.response?.data?.error || "Failed to load saved terminal histories.";
      setError(String(message));
    } finally {
      if (!quiet) setLoading(false);
    }
  }, []);

  const deleteHistory = useCallback(async (history: SavedTerminalHistory) => {
    const confirmed = window.confirm(`Delete saved terminal history "${formatSavedAt(history.saved_at) || history.title}"?`);
    if (!confirmed) return;

    setBusyHistoryId(history.id);
    try {
      await axios.delete(`${API_BASE_URL}/terminal/tmux/saved-history`, { params: { id: history.id } });
      setHistories((current) => current.filter((item) => item.id !== history.id));
      setError("");
    } catch (err: any) {
      const message = err?.response?.data?.error || "Failed to delete saved terminal history.";
      setError(String(message));
    } finally {
      setBusyHistoryId(null);
    }
  }, []);

  useEffect(() => {
    void fetchHistories();
  }, [fetchHistories]);

  return (
    <MainLayout title="Session Histories">
      <main
        style={{
          minHeight: "calc(100vh - 60px)",
          background: theme.colorScheme === "dark" ? theme.colors.dark[8] : theme.colors.gray[0],
          padding: "24px",
        }}
      >
        <Stack spacing="md" maw={980} mx="auto">
          <Group position="apart" align="center">
            <div>
              <Title order={2}>Session Histories</Title>
              <Text size="sm" color="dimmed">Saved terminal histories from closed project sessions.</Text>
            </div>
            <Button
              size="xs"
              variant="default"
              leftIcon={<IconRefresh size="1rem" />}
              onClick={() => void fetchHistories()}
            >
              Refresh
            </Button>
          </Group>

          {error && <Text size="sm" color="red">{error}</Text>}

          {loading ? (
            <Group position="center" py="xl">
              <Loader size="sm" />
              <Text size="sm" color="dimmed">Loading saved histories...</Text>
            </Group>
          ) : histories.length === 0 ? (
            <Text size="sm" color="dimmed">No saved session histories yet.</Text>
          ) : (
            <Stack spacing="xs">
              {histories.map((history) => (
                <div
                  key={history.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 16,
                    border: `1px solid ${theme.colors.gray[3]}`,
                    borderRadius: 8,
                    padding: "10px 12px",
                    background: theme.colorScheme === "dark" ? theme.colors.dark[7] : "#fff",
                  }}
                >
                  <div style={{ minWidth: 0 }}>
                    <button
                      type="button"
                      onClick={() => {
                        void router.push(`/terminal-history?id=${encodeURIComponent(history.id)}`);
                      }}
                      style={{
                        border: 0,
                        padding: 0,
                        background: "transparent",
                        color: theme.colorScheme === "dark" ? theme.colors.blue[3] : theme.colors.blue[7],
                        cursor: "pointer",
                        fontSize: 14,
                        fontWeight: 700,
                        textAlign: "left",
                      }}
                    >
                      {formatSavedAt(history.saved_at) || history.title}
                    </button>
                    <Text size="xs" color="dimmed" truncate>
                      {history.session || history.id} · {history.size} bytes
                    </Text>
                  </div>
                  <Group spacing="xs" noWrap>
                    <Tooltip label="View">
                      <ActionIcon
                        variant="default"
                        aria-label="View saved history"
                        onClick={() => {
                          void router.push(`/terminal-history?id=${encodeURIComponent(history.id)}`);
                        }}
                      >
                        <IconEye size="1rem" />
                      </ActionIcon>
                    </Tooltip>
                    <Tooltip label="Delete">
                      <ActionIcon
                        variant="outline"
                        color="red"
                        aria-label="Delete saved history"
                        loading={busyHistoryId === history.id}
                        onClick={() => void deleteHistory(history)}
                      >
                        <IconTrash size="1rem" />
                      </ActionIcon>
                    </Tooltip>
                  </Group>
                </div>
              ))}
            </Stack>
          )}
        </Stack>
      </main>
    </MainLayout>
  );
};

export default TerminalHistoriesPage;

export const getStaticProps = async (context: GetStaticPropsContext) => {
  return {
    props: {
      ...(await serverSideTranslations(context.locale ?? "en", [
        "common",
      ])),
    },
  };
};
