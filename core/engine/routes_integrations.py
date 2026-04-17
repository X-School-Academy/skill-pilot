from routes_shared import *


@router.get("/api/llm/providers")
def llm_providers():
    providers = load_llm_providers()
    return {
        "providers": [{"id": p.get("id"), "name": p.get("name")} for p in providers],
        "default": get_default_llm_provider_id(),
        "doctor_default": get_default_doctor_provider_id(),
    }


@router.post("/api/llm/stop")
def llm_stop(payload: Dict[str, Any]):
    return {"status": stop_client(payload.get("client_id"))}


@router.post("/rest/assignment-last-step")
def assignment_last_step(payload: Dict[str, Any]):
    course = payload.get("assignment_token")
    last_step = payload.get("last_step")
    if course is None:
        return {"payload": None, "error": "The task does not exist!"}
    file_path = safe_course_path(course)
    text = file_path.read_text(encoding="utf-8", errors="replace")
    updated = write_course_meta(text, {"last_step": int(last_step or 0)})
    file_path.write_text(updated, encoding="utf-8")
    return {"payload": "OK", "error": None}


@router.post("/rest/assignment-web-url")
def assignment_web_url(payload: Dict[str, Any]):
    course = payload.get("assignment_token")
    web_url = payload.get("web_url")
    if course is None:
        return {"payload": None, "error": "The task does not exist!"}
    file_path = safe_course_path(course)
    text = file_path.read_text(encoding="utf-8", errors="replace")
    updated = write_course_meta(text, {"web_url": web_url})
    file_path.write_text(updated, encoding="utf-8")
    return {"payload": "OK", "error": None}


@router.post("/rest/assignment-activity")
def assignment_activity(payload: Dict[str, Any]):
    course = payload.get("assignment_token")
    if course is None:
        return {"payload": None, "error": "The task does not exist!"}
    file_path = safe_course_path(course)
    text = file_path.read_text(encoding="utf-8", errors="replace")
    updates = {"last_activity": payload, "last_step": payload.get("currentStep")}
    updated = write_course_meta(text, updates)
    file_path.write_text(updated, encoding="utf-8")
    return {"payload": "OK", "error": None}


@router.post("/rest/submit-assignment")
def submit_assignment(payload: Dict[str, Any]):
    course = payload.get("assignment_token")
    if course is None:
        return {"payload": None, "error": "The task does not exist!"}
    updates = {
        "result": payload.get("content"),
        "status": payload.get("status"),
        "feedback": payload.get("feedback"),
        "testResults": payload.get("testResults"),
        "submit_time": datetime.utcnow().isoformat(),
        "last_step": payload.get("currentStep"),
    }
    file_path = safe_course_path(course)
    text = file_path.read_text(encoding="utf-8", errors="replace")
    updated = write_course_meta(text, updates)
    file_path.write_text(updated, encoding="utf-8")
    return {"payload": "OK", "error": None}


@router.post("/rest/tikzjax")
def tikzjax(_: Dict[str, Any]):
    return JSONResponse(status_code=501, content={"payload": None, "error": "tikzjax not configured"})


@router.post("/rest/code_v1")
async def rest_code_v1(request: Request):
    data = await request.json()
    message = data.get("message", "")
    lang = data.get("lang")
    extra = data.get("extraInfo")
    provider_id = data.get("provider")
    client_id = data.get("client_id") or request.headers.get("x-client-id") or request.client.host
    auto_allow = _bool_with_default(data.get("auto_allow"), False)
    network_allow = _bool_with_default(data.get("network_allow"), False)
    sandbox_mode = _bool_with_default(data.get("sandbox_mode"), True)
    system_message = build_code_system_message(message, lang or "any")
    prompt = f"{system_message}\n\nUser:\n{message}"
    if extra:
        prompt = f"{prompt}\n\nExtra Info:\n{extra}"
    if lang:
        prompt = f"Language: {lang}\n{prompt}"
    return StreamingResponse(
        llm_stream(
            prompt,
            provider_id,
            client_id,
            auto_allow=auto_allow,
            network_allow=network_allow,
            sandbox_mode=sandbox_mode,
        ),
        media_type="text/plain",
    )


