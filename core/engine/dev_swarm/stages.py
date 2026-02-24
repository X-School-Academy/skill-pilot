from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .project import get_project_root


@dataclass(frozen=True)
class StageDefinition:
    stage_id: str
    name: str
    directory: str


STAGES: List[StageDefinition] = [
    StageDefinition(stage_id="00", name="Init Ideas", directory="00-init-ideas"),
    StageDefinition(stage_id="01", name="Market Research", directory="01-market-research"),
    StageDefinition(stage_id="02", name="Personas", directory="02-personas"),
    StageDefinition(stage_id="03", name="MVP", directory="03-mvp"),
    StageDefinition(stage_id="04", name="Tech Research", directory="04-tech-research"),
    StageDefinition(stage_id="05", name="PRD", directory="05-prd"),
    StageDefinition(stage_id="06", name="UX", directory="06-ux"),
    StageDefinition(stage_id="07", name="Architecture", directory="07-architecture"),
    StageDefinition(stage_id="08", name="Tech Specs", directory="08-tech-specs"),
    StageDefinition(stage_id="09", name="DevOps", directory="09-devops"),
    StageDefinition(stage_id="10", name="Sprints", directory="10-sprints"),
    StageDefinition(stage_id="11", name="Deployment", directory="11-deployment"),
    StageDefinition(stage_id="99", name="Archive", directory="99-archive"),
]

NON_SKIPPABLE = {"00", "05", "08", "10"}
ALLOWED_EXTENSIONS = {".md", ".html"}


def find_stage(stage_id: str) -> Optional[StageDefinition]:
    for stage in STAGES:
        if stage.stage_id == stage_id:
            return stage
    return None


def list_documents_recursive(dir_path: Path, root_path: Path) -> List[str]:
    results: List[str] = []
    if not dir_path.exists():
        return results

    for entry in sorted(dir_path.iterdir(), key=lambda p: p.name):
        if entry.is_dir():
            results.extend(list_documents_recursive(entry, root_path))
        elif entry.is_file() and entry.suffix.lower() in ALLOWED_EXTENSIONS:
            results.append(entry.relative_to(root_path).as_posix())
    return sorted(results)


def derive_status(has_skip: bool, has_readme: bool, has_other_files: bool) -> str:
    if has_skip:
        return "skipped"
    if has_readme and has_other_files:
        return "completed"
    if has_readme:
        return "in-progress"
    return "not-started"


def _build_stage_payload(stage: StageDefinition, files: List[str], has_skip: bool) -> Dict[str, object]:
    readme_path = f"{stage.directory}/README.md"
    skip_path = f"{stage.directory}/SKIP.md"
    has_readme = readme_path in files
    has_other_files = any(item not in {readme_path, skip_path} for item in files)
    return {
        "stageId": stage.stage_id,
        "name": stage.name,
        "status": derive_status(has_skip, has_readme, has_other_files),
        "isSkippable": stage.stage_id not in NON_SKIPPABLE,
        "hasSkipFile": has_skip,
        "files": files,
    }


def list_stages() -> List[Dict[str, object]]:
    root = get_project_root()
    payload: List[Dict[str, object]] = []
    for stage in STAGES:
        stage_dir = root / stage.directory
        has_skip = (stage_dir / "SKIP.md").exists()
        files = list_documents_recursive(stage_dir, root)
        payload.append(_build_stage_payload(stage, files, has_skip))
    return payload


def list_stage_files(stage_id: str) -> List[str]:
    stage = find_stage(stage_id)
    if not stage:
        raise ValueError("Stage not found")
    root = get_project_root()
    return list_documents_recursive(root / stage.directory, root)


def toggle_skip(stage_id: str, skip: bool) -> Dict[str, object]:
    stage = find_stage(stage_id)
    if not stage:
        raise ValueError("Stage not found")
    if stage_id in NON_SKIPPABLE:
        raise ValueError("Stage is not skippable")

    root = get_project_root()
    stage_dir = root / stage.directory
    if not stage_dir.exists():
        raise FileNotFoundError("Stage directory not found")

    skip_file = stage_dir / "SKIP.md"
    current = skip_file.exists()
    if skip and not current:
        skip_file.write_text("# Stage Skipped\n\nSkipped via WebUI.\n", encoding="utf-8")
    elif not skip and current:
        skip_file.unlink()

    has_skip = skip_file.exists()
    files = list_documents_recursive(stage_dir, root)
    return _build_stage_payload(stage, files, has_skip)
