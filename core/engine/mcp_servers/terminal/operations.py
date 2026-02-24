from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field


@dataclass
class AsyncOperation:
    operation_id: str
    operation_type: str
    target: str
    context: dict[str, str] = field(default_factory=dict)
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    progress: dict[str, float | int] = field(default_factory=dict)
    result: dict | None = None
    error: str | None = None


class OperationManager:
    def __init__(self, max_operations: int = 500) -> None:
        self._ops: dict[str, AsyncOperation] = {}
        self._max_operations = max_operations
        self._lock = threading.RLock()

    def create(self, operation_type: str, target: str, context: dict[str, str] | None = None) -> AsyncOperation:
        op = AsyncOperation(
            operation_id=str(uuid.uuid4()),
            operation_type=operation_type,
            target=target,
            context=dict(context or {}),
        )
        with self._lock:
            self._ops[op.operation_id] = op
            self._cleanup_if_needed()
        return op

    def mark_running(self, operation_id: str) -> None:
        with self._lock:
            op = self._must_get(operation_id)
            op.status = "running"
            op.updated_at = time.time()

    def set_progress(self, operation_id: str, transferred: int, total: int) -> None:
        with self._lock:
            op = self._must_get(operation_id)
            op.progress = {
                "transferred": max(0, int(transferred)),
                "total": max(0, int(total)),
                "percent": (0.0 if total <= 0 else round((transferred / total) * 100, 2)),
            }
            op.updated_at = time.time()

    def succeed(self, operation_id: str, result: dict) -> None:
        with self._lock:
            op = self._must_get(operation_id)
            op.status = "succeeded"
            op.result = result
            op.error = None
            op.updated_at = time.time()

    def fail(self, operation_id: str, error: str) -> None:
        with self._lock:
            op = self._must_get(operation_id)
            op.status = "failed"
            op.error = error
            op.updated_at = time.time()

    def get(self, operation_id: str) -> AsyncOperation | None:
        with self._lock:
            return self._ops.get(operation_id)

    def as_dict(self, operation_id: str) -> dict:
        with self._lock:
            op = self._must_get(operation_id)
            return self._serialize(op)

    def _cleanup_if_needed(self) -> None:
        if len(self._ops) <= self._max_operations:
            return
        sorted_ids = sorted(self._ops, key=lambda k: self._ops[k].updated_at)
        remove_count = len(self._ops) - self._max_operations
        removed = 0
        for oid in sorted_ids:
            op = self._ops.get(oid)
            if op is None or op.status in {"pending", "running"}:
                continue
            self._ops.pop(oid, None)
            removed += 1
            if removed >= remove_count:
                break

    def _must_get(self, operation_id: str) -> AsyncOperation:
        op = self._ops.get(operation_id)
        if op is None:
            raise ValueError(f"operation not found: {operation_id}")
        return op

    def _serialize(self, op: AsyncOperation) -> dict:
        return {
            "operationId": op.operation_id,
            "type": op.operation_type,
            "target": op.target,
            "status": op.status,
            "context": op.context,
            "progress": op.progress,
            "result": op.result,
            "error": op.error,
            "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(op.created_at)),
            "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(op.updated_at)),
        }
