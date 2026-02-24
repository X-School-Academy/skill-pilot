---
name: dev-swarm-stage-deployment
description: Deploy to production, configure infrastructure, set up monitoring, and prepare for launch. Use when starting stage 11 (deployment) or when user asks to deploy, go-live, or launch the product.
---

# Stage 11 - Deployment

Deploy the fully developed and tested product to production environment, configure production infrastructure, set up monitoring and alerting, and prepare for launch including documentation and marketing readiness.

## When to Use This Skill

- User asks to start stage 11 (deployment)
- User wants to deploy to production or go-live
- User asks about launch preparation or marketing readiness
- User wants to set up production monitoring or infrastructure

## Your Roles in This Skill

See `dev-swarm/docs/general-dev-stage-rule.md` for role selection guidance.

## Role Communication

See `dev-swarm/docs/general-dev-stage-rule.md` for the required role announcement format.

## Pre-Stage Check

Before starting, verify previous stages:

1. Check if stages `00-init-ideas/` through `10-sprints/` have content (not just `.gitkeep`)
2. If any previous stage is empty and has no `SKIP.md`:
   - Ask user: "Stage {XX} is not complete. Would you like to skip it or start from that stage first?"

## Instructions

### Step 1: Context Review

Read all files to understand the project:

- `ideas.md`
- `00-init-ideas/*.md` through `10-sprints/*.md` - All markdown files
- **Critical:** Review `09-devops/execution-plan.md` to identify any Part 2 items (deferred to Stage 11) that need to be executed before deployment
- **Source Code Location:** Use `{SRC}/` as the default source code root if not specified in project documentation

### Step 2: Create Stage Proposal

**General Rules:** See `dev-swarm/docs/general-dev-stage-rule.md` → "Create Stage Proposal Rules" section.

If this stage is skipped (has SKIP.md), execute the next non-skipped stage's agent skill. Otherwise, create the file `11-deployment/README.md` with the following content:

#### 2.1 Stage Goal

Brief the goal in 2-3 paragraphs:
- What this stage aims to achieve (production deployment, go-live readiness)
- Why proper deployment preparation is critical for product success
- How this stage builds upon all previous stages
- What deliverables will be produced (live production system, documentation, launch plan)

#### 2.2 Deferred Infrastructure Review

Check `09-devops/execution-plan.md` Part 2 and list items that were deferred:
- Which infrastructure items need to be set up now
- What credentials/access is required
- Estimated costs for production infrastructure

#### 2.3 File Selection

Select files from these options based on project needs:

**Deployment Planning:**
- `deployment-plan.md` - Detailed deployment plan including sequence, dependencies, and timeline
- `production-config.md` - Production environment configuration (environment variables, feature flags)
- `deployment-diagram/` - Deployment architecture and flow diagrams (follow `dev-swarm/docs/mermaid-diagram-guide.md`)
- `execution-plan.md` - Checklist of deployment tasks with pre-deployment and post-deployment sections

**Cloud Infrastructure (Production):**
- `aws-production-setup.md` - AWS production setup (EC2, RDS, S3, CloudFront, etc.)
- `runpod-production-setup.md` - RunPod GPU production setup (if applicable)
- `ssl-certificate-setup.md` - SSL/TLS certificate setup and renewal strategy
- `domain-dns-setup.md` - Domain registration and DNS configuration

**Operations & Reliability:**
- `monitoring-alerting.md` - Production monitoring, alerting rules, and on-call procedures
- `backup-strategy.md` - Backup schedules, retention policies, and disaster recovery plan
- `rollback-plan.md` - Rollback procedures for failed deployments
- `security-hardening.md` - Production security measures and hardening checklist
- `performance-optimization.md` - Performance tuning and optimization guide

**Verification & Quality:**
- `post-deployment-verification.md` - Smoke tests, health checks, and verification procedures
- `go-live-checklist.md` - Final checklist before going live

**Documentation:**
- `user-documentation.md` - End-user documentation and help guides
- `admin-documentation.md` - Admin/ops documentation for system management
- `api-documentation.md` - Public API documentation (if applicable)

**Launch & Marketing:**
- `marketing-readiness.md` - Marketing materials checklist (landing page, screenshots, copy)
- `launch-announcement.md` - Launch communication plan (social media, press release, email)

**Mobile App Store Release (if applicable):**
- `app-store-release.md` - Apple App Store submission process
- `google-play-release.md` - Google Play Store submission process
- `mobile-release-checklist.md` - Pre-submission checklist

For each selected file, provide:
- Short description
- Why it's essential for this project
- Key information it should include

