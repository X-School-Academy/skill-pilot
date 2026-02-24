---
name: dev-swarm-stage-devops
description: Set up DevOps infrastructure including GitHub repositories, CI/CD pipelines, containerization, and cloud infrastructure (AWS, RunPod). Use when starting stage 09 (devops) or when user asks about CI/CD, Docker, or cloud setup.
---

# Stage 09 - DevOps

Set up the complete DevOps infrastructure including GitHub repositories, CI/CD pipelines, containerization, cloud infrastructure (AWS, RunPod), and monitoring to enable seamless development and deployment workflows.

## When to Use This Skill

- User asks to start stage 09 (devops)
- User wants to set up CI/CD pipelines or Docker containers
- User asks about GitHub Actions, AWS setup, or cloud infrastructure

## Your Roles in This Skill

See `dev-swarm/docs/general-dev-stage-rule.md` for role selection guidance.

## Role Communication

See `dev-swarm/docs/general-dev-stage-rule.md` for the required role announcement format.

## Pre-Stage Check

Before starting, verify previous stages:

1. Check if `00-init-ideas/` through `08-tech-specs/` folders have content (not just `.gitkeep`)
2. If any previous stage is empty and has no `SKIP.md`:
   - Ask user: "Stage {XX} is not complete. Would you like to skip it or start from that stage first?"

## Instructions

### Step 1: Context Review

Read all files to understand the project:

- `ideas.md`
- `00-init-ideas/*.md` through `08-tech-specs/*.md` - All markdown files

### Step 2: Create Stage Proposal

**General Rules:** See `dev-swarm/docs/general-dev-stage-rule.md` → "Create Stage Proposal Rules" section.

If this stage is skipped (has SKIP.md), execute the next non-skipped stage's agent skill. Otherwise, create the file `09-devops/README.md` with the following content:

#### 2.1 Stage Goal

Brief the goal in 2-3 paragraphs:
- What this stage aims to achieve (infrastructure setup, CI/CD automation)
- Why DevOps setup is critical for development velocity and reliability
- How this builds upon architecture and tech-specs
- What deliverables will be produced

#### 2.2 File Selection

Select files from these options based on project needs:

**DevOps Strategy & Overview:**
- `devops-overview.md` - DevOps strategy overview
- `environment-config.md` - Environment configurations (dev, staging, production)
- `execution-plan.md` - Checklist of infrastructure tasks (Stage 09 vs Stage 11)

**Repository & Version Control:**
- `github-setup.md` - GitHub repository setup
- `ssh-access-policy.md` - SSH key management

**CI/CD Pipeline:**
- `ci-cd-pipeline.md` - CI/CD pipeline design
- `ci-workflow.yml` - GitHub Actions CI workflow
- `cd-workflow.yml` - GitHub Actions CD workflow

**Containerization:**
- `docker_strategy.md` - Dockerfile and docker-compose.yml plan

**Cloud Infrastructure - AWS:**
- `aws-setup.md` - AWS account & services setup
- `ec2-setup.md` - EC2 instance configuration
- `s3-setup.md` - S3 bucket configuration

**Web Server & Database:**
- `nginx-setup.md` - Nginx configuration documentation
- `nginx.conf` - Nginx config file
- `mysql-setup.md` - MySQL setup documentation

**GPU Infrastructure:**
- `runpod-setup.md` - RunPod GPU setup (if applicable)

**Infrastructure as Code:**
- `infrastructure/terraform/` - Terraform configurations

**Monitoring & Security:**
- `monitoring-setup.md` - Monitoring & logging setup
- `secrets-management.md` - Secrets management strategy

**Mobile App Store Setup (if applicable):**
- `app-store-setup.md` - Apple App Store Connect setup
- `google-play-setup.md` - Google Play Console setup
- `mobile-signing-setup.md` - Code signing certificates and keystores

For each selected file, provide:
- Short description
- Why it's essential for this project
- Key configuration it should include

#### 2.3 Request User Approval

Ask user: "Please check the Stage Proposal in `09-devops/README.md`. Update it directly or tell me how to update it."

### Step 3: Create Documentation

Once user approves `09-devops/README.md`:

#### 3.1 Create All Planned Files

Create each file listed in the approved README:

- **For `.md` files:** Write comprehensive documentation with step-by-step instructions
- **For `.yml` files:** Create working GitHub Actions workflow files
- **For `.conf` files:** Create production-ready configuration files
- **For `.tf` files:** Create valid Terraform configurations

**Quality Guidelines:**
- Base configurations on architecture decisions from previous stages
- Include security best practices in all infrastructure setup
- Document all environment variables and secrets required
- Provide both development and production configurations where applicable

#### 3.2 Request User Approval for Files

After creating all files:
- Provide a summary of what was created
- Highlight key infrastructure decisions
- List any credentials or access needed for later execution
- Ask: "Please review the DevOps setup files. You can update or delete files, or let me know how to modify them."

### Step 4: Create Execution Plan

Create `09-devops/execution-plan.md` with tasks organized into:

**Part 1: Execute in Stage 09 (Development Setup)**
- GitHub repository setup
- Local Docker development environment
- CI pipeline setup
- Development environment configuration

**Part 2: Execute in Stage 11 (Production Deployment)**
- AWS account & IAM setup
- EC2 instance provisioning
- Production database setup
- CD pipeline activation
- Monitoring & alerting configuration

Ask user to review and mark which items to execute now.

### Step 5: Execute Approved Items

Execute only the checked items from the execution plan:
- Request credentials before interacting with cloud services
- Test configurations in development environment first
- Report progress and any errors to user immediately

### Step 6: Finalize Stage

Once user confirms infrastructure is working:

#### 6.1 Documentation Finalization
- Sync `09-devops/README.md` to remove any deleted files
- Record actual resource IDs, URLs created
- Document any deviations from the original plan

#### 6.2 Announce Completion

Inform user:
- "Stage 09 (DevOps) is complete"
- Summary of documentation created
- Summary of infrastructure provisioned
- "Ready to proceed to Stage 10 (Sprints) when you are"

## Stage Completion Rules

See `dev-swarm/docs/general-dev-stage-rule.md` for stage completion, commit, and skip rules.

## Key Principles

- Request user credentials before cloud operations
- Test configurations in development first
- Document everything for reproducibility
- Support smooth transition to sprint development
