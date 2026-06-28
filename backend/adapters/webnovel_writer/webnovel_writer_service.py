from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.adapters.webnovel_writer.webnovel_writer_client import WebnovelWriterClient
from backend.adapters.webnovel_writer.webnovel_writer_json import extract_json_object, split_draft_and_changes_with_marker
from backend.adapters.webnovel_writer.webnovel_writer_platform import WebnovelWriterPlatform
from backend.adapters.webnovel_writer.webnovel_writer_prompts import (
    CONTEXT_SYSTEM,
    FACT_SYSTEM,
    PLANNER_SYSTEM,
    REVIEWER_SYSTEM,
    DRAFTER_SYSTEM,
    build_blueprint_json_prompt,
    build_context_agent_prompt,
    build_context_pack,
    build_draft_prompt,
    build_fact_prompt,
    build_outline_prompt,
    build_review_prompt,
)
from backend.adapters.webnovel_writer.webnovel_writer_storage import WebnovelWriterStorage
from backend.adapters.webnovel_writer.webnovel_writer_validator import (
    GateResult,
    blueprint_required_nodes,
    gate,
    validate_changes,
    validate_commit,
    validate_data_artifacts,
    validate_review,
)
from backend.shared.app.app_paths import WEBNOVEL_WRITER_PROJECT_DIR
from backend.shared.task.task_callbacks import TaskCallbacks
from backend.shared.task.task_result import TaskResult