@router.post("/rest/chat")
async def rest_chat(request: Request):
    data = await request.json()
    message = data.get("message", "")
    extra = data.get("extraInfo")
    to_lang = data.get("toLang")
    lang = data.get("lang") or "any"
    provider_id = data.get("provider")
    client_id = data.get("client_id") or request.headers.get("x-client-id") or request.client.host
    auto_allow = _bool_with_default(data.get("auto_allow"), False)
    network_allow = _bool_with_default(data.get("network_allow"), False)
    sandbox_mode = _bool_with_default(data.get("sandbox_mode"), True)

    if to_lang:
        system_message = build_translate_system_message(lang, to_lang)
    else:
        system_message = build_chat_system_message()

    prompt = f"{system_message}\n\nUser:\n{message}"
    if extra:
        prompt = f"{prompt}\n\nExtra Info:\n{extra}"

    return StreamingResponse(
        llm_stream(
            prompt,
            provider_id,
            client_id,
            auto_allow=auto_allow,
            network_allow=network_allow,
            sandbox_mode=sandbox_mode,
        ),
        media_type="text/plain",
    )


@router.post("/rest/audio")
async def rest_audio(
    file: UploadFile = File(None),
    action: str = Form(None),
    provider: str = Form(None),
    client_id: str = Form(None),
):
    _ = file
    _ = action
    _ = provider
    _ = client_id
    return StreamingResponse(iter([b"[-ERROR-]"]), media_type="text/plain")


@router.post("/api/execute_code")
async def execute_code(request: Request):
    data = await request.json()
    lang = data.get("lang")
    meta = data.get("meta")
    source = data.get("source")
    client_ip = request.client.host if request.client else "local"

    result = execute_code_impl(lang, meta, source, client_ip)
    return {"data": {"execute_code": result}}


@router.post("/api/vscode/event")
async def vscode_event(payload: Dict[str, Any]):
    local_dev_token = str(payload.get("local_dev_token") or LOCAL_DEV_TOKEN or "").strip()
    event_payload = payload.get("payload")

    if not local_dev_token:
        return JSONResponse(
            status_code=400,
            content={"payload": None, "error": "local_dev_token is required"},
        )
    if not isinstance(event_payload, dict):
        return JSONResponse(
            status_code=400,
            content={"payload": None, "error": "payload must be a JSON object"},
        )

    sent_count = await emit_to_vscode_clients(local_dev_token, event_payload)
    if sent_count <= 0:
        return JSONResponse(
            status_code=404,
            content={"payload": None, "error": "No VS Code extension clients connected for this local_dev_token"},
        )

    return {"payload": {"sent": sent_count}, "error": None}


@router.get("/api/auth/status")
def auth_status(request: Request):
    return {"authenticated": _is_authorized_request(request)}


@router.post("/api/auth/session")
async def auth_session(request: Request):
    data = await request.json()
    provided = _sanitize_single_line_secret(str(data.get("auth_token") or ""))
    expected = _sanitize_single_line_secret(get_auth_token())
    if not provided:
        return JSONResponse(status_code=400, content={"error": "auth_token is required"})
    if not expected or not secrets.compare_digest(provided, expected):
        return JSONResponse(status_code=401, content={"error": "invalid auth token"})

    response = JSONResponse(content={"status": "ok", "message": "Authenticated"})
    response.set_cookie(
        key=_AUTH_COOKIE_NAME,
        value=expected,
        httponly=True,
        secure=get_only_allow_https(),
        samesite="lax",
        path="/",
        max_age=_AUTH_COOKIE_MAX_AGE,
    )
    return response


@router.post("/api/discord/broadcast")
async def discord_broadcast(request: Request):
    if not _is_authorized_request(request):
        return _auth_required_response()
    data = await request.json()
    message_text = (str(data.get("message") or "")).strip()
    if not message_text:
        return JSONResponse(status_code=400, content={"error": "message is required"})
    from discord_bot import send_dm_to_all
    count = await send_dm_to_all(message_text)
    return {"status": "ok", "sent_count": count}


