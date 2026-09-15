"""Join shipped audio identifiers to the media they reach through the HIRC graph.

This is the first link in the audio chain that carries a *name*, so it is also the
one that most needs its evidence stated plainly. Every step is exact:

1. ``global-metadata.dat`` ``stringLiteral`` rows are exact ``<byteLength,
   dataIndex>`` pairs over exact bytes, so an audio-like literal is a string the
   shipped managed code actually contains.
2. Its FNV-1 hash over UTF-16 code units is compared to HIRC object identities.
   Every current match lands on a numeric type ``0x04`` object and on no other
   type, which is what identifies that type as the object managed code addresses
   by name. The gate refuses to publish if a match ever lands elsewhere, because
   that would dissolve the identification rather than weaken it.
3. From there the walk uses only reference vectors whose whole-corpus resolution
   is already gated, plus the type ``0x03`` target word, which is *not* gated and
   is therefore reported separately rather than folded into the result.
4. A reached numeric type ``0x02`` object yields the source id inside its bounded
   14-byte prefix.

What this does **not** establish: that posting the identifier plays the media,
any ordering or selection among reached sources, audibility, or a name for any
object other than the type ``0x04`` entry point itself. The walk direction is the
physical one -- which object's body holds the value -- and nothing more.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from scripts.audio_semantics.identifiers import collect_metadata_audio_literals

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTER = ROOT / "reports/animestudio/vfs_understanding_latest.json"
DEFAULT_OUTPUT = ROOT / "reports/animestudio/hirc_named_reach_current_latest.json"
DEFAULT_CLI = ROOT / "tools/AnimeStudio/AnimeStudio.CLI/bin/Release/net9.0-windows/AnimeStudio.CLI.exe"
DEFAULT_TEMP_AUDIT = ROOT / "tmp/audio/hirc_named_reach/audio_audit.json"

FNV1_OFFSET_BASIS = 0x811C9DC5
FNV1_PRIME = 0x01000193
# The type that every current literal hash match lands on. Kept as a number: the
# identification is "managed code addresses this type by name", not a Wwise label.
NAMED_OBJECT_TYPE = 0x04


def fnv1_utf16(name: str) -> int:
    """FNV-1 over UTF-16 code units, matching the shipped AudioHashGenerator."""
    state = FNV1_OFFSET_BASIS
    for character in name:
        code_point = ord(character)
        if code_point < 0x10000:
            units: tuple[int, ...] = (code_point,)
        else:
            offset = code_point - 0x10000
            units = (0xD800 + (offset >> 10), 0xDC00 + (offset & 0x3FF))
        for unit in units:
            state = ((state * FNV1_PRIME) & 0xFFFFFFFF) ^ unit
    return state


def index_literals(literals: Iterable[str]) -> dict[int, set[str]]:
    index: dict[int, set[str]] = defaultdict(set)
    for name in literals:
        index[fnv1_utf16(name)].add(name)
    return index


def named_type_share(type_counts: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """How much of the corpus the named type occupies, from the reader's histogram.

    This is the number the identification rests on: if the named type is a small
    share of all objects, a coincidental hash would usually land somewhere else.
    It is measured here rather than asserted in prose.
    """
    totals: Counter[str] = Counter()
    for counts in type_counts:
        if not isinstance(counts, dict):
            raise ValueError("HIRC object type histogram is not an object")
        for key, count in counts.items():
            name = str(key)
            if re.fullmatch(r"0x[0-9A-Fa-f]{2}", name) is None:
                raise ValueError(f"HIRC object type key is not numeric: {name!r}")
            value = int(count)
            if value < 0:
                raise ValueError(f"HIRC object type count is negative: {name}")
            totals[name] += value
    objects = sum(totals.values())
    if objects <= 0:
        raise ValueError("HIRC object type histogram is empty")
    named = totals.get(f"{NAMED_OBJECT_TYPE:#04x}", 0)
    if named <= 0:
        raise ValueError("the named object type does not occur in the corpus")
    return {
        "hircObjects": objects,
        "namedTypeObjects": named,
        "namedTypeSharePercent": round(100.0 * named / objects, 4),
    }


def media_ids_from_audit(audit: dict[str, Any]) -> set[int]:
    """Every media id the corpus declares, unioned across packages.

    A bank's media usually lives in a different package, so this has to be a union;
    joining inside one package answers a question nobody asked.
    """
    media: set[int] = set()
    for row in audit.get("rows", []):
        if row.get("status") != "verified":
            continue
        package = row.get("package")
        if not isinstance(package, dict):
            continue
        join = package.get("hircMediaJoin")
        if not isinstance(join, dict):
            continue
        ids = join.get("mediaIds")
        if not isinstance(ids, list):
            raise ValueError("media join census has invalid mediaIds")
        media.update(int(value) for value in ids)
    return media


def summarise(census_rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate the reader's per-package named-reach census."""
    totals: Counter[str] = Counter()
    matches: Counter[str] = Counter()
    reached_by_identity: dict[str, int] = {}
    reached_ids: dict[str, set[int]] = {}
    scalar_fields = (
        "matchedObjects",
        "matchedNamedType",
        "reachingASource",
        "reachingNoSource",
        "reachedSourceIds",
        "walkEdgesLeavingTheBank",
    )
    for census in census_rows:
        if not isinstance(census, dict):
            raise ValueError("named-reach census row is not an object")
        for field in scalar_fields:
            try:
                value = int(census[field])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"named-reach census has invalid {field}") from exc
            if value < 0:
                raise ValueError(f"named-reach census has negative {field}")
            totals[field] += value
        raw_matches = census.get("matchesByObjectType")
        if not isinstance(raw_matches, dict):
            raise ValueError("named-reach census has invalid matchesByObjectType")
        for key, count in raw_matches.items():
            name = str(key)
            if re.fullmatch(r"type[0-9A-F]{2}", name) is None:
                raise ValueError(f"named-reach match key is not a numeric type: {name!r}")
            matches[name] += int(count)
        raw_list = census.get("reachedSourceIdListByIdentity")
        if not isinstance(raw_list, dict):
            raise ValueError("named-reach census has invalid reachedSourceIdListByIdentity")
        for key, values in raw_list.items():
            identity = str(key)
            if re.fullmatch(r"[0-9A-F]{8}", identity) is None:
                raise ValueError(f"named-reach identity is not a 32-bit hex id: {identity!r}")
            if not isinstance(values, list):
                raise ValueError(f"named-reach reached list is not a list: {identity}")
            reached_ids.setdefault(identity, set()).update(int(value) for value in values)

        raw_reach = census.get("reachedSourceIdsByIdentity")
        if not isinstance(raw_reach, dict):
            raise ValueError("named-reach census has invalid reachedSourceIdsByIdentity")
        for key, count in raw_reach.items():
            identity = str(key)
            if re.fullmatch(r"[0-9A-F]{8}", identity) is None:
                raise ValueError(f"named-reach identity is not a 32-bit hex id: {identity!r}")
            reached_by_identity[identity] = max(reached_by_identity.get(identity, 0), int(count))
    return {
        "literalHashMatchesByObjectType": dict(sorted(matches.items())),
        "namedObjectInstances": int(totals["matchedNamedType"]),
        "matchedObjects": int(totals["matchedObjects"]),
        "namedObjectsReachingASource": int(totals["reachingASource"]),
        "namedObjectsReachingNoSource": int(totals["reachingNoSource"]),
        "reachedSourceIdTotal": int(totals["reachedSourceIds"]),
        "walkEdgesLeavingTheBank": int(totals["walkEdgesLeavingTheBank"]),
        "reachedSourceIdsByIdentity": dict(sorted(reached_by_identity.items())),
        "reachedSourceIdListByIdentity": {
            identity: sorted(values) for identity, values in sorted(reached_ids.items())
        },
    }


