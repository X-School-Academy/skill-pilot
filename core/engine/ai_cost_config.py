from typing import Any, Dict


async def save_cost_event(**_: Any) -> Dict[str, Any]:
    return {"data": {"total_cost": 0.0}}


async def save_cost_task(task_type: str, scope: str, total_cost: float) -> Dict[str, Any]:
    _ = task_type
    _ = scope
    _ = total_cost
    return {"status": "ok"}
