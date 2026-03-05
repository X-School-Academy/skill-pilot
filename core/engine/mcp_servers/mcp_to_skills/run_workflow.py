from __future__ import annotations

import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .workflow_execution import (
    build_node_prompt,
    create_run_output_dir,
    load_workflow_graph,
    node_name,
    node_output_path,
    parse_task_workspace,
)


@dataclass
class WorkflowRunResult:
    status: str
    workflow: str
    workflow_name: str
    duration_sec: float
    run_id: str
    output_root: str
    node_status: dict[int, str]
    node_outputs: dict[int, str]
    final_outputs: list[dict[str, object]]
    errors: list[dict[str, object]]


def resolve_workflow_file(workflow_arg: str, workflows_root: Path) -> Path:
    raw = str(workflow_arg or "").strip()
    if not raw:
        raise ValueError("workflow path is required")

    root = workflows_root.resolve()
    repo_root = root.parent.parent
    input_path = Path(raw).expanduser()

    if input_path.is_absolute():
        candidate = input_path.resolve()
    else:
        normalized_raw = raw.replace("\\", "/")
        if normalized_raw.startswith("core/workflows/"):
            candidate = (repo_root / normalized_raw).resolve()
        elif normalized_raw.startswith("core/"):
            candidate = (repo_root / normalized_raw).resolve()
        else:
            candidate = (root / input_path).resolve()

    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("workflow path must be under core/workflows") from exc

    if not candidate.exists() or not candidate.is_file():
        raise FileNotFoundError(f"workflow file not found: {candidate}")
    return candidate


