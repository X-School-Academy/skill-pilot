import zipfile
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

import routes


def _make_zip(path: Path, files: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)


def test_prepare_showcase_template_files_skips_existing_directory(monkeypatch, tmp_path: Path):
    target = tmp_path / "workspace" / "tasks" / "sample"
    target.mkdir(parents=True)
    (target / "existing.md").write_text("keep\n", encoding="utf-8")

    def fail_download(*args, **kwargs):
        raise AssertionError("should not download when directory exists")

    monkeypatch.setattr(routes, "_download_template_zip", fail_download)

    result = routes._prepare_showcase_template_files(
        {
            "id": "sample",
            "directory": "workspace/tasks/sample",
            "zip-files-url": "https://cdn.example.test/sample.zip",
        },
        tmp_path,
    )

    assert result["status"] == "skipped"
    assert result["reason"] == "directory_exists"
    assert (target / "existing.md").read_text(encoding="utf-8") == "keep\n"


def test_prepare_showcase_template_files_extracts_zip_to_directory(monkeypatch, tmp_path: Path):
    source_zip = tmp_path / "source.zip"
    _make_zip(
        source_zip,
        {
            "showcase.yaml": "id: sample\n",
            "files.yaml": "showcase_id: sample\n",
            "requirements.md": "# Requirements\n",
            "assets/note.txt": "asset\n",
        },
    )

    def fake_download(url: str, destination: Path, **kwargs):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source_zip.read_bytes())

    monkeypatch.setattr(routes, "_download_template_zip", fake_download)

    result = routes._prepare_showcase_template_files(
        {
            "id": "sample",
            "directory": "workspace/tasks/sample",
            "zip-files-url": "https://cdn.example.test/sample.zip",
        },
        tmp_path,
    )

    target = tmp_path / "workspace" / "tasks" / "sample"
    assert result["status"] == "extracted_zip"
    assert not (target / "showcase.yaml").exists()
    assert not (target / "files.yaml").exists()
    assert (target / "requirements.md").read_text(encoding="utf-8") == "# Requirements\n"
    assert (target / "assets" / "note.txt").read_text(encoding="utf-8") == "asset\n"
    assert list((tmp_path / ".skillpilot" / "temp" / "explore-templates").glob("*")) == []


def test_prepare_showcase_template_files_rejects_unsafe_directory(tmp_path: Path):
    with pytest.raises(ValueError, match="Invalid showcase directory"):
        routes._prepare_showcase_template_files(
            {
                "id": "sample",
                "directory": "../outside",
                "zip-files-url": "https://cdn.example.test/sample.zip",
            },
            tmp_path,
        )


def test_safe_extract_zip_rejects_unsafe_entries(tmp_path: Path):
    source_zip = tmp_path / "bad.zip"
    _make_zip(source_zip, {"../outside.txt": "bad"})

    with pytest.raises(ValueError, match="Unsafe path"):
        routes._safe_extract_zip(source_zip, tmp_path / "extract")


def test_normalize_showcase_sample_exposes_zip_files_url():
    sample = routes._normalize_showcase_sample(
        {
            "id": "sample",
            "title": "Sample",
            "description": "Sample description",
            "prompt": "Run this.",
            "directory": "workspace/tasks/sample",
            "zip-files-url": "https://cdn.example.test/sample.zip",
            "skills": [],
            "tools": [],
            "files": [],
        },
        "Category",
    )

    assert sample["zip-files-url"] == "https://cdn.example.test/sample.zip"


def test_normalize_showcase_sample_hides_default_system_skill():
    sample = routes._normalize_showcase_sample(
        {
            "id": "sample",
            "title": "Sample",
            "description": "Sample description",
            "prompt": "Run this.",
            "skills": ["do-and-learn", "core/skills/system/terminal"],
            "tools": [],
            "files": [],
        },
        "Category",
    )

    assert sample["skills"] == ["core/skills/system/terminal"]
    assert [item["label"] for item in sample["skill_items"]] == ["core/skills/system/terminal"]


def test_normalize_showcase_sample_can_disable_system_skill_hiding():
    sample = routes._normalize_showcase_sample(
        {
            "id": "sample",
            "title": "Sample",
            "description": "Sample description",
            "prompt": "Run this.",
            "system_skills": [],
            "skills": ["do-and-learn"],
            "tools": [],
            "files": [],
        },
        "Category",
    )

    assert sample["skills"] == ["do-and-learn"]


def test_build_prompt_target_url_includes_system_skills():
    url = routes._build_prompt_target_url("", "Run this.", system_skills=["do-and-learn", "terminal"])

    assert "systemSkills=" in url
    assert "do-and-learn" in url
