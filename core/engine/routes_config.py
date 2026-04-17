from routes_shared import *


@router.get("/api/config/settings")
def config_settings_get():
    try:
        return _read_settings()
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


@router.get("/api/config/env-safeguard-status")
def config_env_safeguard_status():
    try:
        exists = _CONFIG_ENV_PATH.is_file()
        if not exists:
            return {
                "enabled": False,
                "exists": False,
                "reason": "config/.env not found",
                "repo_root": str(_REPO_ROOT),
            }

        stat_result = _CONFIG_ENV_PATH.stat()
        mode = stat_result.st_mode & 0o777
        owner_is_root = stat_result.st_uid == 0
        readable = os.access(_CONFIG_ENV_PATH, os.R_OK)
        enabled = owner_is_root and mode == 0o600 and not readable
        if enabled:
            reason = "Safe guard is enabled."
        else:
            reason = "Safe guard is not enabled."

        return {
            "enabled": enabled,
            "exists": True,
            "reason": reason,
            "owner_uid": stat_result.st_uid,
            "mode": f"{mode:o}",
            "readable_by_process": readable,
            "repo_root": str(_REPO_ROOT),
        }
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


@router.post("/api/config/settings")
async def config_settings_save(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})
    try:
        _write_settings(body)
    except OSError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})
    return {"status": "ok"}


_DEFAULT_LLM_RE = re.compile(
    r"""("default"\s*:\s*\{[^}]*?"llm"\s*:\s*)"([^"]*)" """.strip(),
    re.DOTALL,
)
_DEFAULT_LLM_RE_JSON5 = re.compile(
    r"""(default\s*:\s*\{[^}]*?llm\s*:\s*)'([^']*)' """.strip(),
    re.DOTALL,
)
_DEFAULT_DOCTOR_RE = re.compile(
    r"""("default"\s*:\s*\{[^}]*?"doctor"\s*:\s*)"([^"]*)" """.strip(),
    re.DOTALL,
)
_DEFAULT_DOCTOR_RE_JSON5 = re.compile(
    r"""(default\s*:\s*\{[^}]*?doctor\s*:\s*)'([^']*)' """.strip(),
    re.DOTALL,
)


@router.post("/api/config/default-provider")
async def config_default_provider(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})
    provider_id = (str(body.get("provider") or "")).strip()
    if not provider_id:
        return JSONResponse(status_code=400, content={"error": "provider is required"})
    target = (str(body.get("target") or "llm")).strip().lower()
    if target not in {"llm", "doctor"}:
        return JSONResponse(status_code=400, content={"error": "target must be llm or doctor"})
    try:
        text = _AI_PROVIDERS_PATH.read_text(encoding="utf-8")
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": f"Failed to read ai_providers: {exc}"})
    if target == "llm":
        new_text, count = _DEFAULT_LLM_RE.subn(rf'\g<1>"{provider_id}"', text, count=1)
        if count == 0:
            new_text, count = _DEFAULT_LLM_RE_JSON5.subn(rf"\g<1>'{provider_id}'", text, count=1)
        if count == 0:
            return JSONResponse(status_code=500, content={"error": "Could not find default.llm in ai_providers config"})
    else:
        new_text, count = _DEFAULT_DOCTOR_RE.subn(rf'\g<1>"{provider_id}"', text, count=1)
        if count == 0:
            new_text, count = _DEFAULT_DOCTOR_RE_JSON5.subn(rf"\g<1>'{provider_id}'", text, count=1)
        if count == 0:
            return JSONResponse(status_code=500, content={"error": "Could not find default.doctor in ai_providers config"})
    try:
        _AI_PROVIDERS_PATH.write_text(new_text, encoding="utf-8")
    except OSError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})
    return {"status": "ok", "provider": provider_id, "target": target}


_PROFILE_PATH = _REPO_ROOT / "config" / "profile.json5"


@router.get("/api/config/profile")
def config_profile_get():
    data: Dict[str, Any] = {}
    if _PROFILE_PATH.is_file():
        try:
            loaded = json5.loads(_PROFILE_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        except Exception as exc:
            logger.warning("Failed to read profile: %s", exc)
    return data


@router.post("/api/config/profile")
async def config_profile_save(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})
    if not isinstance(body, dict):
        return JSONResponse(status_code=400, content={"error": "Profile must be a JSON object"})
    tz_value = (str(body.get("timezone") or "")).strip()
    if tz_value:
        import pytz
        try:
            pytz.timezone(tz_value)
        except pytz.exceptions.UnknownTimeZoneError:
            return JSONResponse(status_code=400, content={"error": f"Invalid timezone: {tz_value}"})
    _PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        _PROFILE_PATH.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})
    return {"status": "ok"}