def check_identification(summary: dict[str, Any]) -> list[str]:
    """Return the reasons this join may not be published, if any."""
    problems: list[str] = []
    matches = summary["literalHashMatchesByObjectType"]
    named_key = f"type{NAMED_OBJECT_TYPE:02X}"
    stray = {key: count for key, count in matches.items() if key != named_key}
    if stray:
        problems.append(
            "a shipped audio literal hashes to an object that is not numeric type "
            f"{NAMED_OBJECT_TYPE:#04x}, which dissolves the identification: {stray}"
        )
    if not matches.get(named_key):
        problems.append("no shipped audio literal matched any object identity")
    if summary["namedObjectInstances"] != matches.get(named_key, 0):
        problems.append("named object instances disagree with the literal hash matches")
    if summary["matchedObjects"] != sum(matches.values()):
        problems.append("matched objects disagree with the per-type match totals")
    if summary["namedObjectsReachingASource"] + summary["namedObjectsReachingNoSource"] != summary[
        "namedObjectInstances"
    ]:
        problems.append("named object reach outcomes do not partition their instances")
    # One identity may occur in several banks, so identities are at most instances.
    # More identities than instances would mean the reader keyed a row it never matched.
    listed = summary.get("reachedSourceIdListByIdentity") or {}
    if set(listed) != set(summary["reachedSourceIdsByIdentity"]):
        problems.append("the reached-id lists and the reached counts cover different identities")
    for identity, values in listed.items():
        if len(values) < summary["reachedSourceIdsByIdentity"].get(identity, 0):
            problems.append(f"identity {identity} lists fewer source ids than it counted")
    identities = len(summary["reachedSourceIdsByIdentity"])
    if identities > summary["namedObjectInstances"]:
        problems.append(
            f"more named identities ({identities}) than matched instances "
            f"({summary['namedObjectInstances']})"
        )
    if summary["namedObjectInstances"] and not identities:
        problems.append("named objects matched but no identity was recorded")
    return problems


def markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    match_rows = "\n".join(
        f"| `{key}` | {count:,} |"
        for key, count in summary["literalHashMatchesByObjectType"].items()
    ) or "| _none_ | 0 |"
    total_matches = sum(summary["literalHashMatchesByObjectType"].values())
    expected_stray = total_matches * (1.0 - summary["namedTypeSharePercent"] / 100.0)
    named = report["identifiers"]
    top = sorted(named.items(), key=lambda item: (-item[1], item[0]))[:20]
    reach_rows = "\n".join(f"| `{name}` | {count:,} |" for name, count in top) or "| _none_ | 0 |"
    return "\n".join(
        [
            "# Shipped audio identifiers and the media they reach",
            "",
            f"- Status: `{report['status']}`.",
            f"- Current VFS input set: `{report['inputSetSha256']}`.",
            f"- IL2CPP metadata: `{report['metadata']['path']}` (SHA-256 `{report['metadata']['sha256']}`).",
            f"- Audio-like managed string literals recovered: {report['metadata']['audioLiteralCount']:,}.",
            f"- Literal hash matches: {sum(summary['literalHashMatchesByObjectType'].values()):,}, all on numeric type `{NAMED_OBJECT_TYPE:#04x}`.",
            f"- Distinct named identifiers: {len(report['identifiers']):,}; reaching at least one source: {sum(1 for count in report['identifiers'].values() if count):,}.",
            f"- Reaching at least one media file this corpus ships: {report['mediaSummary']['identifiersReachingMedia']:,}; distinct media files reached: {report['mediaSummary']['distinctMediaReached']:,}.",
            f"- Reached source ids that name no shipped media: {report['mediaSummary']['reachedIdsNamingNoMedia']:,} (the plug-in partition says some never do).",
            f"- Named object instances: {summary['namedObjectInstances']:,}; reaching a source: {summary['namedObjectsReachingASource']:,}; reaching none: {summary['namedObjectsReachingNoSource']:,}.",
            f"- Walk edges leaving the bank and therefore not followed: {summary['walkEdgesLeavingTheBank']:,}.",
            "",
            "## Literal hash matches by numeric object type",
            "",
            "| Object type | Matches |",
            "|---|---:|",
            match_rows,
            "",
            "This table is the identification. Numeric type "
            f"`{NAMED_OBJECT_TYPE:#04x}` holds {summary['namedTypeObjects']:,} of the "
            f"{summary['hircObjects']:,} HIRC objects in this corpus, or "
            f"{summary['namedTypeSharePercent']:.2f} percent, so if a hash match were "
            f"coincidental about {expected_stray:,.0f} of the {total_matches:,} matches would "
            "have landed on some other type. None did. Every match landing on one type is what "
            "establishes that managed code addresses that type by name. A single match "
            "elsewhere would dissolve the identification, so the gate refuses to publish in "
            "that case rather than reporting a rate.",
            "",
            "## Identifiers reaching the most distinct source ids",
            "",
            "| Identifier | Source ids reached |",
            "|---|---:|",
            reach_rows,
            "",
            "The walk uses the reference vectors whose whole-corpus resolution is already "
            "gated, plus the numeric type `0x03` target word, which is **not** gated: only "
            "about three quarters of those words name an object in their own bank. Edges that "
            "leave the bank are counted above and not followed, which is the main reason a "
            "named identifier can reach no source here.",
            "",
            "The chain is now complete end to end: a shipped identifier hashes to a numeric "
            "type `0x04` object, reference vectors lead from it to numeric type `0x02` "
            "objects, and their source ids are joined against the media this corpus ships. "
            "Each link is gated on its own terms. A reached id that names no media is "
            "reported rather than dropped, because the plug-in partition establishes that "
            "some source ids never name shipped media.",
            "",
            "A reached source id is the value inside the bounded 14-byte prefix of a numeric "
            "type `0x02` object. This report does not establish that posting the identifier "
            "plays that media, nor any ordering or selection among reached sources, nor "
            "audibility, nor a name for any object other than the type "
            f"`{NAMED_OBJECT_TYPE:#04x}` entry point itself.",
            "",
        ]
    )


