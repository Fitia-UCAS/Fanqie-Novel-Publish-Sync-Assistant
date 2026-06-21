from __future__ import annotations


import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from backend.shared.app.app_logging import get_logger
from backend.shared.app.app_paths import get_state_paths

LOGGER = get_logger(__name__)


def open_path(path_key: str) -> bool:
    try:
        target = _resolve_path(path_key)
        if target is None:
            return False
        if target.exists() and target.is_file():
            target = target.parent
        elif target.suffix and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target = target.parent
        else:
            target.mkdir(parents=True, exist_ok=True)
        _open_system(target)
        return True
    except Exception:
        LOGGER.exception("Open path failed: %s", path_key)
        return False


def open_file(path_key: str, *, create: bool = False) -> bool:
    try:
        target = _resolve_path(path_key)
        if target is None:
            return False
        if create and target.suffix and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch()
        elif target.suffix and not target.exists():
            return False
        elif not target.suffix:
            target.mkdir(parents=True, exist_ok=True)
        _open_system(target)
        return True
    except Exception:
        LOGGER.exception("Open file failed: %s", path_key)
        return False


def _resolve_path(path_key: str) -> Path | None:
    paths = get_state_paths()
    raw = str(path_key or "").strip()
    if not raw:
        return None
    return Path(paths.get(raw, raw)).expanduser()


def _open_system(target: Path) -> None:
    if sys.platform == "win32":
        os.startfile(str(target))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(target)])
    else:
        subprocess.Popen(["xdg-open", str(target)])


def open_native_dialog(window: Any, *, save: bool, folder: bool, save_filename: str = "output.txt") -> str:
    if window is None:
        return ""
    try:
        import webview

        if folder:
            result = window.create_file_dialog(_file_dialog_type(webview, "FOLDER"))
        elif save:
            result = window.create_file_dialog(
                _file_dialog_type(webview, "SAVE"),
                save_filename=save_filename or "output.txt",
                file_types=("Text files (*.txt)", "All files (*.*)"),
            )
        else:
            result = window.create_file_dialog(
                _file_dialog_type(webview, "OPEN"),
                allow_multiple=False,
                file_types=("Text files (*.txt)", "All files (*.*)"),
            )
    except Exception:
        LOGGER.exception("Native file dialog failed")
        return ""
    normalized = _normalize_dialog_result(result)
    if save and normalized:
        normalized = _ensure_txt_file_path(normalized)
        try:
            target = Path(normalized).expanduser()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch(exist_ok=True)
        except Exception:
            LOGGER.exception("Create selected TXT failed: %s", normalized)
    return normalized




def _ensure_txt_file_path(path: str) -> str:
    target = Path(path).expanduser()
    if target.suffix.lower() != ".txt":
        target = target.with_suffix(".txt")
    return str(target)

def _file_dialog_type(webview: Any, name: str) -> Any:
    file_dialog = getattr(webview, "FileDialog", None)
    if file_dialog is not None and hasattr(file_dialog, name):
        return getattr(file_dialog, name)
    return getattr(webview, f"{name}_DIALOG")


def _normalize_dialog_result(result: Any) -> str:
    if isinstance(result, (list, tuple)):
        return str(result[0]) if result else ""
    return str(result or "")


