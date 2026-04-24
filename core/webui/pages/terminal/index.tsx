import React, { useCallback, useEffect, useRef, useState } from "react";
import Head from "next/head";
import type { IDisposable, Terminal as XTerm } from "@xterm/xterm";
import type { FitAddon as XtermFitAddon } from "@xterm/addon-fit";

import { getApiBase } from "../../libs/api-base";

type WsMessage = {
  type: "output" | "error";
  data?: string;
  error?: string;
};

type TerminalTarget = {
  command: string;
  session: string | null;
};

const isProtectedSession = (session: string | null): boolean => {
  if (!session) return false;
  return (
    session.startsWith("sp-engine-") ||
    session.startsWith("sp-webui-")
  );
};

const isWebuiLiveSession = (session: string | null): boolean =>
  Boolean(session && session.startsWith("webui-live-"));

const toWsBase = (base: string): string => {
  const normalized = base.replace("://localhost:", "://127.0.0.1:");
  if (normalized.startsWith("https://")) return `wss://${normalized.slice("https://".length)}`;
  if (normalized.startsWith("http://")) return `ws://${normalized.slice("http://".length)}`;
  return normalized;
};

type TerminalTargetExt = TerminalTarget & {
  readonly: boolean;
  allowKill: boolean;
  compactChrome: boolean;
};

type ProjectLinkMatch = {
  displayText: string;
  fullPath: string;
  sourceStart: number;
  sourceEnd: number;
};

const escapeRegex = (value: string): string => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

const trimTrailingPunctuation = (value: string): string =>
  value.replace(/[),.;:[\]{}]+$/g, "");

const buildProjectLinkMatches = (line: string, projectRoot: string): ProjectLinkMatch[] => {
  const matches: ProjectLinkMatch[] = [];
  const seen = new Set<string>();

  const rootPattern = new RegExp(`${escapeRegex(projectRoot)}(?:\\/[^\\s:]+)*`, "g");
  let absoluteMatch: RegExpExecArray | null;
  while ((absoluteMatch = rootPattern.exec(line)) !== null) {
    const raw = trimTrailingPunctuation(absoluteMatch[0]);
    if (!raw.startsWith(projectRoot)) continue;
    const key = `abs:${absoluteMatch.index}:${raw}`;
    if (seen.has(key)) continue;
    seen.add(key);
    matches.push({
      displayText: raw.slice(projectRoot.length + 1) || raw,
      fullPath: raw,
      sourceStart: absoluteMatch.index,
      sourceEnd: absoluteMatch.index + raw.length,
    });
  }

  const relativePattern = /@([A-Za-z0-9._/-]+)/g;
  let relativeMatch: RegExpExecArray | null;
  while ((relativeMatch = relativePattern.exec(line)) !== null) {
    const relativeRaw = trimTrailingPunctuation(relativeMatch[1]);
    if (!relativeRaw || relativeRaw.startsWith("/")) continue;
    const fullPath = `${projectRoot}/${relativeRaw}`.replace(/\/+/g, "/");
    const key = `rel:${relativeMatch.index}:${relativeRaw}`;
    if (seen.has(key)) continue;
    seen.add(key);
    matches.push({
      displayText: relativeRaw,
      fullPath,
      sourceStart: relativeMatch.index,
      sourceEnd: relativeMatch.index + 1 + relativeRaw.length,
    });
  }

  return matches;
};

const readTargetFromUrl = (): TerminalTargetExt => {
  if (typeof window === "undefined") return { command: "top", session: null, readonly: false, allowKill: false, compactChrome: false };
  const params = new URLSearchParams(window.location.search);
  const isReadonly = params.get("readonly") === "1";
  const allowKill = params.get("allowKill") === "1";
  const compactChrome = params.get("compact") === "1";
  const session = params.get("session");
  if (session && session.trim()) {
    const readonlyFlag = isReadonly ? " -r" : "";
    return {
      command: `tmux attach -t ${session.trim()}${readonlyFlag}`,
      session: session.trim(),
      readonly: isReadonly,
      allowKill,
      compactChrome,
    };
  }
  const value = params.get("command");
  return {
    command: value && value.trim() ? value.trim() : "top",
    session: null,
    readonly: false,
    allowKill: false,
    compactChrome,
  };
};

