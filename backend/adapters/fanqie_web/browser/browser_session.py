from __future__ import annotations

import hashlib
import os
import re
import time
from itertools import count
from typing import Any

try:
    from playwright.sync_api import Page, sync_playwright
except Exception as exc:
    Page = Any
    sync_playwright = None
    _PLAYWRIGHT_IMPORT_ERROR: Exception | None = exc
else:
    _PLAYWRIGHT_IMPORT_ERROR = None

from backend.shared.app.app_paths import BROWSER_DATA_DIR, CHAPTER_SYNC_DEBUG_DIR, FANQIE_AUTH_STATE_FILE, PUBLISH_DEBUG_DIR
from backend.shared.app.app_runtime_defaults import BROWSER_CHANNEL, VIEWPORT

_CONTEXT_DEBUG_CATEGORY: dict[int, str] = {}
_CONTEXT_DEBUG_ENABLED: dict[int, bool] = {}
_CONTEXT_FAILURE_DEBUG_ENABLED: dict[int, bool] = {}
_CONTEXT_DEBUG_FINGERPRINTS: dict[int, set[str]] = {}
_DEBUG_COUNTER = count(1)


def launch_system_browser(playwright: Any, launch_kwargs: dict[str, Any]):
    configured_channel = (BROWSER_CHANNEL or "").strip()
    channels: list[str] = []
    for channel in (configured_channel, "msedge", "chrome"):
        if channel and channel not in channels:
            channels.append(channel)

    errors: list[str] = []
    for channel in channels:
        kwargs = dict(launch_kwargs)
        kwargs["channel"] = channel
        try:
            return playwright.chromium.launch(**kwargs)
        except Exception as exc:
            errors.append(f"{channel}: {exc}")

    detail = "\n".join(errors)
    raise RuntimeError(
        "浏览器启动失败。当前版本不会下载或使用 Playwright 内置 Chromium。"
        "请确认电脑已安装 Microsoft Edge 或 Google Chrome。"
        + (f"\n{detail}" if detail else "")
    )


def maximize_page_window(page: Page) -> None:
    try:
        session = page.context.new_cdp_session(page)
        window_info = session.send("Browser.getWindowForTarget")
        window_id = window_info.get("windowId")
        if window_id is not None:
            session.send("Browser.setWindowBounds", {"windowId": window_id, "bounds": {"windowState": "maximized"}})
    except Exception:

        pass


def make_context(headless: bool = False, *, debug_category: str = "chapter_sync", debug_enabled: bool | None = None, failure_debug_enabled: bool | None = None):
    if sync_playwright is None:
        raise RuntimeError("缺少依赖：playwright。请先执行：pip install -r requirements.txt") from _PLAYWRIGHT_IMPORT_ERROR

    p = sync_playwright().start()
    BROWSER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    launch_kwargs: dict[str, Any] = {
        "headless": headless,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--start-maximized",
        ],
    }

    context_kwargs: dict[str, Any] = {}
    if headless:
        context_kwargs["viewport"] = VIEWPORT
    else:
        context_kwargs["no_viewport"] = True
    if FANQIE_AUTH_STATE_FILE.exists():
        context_kwargs["storage_state"] = str(FANQIE_AUTH_STATE_FILE)

    try:
        browser = launch_system_browser(p, launch_kwargs)
        context = browser.new_context(**context_kwargs)
    except Exception as e:
        p.stop()
        raise RuntimeError(
            "浏览器启动失败。当前版本默认使用系统 Microsoft Edge 或 Google Chrome，不再下载 Playwright Chromium；如果浏览器被占用，请先关闭自动化打开的窗口后重试。"
        ) from e

    _CONTEXT_DEBUG_CATEGORY[id(context)] = debug_category or "chapter_sync"
    if debug_enabled is not None:
        _CONTEXT_DEBUG_ENABLED[id(context)] = bool(debug_enabled)
    if failure_debug_enabled is not None:
        _CONTEXT_FAILURE_DEBUG_ENABLED[id(context)] = bool(failure_debug_enabled)
    page = context.pages[0] if context.pages else context.new_page()
    if not headless:
        maximize_page_window(page)
        try:
            page.wait_for_timeout(300)
        except Exception:
            pass
    return p, context, page


