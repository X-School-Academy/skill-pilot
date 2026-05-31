from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from fastapi import HTTPException


_FILENAME_RE = re.compile(r"^[a-z0-9]+(?:[a-z0-9_-]*[a-z0-9])?\.json$")
_NORMALIZED_NODE_NAME_RE = re.compile(r"[^a-z0-9]+")


def _node_type(node: Dict[str, Any]) -> str:
    return str(node.get("type") or "").strip().lower()


def _is_finite_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))


def safe_workflow_path(root: Path, workflow: str) -> Path:
    if not workflow:
        raise HTTPException(status_code=400, detail="Missing workflow path")
    root_resolved = root.resolve()
    candidate = (root_resolved / workflow).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workflow path")
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Workflow not found")
    return candidate


def build_workflow_tree(path: Path, root: Path) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for entry in sorted(path.iterdir(), key=lambda p: p.name.lower()):
        if entry.name.startswith("."):
            continue
        stat = entry.stat()
        if entry.is_dir():
            children = build_workflow_tree(entry, root)
            mtime = max([stat.st_mtime] + [c["mtime"] for c in children]) if children else stat.st_mtime
            items.append(
                {
                    "name": entry.name,
                    "path": str(entry.relative_to(root)),
                    "type": "dir",
                    "mtime": mtime,
                    "children": children,
                }
            )
            continue
        if entry.suffix.lower() != ".json":
            continue
        items.append(
            {
                "name": entry.name,
                "path": str(entry.relative_to(root)),
                "type": "file",
                "mtime": stat.st_mtime,
            }
        )
    return items


def find_latest_workflow(root: Path) -> str | None:
    latest_path: Path | None = None
    latest_mtime = 0.0
    for entry in root.rglob("*"):
        if not entry.is_file():
            continue
        if entry.name.startswith(".") or entry.suffix.lower() != ".json":
            continue
        mtime = entry.stat().st_mtime
        if mtime > latest_mtime:
            latest_mtime = mtime
            latest_path = entry
    if latest_path is None:
        return None
    return str(latest_path.relative_to(root))


def normalize_workflow_filename(name: str) -> str:
    text = str(name or "").strip().lower()
    text = text.replace("_", "-")
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^a-z0-9-]", "", text)
    text = re.sub(r"-+", "-", text).strip("-")
    if not text:
        text = "workflow"
    return f"{text}.json"


def is_valid_workflow_filename(filename: str) -> bool:
    return bool(_FILENAME_RE.fullmatch(filename or ""))


def normalize_workflow_node_name(name: str) -> str:
    normalized = _NORMALIZED_NODE_NAME_RE.sub("-", str(name or "").strip().lower()).strip("-")
    return normalized or "node"


def resolve_filename_collision(root: Path, filename: str) -> str:
    if not filename.endswith(".json"):
        filename = normalize_workflow_filename(filename)
    if not is_valid_workflow_filename(filename):
        raise HTTPException(status_code=400, detail="Invalid workflow filename")

    base = filename[:-5]
    candidate = filename
    i = 1
    while (root / candidate).exists():
        candidate = f"{base}_{i}.json"
        i += 1
    return candidate


