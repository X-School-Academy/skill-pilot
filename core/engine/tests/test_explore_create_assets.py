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
    showcase_yaml = showcase_dir / "showcase.yaml"
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
    monkeypatch.setattr(create_assets, "dump_yaml", fail_call("dump_yaml"))
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

    create_assets.update_showcase_assets(
        repo_root,
        showcase_dir,
        showcase_yaml,
        showcase,
        dry_run=False,
    )

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
    showcase_yaml = showcase_dir / "showcase.yaml"
    repo_root = tmp_path
    calls: list[str] = []
    generated_course = tmp_path / "course.md"
    generated_course.write_text("# Course\n", encoding="utf-8")
    zip_path = tmp_path / "showcase.zip"
    zip_path.write_text("zip", encoding="utf-8")

    def record_dump(path: Path, data: dict, **kwargs):
        calls.append(f"save:{','.join(key for key, value in data.items() if value)}")

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
    monkeypatch.setattr(create_assets, "dump_yaml", record_dump)

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

    create_assets.update_showcase_assets(
        repo_root,
        showcase_dir,
        showcase_yaml,
        showcase,
        dry_run=False,
    )

    assert calls == [
        "thumbnail",
        "save:thumbnail,video,tutorial_prompt,links",
        "learning",
        "save:thumbnail,video,tutorial_prompt,tutorial,links",
        "learning",
        "save:thumbnail,video,tutorial_prompt,tutorial,links",
        "terms",
        "files",
        "zip",
        "zip-upload",
        "save:thumbnail,video,tutorial_prompt,tutorial,links,zip-files-url",
    ]
    assert showcase["thumbnail"] == "https://cdn.example.test/new-image.png"
    assert showcase["video"] == "https://cdn.example.test/existing-video.mp4"
    assert showcase["tutorial"] == "https://cdn.example.test/course.md"
    assert showcase["links"][0]["url"] == "https://cdn.example.test/course.md"
    assert "prompt" not in showcase["links"][0]
    assert showcase["zip-files-url"] == "https://cdn.example.test/files.zip"


def test_create_zip_writes_to_temp_showcases_zip(tmp_path: Path):
    create_assets = _load_create_assets_module()
    repo_root = tmp_path
    showcase_dir = repo_root / "workspace/showcases/sample-showcase"
    assets_dir = showcase_dir / "assets"
    assets_dir.mkdir(parents=True)
    (showcase_dir / "showcase.yaml").write_text("title: Sample\n", encoding="utf-8")
    (showcase_dir / ".DS_Store").write_text("finder metadata\n", encoding="utf-8")
    (assets_dir / "source.txt").write_text("source\n", encoding="utf-8")
    (assets_dir / ".DS_Store").write_text("finder metadata\n", encoding="utf-8")
    (assets_dir / "old.zip").write_text("old zip should not be repackaged\n", encoding="utf-8")

    zip_path = create_assets.create_zip(repo_root, showcase_dir, dry_run=False)

    assert zip_path == repo_root / ".skillpilot/temp/showcases-zip/sample-showcase.zip"
    assert not (assets_dir / "sample-showcase.zip").exists()

    import zipfile

    with zipfile.ZipFile(zip_path) as archive:
        assert sorted(archive.namelist()) == ["assets/source.txt", "showcase.yaml"]


def test_update_files_yaml_ignores_ds_store(tmp_path: Path):
    create_assets = _load_create_assets_module()
    showcase_dir = tmp_path / "showcase"
    assets_dir = showcase_dir / "assets"
    assets_dir.mkdir(parents=True)
    (showcase_dir / "showcase.yaml").write_text("title: Sample\n", encoding="utf-8")
    (showcase_dir / ".DS_Store").write_text("finder metadata\n", encoding="utf-8")
    (assets_dir / "source.txt").write_text("source\n", encoding="utf-8")
    (assets_dir / ".DS_Store").write_text("finder metadata\n", encoding="utf-8")

    create_assets.update_files_yaml(showcase_dir, dry_run=False)

    assert (showcase_dir / "files.yaml").read_text(encoding="utf-8") == (
        "showcase_id: showcase\n"
        "files:\n"
        "- path: assets/source.txt\n"
        "- path: showcase.yaml\n"
    )


def test_update_term_videos_saves_terms_json_after_each_created_resource(
    monkeypatch,
    tmp_path: Path,
):
    create_assets = _load_create_assets_module()
    repo_root = tmp_path
    terms_path = repo_root / "core/engine/data/terms.json"
    calls: list[str] = []

    def fake_create_video(*args, **kwargs):
        url = f"https://cdn.example.test/{len([c for c in calls if c == 'video'])}.mp4"
        calls.append("video")
        return tmp_path / "video.mp4", url

    def fake_save_terms(path: Path, terms: dict[str, str]):
        assert path == terms_path
        calls.append(f"save:{','.join(sorted(terms))}")

    monkeypatch.setattr(create_assets, "create_video", fake_create_video)
    monkeypatch.setattr(create_assets, "save_terms", fake_save_terms)

    create_assets.update_term_videos(
        repo_root,
        {"terms": ["Python", "YAML"]},
        dry_run=False,
    )

    assert calls == ["video", "save:python", "video", "save:python,yaml"]