const TerminalPage = () => {
  const terminalContainerRef = useRef<HTMLDivElement | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const xtermRef = useRef<XTerm | null>(null);
  const fitAddonRef = useRef<XtermFitAddon | null>(null);
  const pendingResizeRef = useRef<{ cols: number; rows: number } | null>(null);
  const lastSentResizeRef = useRef<{ cols: number; rows: number } | null>(null);
  const [connected, setConnected] = useState(false);
  const [isOpen, setIsOpen] = useState(true);
  const [command, setCommand] = useState("top");
  const [sessionName, setSessionName] = useState<string | null>(null);
  const [isReadonly, setIsReadonly] = useState(false);
  const [allowReadonlyKill, setAllowReadonlyKill] = useState(false);
  const [compactChrome, setCompactChrome] = useState(false);

  const fitAndReadSize = useCallback(() => {
    const fitAddon = fitAddonRef.current;
    const term = xtermRef.current;
    if (!fitAddon || !term) return { cols: 120, rows: 30 };
    fitAddon.fit();
    return {
      cols: Math.max(20, term.cols || 120),
      rows: Math.max(5, term.rows || 30),
    };
  }, []);

  const sendResize = useCallback((forceFit: boolean = false) => {
    const term = xtermRef.current;
    if (!term) return;
    let cols = Math.max(20, term.cols || 120);
    let rows = Math.max(5, term.rows || 30);
    if (forceFit) {
      const measured = fitAndReadSize();
      cols = measured.cols;
      rows = measured.rows;
    }
    pendingResizeRef.current = { cols, rows };
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    const last = lastSentResizeRef.current;
    if (last && last.cols === cols && last.rows === rows) {
      pendingResizeRef.current = null;
      return;
    }
    ws.send(JSON.stringify({ type: "resize", cols, rows }));
    lastSentResizeRef.current = { cols, rows };
    pendingResizeRef.current = null;
  }, [fitAndReadSize]);

  const handleClose = useCallback(() => {
    const ws = wsRef.current;
    setIsOpen(false);
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "close" }));
      ws.close();
    }
    wsRef.current = null;
    pendingResizeRef.current = null;
    lastSentResizeRef.current = null;
    setConnected(false);
  }, []);

  const handleKillSession = useCallback(() => {
    const currentSession = sessionName;
    if (!currentSession) return;
    const apiBase = getApiBase();
    void fetch(`${apiBase}/api/terminal/tmux/kill`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session: currentSession }),
    }).catch(() => {});
    handleClose();
  }, [sessionName, handleClose]);

  const handleBackground = useCallback(() => {
    if (typeof window === "undefined") return;
    const processesUrl = "/?view=processes";
    window.open(processesUrl, "_blank", "noopener,noreferrer");
  }, []);

  const handleHistory = useCallback(() => {
    if (typeof window === "undefined" || !sessionName) return;
    const historyUrl = `/terminal/history?session=${encodeURIComponent(sessionName)}`;
    window.open(historyUrl, "_blank", "noopener,noreferrer");
  }, [sessionName]);

  useEffect(() => {
    if (!isOpen || !isWebuiLiveSession(sessionName)) return undefined;
    const apiBase = getApiBase();
    const sendSessionHeartbeat = () => {
      void fetch(`${apiBase}/api/terminal/tmux/heartbeat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session: sessionName }),
        keepalive: true,
      }).catch(() => {});
    };
    sendSessionHeartbeat();
    const heartbeatInterval = window.setInterval(sendSessionHeartbeat, 10000);
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") sendSessionHeartbeat();
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      window.clearInterval(heartbeatInterval);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [isOpen, sessionName]);

  useEffect(() => {
    if (!isOpen) return;
    if (!terminalContainerRef.current) return;

    const currentTarget = readTargetFromUrl();
    setCommand(currentTarget.command);
    setSessionName(currentTarget.session);
    setIsReadonly(currentTarget.readonly);
    setAllowReadonlyKill(currentTarget.allowKill);
    setCompactChrome(currentTarget.compactChrome);

    let disposed = false;
    let term: XTerm | null = null;
    let dataDispose: IDisposable = { dispose: () => undefined };
    let binaryDispose: IDisposable = { dispose: () => undefined };
    let resizeDispose: IDisposable = { dispose: () => undefined };
    let projectLinkDispose: IDisposable = { dispose: () => undefined };

    const connectSocket = () => {
      if (wsRef.current || !term) return;
      const { cols: initialCols, rows: initialRows } = fitAndReadSize();
      const base = toWsBase(getApiBase());
      const readonlyParam = currentTarget.readonly ? "&readonly=1" : "";
      const wsPath = currentTarget.session
        ? `/api/terminal/ws?session=${encodeURIComponent(currentTarget.session)}&cols=${initialCols}&rows=${initialRows}&binary=1${readonlyParam}`
        : `/api/terminal/ws?command=${encodeURIComponent(currentTarget.command)}&cols=${initialCols}&rows=${initialRows}&binary=1`;
      const url = `${base}${wsPath}`;
      const connectStart = performance.now();
      // Debug timing to diagnose delayed websocket handshake in browser.
      console.info("[terminal] ws_connect_start", {
        at: new Date().toISOString(),
        command: currentTarget.command,
        session: currentTarget.session,
        url,
        cols: initialCols,
        rows: initialRows,
      });

      const ws = new WebSocket(url);
      ws.binaryType = "arraybuffer";
      wsRef.current = ws;
      lastSentResizeRef.current = null;
      const textDecoder = new TextDecoder();

      ws.onopen = () => {
        const activeTerm = term;
        if (!activeTerm) return;
        const elapsedMs = Math.round(performance.now() - connectStart);
        console.info("[terminal] ws_open", { at: new Date().toISOString(), elapsedMs, command: currentTarget.command, session: currentTarget.session });
        setConnected(true);
        activeTerm.writeln(`$ ${currentTarget.command}`);
        sendResize(true);
      };

      ws.onmessage = (event: MessageEvent<string | ArrayBuffer | Blob>) => {
        const activeTerm = term;
        if (!activeTerm) return;
        if (typeof event.data !== "string") {
          if (event.data instanceof ArrayBuffer) {
            activeTerm.write(textDecoder.decode(new Uint8Array(event.data), { stream: true }));
            return;
          }
          void event.data.arrayBuffer().then((buffer) => {
            activeTerm.write(textDecoder.decode(new Uint8Array(buffer), { stream: true }));
          });
          return;
        }

        let payload: WsMessage;
        try {
          payload = JSON.parse(event.data) as WsMessage;
        } catch {
          activeTerm.write(event.data);
          return;
        }
        if (payload.type === "output") activeTerm.write(payload.data || "");
        if (payload.type === "error") activeTerm.writeln(`\r\n[error] ${payload.error || "terminal error"}`);
      };

      ws.onclose = () => {
        const elapsedMs = Math.round(performance.now() - connectStart);
        console.info("[terminal] ws_close", { at: new Date().toISOString(), elapsedMs, command: currentTarget.command, session: currentTarget.session });
        setConnected(false);
        lastSentResizeRef.current = null;
        wsRef.current = null;
      };

      ws.onerror = () => {
        const elapsedMs = Math.round(performance.now() - connectStart);
        console.error("[terminal] ws_error", { at: new Date().toISOString(), elapsedMs, command: currentTarget.command, session: currentTarget.session });
      };
    };

    let connectRaf1 = 0;
    let connectRaf2 = 0;
    let connectFallback = 0;
    let resizeRaf = 0;
    const triggerFit = () => {
      if (resizeRaf) cancelAnimationFrame(resizeRaf);
      resizeRaf = requestAnimationFrame(() => {
        if (fitAddonRef.current) {
          try {
            fitAddonRef.current.fit();
          } catch (e) {
            console.warn("[terminal] fit failed", e);
          }
        }
        sendResize(false);
      });
    };
    const triggerForcedFit = () => {
      if (resizeRaf) cancelAnimationFrame(resizeRaf);
      resizeRaf = requestAnimationFrame(() => {
        sendResize(true);
      });
    };

    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") triggerForcedFit();
    };
    const onWindowLoad = () => triggerForcedFit();

    window.addEventListener("resize", triggerFit);
    window.addEventListener("load", onWindowLoad);
    document.addEventListener("visibilitychange", onVisibilityChange);
    const resizeObserver = new ResizeObserver(() => {
      triggerFit();
    });
    if (panelRef.current) resizeObserver.observe(panelRef.current);
    if (terminalContainerRef.current) resizeObserver.observe(terminalContainerRef.current);

    void (async () => {
      try {
        const [xtermMod, fitMod, imageMod, clipboardMod, unicode11Mod, webLinksMod] = await Promise.all([
          import("@xterm/xterm"),
          import("@xterm/addon-fit"),
          import("@xterm/addon-image"),
          import("@xterm/addon-clipboard"),
          import("@xterm/addon-unicode11"),
          import("@xterm/addon-web-links"),
        ]);
        if (disposed || !terminalContainerRef.current) return;

        const { Terminal } = xtermMod;
        const { FitAddon } = fitMod;
        const { ImageAddon } = imageMod;
        const { ClipboardAddon } = clipboardMod;
        const { Unicode11Addon } = unicode11Mod;
        const { WebLinksAddon } = webLinksMod;

        const fitAddon = new FitAddon();
        const clipboardAddon = new ClipboardAddon();
        const imageAddon = new ImageAddon({
          iipSupport: true,
          sixelSupport: true,
          showPlaceholder: true,
          storageLimit: 128,
        });
        const unicode11Addon = new Unicode11Addon();
        const webLinksAddon = new WebLinksAddon((event, uri) => {
          event.preventDefault();
          window.open(uri, "_blank", "noopener,noreferrer");
        });

        term = new Terminal({
          allowProposedApi: true,
          convertEol: true,
          cursorBlink: true,
          fontFamily: "Menlo, Monaco, 'Courier New', monospace",
          fontSize: 13,
          theme: {
            background: "#0b0f19",
            foreground: "#d7e2ff",
          },
        });
        xtermRef.current = term;
        fitAddonRef.current = fitAddon;
        term.loadAddon(fitAddon);
        term.loadAddon(clipboardAddon);
        term.loadAddon(webLinksAddon);
        term.loadAddon(imageAddon);
        term.loadAddon(unicode11Addon);
        term.unicode.activeVersion = "11";
        term.open(terminalContainerRef.current);
        fitAddon.fit();
        term.focus();

        try {
          const infoResp = await fetch(`${getApiBase()}/api/files/info`, { credentials: "include" });
          const infoData = await infoResp.json().catch(() => ({}));
          const projectRoot =
            typeof infoData.root === "string" && infoData.root.trim()
              ? infoData.root.trim().replace(/\/$/, "")
              : "";

          if (projectRoot) {
            projectLinkDispose = term.registerLinkProvider({
              provideLinks: (bufferLineNumber, callback) => {
                const activeTerm = xtermRef.current;
                if (!activeTerm) {
                  callback(undefined);
                  return;
                }

                const line = activeTerm.buffer.active.getLine(bufferLineNumber - 1);
                if (!line) {
                  callback(undefined);
                  return;
                }

                const text = line.translateToString(true);
                const links = buildProjectLinkMatches(text, projectRoot).map((match) => ({
                  text: match.displayText,
                  range: {
                    start: { x: match.sourceStart + 1, y: bufferLineNumber },
                    end: { x: match.sourceEnd + 1, y: bufferLineNumber },
                  },
                  activate: (_event: MouseEvent, _text: string) => {
                    const target = `/file-manager?path=${encodeURIComponent(match.fullPath)}`;
                    window.open(target, "_blank", "noopener,noreferrer");
                  },
                  hover: () => {
                    activeTerm.element?.classList.add("xterm-cursor-pointer");
                  },
                  leave: () => {
                    activeTerm.element?.classList.remove("xterm-cursor-pointer");
                  },
                }));

                callback(links.length ? links : undefined);
              },
            });
          }
        } catch (error) {
          console.warn("[terminal] failed to initialize project path links", error);
        }

        if (!currentTarget.readonly) {
          dataDispose = term.onData((data: string) => {
            const ws = wsRef.current;
            if (!ws || ws.readyState !== WebSocket.OPEN) return;
            ws.send(JSON.stringify({ type: "input", data }));
          });
          binaryDispose = term.onBinary((data: string) => {
            const ws = wsRef.current;
            if (!ws || ws.readyState !== WebSocket.OPEN || data.length < 3) return;
            // Match xterm demo behavior for binary mouse protocol events.
            const sequence = `\x1b[${data.charCodeAt(0) - 32};${data.charCodeAt(1) - 32};${data.charCodeAt(2) - 32}M`;
            ws.send(JSON.stringify({ type: "input", data: sequence }));
          });
        }

        resizeDispose = term.onResize(({ cols, rows }) => {
          console.info("[terminal] resize", { cols, rows });
          sendResize(false);
        });

        connectRaf1 = requestAnimationFrame(() => {
          connectRaf2 = requestAnimationFrame(connectSocket);
        });
        connectFallback = window.setTimeout(connectSocket, 450);
        triggerForcedFit();
      } catch (error) {
        console.error("[terminal] failed to initialize xterm", error);
      }
    })();

    const fontsReady = document.fonts?.ready;
    if (fontsReady) {
      void fontsReady
        .then(() => {
          if (!disposed) triggerForcedFit();
        })
        .catch(() => undefined);
    }

    // Initial syncs to ensure correct size after layout settles and page refresh.
    const earlySync1 = window.setTimeout(triggerForcedFit, 100);
    const earlySync2 = window.setTimeout(triggerForcedFit, 350);
    const earlySync3 = window.setTimeout(triggerForcedFit, 900);

    return () => {
      disposed = true;
      window.removeEventListener("resize", triggerFit);
      window.removeEventListener("load", onWindowLoad);
      document.removeEventListener("visibilitychange", onVisibilityChange);
      resizeObserver.disconnect();
      if (connectRaf1) cancelAnimationFrame(connectRaf1);
      if (connectRaf2) cancelAnimationFrame(connectRaf2);
      window.clearTimeout(connectFallback);
      if (resizeRaf) cancelAnimationFrame(resizeRaf);
      window.clearTimeout(earlySync1);
      window.clearTimeout(earlySync2);
      window.clearTimeout(earlySync3);
      dataDispose.dispose();
      binaryDispose.dispose();
      resizeDispose.dispose();
      projectLinkDispose.dispose();

      const ws = wsRef.current;
      ws?.close();
      wsRef.current = null;
      pendingResizeRef.current = null;
      lastSentResizeRef.current = null;
      setConnected(false);
      term?.dispose();
      term = null;
      xtermRef.current = null;
      fitAddonRef.current = null;
    };
  }, [fitAndReadSize, isOpen, sendResize]);

  if (!isOpen) {
    return (
      <main className="h-screen bg-[#0f1117] text-white flex items-center justify-center">
        <p className="text-sm opacity-80">Terminal closed.</p>
      </main>
    );
  }

  const canKillReadonlySession = Boolean(
    isReadonly &&
    sessionName &&
    allowReadonlyKill &&
    !isProtectedSession(sessionName),
  );

  return (
    <>
      <Head>
        <title>Terminal</title>
      </Head>
      <main className="h-screen bg-[#0f1117] text-white flex flex-col overflow-hidden">
        <div
          ref={panelRef}
          className="flex-1 flex flex-col min-h-0"
        >
          <div className={`${compactChrome ? "h-[32px] px-2" : "h-[42px] px-3"} border-b border-[#2f3645] flex items-center justify-between bg-[#161b26] flex-shrink-0 gap-2`}>
            <div className={`${compactChrome ? "hidden" : "text-sm font-medium truncate"}`}>
              command: <code>{command}</code>{" "}
              {isReadonly
                ? connected ? "(read-only)" : "(disconnected)"
                : connected ? "(connected)" : "(disconnected)"}{" "}
              {sessionName ? `session=${sessionName}` : ""}
            </div>
            <div className={`flex gap-1 ${compactChrome ? "ml-auto" : ""}`}>
              {sessionName && (
                <button
                  type="button"
                  onClick={handleHistory}
                  className={`${compactChrome ? "rounded-sm px-2 py-0.5 text-[11px]" : "rounded px-3 py-1 text-xs"} bg-[#1d6f5f] leading-none hover:opacity-90`}
                >
                  History
                </button>
              )}
              {sessionName && !isReadonly && !isProtectedSession(sessionName) && (
                <button
                  type="button"
                  onClick={handleKillSession}
                  className={`${compactChrome ? "rounded-sm px-2 py-0.5 text-[11px]" : "rounded px-3 py-1 text-xs"} bg-[#8b1d24] leading-none hover:opacity-90`}
                >
                  Kill Session
                </button>
              )}
              {sessionName && !isReadonly && (
                <button
                  type="button"
                  onClick={handleBackground}
                  className={`${compactChrome ? "rounded-sm px-2 py-0.5 text-[11px]" : "rounded px-3 py-1 text-xs"} bg-[#1f4f8b] leading-none hover:opacity-90`}
                >
                  Processes
                </button>
              )}
              <button
                type="button"
                onClick={handleClose}
                className={`${compactChrome ? "rounded-sm px-2 py-0.5 text-[11px]" : "rounded px-3 py-1 text-xs"} bg-[#3a3f52] leading-none hover:opacity-90`}
              >
                {sessionName && !isReadonly ? "Detach" : "Close"}
              </button>
              {canKillReadonlySession && (
                <button
                  type="button"
                  onClick={handleKillSession}
                  className={`${compactChrome ? "rounded-sm px-2 py-0.5 text-[11px]" : "rounded px-3 py-1 text-xs"} bg-[#8b1d24] leading-none hover:opacity-90`}
                >
                  Kill Session
                </button>
              )}
            </div>
          </div>
          <div ref={terminalContainerRef} className="flex-1 bg-[#0b0f19]" />
        </div>
      </main>
    </>
  );
};

export default TerminalPage;
