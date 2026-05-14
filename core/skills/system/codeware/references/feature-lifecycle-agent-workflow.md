# Feature Lifecycle: Agent-Workflow Context

Use when this skill is invoked inside an `agent-workflow` execution.

## How to Detect

You are running inside an agent-workflow when:
- The user message or system context includes a workflow node name or workflow run ID, or
- The skill was launched from a workflow node (the invocation context mentions a workflow).

## Behavior

Follow the same stage sequence as the applicable flow (new feature or update/fix). After each stage step completes, invoke the `agent-workflow` skill's continue-workflow action so the workflow advances to the next node.

## Steps

1. Identify the current workflow node and the expected next node.
2. Complete the stage work for the current node as defined in the matching lifecycle reference.
3. After the stage is done, call the `agent-workflow` skill with the continue-workflow action.
4. Do not advance to the next stage yourself — the workflow engine will invoke this skill again for the next node.
