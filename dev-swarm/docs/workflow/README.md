# Dev-Swarm Development Workflow

This diagram illustrates the complete AI-driven software development workflow from initial idea to project archive.

## Overview

The dev-swarm system guides projects through structured development stages:

1. **User Input** → `/ideas-refine` (using template) → `ideas.md`
2. **Each Stage** follows a two-step pattern:
   - Step 1: Create proposal (README.md)
   - Step 2: Create stage files after user approval
   - Some stages have special subtasks (tech research, UI mockups, etc.)

## Main Workflow Diagram

```mermaid
flowchart TB
    subgraph INPUT["1. User Input"]
        UI[/"User Ideas"/]
        IR["/ideas-refine<br/>(using ideas-template.md)"]
        IM["ideas.md"]
    end

    subgraph STAGE_PATTERN["2. Stage Pattern (All Stages)"]
        direction TB
        SP1["Step 1: Create Proposal<br/>(README.md)"]
        APR1{{"User Approval"}}
        SP2["Step 2: Create Stage Files"]
        APR2{{"User Approval"}}
        SUB["Step 3: Execute Subtasks<br/>(if any)"]
    end

    subgraph STAGES["3. Development Stages"]
        direction TB
        S00["00-init-ideas ★"]
        S01["01-market-research"]
        S02["02-personas"]
        S03["03-mvp"]
        S04["04-tech-research"]
        S05["05-prd ★"]
        S06["06-ux"]
        S07["07-architecture"]
        S08["08-tech-specs ★"]
        S09["09-devops"]
        S10["10-sprints ★"]
        S11["11-deployment"]
        S99["99-archive"]
    end

    %% Input Flow
    UI --> IR
    IR --> IM
    IM --> S00

    %% Stage Pattern Flow
    SP1 --> APR1
    APR1 -->|Approved| SP2
    SP2 --> APR2
    APR2 -->|Approved| SUB

    %% Stage Flow
    S00 --> S01
    S01 --> S02
    S02 --> S03
    S03 --> S04
    S04 --> S05
    S05 --> S06
    S06 --> S07
    S07 --> S08
    S08 --> S09
    S09 --> S10
    S10 --> S11
    S11 --> S99

    %% Styling
    classDef required fill:#4CAF50,stroke:#2E7D32,color:#fff
    classDef skippable fill:#2196F3,stroke:#1565C0,color:#fff
    classDef input fill:#FF9800,stroke:#E65100,color:#fff
    classDef pattern fill:#9C27B0,stroke:#6A1B9A,color:#fff
    classDef approval fill:#FFC107,stroke:#FF8F00,color:#000
    classDef archive fill:#607D8B,stroke:#37474F,color:#fff

    class S00,S05,S08,S10 required
    class S01,S02,S03,S04,S06,S07,S09,S11 skippable
    class UI,IR,IM input
    class SP1,SP2,SUB pattern
    class APR1,APR2 approval
    class S99 archive
```

## Stage Subtasks Diagram

```mermaid
flowchart LR
    subgraph S04_SUB["04-tech-research Subtasks"]
        direction TB
        S04_PROP["1. Approve Stage Proposal"]
        S04_README["2. Create ALL Research READMEs"]
        S04_APR{{"User Approval<br/>(All READMEs)"}}

        subgraph TOPIC_LOOP["3. For Each Research Topic"]
            direction TB
            T_EXEC["Execute Research"]
            T_CODE["Write PoC Code"]
            T_TEST["Write Tests"]
            T_RES["Document Results"]
            T_NEXT["Next Topic"]

            T_EXEC --> T_CODE
            T_CODE --> T_TEST
            T_TEST --> T_RES
            T_RES --> T_NEXT
        end

        S04_PROP --> S04_README
        S04_README --> S04_APR
        S04_APR -->|Approved| TOPIC_LOOP
    end

    subgraph S06_SUB["06-ux Subtasks"]
        direction TB
        S06_PROP["1. Approve Stage Proposal"]
        S06_FILES["2. Create Stage Files<br/>(incl. mockup/README.md)"]
        S06_APR{{"User Approval"}}
        S06_CHECK{"Has design-ui-mockup/?"}

        subgraph MOCKUP_FLOW["3. Create Mockup Files"]
            direction TB
            M_FILES["Create HTML/CSS/JS"]
            M_CSS["styles.css"]
            M_NAV["navigation.js"]
            M_PAGES["page1.html, page2.html, ..."]

            M_FILES --> M_CSS
            M_FILES --> M_NAV
            M_FILES --> M_PAGES
        end

        S06_PROP --> S06_FILES
        S06_FILES --> S06_APR
        S06_APR -->|Approved| S06_CHECK
        S06_CHECK -->|Yes| MOCKUP_FLOW
        S06_CHECK -->|No| S06_DONE["Done"]
    end

    subgraph S09_SUB["09-devops Subtasks"]
        direction TB
        S09_PROP["1. Create Proposal<br/>(README.md)"]
        S09_FILES["2. Create Stage Files"]
        S09_EXEC["3. Execute Tasks<br/>(if any)"]
        S09_PROP --> S09_FILES --> S09_EXEC
    end

    subgraph S10_SUB["10-sprints Subtasks"]
        direction TB
        PLAN["Create Development Plan"]
        SPRINT["Create Sprint Folders"]

        subgraph BACKLOG["Each Backlog"]
            direction LR
            DEV["/dev"]
            REV["/review"]
            TST["/test"]
            DEV --> REV --> TST
        end

        PLAN --> SPRINT
        SPRINT --> BACKLOG
    end

    subgraph S11_SUB["11-deployment Subtasks"]
        direction TB
        S11_PROP["1. Create Proposal<br/>(README.md)"]
        S11_FILES["2. Create Stage Files"]
        S11_EXEC["3. Execute Tasks<br/>(if any)"]
        S11_PROP --> S11_FILES --> S11_EXEC
    end

    subgraph S99_SUB["99-archive / restore"]
        direction TB
        ARCH["Archive Project"]
        RST["Restore Project"]
    end

    %% Styling
    classDef approval fill:#FFC107,stroke:#FF8F00,color:#000
    classDef decision fill:#9C27B0,stroke:#6A1B9A,color:#fff

    class S04_APR,S06_APR approval
    class S06_CHECK decision
```

