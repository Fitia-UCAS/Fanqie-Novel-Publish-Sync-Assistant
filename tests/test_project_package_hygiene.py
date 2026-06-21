from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


def test_no_empty_frontend_placeholder_components() -> None:
    components_dir = ROOT_DIR / "frontend" / "assets" / "components"
    assert not components_dir.exists()


def test_shared_file_helpers_use_text_file_context() -> None:
    assert (ROOT_DIR / "backend" / "shared" / "text_file" / "text_file_storage.py").exists()
    assert (ROOT_DIR / "backend" / "shared" / "text_file" / "text_file_discovery.py").exists()
    assert not (ROOT_DIR / "backend" / "shared" / "file_io.py").exists()
    assert not (ROOT_DIR / "backend" / "services" / "novel_text" / "io.py").exists()


def test_package_project_excludes_runtime_caches() -> None:
    from tools.package_project import should_include

    cache_paths = [
        ROOT_DIR / ".pytest_cache" / "README.md",
        ROOT_DIR / "backend" / "__pycache__" / "config.cpython-313.pyc",
        ROOT_DIR / ".mypy_cache" / "state.json",
        ROOT_DIR / ".ruff_cache" / "content",
        ROOT_DIR / "PATCH_NOTES_AUTO_PUBLISH_FIX.md",
        ROOT_DIR / "data" / "fanqie_web" / "state.json",
        ROOT_DIR / "data" / "fanqie_web" / "chapter_sync_state.json",
        ROOT_DIR / "data" / "fanqie_web" / "browser_edge_profile" / "Default" / "Cookies",
    ]
    assert [should_include(path) for path in cache_paths] == [False, False, False, False, False, False, False, False]
