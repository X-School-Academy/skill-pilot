import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from .agent import (
    get_agents,
    get_run_events,
    interrupt_run,
    is_run_active,
    is_run_finished,
    start_run,
)
from .documents import delete_document, read_asset, read_document, write_document
from .stages import list_stage_files, list_stages, toggle_skip

router = APIRouter()


def _error_status(message: str) -> int:
    if "not found" in message:
        return 404
    if "not allowed" in message or "must target" in message:
        return 403
    return 400


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@router.get("/api/dev-swarm/sync")
def sync_project():
    try:
        return {
            "stages": list_stages(),
            "syncedAt": _now_iso(),
        }
    except Exception as err:
        return JSONResponse(
            status_code=500,
            content={"detail": str(err) or "Sync failed"},
        )


@router.get("/api/dev-swarm/files/read")
def files_read(path: str = Query(None)):
    if not path:
        return JSONResponse(status_code=400, content={"detail": "path parameter is required"})
    try:
        return read_document(path)
    except Exception as err:
        message = str(err) or "Failed to read document"
        return JSONResponse(status_code=_error_status(message), content={"detail": message})


@router.post("/api/dev-swarm/files/write")
async def files_write(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"detail": "Invalid JSON body"})

    file_path = body.get("path")
    content = body.get("content")
    if not file_path or content is None:
        return JSONResponse(status_code=400, content={"detail": "path and content are required"})
    try:
        return write_document(str(file_path), str(content))
    except Exception as err:
        message = str(err) or "Failed to write document"
        return JSONResponse(status_code=_error_status(message), content={"detail": message})


@router.delete("/api/dev-swarm/files/delete")
async def files_delete(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"detail": "Invalid JSON body"})

    file_path = body.get("path")
    if not file_path:
        return JSONResponse(status_code=400, content={"detail": "path is required"})

    try:
        delete_document(str(file_path))
        return {"ok": True}
    except Exception as err:
        message = str(err) or "Failed to delete document"
        status = 403 if "cannot be deleted" in message else _error_status(message)
        return JSONResponse(status_code=status, content={"detail": message})


@router.get("/api/dev-swarm/stages")
def stages_list():
    try:
        return list_stages()
    except Exception as err:
        return JSONResponse(status_code=500, content={"detail": str(err) or "Failed to list stages"})


@router.get("/api/dev-swarm/stages/{stage_id}/files")
def stages_files(stage_id: str):
    try:
        return list_stage_files(stage_id)
    except Exception as err:
        message = str(err) or "Failed to list files"
        status = 404 if "not found" in message else 500
        return JSONResponse(status_code=status, content={"detail": message})


@router.post("/api/dev-swarm/stages/{stage_id}/skip")
async def stages_skip(stage_id: str, request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"detail": "Invalid JSON body"})
    skip = bool(body.get("skip"))
    try:
        return toggle_skip(stage_id, skip)
    except Exception as err:
        message = str(err) or "Failed to toggle skip"
        if "not found" in message:
            status = 404
        elif "not skippable" in message:
            status = 400
        else:
            status = 500
        return JSONResponse(status_code=status, content={"detail": message})


@router.get("/api/dev-swarm/agents")
def agents():
    try:
        return get_agents()
    except Exception as err:
        return JSONResponse(status_code=500, content={"detail": str(err) or "Failed to load agents"})


@router.post("/api/dev-swarm/agent/run")
async def agent_run_start(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"detail": "Invalid JSON body"})

    stage_id = body.get("stageId")
    prompt = body.get("prompt")
    agent_id = body.get("agentId") or "claude"

    if not stage_id or not prompt:
        return JSONResponse(status_code=400, content={"detail": "stageId and prompt are required"})
    if is_run_active():
        return JSONResponse(status_code=409, content={"detail": "A run is already active"})
    try:
        run = start_run(str(stage_id), str(prompt), str(agent_id))
        return {"runId": run.id, "status": run.status}
    except Exception as err:
        return JSONResponse(status_code=500, content={"detail": str(err) or "Failed to start agent"})


@router.get("/api/dev-swarm/agent/run")
async def agent_run_events(runId: str = Query(None)):
    if not runId:
        return JSONResponse(status_code=400, content={"detail": "runId is required"})

    async def stream():
        last_index = 0
        while True:
            events = get_run_events(runId)
            finished = is_run_finished(runId)
            while last_index < len(events):
                event = events[last_index]
                last_index += 1
                payload = json.dumps(event, ensure_ascii=False)
                category = event.get("category", "output")
                yield f"event: {category}\ndata: {payload}\n\n"
            if finished and last_index >= len(events):
                break
            await asyncio.sleep(0.2)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/api/dev-swarm/agent/interrupt")
def agent_interrupt():
    try:
        run = interrupt_run()
        return {"runId": run.id, "status": run.status}
    except Exception as err:
        return JSONResponse(status_code=409, content={"detail": str(err) or "Failed to interrupt"})


@router.get("/api/dev-swarm/static/{file_path:path}")
def static_asset(file_path: str):
    try:
        content, content_type = read_asset(file_path)
        return Response(
            content=content,
            media_type=content_type,
            headers={"Cache-Control": "no-store"},
        )
    except Exception as err:
        message = str(err) or "Failed to load asset"
        return Response(content=message, status_code=_error_status(message))


@router.get("/api/dev-swarm/html/{file_path:path}")
def html_asset(file_path: str):
    if not file_path.lower().endswith(".html"):
        return Response(content="Only HTML files are supported", status_code=400)

    try:
        doc = read_document(file_path)
    except Exception as err:
        message = str(err) or "Failed to load HTML"
        return Response(content=message, status_code=_error_status(message))

    if doc.get("contentType") != "text/html":
        return Response(content="Only HTML files are supported", status_code=400)
    return Response(
        content=str(doc.get("content", "")),
        media_type="text/html; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )
