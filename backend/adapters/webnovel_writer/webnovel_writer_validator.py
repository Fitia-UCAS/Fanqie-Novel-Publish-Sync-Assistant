from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class GateResult:
    ok: bool = True
    stage: str = ""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)

    def fail(self, message: str) -> "GateResult":
        self.ok = False
        self.errors.append(message)
        return self

    def warn(self, message: str) -> "GateResult":
        self.warnings.append(message)
        return self

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "stage": self.stage, "errors": self.errors, "warnings": self.warnings, **self.data}


def gate(stage: str) -> GateResult:
    return GateResult(stage=stage)


def require_dict(value: Any, name: str, result: GateResult) -> dict[str, Any]:
    if not isinstance(value, dict):
        result.fail(f"{name} 必须是 JSON object。")
        return {}
    return value


def require_list(value: Any, name: str, result: GateResult) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        result.fail(f"{name} 必须是数组。")
        return []
    return value


def validate_changes(changes: dict[str, Any], *, marker_found: bool = True) -> GateResult:
    result = gate("draft")
    require_dict(changes, "CHANGES", result)
    if not marker_found:
        result.fail("缺少 ---CHANGES--- 分隔符。")
    required = ["summary", "characters", "locations", "factions", "items", "foreshadows", "conflicts", "timeline", "hooks"]
    for key in required:
        if key not in changes:
            result.fail(f"CHANGES 缺少字段：{key}")
    for key in ["characters", "locations", "factions", "items", "foreshadows", "conflicts"]:
        if key in changes and not isinstance(changes.get(key), dict):
            result.fail(f"CHANGES.{key} 必须是对象。")
    for key in ["timeline", "hooks"]:
        if key in changes and not isinstance(changes.get(key), list):
            result.fail(f"CHANGES.{key} 必须是数组。")
    return result


def validate_review(review: dict[str, Any]) -> GateResult:
    result = gate("review")
    require_dict(review, "review", result)
    if "pass" not in review:
        result.fail("review 缺少 pass 字段。")
    if "blocking_issues" not in review:
        result.fail("review 缺少 blocking_issues 字段。")
    blocking = require_list(review.get("blocking_issues"), "review.blocking_issues", result)
    warnings = require_list(review.get("warnings"), "review.warnings", result)
    result.data["blocking_count"] = len(blocking)
    result.data["warning_count"] = len(warnings)
    if blocking:
        result.fail(f"审稿存在 {len(blocking)} 个 blocking issue。")
    if review.get("pass") is False:
        result.fail("review.pass=false，禁止正式落地。")
    return result


def validate_data_artifacts(fulfillment: dict[str, Any], disambiguation: dict[str, Any], extraction: dict[str, Any]) -> GateResult:
    result = gate("data-agent")
    require_dict(fulfillment, "fulfillment_result", result)
    require_dict(disambiguation, "disambiguation_result", result)
    require_dict(extraction, "extraction_result", result)
    missed = fulfillment.get("missed_nodes") or []
    pending = disambiguation.get("pending") or []
    if not isinstance(missed, list):
        result.fail("fulfillment_result.missed_nodes 必须是数组。")
        missed = []
    if not isinstance(pending, list):
        result.fail("disambiguation_result.pending 必须是数组。")
        pending = []
    if missed:
        result.fail(f"章节蓝图存在 {len(missed)} 个未完成节点。")
    if pending:
        result.fail(f"存在 {len(pending)} 个待消歧实体。")
    if "summary" not in extraction:
        result.fail("extraction_result 缺少 summary。")
    return result


def validate_commit(commit: dict[str, Any]) -> GateResult:
    result = gate("precommit")
    require_dict(commit, "chapter_commit", result)
    for key in ["chapter_no", "chapter_title", "summary", "status", "review", "artifacts"]:
        if key not in commit:
            result.fail(f"chapter_commit 缺少字段：{key}")
    if commit.get("status") != "accepted":
        result.fail(f"chapter_commit.status={commit.get('status')}，非 accepted 禁止正式落地。")
    return result


def blueprint_required_nodes(blueprint: dict[str, Any] | None) -> list[str]:
    if not isinstance(blueprint, dict):
        return []
    nodes = blueprint.get("must_cover_nodes") or blueprint.get("mustCoverNodes") or []
    return [str(item).strip() for item in nodes if str(item).strip()] if isinstance(nodes, list) else []
