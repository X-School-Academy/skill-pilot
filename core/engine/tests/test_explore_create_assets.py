import importlib.util
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "skills/system/explore-showcase/scripts/create-assets.py"
)


def _load_create_assets_module():
    spec = importlib.util.spec_from_file_location("explore_create_assets", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_update_showcase_assets_skips_existing_resource_urls(monkeypatch, tmp_path: Path):
    create_assets = _load_create_assets_module()
    showcase_dir = tmp_path / "showcase"
    showcase_dir.mkdir()
    repo_root = tmp_path
    calls: list[str] = []

    def fail_call(name: str):
        def inner(*args, **kwargs):
            raise AssertionError(f"{name} should not run when URL already exists")

        return inner

    monkeypatch.setattr(create_assets, "create_thumbnail", fail_call("create_thumbnail"))
    monkeypatch.setattr(
        create_assets,
        "create_showcase_video",
        fail_call("create_showcase_video"),
    )
    monkeypatch.setattr(create_assets, "run_agent_cli", fail_call("run_agent_cli"))
    monkeypatch.setattr(create_assets, "update_files_yaml", fail_call("update_files_yaml"))
    monkeypatch.setattr(create_assets, "create_zip", fail_call("create_zip"))
    monkeypatch.setattr(create_assets, "upload_file", fail_call("upload_file"))
    monkeypatch.setattr(
        create_assets,
        "update_term_videos",
        lambda *args, **kwargs: calls.append("terms"),
    )

    showcase = {
        "thumbnail": "https://cdn.example.test/image.png",
        "video": "https://cdn.example.test/video.mp4",
        "tutorial_prompt": "Teach it.",
        "tutorial": "https://cdn.example.test/tutorial.md",
        "links": [
            {
                "name": "Existing resource",
                "prompt": "Generate this only if missing.",
                "url": "https://cdn.example.test/resource.md",
            }
        ],
        "zip-files-url": "https://cdn.example.test/files.zip",
    }

    create_assets.update_showcase_assets(repo_root, showcase_dir, showcase, dry_run=False)

    assert calls == ["terms"]
    assert showcase["thumbnail"] == "https://cdn.example.test/image.png"
    assert showcase["video"] == "https://cdn.example.test/video.mp4"
    assert showcase["tutorial"] == "https://cdn.example.test/tutorial.md"
    assert showcase["links"][0]["url"] == "https://cdn.example.test/resource.md"
    assert showcase["zip-files-url"] == "https://cdn.example.test/files.zip"


def test_update_showcase_assets_creates_only_missing_resource_urls(monkeypatch, tmp_path: Path):
    create_assets = _load_create_assets_module()
    showcase_dir = tmp_path / "showcase"
    showcase_dir.mkdir()
    repo_root = tmp_path
    calls: list[str] = []
    generated_course = tmp_path / "course.md"
    generated_course.write_text("# Course\n", encoding="utf-8")
    zip_path = tmp_path / "showcase.zip"
    zip_path.write_text("zip", encoding="utf-8")

    monkeypatch.setattr(
        create_assets,
        "create_thumbnail",
        lambda *args, **kwargs: calls.append("thumbnail")
        or "https://cdn.example.test/new-image.png",
    )
    monkeypatch.setattr(
        create_assets,
        "create_showcase_video",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("video should be skipped")
        ),
    )
    monkeypatch.setattr(
        create_assets,
        "create_course_output_path",
        lambda _repo_root: generated_course,
    )
    monkeypatch.setattr(
        create_assets,
        "run_agent_cli",
        lambda *args, **kwargs: f"<output-file-path>{generated_course}</output-file-path>",
    )
    monkeypatch.setattr(
        create_assets,
        "upload_generated_learning",
        lambda *args, **kwargs: calls.append("learning")
        or "https://cdn.example.test/course.md",
    )
    monkeypatch.setattr(
        create_assets,
        "update_term_videos",
        lambda *args, **kwargs: calls.append("terms"),
    )
    monkeypatch.setattr(
        create_assets,
        "update_files_yaml",
        lambda *args, **kwargs: calls.append("files"),
    )
    monkeypatch.setattr(
        create_assets,
        "create_zip",
        lambda *args, **kwargs: calls.append("zip") or zip_path,
    )
    monkeypatch.setattr(
        create_assets,
        "upload_file",
        lambda *args, **kwargs: calls.append("zip-upload")
        or "https://cdn.example.test/files.zip",
    )

    showcase = {
        "thumbnail": None,
        "video": "https://cdn.example.test/existing-video.mp4",
        "tutorial_prompt": "Teach it.",
        "tutorial": None,
        "links": [
            {
                "name": "Generated resource",
                "prompt": "Generate this.",
                "url": None,
            }
        ],
        "zip-files-url": None,
    }

    create_assets.update_showcase_assets(repo_root, showcase_dir, showcase, dry_run=False)

    assert calls == ["thumbnail", "learning", "learning", "terms", "files", "zip", "zip-upload"]
    assert showcase["thumbnail"] == "https://cdn.example.test/new-image.png"
    assert showcase["video"] == "https://cdn.example.test/existing-video.mp4"
    assert showcase["tutorial"] == "https://cdn.example.test/course.md"
    assert showcase["links"][0]["url"] == "https://cdn.example.test/course.md"
    assert "prompt" not in showcase["links"][0]
    assert showcase["zip-files-url"] == "https://cdn.example.test/files.zip"
