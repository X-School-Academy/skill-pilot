project-root/
├─ README.md                         # What this repo is, AI agent should update this file from time to time
├─ ideas.md                          # The start engine of the AI builder
│
├─ dev-swarm/                       # AI builder framework and skills
│  └─ docs/
│     ├─ repository-structure.md     # This file
│     └─ source-code-structure.md    # Guide for defining {SRC}/ structure in tech specs
│
│  NOTE:
│  - This is the max doc list for each stage (large-scale projects).
│  - The files structure under each stage from 00 to 11 are just samples.
│  - Each project is different, it needs to have different design document files, different file names.
│  - Do not copy these structure directly without analysis the project actually need to avoid any over development.
│  - For a small project create tons of documents files is bad practice.
│  - Smaller scale projects can skip stages/files.
│  - Example for very small projects (simple scripts):
│    00-init-ideas/README.md         # How to implement `{SRC}/script_name.sh` or refined requirements
│    {SRC}/script_name.sh              # The script itself
│
├─ 00-init-ideas/                    # Stage 0: define the problem
│  ├─ README.md                      # Project and folder overview and guide
│  ├─ problem-solution.md            # Clear problem definition and solution
│  ├─ target-users.md                # Who has the problem (high-level), primary audience
│  ├─ value-proposition.md           # Why this solution matters and the core benefits
│  └─ owner-requirement.md           # From ideas.md + owner constraints for later stages
│
├─ 01-market-research/               # Stage 1: validate problem + understand landscape
│  ├─ README.md                      # Folder overview and guide
│  ├─ market-overview.md             # Market size, trends, growth drivers
│  ├─ competitor-analysis.md         # Direct/indirect competitors, their strengths/weaknesses
│  ├─ gap-analysis.md                # Unmet needs, opportunities competitors miss
│  ├─ pricing-research.md            # How competitors price, willingness to pay signals
│  └─ validation-findings.md         # Evidence the problem is real (interviews, surveys, data)
│
├─ 02-personas/                      # Stage 2: who uses it + user stories (business language)
│  ├─ README.md                      # Folder overview and guide
│  ├─ persona-primary.md             # Primary persona
│  ├─ persona-secondary.md           # Secondary persona (optional)
│  └─ user-stories.md                # Prioritized user stories (no technical design)
│
├─ 03-mvp/                           # Stage 3: MVP scope and success metrics (what NOT to build)
│  ├─ README.md                      # Folder overview and guide
│  ├─ mvp-scope.md                   # MVP definition: smallest testable product
│  ├─ out-of-scope.md                # Explicit exclusions (prevents PRD bloat)
│  └─ success-metrics.md             # Usage/retention/conversion/learning metrics
│
├─ 04-tech-research/                 # Stage 4: validate technical feasibility (PoCs, Spikes)
│  ├─ README.md                      # Folder overview and guide
│  ├─ research-plan.md               # What needs to be researched/validated
│  ├─ research-1-topic-results.md    # Findings for topic 1
│  └─ research-1-topic/              # Code and assets for research topic 1
│
├─ 05-prd/                           # Stage 5: product behavior locked here (still not tech stack)
│  ├─ README.md                      # Folder overview and guide
│  ├─ prd.md                         # Product overview/goals/users/journeys + MVP alignment
│  ├─ functional-requirements.md     # What the product must do (behaviors)
│  ├─ non-functional-requirements.md # Performance/security/compliance requirements
│  └─ out-of-scope.md                # PRD-level exclusions
│
├─ 06-ux/                            # Stage 6: how it feels to use (flows, states, errors)
│  ├─ README.md                      # Folder overview and guide
│  ├─ user-flows.md                  # UX flow diagrams (can include Mermaid)
│  ├─ interaction-specs.md           # States, transitions, interaction rules
│  ├─ edge-cases.md                  # Edge cases + expected outcomes
│  ├─ accessibility.md               # Accessibility requirements/checklist
│  └─ mockup/                        # Static HTML/CSS/JS mockups or a single HTML file (optional)
│
├─ 07-architecture/                  # Stage 7: system shape (structure, not frameworks)
│  ├─ README.md                      # Folder overview and guide
│  ├─ system-overview.md             # Major components + responsibilities
│  ├─ architecture-diagram.md        # Diagram (Mermaid or image link) showing system components
│  ├─ data-flow.md                   # Request/data flow across frontend/backend/db/external services
│  └─ deployment-boundaries.md       # Local vs cloud boundaries, trust zones, scaling assumptions
│
├─ 08-tech-specs/                    # Stage 8: engineering decisions & standards (policy level)
│  ├─ README.md                      # Folder overview and guide
│  ├─ tech-solution-research.md      # Research for frameworks/providers/models/tools
│  ├─ tech-stack.md                  # Languages/frameworks/db/cloud provider choices
│  ├─ theme-standards.md             # UI theme rules (fonts/sizes/colors) if doing UI
│  ├─ coding-standards.md            # Code style rules, repo conventions, naming, formatting
│  ├─ source-code-structure.md       # Define the source code structure under folder `{SRC}/`
│  ├─ testing-standards.md           # Required tests, naming, running, minimum gates
│  └─ security-standards.md          # Secure coding rules, scanning, logging redaction rules
│
├─ 09-devops/                        # Stage 9: development environment foundation (tooling + dev stack)
│  ├─ README.md                      # Folder overview and guide
│  ├─ ci-pipeline.md                 # Continuous Integration
│  ├─ github-setup.md                # GitHub repo settings, branch protection, PR templates
│  ├─ mcp-setup.md                   # MCP tool setup: Playwright/GitHub/AWS + permissions model
│  └─ vscode-devcontainer.md         # VS Code Dev Container + Docker configuration
│
├─ 10-sprints/                       # Stage 10: AI-accelerated development execution with backlog types
│  ├─ README.md                      # Folder overview and guide
│  ├─ sprint-feature-proposal.md     # Proposed sprint feature list for user approval before creating sprints/backlogs
│  │
│  ├─ user-auth/                      # Backlogs of each sprint
│  │  ├─ README.md                    # Sprint overview, status, and plan
│  │  ├─ FEATURE-auth-login.md        # New feature request
│  │  ├─ CHANGE-login-error.md        # Feature change request
│  │  ├─ BUG-login-error.md           # Bug fix
│  │  └─ IMPROVE-rate-limits.md       # Improvement/refactor
│  │
│  └─ profile-basics/
│     └─ ...
│
├─ 11-deployment/                    # Stage 11: cloud infra + deploy process + release verification
│  ├─ README.md                      # Folder overview and guide
│  ├─ cd-pipeline.md                 # Continuous Delivery or Deployment
│  │
│  ├─ _templates/                    # Deployment templates (repeatable and safe)
│  │  ├─ README.md                    # Templates overview and usage guide
│  │  ├─ deploy-plan.template.md      # Plan: goal, infra changes, steps, validation, rollback
│  │  ├─ infra.template.md            # Infra summary for a service/environment
│  │  └─ rollback.template.md         # Rollback procedure template
│  │
│  ├─ infra/                         # Cloud architecture/runbooks (what exists and why)
│  │  ├─ README.md                    # Infrastructure overview and index
│  │  ├─ aws-overview.md              # High-level AWS layout and boundaries
│  │  ├─ ec2.md                       # EC2 deployment approach (systemd/docker, ports, security groups)
│  │  ├─ lambda.md                    # Lambda functions approach (packaging, triggers, limits)
│  │  ├─ iam-security.md              # IAM principles, least privilege, credential handling rules
│  │  ├─ networking.md                # VPC/subnets/security groups/load balancer (if used)
│  │  └─ storage.md                   # S3/CloudFront/RDS choices (if used)
│  │
│  ├─ releases/                      # Versioned releases (production-ready output)
│  │  ├─ README.md                    # Releases index and versioning guide
│  │  ├─ v0.1.0/                      # One release = deployable bundle + proof
│  │  │  ├─ README.md                 # Release overview and summary
│  │  │  ├─ release-notes.md          # What changed, highlights
│  │  │  ├─ verification.md           # Smoke tests, URLs, screenshots, key metrics
│  │  │  └─ rollback.md               # Rollback plan for this release
│  │  └─ changelog.md                 # Running changelog across releases
│  │
│  └─ evidence/                      # Proof of deployments (commands, console screenshots, URLs)
│     ├─ README.md                    # Evidence index and guide
│     ├─ E-deploy-staging.md          # Staging deployment evidence
│     └─ E-deploy-production.md       # Production deployment evidence
│
├─ 99-archive/                       # Finished projects
│
├─ features/                         # AI compressed product knowledge (AI loads on-demand per backlog)
│  ├─ README.md                      # Features index and overview
│  ├─ features-index.md              # Entry point: list of feature files + short descriptions (must stay small)
│  │
│  ├─ flows/                         # Cross-feature flows (only when behavior spans multiple features)
│  │  ├─ README.md                   # Flows index and guide
│  │  └─ auth-login.md               # Example flow doc (can be renamed to FLOW-xxx-*.md if you want IDs)
│  │
│  ├─ contracts/                     # Interfaces/contracts (HTTP APIs, internal interfaces, DB schema contracts)
│  │  ├─ README.md                   # Contracts index and guide
│  │  └─ auth-login.md               # Example contract doc
│  │
│  ├─ impl/                          # Implementation notes (how it is built, pitfalls, code pointers)
│  │  ├─ README.md                   # Implementation docs index and guide
│  │  └─ auth-login.md               # Example impl doc
│  │
│  └─ auth-login.md                  # Feature definition (WHAT/WHY/SCOPE) for the auth-login feature
│
├─ {SRC}/                              # The codebase (AI modifies this)
│  ├─ README.md                      # Codebase overview and structure guide
│  ├─ frontend/                      # UI code
│  │  └─ README.md                   # Frontend structure and getting started
│  └─ backend/                       # API/services code
│     └─ README.md                   # Backend structure and getting started
