import type { ProgressStep, StageType } from "./types";

export type StageConfig = {
  stageId: string;
  name: string;
  folder: string;
  skill: string;
  type: StageType;
  progressSteps: ProgressStep[];
};

export const STAGE_CONFIGS: StageConfig[] = [
  {
    stageId: "00",
    name: "Init Ideas",
    folder: "00-init-ideas",
    skill: "dev-swarm-stage-init-ideas",
    type: "init-ideas",
    progressSteps: [
      { key: "init", label: "Init" },
      { key: "proposal", label: "Proposal" },
      { key: "stage-files", label: "Stage Files" },
    ],
  },
  {
    stageId: "01",
    name: "Market Research",
    folder: "01-market-research",
    skill: "dev-swarm-stage-market-research",
    type: "standard",
    progressSteps: [
      { key: "proposal", label: "Proposal" },
      { key: "stage-files", label: "Stage Files" },
    ],
  },
  {
    stageId: "02",
    name: "Personas",
    folder: "02-personas",
    skill: "dev-swarm-stage-personas",
    type: "standard",
    progressSteps: [
      { key: "proposal", label: "Proposal" },
      { key: "stage-files", label: "Stage Files" },
    ],
  },
  {
    stageId: "03",
    name: "MVP",
    folder: "03-mvp",
    skill: "dev-swarm-stage-mvp",
    type: "standard",
    progressSteps: [
      { key: "proposal", label: "Proposal" },
      { key: "stage-files", label: "Stage Files" },
    ],
  },
  {
    stageId: "04",
    name: "Tech Research",
    folder: "04-tech-research",
    skill: "dev-swarm-stage-tech-research",
    type: "research",
    progressSteps: [
      { key: "proposal", label: "Proposal" },
      { key: "stage-files", label: "Stage Files" },
    ],
  },
  {
    stageId: "05",
    name: "PRD",
    folder: "05-prd",
    skill: "dev-swarm-stage-prd",
    type: "standard",
    progressSteps: [
      { key: "proposal", label: "Proposal" },
      { key: "stage-files", label: "Stage Files" },
    ],
  },
  {
    stageId: "06",
    name: "UX",
    folder: "06-ux",
    skill: "dev-swarm-stage-ux",
    type: "ux",
    progressSteps: [
      { key: "proposal", label: "Proposal" },
      { key: "stage-files", label: "Stage Files" },
    ],
  },
  {
    stageId: "07",
    name: "Architecture",
    folder: "07-architecture",
    skill: "dev-swarm-stage-architecture",
    type: "standard",
    progressSteps: [
      { key: "proposal", label: "Proposal" },
      { key: "stage-files", label: "Stage Files" },
    ],
  },
  {
    stageId: "08",
    name: "Tech Specs",
    folder: "08-tech-specs",
    skill: "dev-swarm-stage-tech-specs",
    type: "standard",
    progressSteps: [
      { key: "proposal", label: "Proposal" },
      { key: "stage-files", label: "Stage Files" },
    ],
  },
  {
    stageId: "09",
    name: "DevOps",
    folder: "09-devops",
    skill: "dev-swarm-stage-devops",
    type: "devops",
    progressSteps: [
      { key: "proposal", label: "Proposal" },
      { key: "stage-files", label: "Stage Files" },
    ],
  },
  {
    stageId: "10",
    name: "Sprints",
    folder: "10-sprints",
    skill: "dev-swarm-stage-sprints",
    type: "sprints",
    progressSteps: [
      { key: "proposal", label: "Proposal" },
      { key: "plan", label: "Plan" },
      { key: "backlogs", label: "Backlogs" },
    ],
  },
  {
    stageId: "11",
    name: "Deployment",
    folder: "11-deployment",
    skill: "dev-swarm-stage-deployment",
    type: "devops",
    progressSteps: [
      { key: "proposal", label: "Proposal" },
      { key: "stage-files", label: "Stage Files" },
    ],
  },
  {
    stageId: "99",
    name: "Archive",
    folder: "99-archive",
    skill: "dev-swarm-stage-archive",
    type: "archive",
    progressSteps: [],
  },
];

export function getStageConfig(stageId: string): StageConfig | undefined {
  return STAGE_CONFIGS.find((s) => s.stageId === stageId);
}