@router.get("/api/discord/status")
def discord_status(request: Request):
    if not _is_authorized_request(request):
        return _auth_required_response()
    has_token = bool(get_discord_bot_token())
    connected = False
    bot_name = None
    guild_count = 0
    if has_token:
        try:
            from discord_bot import bot
            connected = bot.is_ready()
            if connected and bot.user:
                bot_name = str(bot.user)
                guild_count = len(bot.guilds)
        except Exception:
            pass
    keys_safe_guard_enabled = os.getenv("IN_KEYS_SAFE_GUARD", "").strip() == "1"
    return {
        "has_token": has_token,
        "connected": connected,
        "bot_name": bot_name,
        "guild_count": guild_count,
        "keys_safe_guard_enabled": keys_safe_guard_enabled,
    }


@router.get("/api/discord/sessions")
def discord_sessions_list(request: Request):
    if not _is_authorized_request(request):
        return _auth_required_response()
    from discord_session import SessionManager
    mgr = SessionManager()
    return {"sessions": mgr.list_sessions()}


@router.get("/api/discord/sessions/{channel_id}")
def discord_session_history(channel_id: str, request: Request):
    if not _is_authorized_request(request):
        return _auth_required_response()
    from discord_session import ChatSession
    session = ChatSession(channel_id)
    history = session.get_full_history()
    return {"channel_id": channel_id, "messages": history}


@router.get("/api/live-avatar/config")
def live_avatar_config(request: Request):
    if not _is_authorized_request(request):
        return _auth_required_response()
    return JSONResponse({
        "live_avatar_ws_url": get_live_avatar_server_url(),
        "turn_server_urls": get_turn_server_urls(),
        "turn_server_username": get_turn_server_username(),
        "turn_server_password": get_turn_server_password(),
    })


@router.get("/api/cameras/config")
def cameras_config(request: Request):
    if not _is_authorized_request(request):
        return _auth_required_response()
    return JSONResponse({
        "turn_server_urls": get_turn_server_urls(),
        "turn_server_username": get_turn_server_username(),
        "turn_server_password": get_turn_server_password(),
    })


# ── Cameras MCP client (lazy singleton) ──────────────────────────────────────
_cameras_mcp_client = None
_cameras_mcp_lock = asyncio.Lock()
_cameras_signal_tool_lock = asyncio.Lock()


async def _get_cameras_client():
    """Return a live StdioClient for the cameras MCP server, creating it on first call."""
    global _cameras_mcp_client
    async with _cameras_mcp_lock:
        if _cameras_mcp_client is not None:
            # Check if the subprocess is still alive
            proc = getattr(_cameras_mcp_client, "_process", None)
            if proc is not None and proc.poll() is None:
                return _cameras_mcp_client
        # (Re)create the client
        from mcp_servers.mcp_to_skills.sync import create_client, load_mcp_configs, is_server_enabled
        configs, _ = await asyncio.to_thread(load_mcp_configs, _MCP_CONFIG_PATH)
        cam_cfg = configs.get("cameras")
        if cam_cfg is None:
            raise RuntimeError("cameras MCP server not found in config/mcp.json5")
        if not is_server_enabled(cam_cfg):
            raise RuntimeError("cameras MCP server is disabled — enable it in MCP settings first")
        _cameras_mcp_client = await asyncio.to_thread(create_client, cam_cfg)
        return _cameras_mcp_client


async def _reset_cameras_client() -> None:
    global _cameras_mcp_client
    async with _cameras_mcp_lock:
        client = _cameras_mcp_client
        _cameras_mcp_client = None
    if client is not None:
        try:
            await asyncio.to_thread(client.close)
        except Exception:
            pass