@router.get("/api/config/timezones")
def config_timezones():
    import pytz
    return {"timezones": pytz.common_timezones}


def _read_mcp_config() -> Dict[str, Any]:
    if not _MCP_CONFIG_PATH.is_file():
        return {"mcpServers": {}}
    return json5.loads(_MCP_CONFIG_PATH.read_text(encoding="utf-8"))


def _write_mcp_config(data: Dict[str, Any]) -> None:
    _MCP_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _MCP_CONFIG_PATH.write_text(json5.dumps(data, indent=2) + "\n", encoding="utf-8")


def _infer_mcp_server_type(config: Dict[str, Any]) -> str:
    raw_type = config.get("type", "")
    if raw_type == "http":
        return "streamable-http"
    if raw_type == "sse":
        return "sse"
    return "stdio"


def _parse_bool_value(value: Any) -> bool:
    """Parse a potentially string-typed bool field from env expansion."""
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes")
    return bool(value)


@router.get("/api/config/mcp-servers")
def config_mcp_servers_list():
    try:
        data = _read_mcp_config()
    except (ValueError, OSError) as exc:
        return JSONResponse(status_code=500, content={"error": str(exc), "servers": []})
    from mcp_servers.mcp_to_skills.sync import expand_env_placeholders
    expansion_env = dict(os.environ)
    servers_dict = data.get("mcpServers", {})
    servers = []
    for name, cfg in servers_dict.items():
        missing: set = set()
        expanded = expand_env_placeholders(cfg, expansion_env, missing)
        entry: Dict[str, Any] = {"name": name, "type": _infer_mcp_server_type(expanded)}
        if expanded.get("system"):
            entry["system"] = True
        enabled_raw = expanded.get("enabled")
        disabled_raw = expanded.get("disabled", False)
        if enabled_raw is not None:
            is_disabled = not _parse_bool_value(enabled_raw)
        else:
            is_disabled = _parse_bool_value(disabled_raw)
        if is_disabled:
            entry["disabled"] = True
        for field in ("command", "args", "env", "url", "headers"):
            if field in expanded:
                entry[field] = expanded[field]
        servers.append(entry)
    return {"servers": servers}


@router.post("/api/config/mcp-servers")
async def config_mcp_servers_save(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    name = (str(body.get("name") or "")).strip()
    if not name or not _MCP_SERVER_NAME_RE.fullmatch(name):
        return JSONResponse(status_code=400, content={"error": "Invalid server name. Use only letters, digits, hyphens, and underscores."})

    server_type = str(body.get("type") or "stdio").strip()
    if server_type not in ("stdio", "streamable-http", "sse"):
        return JSONResponse(status_code=400, content={"error": f"Invalid type: {server_type}"})

    try:
        data = _read_mcp_config()
    except (json.JSONDecodeError, OSError) as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})

    servers = data.get("mcpServers", {})
    existing = servers.get(name)
    if existing and existing.get("system"):
        return JSONResponse(status_code=403, content={"error": f"Cannot modify system server: {name}"})

    entry: Dict[str, Any] = {}
    if server_type == "stdio":
        command = (str(body.get("command") or "")).strip()
        if not command:
            return JSONResponse(status_code=400, content={"error": "command is required for stdio type"})
        entry["command"] = command
        args = body.get("args")
        if isinstance(args, list) and args:
            entry["args"] = [str(a) for a in args]
        env = body.get("env")
        if isinstance(env, dict) and env:
            entry["env"] = {str(k): str(v) for k, v in env.items()}
    else:
        url = (str(body.get("url") or "")).strip()
        if not url:
            return JSONResponse(status_code=400, content={"error": "url is required for http/sse type"})
        entry["type"] = "http" if server_type == "streamable-http" else "sse"
        entry["url"] = url
        headers = body.get("headers")
        if isinstance(headers, dict) and headers:
            entry["headers"] = {str(k): str(v) for k, v in headers.items()}

    disabled = body.get("disabled")
    if disabled is True or disabled is False:
        entry["disabled"] = disabled

    servers[name] = entry
    data["mcpServers"] = servers
    try:
        _write_mcp_config(data)
    except OSError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})

    # Auto-install requirements.txt if enabling a stdio server that has one
    enabling = disabled is False or (disabled is None and not entry.get("disabled", False))
    if enabling and server_type == "stdio":
        req_path = _REPO_ROOT / "core" / "engine" / "mcp_servers" / name / "requirements.txt"
        if req_path.exists():
            engine_dir = str(_REPO_ROOT / "core" / "engine")
            req_rel = str(req_path.relative_to(_REPO_ROOT / "core" / "engine"))
            try:
                subprocess.run(
                    ["uv", "add", "-r", req_rel],
                    cwd=engine_dir,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
            except Exception as exc:
                logger.warning("Failed to install requirements for %s: %s", name, exc)

    return {"status": "ok", "name": name}


@router.delete("/api/config/mcp-servers/{name}")
def config_mcp_servers_delete(name: str):
    name = name.strip()
    if not name or not _MCP_SERVER_NAME_RE.fullmatch(name):
        return JSONResponse(status_code=400, content={"error": "Invalid server name"})

    try:
        data = _read_mcp_config()
    except (json.JSONDecodeError, OSError) as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})

    servers = data.get("mcpServers", {})
    existing = servers.get(name)
    if not existing:
        return JSONResponse(status_code=404, content={"error": f"Server not found: {name}"})
    if existing.get("system"):
        return JSONResponse(status_code=403, content={"error": f"Cannot delete system server: {name}"})

    del servers[name]
    data["mcpServers"] = servers
    try:
        _write_mcp_config(data)
    except OSError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})
    return {"status": "ok", "name": name}


