import type { StageConfig } from "./stages";
import { getStageConfig } from "./stages";

const INIT_IDEAS_FOLDER = getStageConfig("00")?.folder ?? "00-init-ideas";
const TECH_RESEARCH_FOLDER = getStageConfig("04")?.folder ?? "04-tech-research";
const UX_FOLDER = getStageConfig("06")?.folder ?? "06-ux";
const SPRINTS_FOLDER = getStageConfig("10")?.folder ?? "10-sprints";

// --- Init Ideas (Stage 00) ---

export function refineIdeasPrompt(): string {
  return "Use the prompt defined at `.claude/commands/ideas-refine.md` to update `ideas.md`";
}

export function createProposalPrompt_InitIdeas(): string {
  return `Use agent skill \`dev-swarm-stage-init-ideas\` to create \`${INIT_IDEAS_FOLDER}/README.md\` only, then commit to git`;
}

export function createFilesPrompt_InitIdeas(): string {
  return `Use agent skill \`dev-swarm-stage-init-ideas\` to create stage files by \`${INIT_IDEAS_FOLDER}/README.md\`, then commit all to git`;
}

export function finalizePrompt_InitIdeas(): string {
  return `Use agent skill \`dev-swarm-stage-init-ideas\` to update \`${INIT_IDEAS_FOLDER}/README.md\` to reflect stage files at \`${INIT_IDEAS_FOLDER}/\`, then commit all to git`;
}

// --- Standard Stages ---

export function createProposalPrompt(config: StageConfig): string {
  return `Use agent skill \`${config.skill}\` to create \`${config.folder}/README.md\` only, then commit to git`;
}

export function createFilesPrompt(config: StageConfig): string {
  return `Use agent skill \`${config.skill}\` to create stage files by \`${config.folder}/README.md\`, then commit all to git`;
}

export function finalizePrompt(config: StageConfig): string {
  return `Use agent skill \`${config.skill}\` to update \`${config.folder}/README.md\` to reflect stage files at \`${config.folder}/\`, then commit all to git`;
}

// --- Tech Research (Stage 04) ---

export function researchPrompt(researchName: string): string {
  return `Use agent skill \`dev-swarm-stage-tech-research\` to do tech research for ${researchName}, once finished, then commit all to git`;
}

export function finalizeResearchPrompt(): string {
  return `Use agent skill \`dev-swarm-stage-tech-research\` to update \`${TECH_RESEARCH_FOLDER}/README.md\` to reflect stage files and research results at \`${TECH_RESEARCH_FOLDER}/\`, then commit all to git`;
}

// --- UX (Stage 06) ---

export function createMockupPrompt(): string {
  return "Use agent skill `dev-swarm-stage-ux` to create the UI mockup by the UI mockup readme file, once finished, then commit all to git";
}

export function finalizeUxPrompt(): string {
  return `Use agent skill \`dev-swarm-stage-ux\` to update \`${UX_FOLDER}/README.md\` to reflect stage files and UI mockup, then commit all to git`;
}

// --- DevOps (Stage 09 & 11) ---

export function executeDevOpsPrompt(config: StageConfig): string {
  return `Use agent skill \`${config.skill}\` to execute any local and remote actions based on the stages files, then commit all to git for the result`;
}

// --- Sprints (Stage 10) ---

export function createSprintPlanPrompt(): string {
  return `Use agent skill \`dev-swarm-stage-sprints\` to create development plan file \`${SPRINTS_FOLDER}/development-plan.md\`, then commit all to git`;
}

export function createBacklogsPrompt(): string {
  return "Use agent skill `dev-swarm-stage-sprints` to create all the sprints and backlogs files, then commit all to git";
}

export function developAllSprintsPrompt(): string {
  return "Use agent skill `dev-swarm-stage-sprints` do all the code development, review and test for each backlog one by one.\nOnce finish one sprint, conduct the sprint test by the readme file, then the next sprint until finish the whole project";
}

export function developSprintPrompt(sprintFolder: string): string {
  return `Use agent skill \`dev-swarm-stage-sprints\` do all the code development, review and test for each backlog one by one in this sprint ${sprintFolder} and conduct the sprint test by the readme file`;
}

export function developBacklogPrompt(backlogName: string): string {
  return `Use agent skill \`dev-swarm-stage-sprints\` do the code development, review and test for this backlog name ${backlogName}`;
}

// --- Archive (Stage 99) ---

export function archivePrompt(): string {
  return "Use agent skill `dev-swarm-stage-archive` to archive the current project, and ready to start a new project";
}
