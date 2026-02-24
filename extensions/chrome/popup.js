const PENDING_CONTEXT_KEY = "killPilotPendingContext";

const pageUrlEl = document.getElementById("page-url");
const selectedTextEl = document.getElementById("selected-text");
const taskDescriptionEl = document.getElementById("task-description");
const submitBtn = document.getElementById("submit-btn");
const statusEl = document.getElementById("status");

let pendingContext = {
  pageUrl: "",
  selectedText: ""
};

function renderContext() {
  pageUrlEl.textContent = pendingContext.pageUrl || "(No URL found)";
  selectedTextEl.textContent = pendingContext.selectedText || "(No selected text)";
}

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.style.color = isError ? "#b42318" : "#14683d";
}

function loadContext() {
  chrome.storage.local.get([PENDING_CONTEXT_KEY], (result) => {
    pendingContext = result[PENDING_CONTEXT_KEY] || pendingContext;
    renderContext();
  });
}

function submitTask() {
  const taskDescription = (taskDescriptionEl.value || "").trim();
  if (!taskDescription) {
    setStatus("Please enter a task description.", true);
    return;
  }

  submitBtn.disabled = true;
  setStatus("Submitting...");

  chrome.runtime.sendMessage(
    {
      type: "kill-pilot-submit-task",
      pageUrl: pendingContext.pageUrl || "",
      selectedText: pendingContext.selectedText || "",
      taskDescription
    },
    (response) => {
      submitBtn.disabled = false;
      if (chrome.runtime.lastError) {
        setStatus(`Submit failed: ${chrome.runtime.lastError.message}`, true);
        return;
      }
      if (!response || !response.ok) {
        setStatus("Submit failed. No response from background script.", true);
        return;
      }

      setStatus("Submitted. Check extension service worker logs.");
      taskDescriptionEl.value = "";
      chrome.storage.local.remove(PENDING_CONTEXT_KEY);
      setTimeout(() => {
        window.close();
      }, 150);
    }
  );
}

submitBtn.addEventListener("click", submitTask);
loadContext();