class WebnovelWriterService:
    """Python/JS webnovel product layer.

    Product position:
    - webnovel-writer contributes agent-style workflow and artifact discipline.
    - Tianming contributes hard gates, state ledger, and no-bad-chapter-writeback rules.
    - Fanqie assistant contributes desktop UI, DeepSeek friendly runtime, export/publish loop.
    """

    def __init__(self) -> None:
        self.storage = WebnovelWriterStorage(WEBNOVEL_WRITER_PROJECT_DIR)

    @staticmethod
    def platforms() -> dict[str, str]:
        return WebnovelWriterPlatform.list_platforms()

    @staticmethod
    def default_platform_values(platform: str) -> dict[str, str | int | float]:
        return WebnovelWriterPlatform.default_runtime_values(platform)

    def list_projects(self) -> dict[str, Any]:
        return {"ok": True, "projects": self.storage.list_projects()}

    def save_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.storage.create_or_update_project(payload)
        return {"ok": True, "message": f"项目已保存：{result['meta'].get('title')}", **result}

    def load_project(self, project_id: str) -> dict[str, Any]:
        return {"ok": True, **self.storage.load_project(project_id)}

    def open_project_path(self, project_id: str) -> str:
        return self.storage.paths(project_id).root

    def plan(self, payload: dict[str, Any], callbacks: TaskCallbacks | None = None) -> TaskResult:
        callbacks = callbacks or TaskCallbacks()
        project_id = self._project_id(payload)
        meta = self.storage.load_meta(project_id)
        story_config = self.storage.load_story_config(project_id)
        runtime = WebnovelWriterPlatform.runtime_from_payload(payload)
        client = WebnovelWriterClient(runtime)
        plan_type = str(payload.get("planType") or "full").strip()
        chapter_no = _int(payload.get("chapterNo"), 1)
        scope_label = {"full": "全书大纲", "volume": "分卷大纲", "blueprint": "章节蓝图"}.get(plan_type, "规划")
        callbacks.emit_log(f"规划：开始生成 {scope_label}。", "info")
        callbacks.emit_progress(0, 1)

        if plan_type == "blueprint":
            prompt = self._blueprint_prompt(meta, project_id, chapter_no, payload)
            content = client.chat(PLANNER_SYSTEM, prompt, temperature=0.45, max_tokens=min(runtime.max_tokens, 4096))
            blueprint = extract_json_object(content)
            if not isinstance(blueprint, dict) or not blueprint.get("goal"):
                callbacks.emit_log("蓝图 JSON 不完整，已保存原始内容并标记为待人工确认。", "warning")
                blueprint = {"chapter_no": chapter_no, "raw": content, "must_cover_nodes": [], "forbidden_zones": []}
            md = self._blueprint_markdown(blueprint, content)
            path = self.storage.save_blueprint(project_id, chapter_no, md)
            self.storage.save_blueprint_json(project_id, chapter_no, blueprint)
        else:
            prompt = build_outline_prompt(meta, scope=plan_type, story_config=story_config)
            content = client.chat(PLANNER_SYSTEM, prompt, temperature=_float(payload.get("temperature"), runtime.temperature), max_tokens=runtime.max_tokens)
            filename = "全书大纲" if plan_type == "full" else f"第{_int(payload.get('volumeNo'), 1)}卷_分卷大纲"
            path = self.storage.save_outline(project_id, filename, content)
        callbacks.emit_progress(1, 1)
        callbacks.emit_log(f"写入：{path}", "success")
        return TaskResult(ok=True, message=f"{scope_label}已生成：{path}", path=path, result_kind="output_file", data={"projectId": project_id})

    def write_chapter(self, payload: dict[str, Any], callbacks: TaskCallbacks | None = None) -> TaskResult:
        callbacks = callbacks or TaskCallbacks()
        project_id = self._project_id(payload)
        runtime = WebnovelWriterPlatform.runtime_from_payload(payload)
        client = WebnovelWriterClient(runtime)
        chapter_no = _int(payload.get("chapterNo"), 1)
        chapter_title = str(payload.get("chapterTitle") or f"第{chapter_no}章").strip()
        target_words = max(800, _int(payload.get("targetWords"), 2200))
        strictness = str(payload.get("strictness") or "标准门禁").strip()
        run: dict[str, Any] = {"chapter_no": chapter_no, "started_at": _now(), "steps": [], "artifacts": {}, "status": "running"}

        callbacks.emit_progress(0, 10)
        callbacks.emit_log(f"Step 0/10：prewrite gate 检查项目、蓝图和上一章状态。", "info")
        prewrite = self._prewrite_gate(project_id, chapter_no, strictness)
        self._record_step(run, "prewrite_gate", prewrite.to_dict())
        self.storage.save_artifact(project_id, chapter_no, "00_prewrite_gate", prewrite.to_dict())
        if not prewrite.ok:
            return self._reject(project_id, chapter_no, chapter_title, "prewrite gate 未通过。", run, callbacks, prewrite.to_dict())
        callbacks.emit_progress(1, 10)

        callbacks.emit_log("Step 1/10：程序检索上下文包。", "info")
        context_pack = self._context_pack(project_id, chapter_no, payload)
        context_path = self.storage.save_runtime_text(project_id, chapter_no, "context_pack", context_pack)
        run["artifacts"]["context_pack"] = str(context_path)
        callbacks.emit_progress(2, 10)
        if callbacks.stop_requested():
            raise RuntimeError("任务已停止。")

        callbacks.emit_log("Step 2/10：context-agent 生成写作任务书。", "info")
        blueprint_json = self.storage.load_blueprint_json(project_id, chapter_no)
        story_config = self.storage.load_story_config(project_id)
        brief = client.chat(
            CONTEXT_SYSTEM,
            build_context_agent_prompt(context_pack, blueprint_json, story_config),
            temperature=0.25,
            max_tokens=min(runtime.max_tokens, 6144),
        )
        brief_path = self.storage.save_runtime_text(project_id, chapter_no, "writing_brief", brief)
        run["artifacts"]["writing_brief"] = str(brief_path)
        callbacks.emit_progress(3, 10)
        if callbacks.stop_requested():
            raise RuntimeError("任务已停止。")

        callbacks.emit_log("Step 3/10：起草正文 + CHANGES 协议。", "info")
        raw = client.chat(
            DRAFTER_SYSTEM,
            build_draft_prompt(brief, chapter_no=chapter_no, chapter_title=chapter_title, target_words=target_words, strictness=strictness),
            temperature=_float(payload.get("temperature"), runtime.temperature),
            max_tokens=runtime.max_tokens,
        )
        chapter_text, changes, marker_found = split_draft_and_changes_with_marker(raw)
        draft_gate = self._draft_gate(chapter_text, changes, marker_found)
        if not draft_gate.ok:
            callbacks.emit_log("CHANGES 协议不完整，自动要求模型修复一次。", "warning")
            raw = client.chat(DRAFTER_SYSTEM, self._protocol_repair_prompt(brief, raw, draft_gate.to_dict()), temperature=0.35, max_tokens=runtime.max_tokens)
            chapter_text, changes, marker_found = split_draft_and_changes_with_marker(raw)
            draft_gate = self._draft_gate(chapter_text, changes, marker_found)
        self._record_step(run, "draft_gate", draft_gate.to_dict())
        self.storage.save_artifact(project_id, chapter_no, "03_draft_gate", draft_gate.to_dict())
        if not draft_gate.ok:
            draft_path = self.storage.save_draft(project_id, chapter_no, chapter_title, chapter_text or raw, rejected=True)
            return self._reject(project_id, chapter_no, chapter_title, f"draft gate 未通过，草稿已保存：{draft_path}", run, callbacks, draft_gate.to_dict(), path=draft_path)
        chapter_title = self._resolve_title(chapter_title, chapter_text, chapter_no)
        draft_path = self.storage.save_draft(project_id, chapter_no, chapter_title, chapter_text, rejected=False)
        run["artifacts"]["draft"] = str(draft_path)
        callbacks.emit_progress(4, 10)
        if callbacks.stop_requested():
            raise RuntimeError("任务已停止。")

        callbacks.emit_log("Step 4/10：reviewer 审稿门禁。", "info")
        review_raw = client.chat(REVIEWER_SYSTEM, build_review_prompt(brief, chapter_text, changes), temperature=0.1, max_tokens=4096)
        review = extract_json_object(review_raw)
        review_gate = validate_review(review)
        callbacks.emit_progress(5, 10)

        if payload.get("autoFix") and not review_gate.ok:
            callbacks.emit_log("审稿有阻断问题，按后端策略自动修复一轮。", "warning")
            fixed_raw = client.chat(DRAFTER_SYSTEM, self._fix_prompt(brief, chapter_text, review, target_words), temperature=0.55, max_tokens=runtime.max_tokens)
            fixed_text, fixed_changes, fixed_marker = split_draft_and_changes_with_marker(fixed_raw)
            fixed_draft_gate = self._draft_gate(fixed_text, fixed_changes, fixed_marker)
            if fixed_text.strip() and fixed_draft_gate.ok:
                chapter_text, changes = fixed_text, fixed_changes or changes
                chapter_title = self._resolve_title(chapter_title, chapter_text, chapter_no)
                review_raw = client.chat(REVIEWER_SYSTEM, build_review_prompt(brief, chapter_text, changes), temperature=0.1, max_tokens=4096)
                review = extract_json_object(review_raw)
                review_gate = validate_review(review)
                self.storage.save_draft(project_id, chapter_no, chapter_title, chapter_text, rejected=False)
            self.storage.save_artifact(project_id, chapter_no, "04_repair_draft_gate", fixed_draft_gate.to_dict())
        review_path = self.storage.save_review(project_id, chapter_no, review)
        self._record_step(run, "review_gate", review_gate.to_dict())
        self.storage.save_artifact(project_id, chapter_no, "04_review_gate", review_gate.to_dict())
        if not review_gate.ok:
            rejected_path = self.storage.save_draft(project_id, chapter_no, chapter_title, chapter_text, rejected=True)
            return self._reject(project_id, chapter_no, chapter_title, f"review gate 未通过，未写入正式章节：{rejected_path}", run, callbacks, review_gate.to_dict(), path=rejected_path)
        callbacks.emit_progress(6, 10)
        if callbacks.stop_requested():
            raise RuntimeError("任务已停止。")

        callbacks.emit_log("Step 5/10：data-agent 提取 fulfillment / disambiguation / extraction 三件套。", "info")
        fact_raw = client.chat(FACT_SYSTEM, build_fact_prompt(chapter_no, chapter_title, chapter_text, changes), temperature=0.1, max_tokens=6144)
        fact_bundle = extract_json_object(fact_raw)
        fulfillment = _dict(fact_bundle.get("fulfillment_result"))
        disambiguation = _dict(fact_bundle.get("disambiguation_result"))
        extraction = _dict(fact_bundle.get("extraction_result") or fact_bundle)
        if not fulfillment:
            fulfillment = self._fallback_fulfillment(chapter_no, blueprint_json, chapter_text)
        if not disambiguation:
            disambiguation = {"new_entities": [], "ambiguous_entities": [], "pending": []}
        data_gate = validate_data_artifacts(fulfillment, disambiguation, extraction)
        self.storage.save_artifact(project_id, chapter_no, "05_fulfillment_result", fulfillment)
        self.storage.save_artifact(project_id, chapter_no, "05_disambiguation_result", disambiguation)
        self.storage.save_artifact(project_id, chapter_no, "05_extraction_result", extraction)
        self.storage.save_artifact(project_id, chapter_no, "05_data_gate", data_gate.to_dict())
        self._record_step(run, "data_gate", data_gate.to_dict())
        if not data_gate.ok:
            rejected_path = self.storage.save_draft(project_id, chapter_no, chapter_title, chapter_text, rejected=True)
            return self._reject(project_id, chapter_no, chapter_title, f"data-agent gate 未通过，未写入正式章节：{rejected_path}", run, callbacks, data_gate.to_dict(), path=rejected_path)
        callbacks.emit_progress(7, 10)

        callbacks.emit_log("Step 6/10：构建 chapter_commit 并执行 precommit gate。", "info")
        commit = self._build_commit(chapter_no, chapter_title, changes, extraction, review, fulfillment, disambiguation)
        commit_gate = validate_commit(commit)
        self.storage.save_artifact(project_id, chapter_no, "06_precommit_gate", commit_gate.to_dict())
        self._record_step(run, "precommit_gate", commit_gate.to_dict())
        if not commit_gate.ok:
            return self._reject(project_id, chapter_no, chapter_title, "precommit gate 未通过，未更新 story_state。", run, callbacks, commit_gate.to_dict())
        callbacks.emit_progress(8, 10)

        callbacks.emit_log("Step 7/10：正式落地正文、commit、story_state。", "info")
        chapter_path = self.storage.save_chapter(project_id, chapter_no, chapter_title, chapter_text)
        commit_path = self.storage.save_commit(project_id, chapter_no, commit)
        self._apply_commit(project_id, chapter_no, commit)
        postcommit = self._postcommit_gate(project_id, chapter_no)
        self.storage.save_artifact(project_id, chapter_no, "07_postcommit_gate", postcommit.to_dict())
        self._record_step(run, "postcommit_gate", postcommit.to_dict())
        callbacks.emit_progress(9, 10)
        if not postcommit.ok:
            run["status"] = "postcommit_failed"
            run["finished_at"] = _now()
            self.storage.save_run(project_id, chapter_no, run)
            return TaskResult(ok=False, message="postcommit gate 未通过，请查看 artifacts。", path=commit_path, result_kind="output_file", data={"gate": postcommit.to_dict()})

        callbacks.emit_log("Step 8/10：运行账本与备份点已写入。", "success")
        run["status"] = "committed"
        run["finished_at"] = _now()
        run_path = self.storage.save_run(project_id, chapter_no, run)
        callbacks.emit_progress(10, 10)
        callbacks.emit_log(f"完成：{chapter_path}", "success")
        return TaskResult(
            ok=True,
            message=f"第 {chapter_no} 章已通过硬门禁并正式入账：{chapter_path}",
            path=chapter_path,
            result_kind="output_file",
            data={
                "projectId": project_id,
                "chapterPath": str(chapter_path),
                "reviewPath": str(review_path),
                "commitPath": str(commit_path),
                "runPath": str(run_path),
                "review": review,
                "gates": {"prewrite": prewrite.to_dict(), "draft": draft_gate.to_dict(), "review": review_gate.to_dict(), "data": data_gate.to_dict(), "precommit": commit_gate.to_dict(), "postcommit": postcommit.to_dict()},
            },
        )

    def batch_write(self, payload: dict[str, Any], callbacks: TaskCallbacks | None = None) -> TaskResult:
        callbacks = callbacks or TaskCallbacks()
        project_id = self._project_id(payload)
        start = _int(payload.get("start"), _int(payload.get("chapterNo"), 1))
        end = _int(payload.get("end"), start)
        if end < start:
            raise ValueError("结束章不能小于开始章。")
        total = end - start + 1
        outputs = []
        callbacks.emit_log(f"批量写作：第 {start} - {end} 章，共 {total} 章。失败章节会进入 rejected，不污染 story_state。", "info")
        for offset, chapter_no in enumerate(range(start, end + 1), start=1):
            if callbacks.stop_requested():
                callbacks.emit_log("停止：已收到停止请求。", "warning")
                break
            child_payload = dict(payload, chapterNo=chapter_no, chapterTitle=payload.get("chapterTitle") or f"第{chapter_no}章")
            callbacks.emit_log(f"批量：开始第 {chapter_no} 章。", "info")
            result = self.write_chapter(child_payload, callbacks)
            outputs.append(result.to_dict())
            if not result.ok:
                callbacks.emit_log(f"第 {chapter_no} 章未通过硬门禁，批量流程停止。", "warning")
                break
            callbacks.emit_progress(offset, total)
        return TaskResult(ok=True, message=f"批量写作完成：成功/处理 {len(outputs)} 章。", path=Path(self.storage.paths(project_id).chapters), result_kind="output_dir", data={"outputs": outputs})

    def review_chapter(self, payload: dict[str, Any], callbacks: TaskCallbacks | None = None) -> TaskResult:
        callbacks = callbacks or TaskCallbacks()
        project_id = self._project_id(payload)
        runtime = WebnovelWriterPlatform.runtime_from_payload(payload)
        client = WebnovelWriterClient(runtime)
        chapter_no = _int(payload.get("chapterNo"), 1)
        chapter_path, chapter_text = self.storage.load_chapter(project_id, chapter_no)
        if not chapter_text:
            raise FileNotFoundError(f"未找到第 {chapter_no} 章正式正文。")
        context_pack = self._context_pack(project_id, chapter_no, payload)
        callbacks.emit_progress(0, 1)
        raw = client.chat(REVIEWER_SYSTEM, build_review_prompt(context_pack, chapter_text, {}), temperature=0.1, max_tokens=4096)
        review = extract_json_object(raw)
        review_gate = validate_review(review)
        review["gate"] = review_gate.to_dict()
        review_path = self.storage.save_review(project_id, chapter_no, review)
        callbacks.emit_progress(1, 1)
        return TaskResult(ok=review_gate.ok, message=f"第 {chapter_no} 章审查完成：{review_path}", path=review_path, result_kind="output_file", data={"review": review, "chapterPath": str(chapter_path), "gate": review_gate.to_dict()})

    def validate_project(self, payload: dict[str, Any], callbacks: TaskCallbacks | None = None) -> TaskResult:
        callbacks = callbacks or TaskCallbacks()
        project_id = self._project_id(payload)
        data = self.storage.load_project(project_id)
        state = data["state"]
        issues: list[dict[str, Any]] = []
        callbacks.emit_progress(0, 4)
        # chapter sequence and status
        chapters = data.get("chapters") or []
        statuses = state.get("chapter_status") or {}
        for row in chapters:
            ch = str(row.get("chapterNo"))
            if statuses.get(ch) != "committed":
                issues.append({"level": "warning", "type": "chapter_status", "message": f"第 {ch} 章有正文但状态不是 committed。"})
        callbacks.emit_progress(1, 4)
        # long unresolved foreshadows
        latest = _int(state.get("latest_chapter"), 0)
        for name, item in (state.get("foreshadows") or {}).items():
            if isinstance(item, dict) and str(item.get("status") or "") in {"新增", "推进", "未收", "open"}:
                first = _int(item.get("introduced_chapter"), latest)
                if latest - first >= 30:
                    issues.append({"level": "warning", "type": "foreshadow_debt", "message": f"伏笔《{name}》已超过 30 章未回收。"})
        callbacks.emit_progress(2, 4)
        # entity required fields
        for key in ["characters", "locations", "factions", "items"]:
            for name, item in (state.get(key) or {}).items():
                if isinstance(item, dict) and not item.get("id"):
                    issues.append({"level": "warning", "type": "entity_id", "message": f"{key}.{name} 缺少实体 ID。"})
        callbacks.emit_progress(3, 4)
        ok = not any(item["level"] == "error" for item in issues)
        report = {"ok": ok, "project_id": project_id, "checked_at": _now(), "issue_count": len(issues), "issues": issues}
        path = self.storage.save_validation(project_id, f"全书校验_{datetime.now():%Y%m%d_%H%M%S}", report)
        callbacks.emit_progress(4, 4)
        return TaskResult(ok=ok, message=f"全书校验完成：{len(issues)} 个提示。", path=path, result_kind="output_file", data={"report": report})

    def export(self, payload: dict[str, Any], callbacks: TaskCallbacks | None = None) -> TaskResult:
        callbacks = callbacks or TaskCallbacks()
        project_id = self._project_id(payload)
        callbacks.emit_progress(0, 1)
        output = self.storage.export_txt(project_id)
        callbacks.emit_progress(1, 1)
        callbacks.emit_log(f"导出：{output}", "success")
        return TaskResult(ok=True, message=f"全书已导出：{output}", path=output, result_kind="output_file", data={"projectId": project_id})

    def dashboard(self, project_id: str) -> dict[str, Any]:
        data = self.storage.load_project(project_id)
        state = data["state"]
        statuses = state.get("chapter_status") or {}
        committed = sum(1 for value in statuses.values() if value == "committed")
        rejected = sum(1 for value in statuses.values() if value == "rejected")
        return {
            "ok": True,
            "meta": data["meta"],
            "paths": data["paths"],
            "chapterCount": len(data["chapters"]),
            "committedCount": committed,
            "rejectedCount": rejected,
            "blueprintCount": len(data["blueprints"]),
            "characters": len(state.get("characters") or {}),
            "foreshadows": len(state.get("foreshadows") or {}),
            "latestChapter": state.get("latest_chapter") or 0,
            "chapters": data["chapters"][-20:],
        }

    def _project_id(self, payload: dict[str, Any]) -> str:
        project_id = str(payload.get("projectId") or payload.get("project_id") or payload.get("projectPath") or payload.get("project_path") or "").strip()
        if not project_id:
            result = self.storage.create_or_update_project(payload)
            return str(result["meta"]["project_id"])
        return project_id

    def _blueprint_prompt(self, meta: dict[str, Any], project_id: str, chapter_no: int, payload: dict[str, Any]) -> str:
        state = self.storage.load_state(project_id)
        story_config = self.storage.load_story_config(project_id)
        outline = self.storage.latest_outline_text(project_id)
        recent = self.storage.recent_chapter_summaries(project_id, _int(payload.get("recentContextCount"), 6))
        return build_blueprint_json_prompt(meta, state, outline, recent, chapter_no, story_config)

    def _context_pack(self, project_id: str, chapter_no: int, payload: dict[str, Any]) -> str:
        meta = self.storage.load_meta(project_id)
        state = self.storage.load_state(project_id)
        story_config = self.storage.load_story_config(project_id)
        outline = self.storage.latest_outline_text(project_id)
        blueprint = self.storage.load_blueprint(project_id, chapter_no)
        blueprint_json = self.storage.load_blueprint_json(project_id, chapter_no)
        recent = self.storage.recent_chapter_summaries(project_id, _int(payload.get("recentContextCount"), 6))
        base = build_context_pack(meta, state, outline, blueprint, recent, chapter_no, story_config)
        return f"{base}\n\n【后端 story_config】\n{story_config}\n\n【结构化章节蓝图】\n{blueprint_json or {}}".strip()

    def _prewrite_gate(self, project_id: str, chapter_no: int, strictness: str) -> GateResult:
        result = gate("prewrite")
        meta = self.storage.load_meta(project_id)
        if not meta.get("title"):
            result.fail("项目缺少书名。")
        state = self.storage.load_state(project_id)
        latest = _int(state.get("latest_chapter"), 0)
        if chapter_no > 1 and latest < chapter_no - 1:
            result.warn(f"上一章状态未入账：latest_chapter={latest}，目标章={chapter_no}。")
        blueprint_json = self.storage.load_blueprint_json(project_id, chapter_no)
        blueprint_text = self.storage.load_blueprint(project_id, chapter_no)
        if not blueprint_json and not blueprint_text:
            if "严格" in strictness:
                result.fail("严格门禁要求先生成章节蓝图。")
            else:
                result.warn("本章没有蓝图，将按现有状态自然推进。")
        return result

    def _draft_gate(self, chapter_text: str, changes: dict[str, Any], marker_found: bool) -> GateResult:
        result = validate_changes(changes, marker_found=marker_found)
        if not chapter_text.strip():
            result.fail("章节正文为空。")
        if len(chapter_text.strip()) < 300:
            result.warn("章节正文偏短。")
        return result

    def _postcommit_gate(self, project_id: str, chapter_no: int) -> GateResult:
        result = gate("postcommit")
        state = self.storage.load_state(project_id)
        chapter_path, chapter_text = self.storage.load_chapter(project_id, chapter_no)
        if not chapter_path or not chapter_text.strip():
            result.fail("正式章节文件不存在。")
        if str(chapter_no) not in (state.get("chapter_summaries") or {}):
            result.fail("story_state.chapter_summaries 未写入本章。")
        if (state.get("chapter_status") or {}).get(str(chapter_no)) != "committed":
            result.fail("story_state.chapter_status 未标记 committed。")
        if _int(state.get("latest_chapter"), 0) < chapter_no:
            result.fail("story_state.latest_chapter 未推进。")
        return result

    def _reject(self, project_id: str, chapter_no: int, title: str, message: str, run: dict[str, Any], callbacks: TaskCallbacks, gate_payload: dict[str, Any], path: Path | None = None) -> TaskResult:
        state = self.storage.load_state(project_id)
        state.setdefault("chapter_status", {})[str(chapter_no)] = "rejected"
        self.storage.save_state(project_id, state)
        run["status"] = "rejected"
        run["finished_at"] = _now()
        run["reject_gate"] = gate_payload
        run_path = self.storage.save_run(project_id, chapter_no, run)
        callbacks.emit_log(message, "error")
        return TaskResult(ok=False, message=message, path=path or run_path, result_kind="output_file", data={"projectId": project_id, "runPath": str(run_path), "gate": gate_payload})

    def _protocol_repair_prompt(self, brief: str, raw: str, gate_payload: dict[str, Any]) -> str:
        return f"""
你刚才的章节输出没有通过协议门禁。请保留正文内容，修复输出格式。

【门禁错误】
{gate_payload}

【写作任务书】
{brief}

【原始输出】
{raw}

必须输出：正文 + 单独一行 ---CHANGES--- + 完整 JSON。
JSON 必须包含 summary, characters, locations, factions, items, foreshadows, conflicts, timeline, hooks, quality_notes。
""".strip()

    def _resolve_title(self, title: str, chapter_text: str, chapter_no: int) -> str:
        clean = (title or "").strip()
        if clean and clean != f"第{chapter_no}章":
            return clean
        first_line = chapter_text.strip().splitlines()[0].strip() if chapter_text.strip() else ""
        match = re.match(r"^第\s*\d+\s*章\s*[：:、\s]*(.+)$", first_line)
        if match:
            return match.group(1).strip()[:40] or clean or f"第{chapter_no}章"
        return clean or f"第{chapter_no}章"

    def _fix_prompt(self, brief: str, chapter_text: str, review: dict[str, Any], target_words: int) -> str:
        return f"""
请根据审稿问题修复章节。保留能用的正文，修复阻断问题，不要另起炉灶。

【写作任务书】
{brief}

【原正文】
{chapter_text}

【审稿报告】
{review}

目标字数约 {target_words} 字。输出格式仍然是：正文 + ---CHANGES--- + JSON。
""".strip()

    def _fallback_fulfillment(self, chapter_no: int, blueprint_json: dict[str, Any], chapter_text: str) -> dict[str, Any]:
        nodes = blueprint_required_nodes(blueprint_json)
        completed, missed = [], []
        for node in nodes:
            # Soft heuristic; data-agent remains source of truth when available.
            if any(piece and piece in chapter_text for piece in re.split(r"[，,。；;、\s]+", node)[:3]):
                completed.append(node)
            else:
                missed.append(node)
        return {"chapter_no": chapter_no, "completed_nodes": completed, "missed_nodes": missed, "notes": ["fallback heuristic"]}

    def _build_commit(self, chapter_no: int, chapter_title: str, changes: dict[str, Any], extraction: dict[str, Any], review: dict[str, Any], fulfillment: dict[str, Any], disambiguation: dict[str, Any]) -> dict[str, Any]:
        rejected = bool((review.get("blocking_issues") or []) or (fulfillment.get("missed_nodes") or []) or (disambiguation.get("pending") or []))
        return {
            "schema_version": 2,
            "chapter_no": chapter_no,
            "chapter_title": chapter_title,
            "status": "rejected" if rejected else "accepted",
            "summary": extraction.get("summary") or changes.get("summary") or "",
            "characters": extraction.get("characters") or changes.get("characters") or {},
            "locations": extraction.get("locations") or changes.get("locations") or {},
            "factions": extraction.get("factions") or changes.get("factions") or {},
            "items": extraction.get("items") or changes.get("items") or {},
            "foreshadows": extraction.get("foreshadows") or changes.get("foreshadows") or {},
            "conflicts": extraction.get("conflicts") or changes.get("conflicts") or {},
            "timeline": extraction.get("timeline") or changes.get("timeline") or [],
            "milestones": extraction.get("milestones") or [],
            "hooks": extraction.get("hooks") or changes.get("hooks") or [],
            "review": review,
            "artifacts": {"fulfillment_result": fulfillment, "disambiguation_result": disambiguation, "extraction_result": extraction},
            "created_at": _now(),
        }

    def _apply_commit(self, project_id: str, chapter_no: int, commit: dict[str, Any]) -> None:
        state = self.storage.load_state(project_id)
        for key, prefix in [("characters", "char"), ("locations", "loc"), ("factions", "fac"), ("items", "item"), ("foreshadows", "foresh"), ("conflicts", "conf")]:
            state.setdefault(key, {})
            incoming = commit.get(key) or {}
            if isinstance(incoming, dict):
                for name, value in incoming.items():
                    current = state[key].get(name, {}) if isinstance(state[key].get(name, {}), dict) else {}
                    value_dict = value if isinstance(value, dict) else {"status": value}
                    entity = self._merge_entity(prefix, str(name), current, value_dict, chapter_no)
                    state[key][name] = entity
                    state.setdefault("entity_mentions", []).append({"chapter_no": chapter_no, "type": key, "name": str(name), "id": entity.get("id")})
        state.setdefault("timeline", [])
        if isinstance(commit.get("timeline"), list):
            state["timeline"].extend(commit["timeline"])
        state.setdefault("milestones", [])
        if isinstance(commit.get("milestones"), list):
            state["milestones"].extend(commit["milestones"])
        state.setdefault("chapter_summaries", {})[str(chapter_no)] = commit.get("summary") or ""
        state.setdefault("chapter_status", {})[str(chapter_no)] = "committed"
        state["latest_chapter"] = max(_int(state.get("latest_chapter"), 0), chapter_no)
        # Derived debt/progress views for quick dashboard and long-distance recall.
        state["foreshadow_debts"] = {name: item for name, item in (state.get("foreshadows") or {}).items() if isinstance(item, dict) and str(item.get("status") or "") not in {"回收", "resolved", "closed"}}
        state["conflict_progress"] = {name: item.get("progress") if isinstance(item, dict) else item for name, item in (state.get("conflicts") or {}).items()}
        self.storage.save_state(project_id, state)

    def _merge_entity(self, prefix: str, name: str, current: dict[str, Any], incoming: dict[str, Any], chapter_no: int) -> dict[str, Any]:
        entity = dict(current or {})
        entity.setdefault("id", f"{prefix}_{_slug(name)}")
        entity.setdefault("name", name)
        entity.setdefault("aliases", [])
        entity.setdefault("first_seen_chapter", chapter_no)
        entity["last_seen_chapter"] = chapter_no
        history = entity.setdefault("history", [])
        if isinstance(history, list):
            history.append({"chapter_no": chapter_no, "changes": incoming})
            if len(history) > 80:
                del history[:-80]
        for k, v in incoming.items():
            if k == "history":
                continue
            entity[k] = v
        return entity

    def _record_step(self, run: dict[str, Any], name: str, payload: dict[str, Any]) -> None:
        run.setdefault("steps", []).append({"name": name, "at": _now(), "ok": payload.get("ok"), "payload": payload})

    def _blueprint_markdown(self, blueprint: dict[str, Any], raw: str = "") -> str:
        if "raw" in blueprint:
            return str(raw or blueprint.get("raw") or "")
        nodes = "\n".join(f"- {item}" for item in blueprint.get("must_cover_nodes") or []) or "- 暂无"
        forbidden = "\n".join(f"- {item}" for item in blueprint.get("forbidden_zones") or []) or "- 暂无"
        return f"""# 第{blueprint.get('chapter_no', '')}章：{blueprint.get('title', '')}

## 章节目标
{blueprint.get('goal', '')}

## 时间与场景
- 时间锚点：{blueprint.get('time_anchor', '')}
- 章节跨度：{blueprint.get('chapter_span', '')}
- 视角：{blueprint.get('pov', '')}
- 场景：{blueprint.get('scene', '')}

## 必达节点
{nodes}

## 禁区
{forbidden}

## 冲突 / 爽点 / 钩子
- 冲突：{blueprint.get('conflict', '')}
- 爽点：{blueprint.get('payoff', '')}
- 章末钩子：{blueprint.get('ending_hook', '')}

## 事实回写提示
{blueprint.get('state_writeback_hint', [])}
""".strip()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _int(value: object, default: int) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except Exception:
        return default


def _float(value: object, default: float) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except Exception:
        return default


def _slug(value: str) -> str:
    text = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", value.strip()).strip("_")
    return text[:48] or "entity"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
