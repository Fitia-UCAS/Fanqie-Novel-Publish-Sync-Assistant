from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def read_json(path: str | Path, default: Any = None) -> Any:
    p = Path(path)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: str | Path, data: Any) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def extract_json_object(raw: str) -> dict[str, Any]:
    text = _strip_fences(raw)
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {"value": value}
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            value = json.loads(text[start : end + 1])
            return value if isinstance(value, dict) else {"value": value}
        except Exception:
            return {"raw": raw.strip()}
    return {"raw": raw.strip()}


def split_draft_and_changes(raw: str) -> tuple[str, dict[str, Any]]:
    markers = ["---CHANGES---", "--- changes ---", "---变更---", "---FACTS---"]
    for marker in markers:
        if marker in raw:
            draft, changes = raw.split(marker, 1)
            return draft.strip(), extract_json_object(changes)
    # Try to recover a trailing JSON object without eating prose too aggressively.
    match = re.search(r"\n\s*(\{[\s\S]+\})\s*$", raw.strip())
    if match:
        return raw[: match.start()].strip(), extract_json_object(match.group(1))
    return raw.strip(), {}


def _strip_fences(raw: str) -> str:
    text = str(raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def split_draft_and_changes_with_marker(raw: str) -> tuple[str, dict[str, Any], bool]:
    markers = ["---CHANGES---", "--- changes ---", "---变更---", "---FACTS---"]
    for marker in markers:
        if marker in raw:
            draft, changes = raw.split(marker, 1)
            return draft.strip(), extract_json_object(changes), True
    draft, changes = split_draft_and_changes(raw)
    return draft, changes, False
