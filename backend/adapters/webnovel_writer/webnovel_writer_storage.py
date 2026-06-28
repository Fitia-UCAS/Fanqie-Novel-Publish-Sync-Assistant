from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.adapters.webnovel_writer.webnovel_writer_json import read_json, write_json
from backend.adapters.webnovel_writer.webnovel_writer_models import DEFAULT_STATE, WriterPaths, WriterProjectMeta
from backend.adapters.webnovel_writer.webnovel_writer_story_config import default_story_config
from backend.shared.filename.filename_sanitizer import safe_filename
from backend.shared.text_file.text_file_storage import ensure_dir, write_text, read_text_auto


def make_project_id(title: str) -> str:
    safe = safe_filename(title or "未命名小说")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{safe}_{stamp}"


class WebnovelWriterStorage:
    def __init__(self, root_dir: str | Path) -> None:
        self.root_dir = ensure_dir(root_dir)

    def project_root(self, project_id: str) -> Path:
        if not project_id:
            raise ValueError("project_id 为空，请先选择小说项目目录。")
        raw = str(project_id).strip()
        candidate = Path(raw).expanduser()
        if candidate.is_absolute() or re.match(r"^[A-Za-z]:[\\/]", raw) or raw.startswith("\\\\"):
            return candidate
        return self.root_dir / safe_filename(raw)

    def paths(self, project_id: str) -> WriterPaths:
        root = self.project_root(project_id)
        return WriterPaths(
            root=str(root),
            meta=str(root / "project.json"),
            settings=str(root / "settings.json"),
            story_config=str(root / "story_config.json"),
            state=str(root / "story_state.json"),
            outlines=str(root / "outlines"),
            volumes=str(root / "volumes"),
            blueprints=str(root / "blueprints"),
            chapters=str(root / "chapters"),
            drafts=str(root / "drafts"),
            rejected=str(root / "rejected"),
            reviews=str(root / "reviews"),
            commits=str(root / "commits"),
            runtime=str(root / "runtime"),
            artifacts=str(root / "artifacts"),
            runs=str(root / "runs"),
            validation=str(root / "validation"),
            indexes=str(root / "indexes"),
            exports=str(root / "exports"),
        )

    def ensure_project_dirs(self, project_id: str) -> WriterPaths:
        paths = self.paths(project_id)
        for value in paths.to_dict().values():
            p = Path(value)
            if p.suffix:
                ensure_dir(p.parent)
            else:
                ensure_dir(p)
        return paths

    def create_or_update_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        source_path = str(payload.get("storyConfigPath") or payload.get("story_config_path") or "").strip()
        novel_file = str(payload.get("novelFilePath") or payload.get("novel_file") or "").strip()
        project_path = str(payload.get("projectPath") or payload.get("project_path") or "").strip()
        title = str(payload.get("title") or "").strip()
        if not title:
            title = self._infer_title_from_source(source_path)
        if not title and novel_file:
            title = Path(novel_file).stem
        title = title or "未命名小说"

        project_id = str(payload.get("projectId") or payload.get("project_id") or "").strip()
        if project_path:
            project_id = project_path
        elif not project_id and novel_file:
            project_id = str(Path(novel_file).expanduser().parent)
        elif not project_id:
            project_id = make_project_id(title)

        paths = self.ensure_project_dirs(project_id)
        old = read_json(paths.meta, {}) or {}

        novel_path = Path(novel_file).expanduser() if novel_file else None
        if novel_path:
            ensure_dir(novel_path.parent)
            if not novel_path.exists():
                write_text(novel_path, "")

        story_cfg_path = Path(paths.story_config)
        story_cfg = read_json(story_cfg_path, None) if story_cfg_path.exists() else None
        if not isinstance(story_cfg, dict):
            story_cfg = default_story_config()
        existing_profile = story_cfg.get("story_profile", {}) if isinstance(story_cfg, dict) else {}
        should_import_source = bool(source_path) and (not story_cfg_path.exists() or str(existing_profile.get("source_setting_file") or "") != source_path)
        imported_cfg = self._story_config_from_source(source_path, title) if should_import_source else None
        if imported_cfg:
            story_cfg = imported_cfg
            try:
                source = Path(source_path).expanduser()
                if source.exists() and source.is_file():
                    raw_dir = ensure_dir(Path(paths.root) / "source_settings")
                    write_text(raw_dir / source.name, read_text_auto(source))
            except Exception:
                pass
        story_profile = story_cfg.setdefault("story_profile", {})
        if title and not story_profile.get("title"):
            story_profile["title"] = title
        if novel_path:
            story_cfg.setdefault("source_files", {})["novel_txt"] = str(novel_path)
        meta = WriterProjectMeta(
            project_id=project_id,
            title=title or str(story_profile.get("title") or old.get("title") or "未命名小说"),
            genre=str(old.get("genre") or story_profile.get("genre") or "").strip(),
            premise=str(old.get("premise") or story_profile.get("premise") or "").strip(),
            target_audience=str(old.get("target_audience") or old.get("targetAudience") or story_profile.get("target_audience") or "").strip(),
            style_brief=str(old.get("style_brief") or old.get("styleBrief") or story_profile.get("style_brief") or "").strip(),
            project_path=str(Path(paths.root)),
            novel_file=str(novel_path) if novel_path else str(old.get("novel_file") or ""),
            story_config_source=source_path or str(old.get("story_config_source") or ""),
            created_at=str(old.get("created_at") or datetime.now().isoformat(timespec="seconds")),
            updated_at=datetime.now().isoformat(timespec="seconds"),
        )
        write_json(paths.meta, meta.to_dict())
        if not Path(paths.state).exists():
            write_json(paths.state, dict(DEFAULT_STATE))
        write_json(story_cfg_path, story_cfg)
        self.sync_novel_file(project_id)
        return {"meta": meta.to_dict(), "paths": paths.to_dict()}



    def _infer_title_from_source(self, source_path: str) -> str:
        if not source_path:
            return ""
        source = Path(source_path).expanduser()
        if not source.exists() or not source.is_file():
            return ""
        try:
            if source.suffix.lower() == ".json":
                data = json.loads(read_text_auto(source))
                if isinstance(data, dict):
                    profile = data.get("story_profile") if isinstance(data.get("story_profile"), dict) else {}
                    return str(profile.get("title") or data.get("title") or "").strip()
            raw = read_text_auto(source)
            for pattern in (r"^#\s*[《<]?([^》>\n#]+)[》>]?", r"^##\s*书名\s*\n+\s*[《<]?([^》>\n]+)[》>]?"):
                match = re.search(pattern, raw, re.M)
                if match:
                    title = match.group(1).strip()
                    title = re.sub(r"设定$", "", title).strip(" ：:《》<>")
                    if title:
                        return title
            return source.stem
        except Exception:
            return source.stem

    def _story_config_from_source(self, source_path: str, title: str) -> dict[str, Any] | None:
        if not source_path:
            return None
        source = Path(source_path).expanduser()
        if not source.exists() or not source.is_file():
            return None
        suffix = source.suffix.lower()
        if suffix == ".json":
            try:
                data = json.loads(read_text_auto(source))
                if isinstance(data, dict):
                    return data
            except Exception:
                return None
        if suffix in {".md", ".txt"}:
            raw = read_text_auto(source)
            cfg = default_story_config()
            profile = cfg.setdefault("story_profile", {})
            profile["title"] = title or profile.get("title") or source.stem
            profile["source_setting_file"] = str(source)
            profile["raw_setting_markdown"] = raw
            cfg.setdefault("source_files", {})["story_setting"] = str(source)
            return cfg
        return None

    def list_projects(self) -> list[dict[str, Any]]:
        rows = []
        for root in sorted(self.root_dir.iterdir(), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True):
            if not root.is_dir():
                continue
            meta_path = root / "project.json"
            if not meta_path.exists():
                continue
            meta = read_json(meta_path, {}) or {}
            rows.append({
                "projectId": meta.get("project_id") or root.name,
                "title": meta.get("title") or root.name,
                "genre": meta.get("genre") or "",
                "updatedAt": meta.get("updated_at") or "",
                "path": str(root),
            })
        return rows

    def load_project(self, project_id: str) -> dict[str, Any]:
        paths = self.ensure_project_dirs(project_id)
        meta = read_json(paths.meta, {}) or {}
        state = read_json(paths.state, dict(DEFAULT_STATE)) or dict(DEFAULT_STATE)
        return {"meta": meta, "state": state, "storyConfig": self.load_story_config(project_id), "paths": paths.to_dict(), "chapters": self.list_chapters(project_id), "blueprints": self.list_blueprints(project_id)}

    def load_meta(self, project_id: str) -> dict[str, Any]:
        return read_json(self.paths(project_id).meta, {}) or {}

    def load_state(self, project_id: str) -> dict[str, Any]:
        state = read_json(self.paths(project_id).state, None)
        if not isinstance(state, dict):
            state = dict(DEFAULT_STATE)
        for key, value in DEFAULT_STATE.items():
            state.setdefault(key, value.copy() if isinstance(value, dict) else list(value) if isinstance(value, list) else value)
        return state

    def save_state(self, project_id: str, state: dict[str, Any]) -> Path:
        return write_json(self.paths(project_id).state, state)

    def load_story_config(self, project_id: str) -> dict[str, Any]:
        paths = self.ensure_project_dirs(project_id)
        cfg = read_json(paths.story_config, None)
        if not isinstance(cfg, dict):
            cfg = default_story_config()
            write_json(paths.story_config, cfg)
        return cfg

    def save_story_config(self, project_id: str, cfg: dict[str, Any]) -> Path:
        return write_json(self.paths(project_id).story_config, cfg)

    def save_outline(self, project_id: str, name: str, text: str) -> Path:
        paths = self.ensure_project_dirs(project_id)
        filename = safe_filename(name or "outline") + ".md"
        return write_text(Path(paths.outlines) / filename, text)

    def latest_outline_text(self, project_id: str) -> str:
        paths = self.ensure_project_dirs(project_id)
        candidates = sorted(Path(paths.outlines).glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        return read_text_auto(candidates[0]) if candidates else ""

    def save_blueprint(self, project_id: str, chapter_no: int, text: str) -> Path:
        paths = self.ensure_project_dirs(project_id)
        return write_text(Path(paths.blueprints) / f"第{chapter_no:04d}章_蓝图.md", text)

    def save_blueprint_json(self, project_id: str, chapter_no: int, data: dict[str, Any]) -> Path:
        paths = self.ensure_project_dirs(project_id)
        return write_json(Path(paths.blueprints) / f"第{chapter_no:04d}章_蓝图.json", data)

    def load_blueprint(self, project_id: str, chapter_no: int) -> str:
        path = Path(self.paths(project_id).blueprints) / f"第{chapter_no:04d}章_蓝图.md"
        return read_text_auto(path) if path.exists() else ""

    def load_blueprint_json(self, project_id: str, chapter_no: int) -> dict[str, Any]:
        path = Path(self.paths(project_id).blueprints) / f"第{chapter_no:04d}章_蓝图.json"
        data = read_json(path, {})
        return data if isinstance(data, dict) else {}

    def save_chapter(self, project_id: str, chapter_no: int, title: str, text: str) -> Path:
        paths = self.ensure_project_dirs(project_id)
        clean_title = safe_filename(title or f"第{chapter_no}章")
        chapter_path = write_text(Path(paths.chapters) / f"第{chapter_no:04d}章_{clean_title}.txt", text)
        self.sync_novel_file(project_id)
        return chapter_path

    def load_chapter(self, project_id: str, chapter_no: int) -> tuple[Path | None, str]:
        candidates = sorted(Path(self.paths(project_id).chapters).glob(f"第{chapter_no:04d}章_*.txt"))
        if not candidates:
            return None, ""
        path = candidates[0]
        return path, read_text_auto(path)

    def save_review(self, project_id: str, chapter_no: int, review: dict[str, Any]) -> Path:
        return write_json(Path(self.paths(project_id).reviews) / f"第{chapter_no:04d}章_review.json", review)

    def save_commit(self, project_id: str, chapter_no: int, commit: dict[str, Any]) -> Path:
        return write_json(Path(self.paths(project_id).commits) / f"第{chapter_no:04d}章_commit.json", commit)

    def save_draft(self, project_id: str, chapter_no: int, title: str, text: str, *, rejected: bool = False) -> Path:
        paths = self.ensure_project_dirs(project_id)
        clean_title = safe_filename(title or f"第{chapter_no}章")
        folder = Path(paths.rejected if rejected else paths.drafts)
        return write_text(folder / f"第{chapter_no:04d}章_{clean_title}.txt", text)

    def save_artifact(self, project_id: str, chapter_no: int, name: str, data: Any) -> Path:
        paths = self.ensure_project_dirs(project_id)
        folder = Path(paths.artifacts) / f"第{chapter_no:04d}章"
        return write_json(folder / f"{safe_filename(name)}.json", data)

    def save_runtime_text(self, project_id: str, chapter_no: int, name: str, text: str) -> Path:
        paths = self.ensure_project_dirs(project_id)
        folder = Path(paths.runtime) / f"第{chapter_no:04d}章"
        return write_text(folder / f"{safe_filename(name)}.md", text)

    def save_run(self, project_id: str, chapter_no: int, data: dict[str, Any]) -> Path:
        paths = self.ensure_project_dirs(project_id)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return write_json(Path(paths.runs) / f"第{chapter_no:04d}章_{stamp}.json", data)

    def save_validation(self, project_id: str, name: str, data: dict[str, Any]) -> Path:
        paths = self.ensure_project_dirs(project_id)
        return write_json(Path(paths.validation) / f"{safe_filename(name)}.json", data)

    def list_chapters(self, project_id: str) -> list[dict[str, Any]]:
        root = Path(self.paths(project_id).chapters)
        if not root.exists():
            return []
        rows = []
        for path in sorted(root.glob("第*.txt")):
            match = re.match(r"第(\d+)章_(.+)\.txt$", path.name)
            if not match:
                continue
            rows.append({"chapterNo": int(match.group(1)), "title": match.group(2), "path": str(path)})
        return rows

    def list_blueprints(self, project_id: str) -> list[dict[str, Any]]:
        root = Path(self.paths(project_id).blueprints)
        if not root.exists():
            return []
        rows = []
        for path in sorted(root.glob("第*章_蓝图.md")):
            match = re.match(r"第(\d+)章_蓝图\.md$", path.name)
            if not match:
                continue
            rows.append({"chapterNo": int(match.group(1)), "path": str(path)})
        return rows

    def sync_novel_file(self, project_id: str) -> Path | None:
        meta = self.load_meta(project_id)
        novel_file = str(meta.get("novel_file") or "").strip()
        if not novel_file:
            return None
        output = Path(novel_file).expanduser()
        ensure_dir(output.parent)
        chapters = []
        for row in self.list_chapters(project_id):
            path = Path(row["path"])
            body = read_text_auto(path).strip()
            if not body:
                continue
            header = f"第{row['chapterNo']}章 {row.get('title') or ''}".strip()
            if body.startswith("第"):
                chapters.append(body)
            else:
                chapters.append(f"{header}\n\n{body}")
        write_text(output, ("\n\n".join(chapters).strip() + "\n") if chapters else read_text_auto(output) if output.exists() else "")
        return output

    def export_txt(self, project_id: str) -> Path:
        paths = self.ensure_project_dirs(project_id)
        meta = self.load_meta(project_id)
        title = safe_filename(str(meta.get("title") or project_id))
        chapters = []
        for row in self.list_chapters(project_id):
            path = Path(row["path"])
            text = read_text_auto(path).strip()
            header = f"第{row['chapterNo']}章 {row.get('title') or ''}".strip()
            if text.startswith("第"):
                chapters.append(text)
            else:
                chapters.append(f"{header}\n\n{text}")
        output = Path(paths.exports) / f"{title}_全书导出.txt"
        write_text(output, "\n\n".join(chapters).strip() + "\n")
        return output

    def recent_chapter_summaries(self, project_id: str, count: int = 6) -> list[dict[str, str]]:
        state = self.load_state(project_id)
        summaries = state.get("chapter_summaries") or {}
        rows = []
        for key in sorted(summaries, key=lambda x: int(x) if str(x).isdigit() else 0)[-count:]:
            rows.append({"chapter_no": str(key), "summary": str(summaries.get(key) or "")})
        return rows