**Note:** Not all files may be necessary. Select based on project complexity and launch requirements.

#### 2.4 Request User Approval

Ask user: "Please check the Stage Proposal in `11-deployment/README.md`. Update it directly or tell me how to update it."

### Step 3: Execute Stage Plan

Once user approves `11-deployment/README.md`:

#### 3.1 Create All Planned Files

Create each file listed in the approved README:

- **For `.md` files:** Write comprehensive, well-structured documentation with step-by-step instructions
- **For diagram folders:** Follow `dev-swarm/docs/mermaid-diagram-guide.md` to create related diagrams files

**Quality Guidelines:**
- Base configurations on architecture and tech-specs from previous stages
- Include security best practices for production environment
- Document all environment variables and secrets required
- Provide clear rollback procedures for each deployment step
- Include verification steps after each major deployment action
- Reference sprint deliverables from `10-sprints/`
- Ensure monitoring covers all critical system components
- Document estimated costs for production infrastructure
- **Source Code Management:** Package source code from `{SRC}/` directory (default) or as specified in project setup
- **Git Management:** Create/update `.gitignore` file to exclude unnecessary files (logs, build artifacts, secrets, node_modules, etc.) from commits

#### 3.2 Request User Approval for Files

After creating all files:
- Provide a summary of what was created
- Highlight key deployment decisions
- List any credentials or access needed for deployment
- Ask: "Please review the deployment documentation. You can update or delete files, or let me know how to modify them."

### Step 4: Finalize Documentation

Once user approves all files:

#### 4.1 Documentation Finalization
- Sync `11-deployment/README.md` to remove any deleted files
- Ensure all files are complete and well-formatted
- Verify deployment plan aligns with architecture design
- Confirm all setup steps are documented with prerequisites
- Check that all diagrams render correctly

#### 4.2 Announce Documentation Complete

Inform user:
- "Deployment documentation is complete and ready for execution"
- Summary of files created
- List of infrastructure to be provisioned

### Step 5: Create Execution Plan

Create `11-deployment/execution-plan.md` with deployment tasks organized into these sections:

**Part 1: Pre-Deployment (Infrastructure from Stage 09)**
Items deferred from `09-devops/execution-plan.md` Part 2

**Part 2: Deployment Execution**
- Source code preparation (from `{SRC}/` directory by default, ensure `.gitignore` excludes unnecessary files)
- Code merge, database migration, application deployment, CDN configuration, DNS cutover

**Part 3: Post-Deployment Verification**
- Health checks, smoke tests, performance baseline, security scan, monitoring verification

**Part 4: Go-Live Activities**
- Remove maintenance mode, enable traffic, execute launch announcement

**Part 5: Mobile App Store Release (if applicable)**
- App Store Connect and Google Play metadata, submissions, review monitoring, release

For each item, include:
- Description of what will be done
- Prerequisites (dependencies, credentials, approvals)
- Rollback procedure if it fails
- Success criteria

Ask user: "Please review the deployment execution plan. Confirm which items to execute and provide any required credentials."

### Step 6: Execute Deployment

Once user approves, execute in order with checkpoints after each part:
- Execute Part 1 (deferred infrastructure) first
- Execute Part 2 (deployment) with verification
- Execute Part 3 (post-deployment verification) - all must pass before go-live
- Execute Part 4 (go-live activities)
- Execute Part 5 (mobile releases) if applicable

**Execution Guidelines:**
- Execute steps in order, verify each before proceeding
- Document any issues and resolutions immediately
- Have rollback plan ready at each step
- Maintain communication with user throughout
- Stop and consult user if any critical issues arise

### Step 7: Update Documentation

After deployment:
- Record actual resource IDs, URLs, endpoints created
- Update configuration files with real production values (excluding secrets)
- Document any deviations from the original plan
- Create operations runbook with troubleshooting steps
- Update user documentation with production URLs

### Step 8: Complete Stage & Project

Once user confirms deployment is successful:

#### 8.1 Announce Completion

Inform user:
- "Stage 11 (Deployment) is complete - Product is LIVE!"
- Production URL and access information
- Summary of infrastructure deployed
- List of documentation delivered
- Recommended post-launch activities
- "Congratulations on your successful launch!"

## Stage Completion Rules

See `dev-swarm/docs/general-dev-stage-rule.md` for stage completion, commit, and skip rules.

## Key Principles

- Prioritize safety with multiple checkpoints before and after deployment
- Document everything for future maintenance
- Ensure rollback capability at every step
- Communicate clearly with user throughout the process
- Verify production system is fully operational before announcing completion