## Sprint Workflow Detail

```mermaid
flowchart TB
    subgraph SPRINT_CMD["Sprint Commands"]
        SC["/sprint [name]"]
        BC["/backlog [name]"]
        DC["/dev [name]"]
        RC["/review [name]"]
        TC["/test [name]"]
    end

    subgraph SPRINT_EXEC["Sprint Execution"]
        direction TB
        SF["SPRINT-XX-name/"]
        BF1["FEATURE-01-*.md"]
        BF2["CHANGE-02-*.md"]
        BF3["BUG-03-*.md"]
        BF4["IMPROVE-04-*.md"]
    end

    subgraph BACKLOG_EXEC["Backlog Execution"]
        direction LR
        D["Development<br/>(code-development)"]
        R["Review<br/>(code-review)"]
        T["Test<br/>(code-test)"]
        D --> R --> T
    end

    SC --> SF
    SF --> BF1 & BF2 & BF3 & BF4
    BC --> BF1
    BF1 --> BACKLOG_EXEC
    BF2 --> BACKLOG_EXEC
    BF3 --> BACKLOG_EXEC
    BF4 --> BACKLOG_EXEC

    DC -.-> D
    RC -.-> R
    TC -.-> T

    classDef cmd fill:#9C27B0,stroke:#6A1B9A,color:#fff
    classDef folder fill:#2196F3,stroke:#1565C0,color:#fff
    classDef exec fill:#4CAF50,stroke:#2E7D32,color:#fff

    class SC,BC,DC,RC,TC cmd
    class SF,BF1,BF2,BF3,BF4 folder
    class D,R,T exec
```

## Stage Details

| Stage | Name | Required | Special Subtasks |
|-------|------|----------|------------------|
| 00 | init-ideas | ★ Yes | - |
| 01 | market-research | No | Web research, competitor analysis |
| 02 | personas | No | - |
| 03 | mvp | No | Feature prioritization (MoSCoW, RICE) |
| 04 | tech-research | No | Create ALL research READMEs → approval → execute each topic (PoC code + tests + results) |
| 05 | prd | ★ Yes | - |
| 06 | ux | No | Create stage files (incl. mockup/README.md) → approval → create mockup files |
| 07 | architecture | No | Create diagrams (C4, data flow, etc.) |
| 08 | tech-specs | ★ Yes | - |
| 09 | devops | No | Proposal → files → execute tasks (if any) |
| 10 | sprints | ★ Yes | Create sprints, run dev/review/test |
| 11 | deployment | No | Proposal → files → execute tasks (if any) |
| 99 | archive | - | Single action (archive or restore) |

## Commands Reference

| Command | Description |
|---------|-------------|
| `/ideas-refine` | Refine ideas.md using ideas-template.md |
| `/stage [n]` | Start stage n (0-11, 99) |
| `/skip [n]` | Skip stage n by creating SKIP.md |
| `/sprint [name]` | Process all backlogs in a sprint |
| `/backlog [name]` | Process single backlog (dev + review + test) |
| `/dev [name]` | Development phase only |
| `/review [name]` | Review phase only |
| `/test [name]` | Test phase only |
| `/stage restore [name]` | Restore project from 99-archive |

## Legend

- **★ Green (Required)**: Non-skippable stages (00, 05, 08, 10)
- **Blue (Skippable)**: Optional stages (create SKIP.md to skip)
- **Orange (Input)**: User input and ideas refinement
- **Purple (Commands)**: Slash commands
- **Yellow (Approval)**: User approval checkpoints
- **Gray (Archive)**: Archive and restore operations
