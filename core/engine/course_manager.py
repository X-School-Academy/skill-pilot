import hashlib
import json
from typing import Any, Dict


def update_node_version(node: Dict[str, Any]) -> Dict[str, Any]:
    payload = json.dumps(node, sort_keys=True, ensure_ascii=False).encode("utf-8")
    node_hash = hashlib.sha256(payload).hexdigest()
    node["hash"] = node_hash
    node["uid"] = node.get("uid") or node_hash[:16]
    node["version"] = int(node.get("version") or 1)
    return node