def _parse_skill_frontmatter(skill_md_path: Path) -> Dict[str, str]:
    text = skill_md_path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    block = text[3:end]
    result: Dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


def _read_disabled_skills() -> List[str]:
    if not _DISABLED_SKILLS_PATH.is_file():
        return []
    try:
        data = json5.loads(_DISABLED_SKILLS_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [str(s) for s in data]
    except (ValueError, OSError):
        pass
    return []


@router.get("/api/config/skills")
def config_skills_list():
    disabled_set = set(_read_disabled_skills())
    categories = []
    for cat_id, cat_label, cat_dir in _SKILL_CATEGORIES:
        skills = []
        if cat_dir.is_dir():
            for child in sorted(cat_dir.iterdir()):
                skill_md = child / "SKILL.md"
                if child.is_dir() and skill_md.exists():
                    meta = _parse_skill_frontmatter(skill_md)
                    skills.append({
                        "name": meta.get("name", child.name),
                        "description": meta.get("description", ""),
                        "disabled": child.name in disabled_set,
                    })
        categories.append({"id": cat_id, "label": cat_label, "skills": skills})
    return {"categories": categories}


@router.post("/api/config/skills/update")
async def config_skills_update(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    disabled = body.get("disabled", [])
    if not isinstance(disabled, list):
        return JSONResponse(status_code=400, content={"error": "disabled must be an array"})

    _DISABLED_SKILLS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _DISABLED_SKILLS_PATH.write_text(
        json5.dumps(disabled, indent=2) + "\n", encoding="utf-8"
    )

    bin_dir = _REPO_ROOT / "core" / "bin"
    skill_verify_paths: List[str] = []
    for _, _, cat_dir in _SKILL_CATEGORIES:
        if cat_dir.is_dir():
            for child in sorted(cat_dir.iterdir()):
                if child.is_dir() and (child / "SKILL.md").exists():
                    skill_verify_paths.append(str(child))

    commands: List[tuple[str, List[str]]] = [
        ("skill-verify", [str(bin_dir / "skill-verify")] + skill_verify_paths),
        ("skill-install", [str(bin_dir / "skill-install")]),
    ]

    results: List[Dict[str, Any]] = []
    for cmd_name, cmd_args in commands:
        if cmd_name == "skill-verify" and not skill_verify_paths:
            results.append({"command": cmd_name, "exit_code": 0, "output": "No skills to verify (skipped)"})
            continue
        try:
            proc = await asyncio.to_thread(
                subprocess.run,
                cmd_args,
                capture_output=True,
                text=True,
                cwd=str(_REPO_ROOT),
                timeout=120,
                shell=False,
                env=safe_env(),
            )
            results.append({
                "command": cmd_name,
                "exit_code": proc.returncode,
                "output": (proc.stdout or "") + (proc.stderr or ""),
            })
        except subprocess.TimeoutExpired:
            results.append({"command": cmd_name, "exit_code": -1, "output": "Timed out after 120s"})
        except Exception as exc:
            results.append({"command": cmd_name, "exit_code": -1, "output": str(exc)})

    return {"status": "ok", "results": results}


@router.get("/api/config/extensions")
def config_extensions_list():
    return {"extensions": _list_extensions()}


@router.post("/api/config/extensions/action")
async def config_extensions_action(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    dir_name = str(body.get("dir") or "").strip()
    action = str(body.get("action") or "").strip()
    if not dir_name:
        return JSONResponse(status_code=400, content={"error": "dir is required"})
    if action not in _EXTENSION_ACTIONS:
        return JSONResponse(status_code=400, content={"error": "action must be install, update, or uninstall"})

    entry = _find_extension(dir_name)
    if entry is None:
        return JSONResponse(status_code=404, content={"error": f"Extension not found: {dir_name}"})
    if entry.get("type") != "script":
        return JSONResponse(status_code=400, content={"error": f"Extension does not support script actions: {dir_name}"})

    ext_dir = (_EXTENSIONS_DIR / dir_name).resolve()
    script_rel = str(entry.get("script") or "extension.py").strip() or "extension.py"
    script_path = (ext_dir / script_rel).resolve()
    try:
        script_path.relative_to(ext_dir)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "script must stay inside the extension directory"})

    if not script_path.is_file():
        return JSONResponse(status_code=404, content={"error": f"Script not found: {script_rel}"})

    python_bin = _REPO_ROOT / "core" / "bin" / "python"
    if not python_bin.is_file():
        return JSONResponse(status_code=500, content={"error": "core/bin/python not found"})

    try:
        proc = await asyncio.to_thread(
            subprocess.run,
            [str(python_bin), str(script_path), action],
            capture_output=True,
            text=True,
            cwd=str(ext_dir),
            timeout=300,
            shell=False,
            env=safe_env(),
        )
    except subprocess.TimeoutExpired:
        return JSONResponse(status_code=500, content={"error": "Extension command timed out after 300s"})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})

    output = (proc.stdout or "") + (proc.stderr or "")
    payload = {
        "dir": dir_name,
        "action": action,
        "exit_code": proc.returncode,
        "output": output,
    }
    if proc.returncode != 0:
        return JSONResponse(status_code=500, content=payload)

    # Update the installed flag in extension.json5 after successful install/uninstall
    if action in ("install", "uninstall"):
        config_path = ext_dir / "extension.json5"
        try:
            raw_text = config_path.read_text(encoding="utf-8")
            raw_data = json5.loads(raw_text)
            if isinstance(raw_data, dict):
                raw_data["installed"] = action == "install"
                config_path.write_text(
                    json5.dumps(raw_data, indent=2, ensure_ascii=False, trailing_commas=False) + "\n",
                    encoding="utf-8",
                )
        except Exception as exc:
            logger.warning("Failed to update installed flag in %s: %s", config_path, exc)

    return payload