def validate_workflow_doc(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    errors: List[Dict[str, Any]] = []

    nodes = doc.get("nodes")
    edges = doc.get("edges")
    if not isinstance(nodes, list):
        errors.append(_err("SHAPE_NODES", "`nodes` must be an array."))
        return errors
    if not isinstance(edges, list):
        errors.append(_err("SHAPE_EDGES", "`edges` must be an array."))
        return errors

    id_to_node: Dict[int, Dict[str, Any]] = {}
    duplicate_node_ids: Set[int] = set()
    normalized_name_to_ids: Dict[str, List[int]] = {}
    start_count = 0
    end_count = 0

    for node in nodes:
        if not isinstance(node, dict):
            errors.append(_err("NODE_TYPE", "Each node must be an object."))
            continue
        node_id = node.get("id")
        node_type = _node_type(node)
        position = node.get("position")

        if not isinstance(node_id, int):
            errors.append(_err("NODE_ID", "Node `id` must be an integer."))
            continue
        if not isinstance(position, dict):
            errors.append(_err("NODE_POSITION", "Node `position` must be an object with numeric `x` and `y`.", [node_id]))
        else:
            px = position.get("x")
            py = position.get("y")
            if not _is_finite_number(px) or not _is_finite_number(py):
                errors.append(_err("NODE_POSITION", "Node `position.x` and `position.y` must be finite numbers.", [node_id]))
        if node_id in id_to_node:
            duplicate_node_ids.add(node_id)
        else:
            id_to_node[node_id] = node

        if node_type == "start":
            raw_node_name = "Start"
        elif node_type == "end":
            raw_node_name = "End"
        else:
            data = node.get("data") if isinstance(node.get("data"), dict) else {}
            raw_node_name = str(data.get("title") or "").strip() or f"Agent {node_id}"
        normalized_name = normalize_workflow_node_name(raw_node_name)
        normalized_name_to_ids.setdefault(normalized_name, []).append(node_id)

        if node_type == "start":
            start_count += 1
            if node_id != 0:
                errors.append(_err("START_ID", "Start node id must be 0.", [node_id]))
        elif node_type == "end":
            end_count += 1
            if node_id != -1:
                errors.append(_err("END_ID", "End node id must be -1.", [node_id]))
        elif node_type == "agent":
            if node_id <= 0:
                errors.append(_err("AGENT_ID", "Agent id must be a positive integer.", [node_id]))
            data = node.get("data")
            if not isinstance(data, dict):
                errors.append(_err("AGENT_DATA", "Agent `data` is required.", [node_id]))
            else:
                for field in ("title", "provider_id"):
                    val = data.get(field)
                    if not isinstance(val, str) or not val.strip():
                        errors.append(
                            _err(
                                "AGENT_FIELD",
                                f"Agent requires non-empty `{field}`.",
                                [node_id],
                            )
                        )
                subagent = str(data.get("subagent") or "").strip()
                responsibility = str(data.get("responsibility") or "").strip()
                if not subagent and not responsibility:
                    errors.append(
                        _err(
                            "AGENT_FIELD",
                            "Agent requires non-empty `subagent` or `responsibility`.",
                            [node_id],
                        )
                    )
        else:
            errors.append(_err("NODE_KIND", "Node `type` must be start, agent, or end.", [node_id]))

    if duplicate_node_ids:
        errors.append(_err("NODE_DUPLICATE", "Node ids must be unique.", sorted(duplicate_node_ids)))

    duplicate_name_ids = sorted(
        {
            node_id
            for node_ids in normalized_name_to_ids.values()
            if len(node_ids) > 1
            for node_id in node_ids
        }
    )
    if duplicate_name_ids:
        errors.append(
            _err(
                "NODE_NAME_DUPLICATE",
                "Node names must be unique after normalization.",
                duplicate_name_ids,
            )
        )

    if start_count != 1:
        errors.append(_err("START_COUNT", "Workflow must contain exactly one Start node."))
    if end_count != 1:
        errors.append(_err("END_COUNT", "Workflow must contain exactly one End node."))

    indegree: Dict[int, int] = {nid: 0 for nid in id_to_node}
    outdegree: Dict[int, int] = {nid: 0 for nid in id_to_node}
    adj: Dict[int, List[int]] = {nid: [] for nid in id_to_node}
    rev: Dict[int, List[int]] = {nid: [] for nid in id_to_node}

    edge_pairs: Set[Tuple[int, int]] = set()
    edge_ids: Set[str] = set()
    for edge in edges:
        if not isinstance(edge, dict):
            errors.append(_err("EDGE_TYPE", "Each edge must be an object."))
            continue
        src = edge.get("source")
        dst = edge.get("target")
        edge_id_raw = edge.get("id")
        edge_id = str(edge_id_raw or "")
        if not isinstance(edge_id_raw, str) or not edge_id_raw.strip():
            errors.append(_err("EDGE_ID", "Edge `id` must be a non-empty string.", edge_ids=[edge_id]))
        elif edge_id_raw in edge_ids:
            errors.append(_err("EDGE_ID_DUPLICATE", "Edge `id` must be unique.", edge_ids=[edge_id_raw]))
        else:
            edge_ids.add(edge_id_raw)
        if not isinstance(src, int) or not isinstance(dst, int):
            errors.append(_err("EDGE_NODE", "Edge source and target must be integers.", edge_ids=[edge_id]))
            continue
        if src not in id_to_node or dst not in id_to_node:
            errors.append(
                _err(
                    "EDGE_REF",
                    "Edge source/target must reference existing nodes.",
                    [src, dst],
                    [edge_id],
                )
            )
            continue
        if src == dst:
            errors.append(_err("EDGE_SELF_LOOP", "Self-loop is not allowed.", [src], [edge_id]))
        pair = (src, dst)
        if pair in edge_pairs:
            errors.append(_err("EDGE_DUPLICATE", "Duplicate edge is not allowed.", [src, dst], [edge_id]))
            continue
        edge_pairs.add(pair)

        outdegree[src] += 1
        indegree[dst] += 1
        adj[src].append(dst)
        rev[dst].append(src)

    # Degree validation
    for nid, node in id_to_node.items():
        kind = _node_type(node)
        in_d = indegree.get(nid, 0)
        out_d = outdegree.get(nid, 0)
        if kind == "start":
            if in_d != 0 or out_d < 1:
                errors.append(_err("DEGREE_START", "Start node requires indegree=0 and outdegree>=1.", [nid]))
        elif kind == "end":
            if in_d < 1 or out_d != 0:
                errors.append(_err("DEGREE_END", "End node requires indegree>=1 and outdegree=0.", [nid]))
        elif kind == "agent":
            if in_d < 1 or out_d < 1:
                errors.append(_err("DEGREE_AGENT", "Agent requires indegree>=1 and outdegree>=1.", [nid]))

    start_id = 0
    end_id = -1

    # Reachability forward from Start.
    if start_id in id_to_node:
        reachable = _dfs(start_id, adj)
        missing = [nid for nid in id_to_node if nid not in reachable]
        if missing:
            errors.append(
                _err(
                    "REACH_FROM_START",
                    "All nodes must be reachable from Start.",
                    sorted(missing),
                )
            )

    # Reachability to End (reverse traversal).
    if end_id in id_to_node:
        can_reach_end = _dfs(end_id, rev)
        missing = [nid for nid in id_to_node if nid not in can_reach_end]
        if missing:
            errors.append(
                _err(
                    "REACH_TO_END",
                    "All nodes must have a path to End.",
                    sorted(missing),
                )
            )

    # Cycle detection (Kahn)
    if id_to_node:
        has_cycle, cycle_nodes = _has_cycle_kahn(id_to_node.keys(), indegree, adj)
        if has_cycle:
            errors.append(
                _err(
                    "CYCLE",
                    "Workflow graph must be acyclic.",
                    sorted(cycle_nodes),
                )
            )

    # At least one Start -> End path
    if start_id in id_to_node and end_id in id_to_node:
        reachable = _dfs(start_id, adj)
        if end_id not in reachable:
            errors.append(_err("PATH_START_END", "At least one path from Start to End is required."))

    return errors


def _dfs(start: int, graph: Dict[int, List[int]]) -> Set[int]:
    visited: Set[int] = set()
    stack = [start]
    while stack:
        cur = stack.pop()
        if cur in visited:
            continue
        visited.add(cur)
        for nxt in graph.get(cur, []):
            if nxt not in visited:
                stack.append(nxt)
    return visited


def _has_cycle_kahn(
    node_ids: Any,
    indegree: Dict[int, int],
    graph: Dict[int, List[int]],
) -> Tuple[bool, Set[int]]:
    local_indegree = dict(indegree)
    queue = [nid for nid in node_ids if local_indegree.get(nid, 0) == 0]
    visited_count = 0

    while queue:
        cur = queue.pop()
        visited_count += 1
        for nxt in graph.get(cur, []):
            local_indegree[nxt] = local_indegree.get(nxt, 0) - 1
            if local_indegree[nxt] == 0:
                queue.append(nxt)

    total = len(list(node_ids))
    if visited_count == total:
        return False, set()

    cycle_nodes = {nid for nid in node_ids if local_indegree.get(nid, 0) > 0}
    return True, cycle_nodes


def _err(rule: str, message: str, node_ids: List[int] | None = None, edge_ids: List[str] | None = None) -> Dict[str, Any]:
    return {
        "rule": rule,
        "message": message,
        "node_ids": node_ids or [],
        "edge_ids": edge_ids or [],
    }
