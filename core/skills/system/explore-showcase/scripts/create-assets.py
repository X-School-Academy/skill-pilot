#!/usr/bin/env python3
"""Create and upload generated assets for an Explore showcase."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import uuid
import zipfile
from pathlib import Path
from typing import Any


ROOT_MARKERS = ("core/bin", "core/engine", "core/skills")
OUTPUT_PATH_TAG = "output-file-path"
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}
MARKDOWN_EXTENSIONS = {".md", ".markdown"}


def is_repo_root(path: Path) -> bool:
    return all((path / marker).exists() for marker in ROOT_MARKERS)


def parents_inclusive(path: Path) -> list[Path]:
    path = path.resolve()
    if path.is_file():
        path = path.parent
    return [path, *path.parents]


def find_repo_root(showcase_arg: str) -> Path:
    candidates: list[Path] = []
    raw_showcase = Path(showcase_arg).expanduser()
    if raw_showcase.is_absolute():
        candidates.extend(parents_inclusive(raw_showcase))
    else:
        candidates.extend(parents_inclusive(Path.cwd() / raw_showcase))
        candidates.extend(parents_inclusive(Path.cwd()))
    candidates.extend(parents_inclusive(Path(__file__)))

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if is_repo_root(candidate):
            return candidate
    raise SystemExit(
        "Could not find the Skill Pilot repo root. Expected a parent directory "
        "containing core/bin, core/engine, and core/skills."
    )


def ensure_engine_venv(repo_root: Path) -> None:
    venv_python = repo_root / "core/engine/.venv/bin/python"
    if not venv_python.exists():
        return
    if Path(sys.executable).resolve() == venv_python.resolve():
        return
    if os.environ.get("EXPLORE_SHOWCASE_CREATE_ASSETS_VENV") == "1":
        return
    env = os.environ.copy()
    env["EXPLORE_SHOWCASE_CREATE_ASSETS_VENV"] = "1"
    os.execve(str(venv_python), [str(venv_python), *sys.argv], env)


def resolve_showcase_dir(repo_root: Path, showcase_arg: str) -> Path:
    raw = Path(showcase_arg).expanduser()
    candidates = [raw] if raw.is_absolute() else [Path.cwd() / raw, repo_root / raw]
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.is_dir():
            return resolved
    raise SystemExit(f"Showcase directory does not exist: {showcase_arg}")


def load_yaml(path: Path) -> dict[str, Any]:
    import yaml

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise SystemExit(f"Expected YAML mapping in {path}")
    return data


class LiteralString(str):
    pass


def dump_yaml(path: Path, data: dict[str, Any]) -> None:
    import yaml

    def literal_representer(dumper: yaml.Dumper, value: LiteralString) -> yaml.ScalarNode:
        return dumper.represent_scalar("tag:yaml.org,2002:str", value, style="|")

    def prepare(value: Any) -> Any:
        if isinstance(value, str) and "\n" in value:
            return LiteralString(value)
        if isinstance(value, dict):
            return {key: prepare(child) for key, child in value.items()}
        if isinstance(value, list):
            return [prepare(child) for child in value]
        return value

    yaml.add_representer(LiteralString, literal_representer, Dumper=yaml.SafeDumper)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            prepare(data),
            handle,
            sort_keys=False,
            allow_unicode=False,
            width=100,
        )


def run_command(args: list[str], repo_root: Path) -> str:
    printable = " ".join(args)
    print(f"Running: {printable}")
    completed = subprocess.run(
        args,
        cwd=repo_root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        raise SystemExit(
            f"Command failed ({completed.returncode}): {printable}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return completed.stdout.strip()


def first_output_line(output: str) -> str:
    for line in reversed(output.splitlines()):
        line = line.strip()
        if line:
            return line
    raise SystemExit("Command completed without printing an output path or URL.")


def upload_file(repo_root: Path, file_path: Path, folder: str, dry_run: bool) -> str:
    if dry_run:
        print(f"[dry-run] skip S3 upload for {file_path}")
        print(f"[dry-run] local {folder} file: {file_path}")
        return str(file_path)
    output = run_command(
        [str(repo_root / "core/bin/aws-s3"), "upload", str(file_path), "--folder", folder],
        repo_root,
    )
    return first_output_line(output)


def upload_generated_learning(repo_root: Path, file_path: Path, dry_run: bool) -> str:
    suffix = file_path.suffix.lower()
    if suffix in MARKDOWN_EXTENSIONS:
        return upload_file(repo_root, file_path, "course", dry_run)
    if suffix in VIDEO_EXTENSIONS:
        return upload_file(repo_root, file_path, "video", dry_run)
    raise SystemExit(
        "Generated learning output must be a markdown course or video file. "
        f"Got: {file_path}"
    )


def goals_text(showcase: dict[str, Any]) -> str:
    goals = showcase.get("goals")
    if isinstance(goals, list):
        return "\n".join(f"- {item}" for item in goals)
    return str(goals or "").strip()


def base_context(showcase: dict[str, Any]) -> str:
    return "\n".join(
        part
        for part in [
            f"Title: {showcase.get('title', '')}".strip(),
            f"Description: {showcase.get('description', '')}".strip(),
            f"Goals:\n{goals_text(showcase)}" if goals_text(showcase) else "",
        ]
        if part
    )


def generated_learning_prompt(context: str) -> str:
    return (
        "Use agent skill multiple-scene-video or course-creator to create a video or online course "
        f"for {context}, then output the file absolute path in format"
        f"<{OUTPUT_PATH_TAG}>file path<{OUTPUT_PATH_TAG}>"
    )


def parse_output_file_path(output: str) -> Path:
    marker = re.escape(OUTPUT_PATH_TAG)
    pattern = rf"<{marker}>\s*(.*?)\s*<{marker}>"
    match = re.search(pattern, output, flags=re.DOTALL)
    if not match:
        raise SystemExit(
            f"Could not find <{OUTPUT_PATH_TAG}>...<{OUTPUT_PATH_TAG}> in agent-cli output:\n"
            f"{output}"
        )
    raw_path = match.group(1).strip()
    if not raw_path:
        raise SystemExit(f"Empty path inside <{OUTPUT_PATH_TAG}> marker.")
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        raise SystemExit(f"Generated learning output path must be absolute: {raw_path}")
    if not path.exists() or not path.is_file():
        raise SystemExit(f"Generated learning output file does not exist: {path}")
    return path


def run_agent_cli(repo_root: Path, prompt: str) -> str:
    return run_command([str(repo_root / "core/bin/agent-cli"), prompt], repo_root)


def create_thumbnail(repo_root: Path, showcase: dict[str, Any], dry_run: bool) -> str:
    prompt = (
        "Create a polished landscape thumbnail for a Skill Pilot Explore showcase.\n"
        "Use clear product-style composition, readable visual hierarchy, and no tiny text.\n\n"
        f"{base_context(showcase)}"
    )
    output = run_command(
        [str(repo_root / "core/bin/create-image"), "--ratio", "landscape", "--prompt", prompt],
        repo_root,
    )
    source = Path(first_output_line(output)).expanduser()
    if not source.exists():
        raise SystemExit(f"Generated thumbnail file does not exist: {source}")
    print(f"Thumbnail file: {source}")
    return upload_file(repo_root, source, "image", dry_run)


def create_video(
    repo_root: Path,
    requirement: str,
    duration_seconds: int,
    dry_run: bool,
) -> tuple[Path, str]:
    output_dir = repo_root / ".skillpilot" / "temp" / f"showcases-{uuid.uuid4()}"
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "requirement": requirement,
        "target_duration": duration_seconds,
        "resolution": "1920x1080",
        "output_path": str(output_dir),
        "voice_name": None,
        "theme": None,
    }
    output = run_command(
        [
            str(repo_root / "core/bin/api-invoke"),
            "create_multiple_scene_video",
            json.dumps(payload, ensure_ascii=True),
        ],
        repo_root,
    )
    try:
        response = json.loads(first_output_line(output))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Could not parse create_multiple_scene_video response: {output}") from exc
    video_path = response.get("video_file_path")
    if not video_path:
        raise SystemExit(f"Missing video_file_path in response: {output}")
    source = Path(str(video_path)).expanduser()
    if not source.exists():
        raise SystemExit(f"Generated video file does not exist: {source}")
    print(f"Video file: {source}")
    return source, upload_file(repo_root, source, "video", dry_run)


def create_showcase_video(
    repo_root: Path,
    showcase_dir: Path,
    showcase: dict[str, Any],
    dry_run: bool,
) -> str:
    extra = str(showcase.get("video_prompt") or "").strip()
    requirement = (
        "Create a 5 minute 1080p landscape video for this Skill Pilot Explore showcase. "
        "The video should either teach the user what they will learn or demonstrate the final outcome. "
        "Use the extra video direction only as context; build the final script and scenes yourself.\n\n"
        f"{base_context(showcase)}"
    )
    if extra:
        requirement += f"\n\nExtra video direction:\n{extra}"
    _, url = create_video(repo_root, requirement, 300, dry_run)
    return url


def update_generated_learning(
    repo_root: Path,
    showcase_dir: Path,
    showcase: dict[str, Any],
    dry_run: bool,
) -> None:
    tutorial_prompt = str(showcase.get("tutorial_prompt") or "").strip()
    if tutorial_prompt and not showcase.get("tutorial"):
        context = (
            "this Skill Pilot Explore showcase tutorial. Use the showcase title, description, "
            "goals, thumbnail direction, and video direction as context; create a course or video "
            "that teaches the user how to complete the showcase end-to-end. If creating an online "
            "course and the course type is not stated, default to guided_challenge.\n\n"
            f"{base_context(showcase)}\n\nTutorial direction:\n{tutorial_prompt}"
        )
        output = run_agent_cli(repo_root, generated_learning_prompt(context))
        generated_path = parse_output_file_path(output)
        print(f"Tutorial file: {generated_path}")
        showcase["tutorial"] = upload_generated_learning(repo_root, generated_path, dry_run)

    links = showcase.get("links") or []
    if not isinstance(links, list):
        raise SystemExit("Expected showcase.yaml field 'links' to be a list when present.")

    for link in links:
        if not isinstance(link, dict):
            continue
        link_prompt = str(link.get("prompt") or "").strip()
        if not link_prompt or link.get("url"):
            continue
        link_name = str(link.get("name") or "generated learning resource").strip()
        context = (
            f"the reusable learning topic '{link_name}'. Use the surrounding showcase context "
            "only to choose relevant examples. Create either a standalone tutorial video or an "
            "online course. If creating an online course and the course type is not stated, "
            "default to guided_challenge.\n\n"
            f"Showcase context:\n{base_context(showcase)}\n\nLearning prompt:\n{link_prompt}"
        )
        output = run_agent_cli(repo_root, generated_learning_prompt(context))
        generated_path = parse_output_file_path(output)
        print(f"Link learning file: {generated_path}")
        link["url"] = upload_generated_learning(repo_root, generated_path, dry_run)
        link.pop("prompt", None)


def term_slug(term: str) -> str:
    slug = term.strip().lower()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"[^a-z0-9._~-]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        raise SystemExit(f"Could not create URL-safe term slug for: {term!r}")
    return slug


def load_terms(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise SystemExit(f"Expected object in {path}")
    return {str(key): str(value) for key, value in data.items()}


def save_terms(path: Path, terms: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(dict(sorted(terms.items())), handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def update_term_videos(
    repo_root: Path,
    showcase: dict[str, Any],
    dry_run: bool,
) -> None:
    terms = showcase.get("terms") or []
    if not isinstance(terms, list):
        raise SystemExit("Expected showcase.yaml field 'terms' to be a list when present.")

    terms_path = repo_root / "core/engine/data/terms.json"
    term_urls = load_terms(terms_path)
    changed = False
    for raw_term in terms:
        term = str(raw_term).strip()
        if not term:
            continue
        slug = term_slug(term)
        if term_urls.get(slug):
            print(f"Term already has video, skipping: {slug}")
            continue
        requirement = (
            "Create a 3 minute 1080p landscape educational video about one technology term. "
            "The video must stand alone outside the showcase. Use the showcase context only to "
            "choose relevant examples, then explain the term clearly for a beginner.\n\n"
            f"Term: {term}\n\n"
            f"Showcase context:\n{base_context(showcase)}"
        )
        _, url = create_video(
            repo_root,
            requirement,
            180,
            dry_run,
        )
        term_urls[slug] = url
        changed = True

    if changed or (terms and not terms_path.exists()):
        if dry_run:
            print(f"[dry-run] skip terms.json update: {terms_path}")
        else:
            save_terms(terms_path, term_urls)


def create_zip(showcase_dir: Path, dry_run: bool) -> Path:
    zip_path = showcase_dir / "assets" / f"{showcase_dir.name}.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(showcase_dir.rglob("*")):
            if path == zip_path or path.is_dir():
                continue
            if path.suffix == ".zip" and path.parent == zip_path.parent:
                continue
            archive.write(path, path.relative_to(showcase_dir))
    print(f"Zip file: {zip_path}")
    return zip_path


def update_files_yaml(showcase_dir: Path, dry_run: bool) -> None:
    files_yaml = showcase_dir / "files.yaml"
    zip_dir = showcase_dir / "assets"
    paths: list[str] = []
    for path in sorted(showcase_dir.rglob("*")):
        if path.is_dir() or path == files_yaml:
            continue
        if path.suffix == ".zip" and path.parent == zip_dir:
            continue
        paths.append(path.relative_to(showcase_dir).as_posix())

    data = {
        "showcase_id": showcase_dir.name,
        "files": [{"path": path} for path in paths],
    }
    if dry_run:
        print(f"[dry-run] skip files.yaml update: {files_yaml}")
        return
    dump_yaml(files_yaml, data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create and upload assets for an Explore showcase.")
    parser.add_argument("showcase_dir", help="Path to workspace/showcases/<showcase-id>.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate local image/video/zip assets, but skip S3 uploads and YAML/JSON updates.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = find_repo_root(args.showcase_dir)
    ensure_engine_venv(repo_root)

    showcase_dir = resolve_showcase_dir(repo_root, args.showcase_dir)
    showcase_yaml = showcase_dir / "showcase.yaml"
    if not showcase_yaml.exists():
        raise SystemExit(f"Missing required file: {showcase_yaml}")

    showcase = load_yaml(showcase_yaml)
    showcase["thumbnail"] = create_thumbnail(repo_root, showcase, args.dry_run)
    showcase["video"] = create_showcase_video(repo_root, showcase_dir, showcase, args.dry_run)
    update_generated_learning(repo_root, showcase_dir, showcase, args.dry_run)
    update_term_videos(repo_root, showcase, args.dry_run)
    update_files_yaml(showcase_dir, args.dry_run)
    zip_path = create_zip(showcase_dir, args.dry_run)
    showcase["zip-files-url"] = upload_file(repo_root, zip_path, "zip", args.dry_run)

    if args.dry_run:
        print(f"[dry-run] skip showcase.yaml update: {showcase_yaml}")
    else:
        dump_yaml(showcase_yaml, showcase)
    print(f"Updated assets for showcase: {showcase_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