async def _call_cameras_tool(
    tool_name: str,
    arguments: dict[str, Any],
    *,
    timeout_seconds: float = 20.0,
    retry_timeouts: tuple[float, float] | None = None,
) -> Any:
    """Call a cameras MCP tool with timeout and one automatic client-reset retry."""
    async with _cameras_signal_tool_lock:
        last_exc: Exception | None = None
        for _attempt in (1, 2):
            current_timeout = (
                retry_timeouts[_attempt - 1]
                if retry_timeouts is not None
                else timeout_seconds
            )
            started = time.monotonic()
            try:
                client = await _get_cameras_client()
                result = await asyncio.wait_for(
                    asyncio.to_thread(
                        client.request,
                        "tools/call",
                        {"name": tool_name, "arguments": arguments},
                    ),
                    timeout=current_timeout,
                )
                elapsed_ms = int((time.monotonic() - started) * 1000)
                logger.info(
                    "[cameras.signal] tool=%s attempt=%d ok elapsed_ms=%d timeout_ms=%d",
                    tool_name,
                    _attempt,
                    elapsed_ms,
                    int(current_timeout * 1000),
                )
                return result
            except Exception as exc:
                last_exc = exc
                elapsed_ms = int((time.monotonic() - started) * 1000)
                logger.warning(
                    "[cameras.signal] tool=%s attempt=%d failed elapsed_ms=%d timeout_ms=%d error=%s",
                    tool_name,
                    _attempt,
                    elapsed_ms,
                    int(current_timeout * 1000),
                    exc,
                )
                await _reset_cameras_client()
        if last_exc is None:
            raise RuntimeError("Unknown cameras MCP call error")
        raise last_exc


@router.post("/api/cameras/signal")
async def cameras_signal(request: Request):
    if not _is_authorized_request(request):
        return _auth_required_response()
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    signal_type = body.get("type", "")
    req_started = time.monotonic()
    logger.info("[cameras.signal] recv type=%s", signal_type)
    try:
        client = await _get_cameras_client()
    except RuntimeError as exc:
        return JSONResponse(status_code=503, content={"error": str(exc)})

    if signal_type == "offer":
        def _normalize_sdp_answer(payload: Any) -> dict[str, Any] | Any:
            if not isinstance(payload, dict):
                return payload
            # Some MCP tool wrappers return {"result":"{...json...}"} (or nested dict).
            # Unwrap that shape first so WebUI always receives top-level sdp/type.
            if "result" in payload and ("sdp" not in payload and "type" not in payload and "sdpType" not in payload):
                result_payload = payload.get("result")
                if isinstance(result_payload, str):
                    try:
                        decoded = json.loads(result_payload)
                        if isinstance(decoded, dict):
                            payload = decoded
                    except json.JSONDecodeError:
                        pass
                elif isinstance(result_payload, dict):
                    payload = result_payload
            answer_type = payload.get("type")
            if not isinstance(answer_type, str) or not answer_type:
                if isinstance(payload.get("sdpType"), str) and payload.get("sdpType"):
                    payload["type"] = payload["sdpType"]
                elif isinstance(payload.get("sdp_type"), str) and payload.get("sdp_type"):
                    payload["type"] = payload["sdp_type"]
            if isinstance(payload.get("type"), str) and payload.get("type") and "sdpType" not in payload:
                payload["sdpType"] = payload["type"]
            return payload

        sdp = body.get("sdp", "")
        sdp_type = body.get("sdpType", "offer")
        is_ice_restart = bool(body.get("iceRestart", False))
        candidates = body.get("candidates", [])
        if not isinstance(candidates, list):
            candidates = []
        if not sdp:
            return JSONResponse(status_code=400, content={"error": "sdp is required"})
        try:
            result_raw = await _call_cameras_tool(
                "webrtc_offer",
                {
                    "sdp": sdp,
                    "sdp_type": sdp_type,
                    "candidates": candidates,
                },
                timeout_seconds=6.0,
                retry_timeouts=(2.5, 6.0) if is_ice_restart else None,
            )
        except Exception as exc:
            logger.warning("[cameras.signal] offer failed error=%s", exc)
            return JSONResponse(status_code=502, content={"error": f"cameras MCP webrtc_offer failed: {exc}"})
        # Accept both structuredContent and text content from MCP responses.
        if not isinstance(result_raw, dict):
            return JSONResponse(status_code=502, content={"error": "Invalid cameras MCP response"})
        if isinstance(result_raw.get("structuredContent"), dict):
            return JSONResponse(_normalize_sdp_answer(result_raw["structuredContent"]))
        if isinstance(result_raw.get("sdp"), str) and isinstance(result_raw.get("type"), str):
            return JSONResponse({"sdp": result_raw["sdp"], "type": result_raw["type"]})

        content = result_raw.get("content")
        text = ""
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    candidate = item.get("text")
                    if isinstance(candidate, str) and candidate.strip():
                        text = candidate
                        break
        if bool(result_raw.get("isError")):
            detail = text or "Unknown cameras MCP tool error"
            return JSONResponse(status_code=502, content={"error": detail})
        if not text:
            return JSONResponse(
                status_code=502,
                content={"error": "Empty cameras MCP response for webrtc_offer"},
            )
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return JSONResponse(
                status_code=502,
                content={"error": "Invalid JSON from cameras MCP webrtc_offer", "raw": text[:300]},
            )
        if not isinstance(parsed, dict):
            return JSONResponse(status_code=502, content={"error": "Unexpected webrtc_offer response shape"})
        normalized = _normalize_sdp_answer(parsed)
        elapsed_ms = int((time.monotonic() - req_started) * 1000)
        cand_count = len(normalized.get("candidates", [])) if isinstance(normalized, dict) and isinstance(normalized.get("candidates"), list) else 0
        logger.info("[cameras.signal] offer ok elapsed_ms=%d answer_candidates=%d", elapsed_ms, cand_count)
        return JSONResponse(normalized)

    elif signal_type == "ice_candidate":
        candidate = body.get("candidate", {})
        if not candidate:
            return JSONResponse(status_code=400, content={"error": "candidate is required"})
        try:
            ice_result = await _call_cameras_tool(
                "webrtc_ice_candidate",
                {
                    "candidate": candidate.get("candidate", ""),
                    "sdp_mid": candidate.get("sdpMid", ""),
                    "sdp_mline_index": int(candidate.get("sdpMLineIndex", 0)),
                },
                timeout_seconds=4.0,
            )
        except Exception as exc:
            logger.warning("[cameras.signal] ice_candidate failed error=%s", exc)
            return JSONResponse(status_code=502, content={"error": f"cameras MCP webrtc_ice_candidate failed: {exc}"})
        if isinstance(ice_result, dict) and bool(ice_result.get("isError")):
            content = ice_result.get("content")
            detail = "Unknown cameras MCP tool error"
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        text = item.get("text")
                        if isinstance(text, str) and text.strip():
                            detail = text
                            break
            return JSONResponse(status_code=502, content={"error": detail})
        elapsed_ms = int((time.monotonic() - req_started) * 1000)
        logger.info("[cameras.signal] ice_candidate ok elapsed_ms=%d", elapsed_ms)
        return JSONResponse({"status": "ok"})

    else:
        return JSONResponse(status_code=400, content={"error": f"Unknown signal type: {signal_type}"})