def _serve_extension_static(dir_name: str, file_path: str):
    """Serve static files from an extension folder.

    Only serves files when the extension has an HTML entrypoint configured.
    Does not serve directory listings; only serves actual files.
    If no file_path is given, serves the entrypoint (e.g. index.html).
    """
    entry = _find_extension(dir_name)
    if entry is None:
        return JSONResponse(status_code=404, content={"error": f"Extension not found: {dir_name}"})

    entrypoint = str(entry.get("entrypoint") or "").strip()
    if not entrypoint or not entrypoint.endswith(".html"):
        return JSONResponse(status_code=400, content={"error": "Extension does not have an HTML entrypoint"})

    ext_dir = (_EXTENSIONS_DIR / dir_name).resolve()
    if not ext_dir.is_dir():
        return JSONResponse(status_code=404, content={"error": f"Extension directory not found: {dir_name}"})

    # Default to entrypoint if path is empty
    target_path = file_path.strip() if file_path.strip() else entrypoint
    resolved = (ext_dir / target_path).resolve()

    # Security: ensure the resolved path is inside the extension directory
    try:
        resolved.relative_to(ext_dir)
    except ValueError:
        return JSONResponse(status_code=403, content={"error": "Path traversal not allowed"})

    if not resolved.is_file():
        return JSONResponse(status_code=404, content={"error": f"File not found: {target_path}"})

    # Determine content type
    import mimetypes
    content_type, _ = mimetypes.guess_type(str(resolved))
    if content_type is None:
        content_type = "application/octet-stream"

    return FileResponse(str(resolved), media_type=content_type)


