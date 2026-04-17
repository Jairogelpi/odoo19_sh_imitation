from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import markdown

from .config import settings


MD_EXTENSIONS = ["fenced_code", "tables", "toc", "codehilite", "sane_lists"]


@dataclass
class Node:
    name: str
    rel_path: str
    is_dir: bool
    children: list["Node"]

    @property
    def display_name(self) -> str:
        return self.name.replace("_", " ").replace("-", " ")


def _root() -> Path:
    return Path(settings.docs_root).resolve()


def _resolve(rel_path: str) -> Path:
    root = _root()
    target = (root / rel_path).resolve()
    if not str(target).startswith(str(root)):
        raise ValueError("Path escapes docs root")
    if not target.exists():
        raise FileNotFoundError(rel_path)
    return target


def build_tree() -> Node:
    root = _root()

    def walk(path: Path) -> Node:
        rel = str(path.relative_to(root)) if path != root else ""
        node = Node(
            name=path.name or "docs",
            rel_path=rel,
            is_dir=path.is_dir(),
            children=[],
        )
        if path.is_dir():
            entries = sorted(
                path.iterdir(),
                key=lambda p: (not p.is_dir(), p.name.lower()),
            )
            for child in entries:
                if child.name.startswith(".") or child.name == "logs":
                    continue
                if child.is_file() and child.suffix.lower() != ".md":
                    continue
                node.children.append(walk(child))
        return node

    return walk(root)


def read_markdown(rel_path: str) -> tuple[str, str]:
    target = _resolve(rel_path)
    if target.is_dir():
        candidate = target / "README.md"
        if candidate.exists():
            target = candidate
        else:
            listing = "\n".join(
                f"- [{p.name}]({Path(rel_path) / p.name})"
                for p in sorted(target.iterdir(), key=lambda p: p.name.lower())
                if not p.name.startswith(".")
            )
            return target.name, markdown.markdown(
                f"# {target.name}\n\n{listing}", extensions=MD_EXTENSIONS
            )

    if target.suffix.lower() != ".md":
        raise ValueError("Only markdown files are rendered")

    content = target.read_text(encoding="utf-8")
    html = markdown.markdown(content, extensions=MD_EXTENSIONS)
    return target.name, html
