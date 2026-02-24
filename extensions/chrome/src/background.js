import { io } from "socket.io-client";

const SOCKET_SERVER_URL = process.env.SOCKET_SERVER_URL || "http://127.0.0.1:3001";
const LOCAL_CHROME_TOKEN = process.env.LOCAL_CHROME_TOKEN || "";
const CONTEXT_MENU_ID = "kill-pilot-context-menu";
const PENDING_CONTEXT_KEY = "killPilotPendingContext";

let socket = null;

function ensureSocketConnection() {
  if (socket && socket.connected) {
    return;
  }

  socket = io(SOCKET_SERVER_URL, {
    transports: ["websocket", "polling"],
    autoConnect: true,
    reconnection: true
  });

  socket.on("connect", () => {
    console.log("[Kill Pilot] Connected to webui socket server:", SOCKET_SERVER_URL);
    socket.emit("chrome_event", {
      type: "sign-in",
      token: LOCAL_CHROME_TOKEN
    });
  });

  socket.on("disconnect", (reason) => {
    console.log("[Kill Pilot] Disconnected from webui socket server:", reason);
  });

  socket.on("connect_error", (error) => {
    console.error("[Kill Pilot] Socket connection error:", error?.message || error);
  });

  socket.on("connected", (payload) => {
    console.log("[Kill Pilot] server connected event:", payload);
  });

  socket.on("assignment_event", (payload) => {
    console.log("[Kill Pilot] assignment_event:", payload);
  });

  socket.on("container_event", (payload) => {
    console.log("[Kill Pilot] container_event:", payload);
  });

  socket.on("server_event", (payload) => {
    console.log("[Kill Pilot] server_event:", payload);
  });
}

function createContextMenu() {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: CONTEXT_MENU_ID,
      title: "Kill Pilot",
      contexts: ["selection", "page"]
    });
  });
}

function openTaskPopup() {
  const popupWidth = 420;
  const popupHeight = 460;

  chrome.windows.getLastFocused({}, (currentWindow) => {
    const baseLeft = typeof currentWindow?.left === "number" ? currentWindow.left : 0;
    const baseTop = typeof currentWindow?.top === "number" ? currentWindow.top : 0;
    const baseWidth = typeof currentWindow?.width === "number" ? currentWindow.width : 1280;
    const baseHeight = typeof currentWindow?.height === "number" ? currentWindow.height : 720;

    const left = Math.max(0, Math.round(baseLeft + (baseWidth - popupWidth) / 2));
    const top = Math.max(0, Math.round(baseTop + (baseHeight - popupHeight) / 2));

    chrome.windows.create({
      url: chrome.runtime.getURL("popup.html"),
      type: "popup",
      width: popupWidth,
      height: popupHeight,
      left,
      top
    });
  });
}

chrome.runtime.onInstalled.addListener(() => {
  ensureSocketConnection();
  createContextMenu();
});

chrome.runtime.onStartup.addListener(() => {
  ensureSocketConnection();
  createContextMenu();
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId !== CONTEXT_MENU_ID) {
    return;
  }

  const context = {
    pageUrl: info.pageUrl || tab?.url || "",
    selectedText: info.selectionText || "",
    createdAt: new Date().toISOString()
  };

  chrome.storage.local.set({ [PENDING_CONTEXT_KEY]: context }, () => {
    openTaskPopup();
  });
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message || message.type !== "kill-pilot-submit-task") {
    return false;
  }

  ensureSocketConnection();

  const payload = {
    pageUrl: message.pageUrl || "",
    selectedText: message.selectedText || "",
    taskDescription: message.taskDescription || ""
  };

  console.log("[Kill Pilot] send task to webui backend:", payload);

  if (socket && socket.connected) {
    socket.emit("chrome_event", {
      type: "kill-pilot-task",
      payload
    });
  } else {
    console.warn("[Kill Pilot] Socket is not connected. Task payload only logged locally.");
  }

  sendResponse({ ok: true });
  return true;
});