@router.get("/api/config/extensions/{dir_name}/static")
def config_extension_static_root(dir_name: str):
    return _serve_extension_static(dir_name, "")


@router.get("/api/config/extensions/{dir_name}/static/{file_path:path}")
def config_extension_static(dir_name: str, file_path: str):
    return _serve_extension_static(dir_name, file_path)


def _find_skill_category_dir(category: str) -> Path | None:
    for cat_id, _, cat_dir in _SKILL_CATEGORIES:
        if cat_id == category:
            return cat_dir
    return None


@router.get("/api/config/skills/{category}/{name}/content")
def config_skill_content_read(category: str, name: str):
    cat_dir = _find_skill_category_dir(category)
    if cat_dir is None:
        return JSONResponse(status_code=404, content={"error": f"Unknown category: {category}"})
    skill_md = cat_dir / name / "SKILL.md"
    if not skill_md.is_file():
        return JSONResponse(status_code=404, content={"error": f"Skill not found: {category}/{name}"})
    content = skill_md.read_text(encoding="utf-8", errors="replace")
    return {"content": content}


@router.post("/api/config/skills/{category}/{name}/content")
async def config_skill_content_write(category: str, name: str, request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    content = body.get("content")
    if content is None:
        return JSONResponse(status_code=400, content={"error": "content is required"})

    cat_dir = _find_skill_category_dir(category)
    if cat_dir is None:
        return JSONResponse(status_code=404, content={"error": f"Unknown category: {category}"})
    skill_dir = cat_dir / name
    skill_md = skill_dir / "SKILL.md"
    if not skill_dir.is_dir():
        return JSONResponse(status_code=404, content={"error": f"Skill not found: {category}/{name}"})

    skill_md.write_text(content, encoding="utf-8")

    bin_dir = _REPO_ROOT / "core" / "bin"
    results: List[Dict[str, Any]] = []
    try:
        proc = await asyncio.to_thread(
            subprocess.run,
            [str(bin_dir / "skill-verify"), str(skill_dir)],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
            timeout=120,
            shell=False,
            env=safe_env(),
        )
        results.append({
            "command": "skill-verify",
            "exit_code": proc.returncode,
            "output": (proc.stdout or "") + (proc.stderr or ""),
        })
    except subprocess.TimeoutExpired:
        results.append({"command": "skill-verify", "exit_code": -1, "output": "Timed out after 120s"})
    except Exception as exc:
        results.append({"command": "skill-verify", "exit_code": -1, "output": str(exc)})

    return {"status": "ok", "results": results}


@router.post("/api/config/mcp-servers/sync")
async def config_mcp_servers_sync():
    bin_dir = _REPO_ROOT / "core" / "bin"
    skill_verify_paths: List[str] = []
    for skills_dir in (_MCP_SKILLS_DIR, _SYSTEM_SKILLS_DIR):
        if skills_dir.is_dir():
            for child in sorted(skills_dir.iterdir()):
                if child.is_dir() and (child / "SKILL.md").exists():
                    skill_verify_paths.append(str(child))

    results: List[Dict[str, Any]] = []

    # 1) Sync MCP in-process (do not shell out to core/bin/sync-mcp).
    try:
        from mcp_servers.mcp_to_skills.sync import sync_mcp_tools

        summary = await asyncio.to_thread(sync_mcp_tools, repo_root=_REPO_ROOT)
        output_lines: list[str] = []
        output_lines.append(f"Synced {summary.get('total_tools', 0)} tools.")
        synced = summary.get("synced_servers") or []
        skipped = summary.get("skipped_servers") or []
        if synced:
            output_lines.append("Servers synced:")
            for line in synced:
                output_lines.append(f"  - {line}")
        if skipped:
            output_lines.append("Skipped:")
            for line in skipped:
                output_lines.append(f"  - {line}")
        results.append({"command": "sync-mcp (in-process)", "exit_code": 0, "output": "\n".join(output_lines) + "\n"})
    except Exception as exc:
        results.append({"command": "sync-mcp (in-process)", "exit_code": -1, "output": str(exc)})
        return JSONResponse(status_code=500, content={"error": str(exc), "results": results})

    # 2) Verify generated skills (still uses core/bin scripts).
    if not skill_verify_paths:
        results.append({"command": "skill-verify", "exit_code": 0, "output": "No skills to verify (skipped)"})
    else:
        try:
            proc = await asyncio.to_thread(
                subprocess.run,
                [str(bin_dir / "skill-verify"), *skill_verify_paths],
                capture_output=True,
                text=True,
                cwd=str(_REPO_ROOT),
                timeout=120,
                shell=False,
                env=safe_env(),
            )
            results.append({
                "command": "skill-verify",
                "exit_code": proc.returncode,
                "output": (proc.stdout or "") + (proc.stderr or ""),
            })
            if proc.returncode != 0:
                return JSONResponse(status_code=500, content={
                    "error": f"skill-verify failed with exit code {proc.returncode}",
                    "results": results,
                })
        except subprocess.TimeoutExpired:
            results.append({"command": "skill-verify", "exit_code": -1, "output": "Timed out after 120s"})
            return JSONResponse(status_code=500, content={"error": "skill-verify timed out", "results": results})
        except Exception as exc:
            results.append({"command": "skill-verify", "exit_code": -1, "output": str(exc)})
            return JSONResponse(status_code=500, content={"error": str(exc), "results": results})

    # 3) Install skills.
    try:
        proc = await asyncio.to_thread(
            subprocess.run,
            [str(bin_dir / "skill-install")],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
            timeout=120,
            shell=False,
            env=safe_env(),
        )
        results.append({
            "command": "skill-install",
            "exit_code": proc.returncode,
            "output": (proc.stdout or "") + (proc.stderr or ""),
        })
        if proc.returncode != 0:
            return JSONResponse(status_code=500, content={
                "error": f"skill-install failed with exit code {proc.returncode}",
                "results": results,
            })
    except subprocess.TimeoutExpired:
        results.append({"command": "skill-install", "exit_code": -1, "output": "Timed out after 120s"})
        return JSONResponse(status_code=500, content={"error": "skill-install timed out", "results": results})
    except Exception as exc:
        results.append({"command": "skill-install", "exit_code": -1, "output": str(exc)})
        return JSONResponse(status_code=500, content={"error": str(exc), "results": results})

    return {"status": "ok", "results": results}


@router.get("/api/config/schedules")
def config_schedules_list():
    from scheduler import load_schedules
    try:
        schedules = load_schedules()
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc), "schedules": []})
    return {"schedules": schedules}


