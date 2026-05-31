# RunPod — Manage GPU Workloads

Manage RunPod GPU pods, serverless endpoints, templates, network volumes, and models via the `runpodctl` CLI.

> **Spelling:** "Runpod" (capital R). Command is `runpodctl` (lowercase).

## Install

```bash
# Any platform (official installer)
curl -sSL https://cli.runpod.net | bash

# macOS (Homebrew)
brew install runpod/runpodctl/runpodctl

# macOS (manual — universal binary)
mkdir -p ~/.local/bin && curl -sL https://github.com/runpod/runpodctl/releases/latest/download/runpodctl-darwin-all.tar.gz | tar xz -C ~/.local/bin

# Linux
mkdir -p ~/.local/bin && curl -sL https://github.com/runpod/runpodctl/releases/latest/download/runpodctl-linux-amd64.tar.gz | tar xz -C ~/.local/bin
```

Ensure `~/.local/bin` is on `PATH` (add `export PATH="$HOME/.local/bin:$PATH"` to `~/.bashrc` or `~/.zshrc`).

## Quick Start

```bash
runpodctl doctor                    # First-time setup (API key + SSH)
runpodctl gpu list                  # See available GPUs
runpodctl template search pytorch   # Find a template
runpodctl pod create --template-id runpod-torch-v21 --gpu-id "NVIDIA RTX 4090"
runpodctl pod list                  # List your pods
```

API key: https://runpod.io/console/user/settings

## Commands

### Pods

```bash
runpodctl pod list                                    # List running pods
runpodctl pod list --all                              # All pods including exited
runpodctl pod list --status exited
runpodctl pod list --since 24h
runpodctl pod get <pod-id>                            # Get pod details (includes SSH info)
runpodctl pod create --template-id runpod-torch-v21 --gpu-id "NVIDIA RTX 4090"
runpodctl pod create --image "runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04" --gpu-id "NVIDIA RTX 4090"
runpodctl pod create --compute-type cpu --image ubuntu:22.04
runpodctl pod start <pod-id>
runpodctl pod stop <pod-id>
runpodctl pod restart <pod-id>
runpodctl pod delete <pod-id>
```

**Create flags:** `--template-id`, `--image`, `--name`, `--gpu-id`, `--gpu-count`, `--compute-type`, `--ssh`, `--container-disk-in-gb`, `--volume-in-gb`, `--volume-mount-path`, `--ports`, `--env`, `--cloud-type`, `--data-center-ids`, `--global-networking`, `--public-ip`

### Serverless (alias: sls)

```bash
runpodctl serverless list
runpodctl serverless get <endpoint-id>
runpodctl serverless create --name "x" --template-id "tpl_abc"
runpodctl serverless update <endpoint-id> --workers-max 5
runpodctl serverless delete <endpoint-id>
```

**Update flags:** `--workers-min`, `--workers-max`, `--idle-timeout`, `--scaler-type` (QUEUE_DELAY or REQUEST_COUNT), `--scaler-value`

### Templates (alias: tpl)

```bash
runpodctl template list
runpodctl template list --type official
runpodctl template list --type community
runpodctl template search pytorch
runpodctl template search vllm --type official
runpodctl template get <template-id>
runpodctl template create --name "x" --image "img"
runpodctl template create --name "x" --image "img" --serverless
runpodctl template update <template-id> --name "new"
runpodctl template delete <template-id>
```

### Network Volumes (alias: nv)

```bash
runpodctl network-volume list
runpodctl network-volume get <volume-id>
runpodctl network-volume create --name "x" --size 100 --data-center-id "US-GA-1"
runpodctl network-volume update <volume-id> --name "new"
runpodctl network-volume delete <volume-id>
```

### Models

```bash
runpodctl model list
runpodctl model list --name "llama"
runpodctl model list --provider "meta"
runpodctl model add --name "my-model" --model-path ./model
runpodctl model remove --name "my-model"
```

### Info & Billing

```bash
runpodctl user                        # Account info and balance
runpodctl gpu list                    # Available GPUs
runpodctl gpu list --include-unavailable
runpodctl datacenter list
runpodctl billing pods
runpodctl billing serverless
runpodctl billing network-volume
```

### SSH

```bash
runpodctl ssh info <pod-id>           # Get SSH connection details (does not open session)
runpodctl ssh list-keys
runpodctl ssh add-key
```

To open an interactive SSH session, use the connection details from `ssh info` with the `terminal-open-session` skill.

### File Transfer

```bash
runpodctl send <path>                 # Send files (outputs a receive code)
runpodctl receive <code>              # Receive files using code
```

### Utilities

```bash
runpodctl doctor                      # Diagnose and fix CLI issues
runpodctl update                      # Update CLI
runpodctl version
```

## URLs

### Pod service URLs

```
https://<pod-id>-<port>.proxy.runpod.net
```

### Serverless endpoints

```
https://api.runpod.ai/v2/<endpoint-id>/run        # Async
https://api.runpod.ai/v2/<endpoint-id>/runsync    # Sync
https://api.runpod.ai/v2/<endpoint-id>/health
https://api.runpod.ai/v2/<endpoint-id>/status/<job-id>
```