@router.post("/api/webui/log")
async def webui_log(request: Request):
    if not _is_authorized_request(request):
        return _auth_required_response()
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
    if not isinstance(payload, dict):
        return JSONResponse(status_code=400, content={"error": "payload must be an object"})

    tag = str(payload.get("tag") or "webui").replace("\n", " ").replace("\r", " ").strip()
    level = str(payload.get("level") or "info").lower()
    message = str(payload.get("message") or "").replace("\n", " ").replace("\r", " ").strip()
    data = payload.get("data")

    if not message:
        return JSONResponse(status_code=400, content={"error": "message is required"})

    line = f"[{tag}] {message}"
    if data is not None:
        line = f"{line} data={data!r}"

    if level in {"error"}:
        logger.error(line)
    elif level in {"warn", "warning"}:
        logger.warning(line)
    elif level in {"debug"}:
        logger.debug(line)
    else:
        logger.info(line)
    return JSONResponse({"status": "ok"})


@router.post("/api/internal/discord/notify")
async def internal_discord_notify(request: Request):
    """Internal endpoint for cameras MCP server to send Discord DMs with detection images."""
    # Only allow requests from localhost
    client_host = request.client.host if request.client else ""
    if client_host not in ("127.0.0.1", "::1", "localhost"):
        return JSONResponse(status_code=403, content={"error": "Forbidden"})
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
    message = str(body.get("message", ""))
    image_path = str(body.get("image_path", ""))
    if not message:
        return JSONResponse(status_code=400, content={"error": "message is required"})
    try:
        from discord_bot import bot, send_dm_to_all
        if bot.is_ready():
            sent = await send_dm_to_all(message, image_path=image_path or None)
            return JSONResponse({"status": "ok", "sent": sent})
        else:
            return JSONResponse({"status": "skipped", "reason": "Discord bot not ready"})
    except Exception as exc:
        logger.warning("Discord notify error: %s", exc)
        return JSONResponse(status_code=500, content={"error": str(exc)})