@router.post("/api/config/schedules")
async def config_schedules_save(request: Request):
    from scheduler import load_schedules, save_schedules, reload_scheduler
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    schedule_id = (str(body.get("id") or "")).strip()
    name = (str(body.get("name") or "")).strip()
    skill = (str(body.get("skill") or "")).strip()
    cron = (str(body.get("cron") or "")).strip()
    provider = (str(body.get("provider") or "")).strip()
    enabled = body.get("enabled", True)

    if not name:
        return JSONResponse(status_code=400, content={"error": "name is required"})
    if not skill:
        return JSONResponse(status_code=400, content={"error": "skill is required"})
    if not cron:
        return JSONResponse(status_code=400, content={"error": "cron is required"})

    try:
        CronTrigger.from_crontab(cron)
    except (ValueError, KeyError) as exc:
        return JSONResponse(status_code=400, content={"error": f"Invalid cron expression: {exc}"})

    schedules = load_schedules()

    entry = {
        "id": schedule_id or secrets.token_hex(4),
        "name": name,
        "skill": skill,
        "cron": cron,
        "provider": provider,
        "enabled": bool(enabled),
    }

    if schedule_id:
        found = False
        for i, existing in enumerate(schedules):
            if existing.get("id") == schedule_id:
                schedules[i] = entry
                found = True
                break
        if not found:
            schedules.append(entry)
    else:
        schedules.append(entry)

    try:
        save_schedules(schedules)
        reload_scheduler()
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})

    return {"status": "ok", "schedule": entry}


@router.delete("/api/config/schedules/{schedule_id}")
def config_schedules_delete(schedule_id: str):
    from scheduler import load_schedules, save_schedules, reload_scheduler

    schedule_id = schedule_id.strip()
    if not schedule_id:
        return JSONResponse(status_code=400, content={"error": "Schedule ID is required"})

    schedules = load_schedules()
    original_len = len(schedules)
    schedules = [s for s in schedules if s.get("id") != schedule_id]

    if len(schedules) == original_len:
        return JSONResponse(status_code=404, content={"error": f"Schedule not found: {schedule_id}"})

    try:
        save_schedules(schedules)
        reload_scheduler()
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})

    return {"status": "ok"}