def run(
    *,
    expected_input_set_sha256: str,
    outer_path: Path,
    metadata_path: Path,
    cli_path: Path,
    intermediate_path: Path,
    output_json: Path,
    output_markdown: Path | None,
) -> dict[str, Any]:
    outer = json.loads(outer_path.read_text(encoding="utf-8"))
    input_set = str(outer.get("inputSetSha256") or "").upper()
    if input_set != expected_input_set_sha256.upper():
        raise ValueError(
            "outer VFS input-set mismatch: "
            f"expected={expected_input_set_sha256.upper()} actual={input_set}"
        )
    if not metadata_path.is_file():
        raise ValueError(f"IL2CPP metadata is missing: {metadata_path}")
    metadata_bytes = metadata_path.read_bytes()
    metadata_sha = hashlib.sha256(metadata_bytes).hexdigest().upper()
    literals = collect_metadata_audio_literals(metadata_path)
    if not literals:
        raise ValueError(f"no audio-like managed string literals in {metadata_path}")
    literal_index = index_literals(literals)

    intermediate_path.parent.mkdir(parents=True, exist_ok=True)
    hash_file = intermediate_path.with_suffix(".hashes.txt")
    hash_file.write_text(
        "".join(f"{value:08X}" + chr(10) for value in sorted(literal_index)), encoding="utf-8"
    )
    command = [
        str(cli_path),
        "audio-audit",
        "--streaming-assets",
        str(outer["primaryAssets"]),
        "--fallback-assets",
        str(outer["fallbackAssets"]),
        "--hirc-only",
        "--named-hash-file",
        str(hash_file),
        "--output",
        str(intermediate_path),
    ]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise ValueError(
            f"AnimeStudio audio-audit failed: exit={result.returncode} stderr={result.stderr[-800:]}"
        )
    audit = json.loads(intermediate_path.read_text(encoding="utf-8"))
    rows = [row for row in audit.get("rows", []) if row.get("status") == "verified"]
    summary = summarise(
        row["package"]["hircNamedReachCensus"]
        for row in rows
        if isinstance(row.get("package"), dict)
    )
    summary.update(
        named_type_share(
            row["package"]["hircObjectTypeCounts"]
            for row in rows
            if isinstance(row.get("package"), dict)
        )
    )
    problems = check_identification(summary)
    media = media_ids_from_audit(audit)
    if not media:
        problems.append("the audit declares no media ids, so the media join cannot be checked")

    # Map identities back to the literals that produced them. A hash collision between
    # two shipped literals would make the name ambiguous, so it is reported, not picked.
    identifiers: dict[str, int] = {}
    media_reached: dict[str, list[int]] = {}
    unmatched_reached: dict[str, list[int]] = {}
    ambiguous: dict[str, list[str]] = {}
    for identity, count in summary["reachedSourceIdsByIdentity"].items():
        names = sorted(literal_index.get(int(identity, 16), ()))
        if not names:
            problems.append(f"reader reported an identity no literal produced: {identity}")
            continue
        if len(names) > 1:
            # Two shipped literals hashing alike means the name is not determined.
            # Report it and publish nothing for it rather than picking one.
            ambiguous[identity] = names
            problems.append(
                f"identity {identity} is claimed by more than one shipped literal: {names}"
            )
            continue
        identifiers[names[0]] = count
        reached = set(summary["reachedSourceIdListByIdentity"].get(identity, ()))
        media_reached[names[0]] = sorted(reached & media)
        unmatched = reached - media
        if unmatched:
            # A reached source id that names no shipped media is a real outcome --
            # the plug-in partition says some never do -- so it is reported, not
            # treated as an error, and never silently dropped.
            unmatched_reached[names[0]] = sorted(unmatched)

    report = {
        "format": "animestudio-wwise-hirc-named-reach-audit",
        "schemaVersion": 1,
        "generatedUtc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "complete" if not problems else "incomplete",
        "closureEnforced": True,
        "inputSetSha256": input_set,
        "metadata": {
            "path": str(metadata_path),
            "sha256": metadata_sha,
            "audioLiteralCount": len(literals),
            "distinctLiteralHashes": len(literal_index),
            "ambiguousIdentities": ambiguous,
        },
        "audioAudit": {
            "tool": str(cli_path),
            "toolSha256": hashlib.sha256(cli_path.read_bytes()).hexdigest().upper(),
            "intermediatePath": str(intermediate_path),
        },
        "summary": summary,
        "identifiers": identifiers,
        "mediaReachedByIdentifier": media_reached,
        "reachedSourceIdsNamingNoMedia": unmatched_reached,
        "mediaSummary": {
            "declaredMediaIds": len(media),
            "identifiersReachingMedia": sum(1 for v in media_reached.values() if v),
            "distinctMediaReached": len({m for v in media_reached.values() for m in v}),
            "reachedIdsNamingNoMedia": len({m for v in unmatched_reached.values() for m in v}),
        },
        "problems": problems,
        "evidenceBoundary": {
            "layer": 5,
            "claim": (
                "numeric HIRC type 0x04 is the object that shipped managed code addresses "
                "by name, and a named object reaches these type 0x02 source ids through "
                "reference vectors alone"
            ),
            "semanticStatus": "direct",
            "nonClaims": [
                "that posting the identifier plays the reached media",
                "ordering, selection or mixing among the reached sources",
                "audibility, or that the media is ever decoded at runtime",
                "a name for any object other than the type 0x04 entry point",
                "that an edge leaving the bank resolves to anything in particular",
            ],
        },
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8")
    output_markdown = output_markdown or output_json.with_suffix(".md")
    output_markdown.write_text(markdown(report), encoding="utf-8")
    if problems:
        raise ValueError("; ".join(problems))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--outer-report", type=Path, default=DEFAULT_OUTER)
    parser.add_argument("--metadata", type=Path, default=None)
    parser.add_argument("--animestudio-cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--intermediate", type=Path, default=DEFAULT_TEMP_AUDIT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--output-markdown", type=Path, default=None)
    args = parser.parse_args(argv)
    metadata = args.metadata
    if metadata is None:
        outer = json.loads(args.outer_report.read_text(encoding="utf-8"))
        metadata = Path(outer["primaryAssets"]).parent / "il2cpp_data/Metadata/global-metadata.dat"
    try:
        report = run(
            expected_input_set_sha256=args.expected_input_set_sha256,
            outer_path=args.outer_report,
            metadata_path=metadata,
            cli_path=args.animestudio_cli,
            intermediate_path=args.intermediate,
            output_json=args.output_json,
            output_markdown=args.output_markdown,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"HIRC named-reach audit failed: {exc}", file=sys.stderr)
        return 1
    summary = report["summary"]
    print(
        "HIRC named reach: "
        f"{summary['namedObjectInstances']:,} identities matched, all on numeric type 0x04; "
        f"{summary['namedObjectsReachingASource']:,} reach a source id "
        f"({summary['reachedSourceIdTotal']:,} in total); "
        f"inputSetSha256={report['inputSetSha256']}"
    )
    print(f"Named reach report: {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