@router.post("/api/discord/token")
async def discord_token_save(request: Request):
    if not _is_authorized_request(request):
        return _auth_required_response()
    data = await request.json()
    token = _sanitize_single_line_secret(str(data.get("token") or ""))
    if not token:
        return JSONResponse(status_code=400, content={"error": "token is required"})

    keys_safe_guard = str(PROJECT_DIR / "core" / "bin" / "keys-safe-guard")
    cmd = [keys_safe_guard]
    if os.getenv("IN_KEYS_SAFE_GUARD", "").strip() == "1":
        # config/.env is root-owned — request GUI elevation dialog.
        cmd.append("--gui")
    cmd += ["put_key_values", f"DISCORD_BOT_TOKEN={token}"]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("keys-safe-guard failed: %s", result.stderr)
        detail = (result.stderr or result.stdout or "").strip()
        if detail:
            detail = f"\n\nDetails:\n{detail}"
        return JSONResponse(
            status_code=500,
            content={
                "error": (
                    "Could not save token with keys-safe-guard. "
                    "If safe guard is enabled, this request needs either a GUI permission dialog or passwordless sudo. "
                    "Otherwise disable safe guard and retry.\n"
                    "To set the token manually, run as root:\n"
                    "  sudo nano config/.env\n"
                    "then add or update the line:\n"
                    "  DISCORD_BOT_TOKEN=<your-token>"
                    f"{detail}"
                )
            },
        )
    # Keep the running engine environment in sync for callers that still rely on this route.
    os.environ["DISCORD_BOT_TOKEN"] = token

    return {"status": "ok", "message": "Token saved and applied to the running engine."}


@router.post("/api/create_course_plan")
@router.post("/create_course_plan")
def create_course_plan(payload: Dict[str, Any]):
    requirement = str(payload.get("requirement") or "").strip()
    language = str(payload.get("language") or "English").strip() or "English"
    if not requirement:
        return JSONResponse(status_code=400, content={"error": "requirement is required"})

    course_details = COURSE_PLANNER.create_course_plan(requirement=requirement, language=language)
    return {"course_details": course_details}


@router.post("/api/create_multiple_scene_video")
@router.post("/create_multiple_scene_video")
def create_multiple_scene_video(payload: Dict[str, Any]):
    requirement = str(payload.get("requirement") or "").strip()
    if not requirement:
        return JSONResponse(status_code=400, content={"error": "requirement is required"})

    try:
        target_duration = int(payload.get("target_duration") or 60)
    except (TypeError, ValueError):
        target_duration = 60
    resolution = str(payload.get("resolution") or "1080x1920")
    output_path = str(payload.get("output_path") or "/tmp").strip() or "/tmp"
    voice_name = str(payload.get("voice_name") or "").strip() or None
    theme = str(payload.get("theme") or "").strip() or None
    result = VIDEO_CREATOR.create_multiple_scene_video(
        requirement=requirement,
        target_duration=target_duration,
        resolution=resolution,
        output_path=output_path,
        voice_name=voice_name,
        theme=theme,
    )
    return result


@router.post("/api/resume_multiple_scene_video")
@router.post("/resume_multiple_scene_video")
def resume_multiple_scene_video(payload: Dict[str, Any]):
    output_path = str(payload.get("output_path") or "/tmp").strip() or "/tmp"
    result = VIDEO_CREATOR.resume_multiple_scene_video(output_path=output_path)
    return result



