from __future__ import annotations

import json
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from workflow_editor_utils import validate_workflow_doc


@dataclass
class WorkflowRunResult:
    status: str
    workflow: str
    workflow_name: str
    duration_sec: float
    node_status: dict[int, str]
    node_outputs: dict[int, str]
    final_outputs: list[dict[str, Any]]
    errors: list[dict[str, Any]]


def resolve_workflow_file(workflow_arg: str, workflows_root: Path) -> Path:
    raw = str(workflow_arg or "").strip()
    if not raw:
        raise ValueError("workflow path is required")

    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = (workflows_root / candidate).resolve()
    else:
        candidate = candidate.resolve()

    root = workflows_root.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("workflow path must be under core/workflows") from exc

    if not candidate.exists() or not candidate.is_file():
        raise FileNotFoundError(f"workflow file not found: {candidate}")
    return candidate


def _node_type(node: dict[str, Any]) -> str:
    return str(node.get("type") or "").strip().lower()


def _node_name(node: dict[str, Any]) -> str:
    ntype = _node_type(node)
    if ntype == "start":
        return "Start"
    if ntype == "end":
        return "End"
    data = node.get("data") if isinstance(node.get("data"), dict) else {}
    title = str(data.get("title") or "").strip()
    if title:
        return title
    return f"Agent {node.get('id')}"


def _build_prompt(
    workflow_name: str,
    workflow_prompt: str,
    current_node: dict[str, Any],
    upstream_nodes: list[dict[str, Any]],
    upstream_outputs: dict[int, str],
) -> str:
    data = current_node.get("data") if isinstance(current_node.get("data"), dict) else {}
    current_name = _node_name(current_node)
    skill = str(data.get("skill") or "").strip()
    responsibility = str(data.get("responsibility") or "").strip()

    lines: list[str] = [
        "You are running as a Agent inside a multi-step workflow.",
        "",
        f"Workflow name: {workflow_name}",
        f"Current Agent: {current_name}",
    ]
    if skill:
        lines.append(f"Current Agent skill: {skill}")
    if responsibility:
        lines.append(f"Current Agent role: {responsibility}")

    lines.extend(
        [
            "",
            "Global workflow instruction:",
            workflow_prompt.strip(),
            "",
            "Upstream inputs from directly connected Agents:",
        ]
    )

    if upstream_nodes:
        for upstream_node in upstream_nodes:
            upstream_id = int(upstream_node["id"])
            upstream_name = _node_name(upstream_node)
            upstream_data = upstream_node.get("data") if isinstance(upstream_node.get("data"), dict) else {}
            upstream_role = str(upstream_data.get("responsibility") or "").strip()
            upstream_text = upstream_outputs.get(upstream_id, "").strip()
            lines.append(f"[from:{upstream_name}]")
            if upstream_role:
                lines.append(f"Role: {upstream_role}")
            lines.append(f"Output: {upstream_text}")
            lines.append("")
    else:
        lines.append("[from:none] No upstream Agent input.")

    lines.extend(
        [
            "",
            "Task:",
            "1. Complete the work required by your current Agent skill.",
            "2. Use the global workflow instruction plus upstream inputs as context.",
            "3. Return a concise, structured result that downstream Agents can consume directly.",
            "4. If inputs are missing or conflicting, state assumptions clearly before your final output.",
        ]
    )
    return "\n".join(lines).strip()


