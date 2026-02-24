export type StageStatus = "not-started" | "in-progress" | "completed" | "skipped" | "error";

export type Stage = {
  stageId: string;
  name: string;
  status: StageStatus;
  isSkippable: boolean;
  hasSkipFile: boolean;
  files: string[];
};

export type DocumentPayload = {
  path: string;
  content: string;
  contentType: "text/markdown" | "text/html";
  lastModified: string;
};

export type ConsoleEventCategory = "system" | "output" | "stderr" | "status";

export type ConsoleEvent = {
  id: string;
  timestamp: string;
  category: ConsoleEventCategory;
  message: string;
};

export type Toast = {
  message: string;
  variant: "error" | "success";
};

export type SyncResponse = {
  stages: Stage[];
  syncedAt: string;
};

export type StageType =
  | "init-ideas"
  | "standard"
  | "research"
  | "ux"
  | "devops"
  | "sprints"
  | "archive";

export type ProgressStep = {
  key: string;
  label: string;
};
