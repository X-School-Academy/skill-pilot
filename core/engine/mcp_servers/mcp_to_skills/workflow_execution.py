from __future__ import annotations

import json
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from workflow_editor_utils import validate_workflow_doc


_WORKSPACE_LINE_RE = re.compile(r"(?mi)^Workspace path:\s*(.+?)\s*$")
_SAFE_FILENAME_RE = re.compile(r"[^a-z0-9]+")


@dataclass
class WorkflowGraph:
    workflow_file: Path
    workflow_name: str
    workflow_relative_path: str
    doc: dict[str, Any]
    id_to_node: dict[int, dict[str, Any]]
    upstream_agents: dict[int, list[int]]
    downstream_agents: dict[int, list[int]]
    end_inputs: list[int]


def node_type(node: dict[str, Any]) -> str:
    return str(node.get("type") or "").strip().lower()


def node_name(node: dict[str, Any]) -> str:
    ntype = node_type(node)
    if ntype == "start":
        return "Start"
    if ntype == "end":
        return "End"
    data = node.get("data") if isinstance(node.get("data"), dict) else {}
    title = str(data.get("title") or "").strip()
    if title:
        return title
    return f"Agent {node.get('id')}"


def parse_task_workspace(workflow_prompt: str) -> str | None:
    match = _WORKSPACE_LINE_RE.search(str(workflow_prompt or ""))
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def repo_root_from_workflow_file(workflow_file: Path) -> Path:
    current = workflow_file.resolve()
    for parent in current.parents:
        if parent.name == "core" and parent.parent.exists():
            return parent.parent
    return current.parents[2]


def display_repo_relative(path: Path, repo_root: Path) -> str:
    candidate = path.resolve()
    root = repo_root.resolve()
    try:
        return str(candidate.relative_to(root))
    except ValueError:
        return str(candidate)


def create_run_output_dir(base_dir: Path, *, cleanup_base_dir: bool = False) -> tuple[str, Path]:
    if cleanup_base_dir and base_dir.exists():
        for child in base_dir.iterdir():
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                try:
                    child.unlink()
                except OSError:
                    pass
    base_dir.mkdir(parents=True, exist_ok=True)
    run_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8]
    output_root = base_dir / run_id
    output_root.mkdir(parents=True, exist_ok=True)
    return run_id, output_root


def safe_node_filename_prefix(name: str) -> str:
    value = _SAFE_FILENAME_RE.sub("-", str(name or "").strip().lower()).strip("-")
    return value or "node"


def node_output_path(output_root: Path, node_id: int, node_label: str | None = None) -> Path:
    prefix = safe_node_filename_prefix(node_label or "")
    return output_root / f"{prefix}.md"


def write_node_output(output_root: Path, node_id: int, text: str, node_label: str | None = None) -> Path:
    output_file = node_output_path(output_root, node_id, node_label)
    output_file.write_text(str(text), encoding="utf-8")
    return output_file


def load_workflow_graph(workflow_file: Path, workflows_root: Path | None = None) -> WorkflowGraph:
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

    upstream_agents: dict[int, list[int]] = {}
    downstream_agents: dict[int, list[int]] = {}
    end_inputs: list[int] = []

    for node_id, node in id_to_node.items():
        if node_type(node) == "agent":
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
        source_type = node_type(source_node)
        target_type = node_type(target_node)
        if source_type == "agent" and target_type == "agent":
            upstream_agents[target].append(source)
            downstream_agents[source].append(target)
        if source_type == "agent" and target_type == "end":
            end_inputs.append(source)

    repo_root = repo_root_from_workflow_file(workflow_file)
    effective_workflows_root = workflows_root or (repo_root / "core" / "workflows")
    try:
        workflow_relative_path = str(workflow_file.resolve().relative_to(effective_workflows_root.resolve()))
    except ValueError:
        workflow_relative_path = workflow_file.name

    return WorkflowGraph(
        workflow_file=workflow_file.resolve(),
        workflow_name=str(doc.get("name") or "").strip() or workflow_file.stem,
        workflow_relative_path=workflow_relative_path,
        doc=doc,
        id_to_node=id_to_node,
        upstream_agents=upstream_agents,
        downstream_agents=downstream_agents,
        end_inputs=end_inputs,
    )


def build_node_prompt(
    *,
    graph: WorkflowGraph,
    current_node: dict[str, Any],
    workflow_prompt: str,
    output_root: Path,
    upstream_node_ids: list[int],
    task_workspace: str | None = None,
    start_by_prompt_mode: bool = False,
) -> str:
    repo_root = repo_root_from_workflow_file(graph.workflow_file)
    current_node_id = int(current_node["id"])
    data = current_node.get("data") if isinstance(current_node.get("data"), dict) else {}
    skill = str(data.get("skill") or "").strip()
    responsibility = str(data.get("responsibility") or "").strip()
    output_root_text = display_repo_relative(output_root, repo_root)
    current_node_title = node_name(current_node)

    lines: list[str] = [
        "You are running as an AI agent node inside a multi-step workflow.",
        "You need to use the workflow instruction and the agent skill provided for this node to finish the task.",
        "",
        f"Workflow name: {graph.workflow_name}",
        f"Workflow file: core/workflows/{graph.workflow_relative_path}",
        f"Current AI agent node UID: {current_node_id}",
        f"Current AI agent node name: {current_node_title}",
        "",
        "Workflow system prompt:",
        str(workflow_prompt or "").strip() or "(empty)",
        "",
        "Node-specific instruction (derived from workflow node data):",
    ]

    if skill:
        lines.append(f"- Skill: {skill}")
    if responsibility:
        lines.append(f"- Responsibility: {responsibility}")
    if not skill and not responsibility:
        lines.append("- Follow the workflow node instructions already defined by code.")

    if task_workspace:
        lines.extend(["", "Task workspace:", task_workspace])

    lines.extend(["", "Workflow output root:", output_root_text])

    if upstream_node_ids:
        lines.extend(
            [
                "",
                "If you have upstream outputs as your inputs as needed, they are stored in:",
            ]
        )
        lines.append(f"{output_root_text}/*.md")
        lines.extend(["", "Read those files to get all required context before you start."])

    lines.extend(
        [
            "",
            "When you finish:",
            "load agent skill continue-workflow-execution but not use it until explicitly instructed."
            if start_by_prompt_mode
            else None,
            f"1. Write your final output to {display_repo_relative(node_output_path(output_root, current_node_id, current_node_title), repo_root)}",
            "2. Keep the output concise, structured, and easy for downstream nodes to understand",
            "3. Include enough basic context in the output so another agent can understand what the result represents",
            "4. Do not return only a bare number, string, or similarly context-free value unless the workflow explicitly requires that exact format",
            "5. If you make assumptions, state them before the final result",
            "6. Do not write output files outside the task workspace or workflow output root unless explicitly required",
        ]
    )
    return "\n".join([line for line in lines if line is not None]).strip()