def run_workflow(
    workflow_file: Path,
    workflow_prompt: str,
    *,
    max_workers: int,
    infer_fn: Callable[[str, str | None], str],
) -> WorkflowRunResult:
    raw = workflow_file.read_text(encoding="utf-8", errors="replace")
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid workflow JSON: {exc}") from exc

    if not isinstance(doc, dict):
        raise ValueError("workflow document must be a JSON object")

    errors = validate_workflow_doc(doc)
    if errors:
        raise ValueError(f"workflow validation failed: {json.dumps(errors, ensure_ascii=True)}")

    nodes = doc.get("nodes")
    edges = doc.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise ValueError("workflow must include array fields: nodes, edges")

    id_to_node: dict[int, dict[str, Any]] = {}
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = node.get("id")
        if isinstance(node_id, int):
            id_to_node[node_id] = node

    # Agent dependency graph only (Start/End are orchestration nodes).
    upstream_agents: dict[int, list[int]] = {}
    downstream_agents: dict[int, list[int]] = {}
    end_inputs: list[int] = []

    for node_id, node in id_to_node.items():
        if _node_type(node) == "agent":
            upstream_agents[node_id] = []
            downstream_agents[node_id] = []

    for edge in edges:
        if not isinstance(edge, dict):
            continue
        source = edge.get("source")
        target = edge.get("target")
        if not isinstance(source, int) or not isinstance(target, int):
            continue
        source_node = id_to_node.get(source)
        target_node = id_to_node.get(target)
        if source_node is None or target_node is None:
            continue
        source_type = _node_type(source_node)
        target_type = _node_type(target_node)

        if source_type == "agent" and target_type == "agent":
            upstream_agents[target].append(source)
            downstream_agents[source].append(target)
        if source_type == "agent" and target_type == "end":
            end_inputs.append(source)

    node_outputs: dict[int, str] = {}
    node_status: dict[int, str] = {node_id: "pending" for node_id in upstream_agents}
    blocked_reasons: dict[int, str] = {}
    run_errors: list[dict[str, Any]] = []

    pending_upstream_count: dict[int, int] = {
        node_id: len(up_ids) for node_id, up_ids in upstream_agents.items()
    }
    has_failed_upstream: dict[int, bool] = {node_id: False for node_id in upstream_agents}

    ready: list[int] = [node_id for node_id, count in pending_upstream_count.items() if count == 0]
    for node_id in ready:
        node_status[node_id] = "ready"

    def mark_blocked(node_id: int, reason: str) -> None:
        current = node_status.get(node_id)
        if current in {"done", "running", "failed", "blocked"}:
            return
        node_status[node_id] = "blocked"
        blocked_reasons[node_id] = reason
        for downstream_id in downstream_agents.get(node_id, []):
            has_failed_upstream[downstream_id] = True
            pending_upstream_count[downstream_id] = max(0, pending_upstream_count[downstream_id] - 1)
            if pending_upstream_count[downstream_id] == 0:
                mark_blocked(downstream_id, f"upstream node {node_id} failed or was blocked")

    def execute_agent(node_id: int) -> str:
        node = id_to_node[node_id]
        data = node.get("data") if isinstance(node.get("data"), dict) else {}
        provider_id = str(data.get("provider_id") or "").strip() or None

        upstream_nodes = [id_to_node[uid] for uid in upstream_agents[node_id]]
        prompt = _build_prompt(
            workflow_name=str(doc.get("name") or "").strip() or workflow_file.stem,
            workflow_prompt=workflow_prompt,
            current_node=node,
            upstream_nodes=upstream_nodes,
            upstream_outputs=node_outputs,
        )
        return infer_fn(prompt, provider_id)

    started_at = time.time()
    futures: dict[Future[str], int] = {}
    worker_count = max(1, int(max_workers))

    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        while ready or futures:
            while ready:
                next_id = ready.pop(0)
                if node_status.get(next_id) in {"blocked", "failed", "done"}:
                    continue
                if has_failed_upstream.get(next_id):
                    mark_blocked(next_id, "has failed upstream dependency")
                    continue
                node_status[next_id] = "running"
                future = pool.submit(execute_agent, next_id)
                futures[future] = next_id

            if not futures:
                continue

            done, _ = wait(set(futures.keys()), return_when=FIRST_COMPLETED)
            for done_future in done:
                node_id = futures.pop(done_future)
                try:
                    text = done_future.result().strip()
                    node_outputs[node_id] = text
                    node_status[node_id] = "done"
                except Exception as exc:  # noqa: BLE001
                    node_status[node_id] = "failed"
                    run_errors.append(
                        {
                            "node_id": node_id,
                            "node_name": _node_name(id_to_node[node_id]),
                            "skill": str(
                                (id_to_node[node_id].get("data") or {}).get("skill")  # type: ignore[union-attr]
                                or ""
                            ),
                            "error": str(exc),
                        }
                    )

                for downstream_id in downstream_agents.get(node_id, []):
                    pending_upstream_count[downstream_id] = max(0, pending_upstream_count[downstream_id] - 1)
                    if node_status[node_id] != "done":
                        has_failed_upstream[downstream_id] = True
                    if pending_upstream_count[downstream_id] == 0:
                        if has_failed_upstream[downstream_id]:
                            mark_blocked(
                                downstream_id,
                                f"one or more upstream dependencies failed before node {downstream_id} could run",
                            )
                        else:
                            if node_status.get(downstream_id) == "pending":
                                node_status[downstream_id] = "ready"
                            ready.append(downstream_id)

    final_outputs: list[dict[str, Any]] = []
    for node_id in end_inputs:
        if node_id in node_outputs:
            final_outputs.append(
                {
                    "node_id": node_id,
                    "node_name": _node_name(id_to_node[node_id]),
                    "output": node_outputs[node_id],
                }
            )

    for node_id, reason in blocked_reasons.items():
        run_errors.append(
            {
                "node_id": node_id,
                "node_name": _node_name(id_to_node[node_id]),
                "skill": str(((id_to_node[node_id].get("data") or {}).get("skill"))),  # type: ignore[union-attr]
                "error": f"blocked: {reason}",
            }
        )

    status = "ok"
    if run_errors:
        status = "error"

    return WorkflowRunResult(
        status=status,
        workflow=str(workflow_file),
        workflow_name=str(doc.get("name") or "").strip() or workflow_file.stem,
        duration_sec=round(time.time() - started_at, 3),
        node_status=node_status,
        node_outputs=node_outputs,
        final_outputs=final_outputs,
        errors=run_errors,
    )
