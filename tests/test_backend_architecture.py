from __future__ import annotations

import ast
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"


def _backend_imports() -> list[tuple[str, str]]:
    edges: list[tuple[str, str]] = []
    for path in BACKEND_DIR.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        module = ".".join(path.with_suffix("").relative_to(ROOT_DIR).parts)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("backend."):
                edges.append((module, node.module))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("backend."):
                        edges.append((module, alias.name))
    return edges


def test_shared_and_models_do_not_depend_on_outer_layers() -> None:
    for source, target in _backend_imports():
        if source.startswith("backend.shared"):
            assert target.startswith("backend.shared"), f"{source} must not import {target}"
        if source.startswith("backend.models"):
            assert target.startswith(("backend.shared", "backend.models")), f"{source} must not import {target}"


def test_services_do_not_depend_on_workflows_api_or_external_adapters() -> None:
    for source, target in _backend_imports():
        if source.startswith("backend.services"):
            assert not target.startswith(("backend.workflows", "backend.api", "backend.adapters")), f"{source} must not import {target}"


def test_adapters_do_not_depend_on_workflows_or_api() -> None:
    for source, target in _backend_imports():
        if source.startswith("backend.adapters"):
            assert not target.startswith(("backend.workflows", "backend.api")), f"{source} must not import {target}"
