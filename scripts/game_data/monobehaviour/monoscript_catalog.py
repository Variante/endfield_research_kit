"""The authoritative script-name table behind the MonoBehaviour corpus.

A MonoBehaviour's `m_Script` is a PPtr into a MonoScript object, and that
object carries the class name, namespace and assembly outright. The WebUI
export scope never writes MonoScript, so the exported corpus resolves only to
an anonymous `scriptPathId` -- but the object itself is present in the
installed client and can be read directly.

In this client the whole corpus points at **one** MonoScript container. That is
what makes the table tractable: a single CAB supplies the names for every
exported MonoBehaviour, so understanding the corpus does not require walking
the bundle tree.

This module parses a MonoScript dump directory into a `pathId -> class`
catalog. It neither locates the container nor runs the exporter: resolving a
CAB name to its chunk and offset goes through the CABMap reader, and producing
the dump is an AnimeStudio invocation with its own scheduling and output rules.
Both steps are operator commands recorded in `scripts/README.md`, and the dump
they produce is disposable. This module reads whatever dump it is pointed at
and fails closed on one it cannot account for.

A catalog entry is an exact identity for the *script*. It says what class a
MonoBehaviour instantiates, not what that instance owns, when it runs, or
whether anything reaches it at runtime.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.monoscript-catalog.v1"

# AnimeStudio's Dump writer emits one tab-indented ``string <field> = "value"``
# line per serialized string at depth one.
FIELD_LINE = re.compile(r'^\tstring (?P<field>m_\w+) = "(?P<value>.*)"\s*$', re.M)
# It names each file ``<objectName>_p<PathID as 16 hex digits>.txt``.
DUMP_FILENAME = re.compile(r"^(?P<name>.*)_p(?P<path_id>[0-9A-Fa-f]{16})\.txt$")

DEFAULT_DUMP_ROOT = REPO_ROOT / "tmp" / "game_data" / "monoscript" / "MonoScript"


class CatalogError(RuntimeError):
    """The MonoScript catalog could not be built from what was supplied."""


@dataclass(frozen=True)
class ScriptName:
    path_id: int
    class_name: str
    namespace: str
    assembly: str

    @property
    def full_name(self) -> str:
        return f"{self.namespace}.{self.class_name}" if self.namespace else self.class_name

    def row(self) -> dict[str, Any]:
        return {
            "pathId": self.path_id,
            "fullName": self.full_name,
            "className": self.class_name,
            "namespace": self.namespace,
            "assembly": self.assembly,
        }


def signed_path_id(unsigned: int) -> int:
    """Unity PathIDs are signed; the dump filename spells them unsigned."""

    return unsigned - (1 << 64) if unsigned >= (1 << 63) else unsigned


def parse_dump_file(path: Path) -> ScriptName | None:
    """Read one MonoScript dump into a catalog entry, or reject it.

    The PathID comes from the filename and the names from the body. A file that
    supplies neither a PathID nor a class name is rejected rather than recorded
    with a hole, because a partial identity is what a later join would silently
    trust.
    """

    match = DUMP_FILENAME.match(path.name)
    if match is None:
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    fields = {found.group("field"): found.group("value") for found in FIELD_LINE.finditer(text)}
    class_name = fields.get("m_ClassName") or ""
    if not class_name:
        return None
    return ScriptName(
        path_id=signed_path_id(int(match.group("path_id"), 16)),
        class_name=class_name,
        namespace=fields.get("m_Namespace") or "",
        assembly=fields.get("m_AssemblyName") or "",
    )


def load_catalog(dump_root: Path = DEFAULT_DUMP_ROOT) -> dict[int, ScriptName]:
    """Parse a MonoScript dump directory into a ``pathId -> class`` table."""

    root = Path(dump_root)
    if not root.is_dir():
        raise CatalogError(f"MonoScript dump directory not found: {root}")
    catalog: dict[int, ScriptName] = {}
    collisions: list[tuple[int, str, str]] = []
    rejected = 0
    for path in sorted(root.glob("*.txt")):
        entry = parse_dump_file(path)
        if entry is None:
            rejected += 1
            continue
        existing = catalog.get(entry.path_id)
        if existing is not None and existing.full_name != entry.full_name:
            collisions.append((entry.path_id, existing.full_name, entry.full_name))
            continue
        catalog[entry.path_id] = entry
    if collisions:
        # One PathID naming two classes means the dump mixes containers, which
        # would make every downstream name a coin flip.
        detail = ", ".join(f"{pid}: {a} vs {b}" for pid, a, b in collisions[:5])
        raise CatalogError(
            f"{len(collisions)} PathID collisions in {root}; a catalog must come "
            f"from one container set ({detail})"
        )
    if not catalog:
        raise CatalogError(f"no MonoScript dumps parsed from {root} ({rejected} rejected)")
    return catalog


def build_report(dump_root: Path = DEFAULT_DUMP_ROOT) -> dict[str, Any]:
    catalog = load_catalog(dump_root)
    by_assembly: dict[str, int] = {}
    for entry in catalog.values():
        by_assembly[entry.assembly] = by_assembly.get(entry.assembly, 0) + 1
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "dumpRoot": str(dump_root),
        "summary": {
            "scripts": len(catalog),
            "distinctAssemblies": len(by_assembly),
            "byAssembly": dict(
                sorted(by_assembly.items(), key=lambda item: (-item[1], item[0]))
            ),
        },
        "scripts": [
            entry.row() for entry in sorted(catalog.values(), key=lambda row: row.full_name)
        ],
    }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Parse a MonoScript dump directory into the authoritative "
            "scriptPathId to managed class table."
        )
    )
    parser.add_argument("--dump-root", type=Path, default=DEFAULT_DUMP_ROOT)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)

    try:
        report = build_report(args.dump_root)
    except CatalogError as exc:
        print(f"MonoScript catalog unavailable: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered, encoding="utf-8")
        summary = report["summary"]
        print(
            f"catalogued {summary['scripts']} scripts across "
            f"{summary['distinctAssemblies']} assemblies -> {args.report}"
        )
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":  # pragma: no cover - documented entry point
    if not __package__:
        raise SystemExit("run as: python -m scripts.game_data.monobehaviour.monoscript_catalog")
    raise SystemExit(main())
