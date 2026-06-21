from __future__ import annotations

from backend.shared.app.app_paths import (
    CHAPTER_SYNC_DIR,
    CHAPTER_SYNC_LOG_DIR,
    CONFIG_DIR,
    CONFIG_FILE,
    LOG_CATEGORIES,
    PROCESS_NOVEL_DIR,
    PROCESS_OUTPUT_DIR,
    PUBLISH_DIR,
    ROOT_DIR,
    WEB_CRAWLER_DIR,
    WEB_CRAWLER_OUTPUT_DIR,
    get_state_paths,
    latest_log_file,
    task_log_file,
)


def test_config_file_stays_in_project_config_dir() -> None:
    assert CONFIG_DIR == ROOT_DIR / "config"
    assert CONFIG_FILE == CONFIG_DIR / "config.json"


def test_log_categories_use_timestamped_log_files() -> None:
    for category in LOG_CATEGORIES:
        path = task_log_file(category)
        assert path.name.startswith("task_")
        assert path.name.endswith(".log")
        assert path.parent.name.endswith("_tasklogs")


def test_latest_log_file_uses_stable_fallback() -> None:
    for category in LOG_CATEGORIES:
        path = latest_log_file(category)
        assert path.name.endswith(".log")
        assert path.parent.name.endswith("_tasklogs")


def test_no_legacy_root_features_package() -> None:
    assert not (ROOT_DIR / "features").exists()


def test_no_legacy_app_package() -> None:
    assert not (ROOT_DIR / "app").exists()


def test_human_readable_architecture_roots_are_used() -> None:
    assert (ROOT_DIR / "backend").exists()
    assert (ROOT_DIR / "frontend").exists()
    assert (ROOT_DIR / "backend" / "shared").exists()
    assert (ROOT_DIR / "backend" / "services").exists()
    assert (ROOT_DIR / "backend" / "workflows").exists()
    assert (ROOT_DIR / "backend" / "adapters").exists()
    assert not (ROOT_DIR / "backend" / "core").exists()
    assert not (ROOT_DIR / "backend" / "features").exists()


def test_novel_text_rules_have_explicit_name() -> None:
    assert (ROOT_DIR / "backend" / "services" / "novel_text").exists()
    assert not (ROOT_DIR / "backend" / "features" / "common").exists()


def test_open_directory_aliases_stay_inside_feature_data_dirs() -> None:
    paths = get_state_paths()

    assert paths["novel_processor"] == str(PROCESS_NOVEL_DIR)
    assert paths["novel_crawler"] == str(WEB_CRAWLER_DIR)
    assert paths["fanqie_publisher"] == str(PUBLISH_DIR)
    assert paths["fanqie_syncer"] == str(CHAPTER_SYNC_DIR)
    assert paths["novel_process_outputs"] == str(PROCESS_OUTPUT_DIR)
    assert paths["novel_crawl_outputs"] == str(WEB_CRAWLER_OUTPUT_DIR)
    assert paths["fanqie_sync_tasklogs"] == str(CHAPTER_SYNC_LOG_DIR)