def run_workflow(
    workflow_file: Path,
    workflow_prompt: str,
    *,
    max_workers: int,
    infer_fn: Callable[[str, str | None], str],
    output_base_dir: Path | None = None,
    cleanup_base_dir: bool = False,
    log_fn: Callable[[str], None] | None = None,
) -> WorkflowRunResult:
    graph = load_workflow_graph(workflow_file)
    repo_root = workflow_file.resolve().parents[2]
    base_dir = output_base_dir or (repo_root / ".skillpilot" / "temp" / "background-workflow")
    run_id, output_root = create_run_output_dir(base_dir, cleanup_base_dir=cleanup_base_dir)
    task_workspace = parse_task_workspace(workflow_prompt)

    def emit(message: str) -> None:
        if log_fn is not None:
            log_fn(message)

    emit(
        "[workflow-run] start "
        f"workflow={graph.workflow_relative_path} "
        f"workflow_name={graph.workflow_name} "
        f"run_id={run_id} "
        f"output_root={output_root}"
    )

    node_outputs: dict[int, str] = {}
    node_status: dict[int, str] = {node_id: "pending" for node_id in graph.upstream_agents}
    blocked_reasons: dict[int, str] = {}
    run_errors: list[dict[str, object]] = []

    pending_upstream_count: dict[int, int] = {
        node_id: len(up_ids) for node_id, up_ids in graph.upstream_agents.items()
    }
    has_failed_upstream: dict[int, bool] = {node_id: False for node_id in graph.upstream_agents}

    ready: list[int] = [node_id for node_id, count in pending_upstream_count.items() if count == 0]
    for node_id in ready:
        node_status[node_id] = "ready"

    def mark_blocked(node_id: int, reason: str) -> None:
        current = node_status.get(node_id)
        if current in {"done", "running", "failed", "blocked"}:
            return
        node_status[node_id] = "blocked"
        blocked_reasons[node_id] = reason
        emit(f"[workflow-run] node_blocked node_id={node_id} node_name={node_name(graph.id_to_node[node_id])} reason={reason}")
        for downstream_id in graph.downstream_agents.get(node_id, []):
            has_failed_upstream[downstream_id] = True
            pending_upstream_count[downstream_id] = max(0, pending_upstream_count[downstream_id] - 1)
            if pending_upstream_count[downstream_id] == 0:
                mark_blocked(downstream_id, f"upstream node {node_id} failed or was blocked")

    def execute_agent(node_id: int) -> str:
        node = graph.id_to_node[node_id]
        data = node.get("data") if isinstance(node.get("data"), dict) else {}
        provider_id = str(data.get("provider_id") or "").strip() or None
        upstream_node_ids = list(graph.upstream_agents[node_id])
        expected_output_file = node_output_path(output_root, node_id, node_name(node))
        prompt = build_node_prompt(
            graph=graph,
            current_node=node,
            workflow_prompt=workflow_prompt,
            output_root=output_root,
            upstream_node_ids=upstream_node_ids,
            task_workspace=task_workspace,
        )

        emit(
            "[workflow-run] node_start "
            f"node_id={node_id} "
            f"node_name={node_name(node)} "
            f"provider_id={provider_id or ''} "
            f"upstream_ids={upstream_node_ids} "
            f"expected_output={expected_output_file}"
        )
        emit(f"[workflow-run] node_prompt node_id={node_id}\n{prompt}")
        raw_text = infer_fn(prompt, provider_id).strip()
        emit(f"[workflow-run] node_response node_id={node_id}\n{raw_text}")
        if not expected_output_file.exists() or not expected_output_file.is_file():
            raise RuntimeError(
                "agent did not create expected output file: "
                f"{expected_output_file}"
            )
        output_text = expected_output_file.read_text(encoding="utf-8", errors="replace").strip()
        emit(f"[workflow-run] node_output node_id={node_id} output_file={expected_output_file}\n{output_text}")
        return output_text

    started_at = time.time()
    futures: dict[Future[str], int] = {}
    worker_count = max(1, int(max_workers))

    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        while ready or futures:
            ready.sort()
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
                    emit(f"[workflow-run] node_done node_id={node_id} node_name={node_name(graph.id_to_node[node_id])}")
                except Exception as exc:  # noqa: BLE001
                    node_status[node_id] = "failed"
                    error_text = str(exc)
                    emit(
                        "[workflow-run] node_failed "
                        f"node_id={node_id} "
                        f"node_name={node_name(graph.id_to_node[node_id])} "
                        f"error={error_text}"
                    )
                    run_errors.append(
                        {
                            "node_id": node_id,
                            "node_name": node_name(graph.id_to_node[node_id]),
                            "skill": str(
                                (graph.id_to_node[node_id].get("data") or {}).get("skill")  # type: ignore[union-attr]
                                or ""
                            ),
                            "error": error_text,
                        }
                    )

                for downstream_id in graph.downstream_agents.get(node_id, []):
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

    final_outputs: list[dict[str, object]] = []
    for node_id in graph.end_inputs:
        if node_id in node_outputs:
            final_outputs.append(
                {
                    "node_id": node_id,
                    "node_name": node_name(graph.id_to_node[node_id]),
                    "output": node_outputs[node_id],
                }
            )

    for node_id, reason in blocked_reasons.items():
        run_errors.append(
            {
                "node_id": node_id,
                "node_name": node_name(graph.id_to_node[node_id]),
                "skill": str(((graph.id_to_node[node_id].get("data") or {}).get("skill"))),  # type: ignore[union-attr]
                "error": f"blocked: {reason}",
            }
        )

    status = "ok" if not run_errors else "error"
    duration_sec = round(time.time() - started_at, 3)
    emit(
        "[workflow-run] finish "
        f"workflow={graph.workflow_relative_path} "
        f"run_id={run_id} "
        f"status={status} "
        f"duration_sec={duration_sec}"
    )

    return WorkflowRunResult(
        status=status,
        workflow=str(graph.workflow_file),
        workflow_name=graph.workflow_name,
        duration_sec=duration_sec,
        run_id=run_id,
        output_root=str(output_root),
        node_status=node_status,
        node_outputs=node_outputs,
        final_outputs=final_outputs,
        errors=run_errors,
    )