def close_context(p, context, *, save_state: bool = True) -> None:
    try:
        if save_state:
            FANQIE_AUTH_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            try:
                context.storage_state(path=str(FANQIE_AUTH_STATE_FILE), indexed_db=True)
            except TypeError:
                context.storage_state(path=str(FANQIE_AUTH_STATE_FILE))
    except Exception:
        pass
    context_id = id(context)
    _CONTEXT_DEBUG_CATEGORY.pop(context_id, None)
    _CONTEXT_DEBUG_ENABLED.pop(context_id, None)
    _CONTEXT_FAILURE_DEBUG_ENABLED.pop(context_id, None)
    _CONTEXT_DEBUG_FINGERPRINTS.pop(context_id, None)
    try:
        browser = context.browser
    except Exception:
        browser = None
    try:
        context.close()
    except Exception:
        pass
    try:
        if browser is not None:
            browser.close()
    except Exception:
        pass
    try:
        p.stop()
    except Exception:
        pass


def _current_debug_category(page: Page, category: str | None) -> str:
    if category:
        return category
    try:
        return _CONTEXT_DEBUG_CATEGORY.get(id(page.context), "chapter_sync")
    except Exception:
        return "chapter_sync"


def _debug_enabled(category: str, page: Page | None = None) -> bool:
    if page is not None:
        try:
            flag = _CONTEXT_DEBUG_ENABLED.get(id(page.context))
            if flag is not None:
                return bool(flag)
        except Exception:
            pass
    env_key = "AUTO_PUBLISH_DEBUG" if category == "auto_publish" else "CHAPTER_SYNC_DEBUG"
    env_value = os.getenv(env_key)
    if env_value is not None:
        return env_value == "1"
    if category == "auto_publish":
        try:
            from backend.shared.app.app_config import load_config

            section = load_config().get("auto_publish", {})
            if isinstance(section, dict):
                return bool(section.get("debugScreenshots", True))
        except Exception:
            return True

    return False


def _debug_dir(category: str):
    return PUBLISH_DEBUG_DIR if category == "auto_publish" else CHAPTER_SYNC_DEBUG_DIR


def _safe_debug_name(name: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]+", "_", str(name or "page"))
    return cleaned.strip("_")[:80] or "page"


def _debug_dedupe_enabled(category: str) -> bool:
    if category == "auto_publish":
        try:
            from backend.shared.app.app_config import load_config

            section = load_config().get("auto_publish", {})
            if isinstance(section, dict):
                return bool(section.get("dedupeDebugScreenshots", True))
        except Exception:
            return True
    return True


def _page_state_fingerprint(page: Page, screenshot_bytes: bytes) -> str:


    try:
        state = page.evaluate(
            """() => {
                const body = document.body ? document.body.innerText : '';
                const size = `${window.innerWidth}x${window.innerHeight}:${document.documentElement.scrollWidth}x${document.documentElement.scrollHeight}`;
                return `${location.href}\n${document.title}\n${size}\n${body}`;
            }"""
        )
        if isinstance(state, str) and state.strip():
            normalized = "\n".join(line.strip() for line in state.splitlines() if line.strip())
            return hashlib.sha256(normalized.encode("utf-8", errors="ignore")).hexdigest()
    except Exception:
        pass
    return hashlib.sha256(screenshot_bytes).hexdigest()


def save_debug(page: Page, name: str, *, category: str | None = None, force: bool = False) -> None:
    current_category = _current_debug_category(page, category)
    if not _debug_enabled(current_category, page):
        return
    _write_debug_image(page, name, category=current_category, force=force)


def save_failure_debug(page: Page, name: str, *, category: str | None = None) -> None:
    current_category = _current_debug_category(page, category)
    if not _failure_debug_enabled(page):
        return
    _write_debug_image(page, name, category=current_category, force=True)


def _failure_debug_enabled(page: Page) -> bool:
    try:
        flag = _CONTEXT_FAILURE_DEBUG_ENABLED.get(id(page.context))
        if flag is not None:
            return bool(flag)
    except Exception:
        pass
    return True


def _write_debug_image(page: Page, name: str, *, category: str, force: bool = False) -> None:
    directory = _debug_dir(category)
    directory.mkdir(parents=True, exist_ok=True)

    try:
        screenshot_bytes = page.screenshot(full_page=True)
    except Exception:
        return

    if not force and _debug_dedupe_enabled(category):
        try:
            context_id = id(page.context)
        except Exception:
            context_id = 0
        fingerprint = _page_state_fingerprint(page, screenshot_bytes)
        seen = _CONTEXT_DEBUG_FINGERPRINTS.setdefault(context_id, set())
        if fingerprint in seen:
            return
        seen.add(fingerprint)

    ts = time.strftime("%Y%m%d_%H%M%S")
    ms = int((time.time() % 1) * 1000)
    seq = next(_DEBUG_COUNTER)
    stem = f"{ts}_{ms:03d}_{seq:04d}_{_safe_debug_name(name)}"
    png_path = directory / f"{stem}.png"
    try:
        png_path.write_bytes(screenshot_bytes)
    except Exception:
        pass

