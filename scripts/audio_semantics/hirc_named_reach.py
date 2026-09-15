"""Join shipped audio identifiers to the media they reach through the HIRC graph.

This is the first link in the audio chain that carries a *name*, so it is also the
one that most needs its evidence stated plainly. Every step is exact:

1. ``global-metadata.dat`` ``stringLiteral`` rows are exact ``<byteLength,
   dataIndex>`` pairs over exact bytes, so an audio-like literal is a string the
   shipped managed code actually contains.
2. Its hash under the shipped ``AudioHashGenerator`` -- FNV-1 over UTF-16 code
   units, folding ASCII ``A``-``Z`` before each XOR -- is compared to HIRC object
   identities. The folding is not cosmetic: 46 shipped literals contain capitals,
   and hashing them unfolded loses every one of their names.
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

from scripts.audio_semantics.identifiers import (
    audio_hash_generator_compute,
    collect_metadata_audio_literals,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTER = ROOT / "reports/animestudio/vfs_understanding_latest.json"
DEFAULT_OUTPUT = ROOT / "reports/animestudio/hirc_named_reach_current_latest.json"
DEFAULT_CLI = ROOT / "tools/AnimeStudio/AnimeStudio.CLI/bin/Release/net9.0-windows/AnimeStudio.CLI.exe"
DEFAULT_TEMP_AUDIT = ROOT / "tmp/audio/hirc_named_reach/audio_audit.json"

# The type that every current literal hash match lands on. Kept as a number: the
# identification is "managed code addresses this type by name", not a Wwise label.
NAMED_OBJECT_TYPE = 0x04


def index_literals(literals: Iterable[str]) -> dict[int, set[str]]:
    index: dict[int, set[str]] = defaultdict(set)
    for name in literals:
        index[audio_hash_generator_compute(name)].add(name)
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

# A general identifier shape. The narrow prefix list that drives the type 0x04
# claim exists because unfiltered literals resolve generic words by coincidence;
# this keeps a structural filter but drops the vocabulary, so the coincidence rate
# can be measured instead of assumed.
BROAD_IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_./+:-]{5,}$")
# A type is only claimed as named when its matches exceed chance by this factor.
# The id space is 32 bits, so chance is computable rather than a matter of taste.
NAMED_TYPE_MINIMUM_RATIO = 100.0
HASH_SPACE = float(1 << 32)


def source_values_from_audit(audit: dict[str, Any]) -> dict[str, dict[str, set[int]]]:
    """Distinct source-record values per type, at the id field and either side of it.

    Unioned across packages for the same reason the media are: a source record names
    media that a different package declares, so the join has to cross the file
    boundary. Joining inside one package scores 12 of 147,262 and answers nothing.
    """
    out: dict[str, dict[str, set[int]]] = {}
    keys = ("idValuesByType", "idValuesBeforeByType", "idValuesAfterByType")
    for row in audit.get("rows", []):
        if row.get("status") != "verified":
            continue
        package = row.get("package")
        if not isinstance(package, dict):
            continue
        # The census is published inside the media-join block, next to the media ids
        # it has to be joined against. Read it from there rather than moving it: the
        # two belong together and the audit shape is already committed.
        join = package.get("hircMediaJoin")
        census = join.get("hircSourceRecords") if isinstance(join, dict) else None
        if not isinstance(census, dict):
            continue
        for key in keys:
            block = census.get(key)
            if block is None:
                continue
            if not isinstance(block, dict):
                raise ValueError(f"source record census has invalid {key}")
            for type_key, values in block.items():
                if not isinstance(values, list):
                    raise ValueError(f"source record census has invalid {key}")
                out.setdefault(str(type_key), {}).setdefault(key, set()).update(
                    int(value) for value in values)
    return out


def media_attribution(
    media: set[int], by_type: dict[str, dict[str, set[int]]]
) -> dict[str, Any]:
    """How much of the shipped media some source record accounts for.

    The id field is scored against the words one byte either side, over the same
    pooled media. A field that resolves at one offset and nowhere near it is located;
    a field that resolves at several is a coincidence with a wide net.
    """
    owned: set[int] = set()
    per_type: dict[str, int] = {}
    controls = {"idValuesBeforeByType": 0, "idValuesAfterByType": 0}
    for type_key, blocks in sorted(by_type.items()):
        hit = blocks.get("idValuesByType", set()) & media
        per_type[type_key] = len(hit)
        owned |= hit
        for control in controls:
            controls[control] += len(blocks.get(control, set()) & media)
    return {
        "mediaIdsDeclared": len(media),
        "mediaIdsNamedBySomeRecord": len(owned),
        "mediaIdsNamedByNoRecord": len(media - owned),
        "mediaIdsNamedByType": per_type,
        "controlMediaIdsNamedByNeighbouringWords": dict(sorted(controls.items())),
    }


def media_attribution_is_discriminated(attribution: dict[str, Any]) -> bool:
    """The attribution is a located field, not a wide net, and it covers the corpus.

    Two things must hold and they guard different failures.

    The id field must account for essentially all of the shipped media. It does:
    61,325 of 61,333, with 60,049 named by numeric type 0x02 and 1,279 by 0x0B, and
    only 8 named by no record at all.

    And the words one byte either side must not. If a shifted read resolved to media
    at a comparable rate the join would be telling us that 32-bit values in this
    region often look like media ids, which is a fact about the id space rather than
    about the field.
    """
    if not isinstance(attribution, dict):
        return False
    declared = int(attribution.get("mediaIdsDeclared") or 0)
    named = int(attribution.get("mediaIdsNamedBySomeRecord") or 0)
    if declared <= 0 or named <= 0:
        return False
    if named * 100 < declared * 99:
        return False
    by_type = attribution.get("mediaIdsNamedByType")
    if not isinstance(by_type, dict) or len(by_type) < 2:
        # One contributing type cannot show that the record is shared, which is the
        # whole content of this census.
        return False
    if any(int(value) <= 0 for value in by_type.values()):
        return False
    controls = attribution.get("controlMediaIdsNamedByNeighbouringWords")
    if not isinstance(controls, dict) or not controls:
        return False
    return all(int(value) * 100 < named for value in controls.values())


MUSIC_REACH_SCALARS = (
    "musicObjects", "entryEdges", "banksWithAnEntry", "reachedObjects",
    "reachedSourceIdCount", "edges", "edgeSources", "rootsWithNoIncomingEdge",
    "entriesWithOutgoingEdges", "entriesThatAreRoots",
)


def music_reach_from_audit(audit: dict[str, Any]) -> dict[str, Any]:
    """Sum the music-reach census over every verified package."""
    totals = {key: 0 for key in MUSIC_REACH_SCALARS}
    kinds: Counter[str] = Counter()
    roots: Counter[str] = Counter()
    reached: Counter[str] = Counter()
    for row in audit.get("rows", []):
        if row.get("status") != "verified":
            continue
        package = row.get("package")
        if not isinstance(package, dict):
            continue
        # Published inside the action-target block, because the only edges that enter
        # the music family are action target words and the two are read together.
        targets = package.get("hircType03Targets")
        census = targets.get("hircMusicReach") if isinstance(targets, dict) else None
        if census is None:
            continue
        if not isinstance(census, dict):
            raise ValueError("music reach census is not an object")
        for key in MUSIC_REACH_SCALARS:
            try:
                value = int(census[key])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"music reach census has invalid {key}") from exc
            if value < 0:
                raise ValueError(f"music reach census has negative {key}")
            totals[key] += value
        kinds.update(census.get("entryKinds") or {})
        roots.update(census.get("rootTypes") or {})
        reached.update(census.get("reachedTypes") or {})
    totals["entryKinds"] = dict(sorted(kinds.items()))
    totals["rootTypes"] = dict(sorted(roots.items()))
    totals["reachedTypes"] = dict(sorted(reached.items()))
    return totals


def the_music_family_is_not_entered_from_the_object_graph(
    reach: dict[str, Any]
) -> bool:
    """Nothing in the HIRC object graph reaches the music family's media.

    This is a negative result stated as a gate, so that the day it stops being true
    is a day something fires rather than a day nobody notices.

    The music types are their own component. The main reference graph's 230,247 edges
    carry no music type at either end; the parent field's 199,445 carry none either.
    The family has 11,656 objects and 7,305 downward edges of its own, so a walk
    inside it has plenty to follow -- that is what makes the next number meaningful
    rather than an artefact of an empty edge set.

    Entering it from outside there are **5** edges in the whole corpus, all of them an
    action target word landing on numeric type 0x0C. All 5 land on objects that are
    roots, none of the 5 has an outgoing edge, and together they reach **0** source
    ids. The family's 1,279 media are reached by nothing.

    The gate therefore asserts three things at once: the walk has edges to follow, the
    entry count is negligible against the family's size, and no media are reached. If
    a later reading finds the real entry point, `reachedSourceIdCount` becomes
    positive and this fails. **That failure is the good news** -- change this then,
    and not before.

    What it does not say: that music is unreachable at runtime. It says no relation
    this reader has resolved reaches it, which is a smaller claim and the only one
    the bytes support.
    """
    if not isinstance(reach, dict):
        return False
    objects = int(reach.get("musicObjects") or 0)
    edges = int(reach.get("edges") or 0)
    if objects <= 0 or edges <= 0:
        # An empty family, or one with no internal edges, cannot support the claim:
        # "nothing reaches it" would then be a statement about the walk.
        return False
    if int(reach.get("reachedSourceIdCount") or 0) != 0:
        return False
    return int(reach.get("entryEdges") or 0) * 1000 < objects


def broad_literals(metadata_path: Path) -> list[str]:
    """Identifier-shaped managed literals, without the audio prefix vocabulary."""
    from scripts.audio_semantics.identifiers import (  # noqa: PLC0415
        collect_metadata_literals_raw,
    )

    return [value for value in collect_metadata_literals_raw(metadata_path)
            if BROAD_IDENTIFIER_RE.fullmatch(value)]


def coincidence_table(
    matches_by_type: dict[str, int], populations: dict[str, int], literals: int
) -> dict[str, Any]:
    """Compare observed matches per numeric type against chance.

    With a 32-bit hash, a literal hits a given type's population by chance with
    probability population / 2**32, so the expected count is literals * that. A
    type whose observed count sits at its expectation is noise no matter how
    meaningful its names look; one that sits orders of magnitude above it is not.
    """
    rows: dict[str, Any] = {}
    claimed: list[str] = []
    coincidental: list[str] = []
    for type_key, population in sorted(populations.items()):
        observed = int(matches_by_type.get(type_key, 0))
        if not observed:
            continue
        expected = literals * population / HASH_SPACE
        ratio = observed / expected if expected > 0 else float("inf")
        rows[type_key] = {
            "observed": observed,
            "population": population,
            "expectedByChance": round(expected, 6),
            "ratio": round(ratio, 1) if ratio != float("inf") else None,
        }
        if ratio >= NAMED_TYPE_MINIMUM_RATIO:
            claimed.append(type_key)
        else:
            coincidental.append(type_key)
    return {
        "literals": literals,
        "byType": rows,
        "typesNamedAboveChance": claimed,
        "typesIndistinguishableFromChance": coincidental,
        "minimumRatio": NAMED_TYPE_MINIMUM_RATIO,
    }


def broad_naming_is_discriminated(table: dict[str, Any]) -> bool:
    """At least one type must clear the bar and the rule must be applied to all.

    If nothing clears it the section claims nothing; if every type clears it the
    bar is not doing any work and the discrimination is not being tested.
    """
    rows = table.get("byType") or {}
    named = table.get("typesNamedAboveChance") or []
    if not rows or not named:
        return False
    for type_key, row in rows.items():
        ratio = row.get("ratio")
        above = ratio is None or ratio >= table["minimumRatio"]
        if above != (type_key in named):
            return False
    return True



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
        "walkEdgesLeavingThePackage",
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
        "walkEdgesLeavingThePackage": int(totals["walkEdgesLeavingThePackage"]),
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
            f"- Walk edges leaving the package and therefore not followed: {summary['walkEdgesLeavingThePackage']:,}.",
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
            "that case rather than reporting a rate. Read the scope literally: this is "
            "about these literals, not the format. The broad pass below names numeric "
            "types `0x08` and `0x15` from other literals, so `0x04` is not the only type "
            "addressed by name.",
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
            "## Naming beyond type `0x04`, judged against chance",
            "",
            "| Numeric type | Population | Matches | Expected by chance | Ratio |",
            "|---|---:|---:|---:|---:|",
            *(
                f"| `{name}` | {row['population']:,} | {row['observed']:,} | "
                f"{row['expectedByChance']:.4g} | {row['ratio']:,.0f}x |"
                for name, row in sorted(
                    report["broadNaming"]["byType"].items(),
                    key=lambda item: -(item[1]["ratio"] or 0),
                )
            ),
            "",
            "The prefix vocabulary that drives the claim above exists because unfiltered "
            "literals resolve generic words by coincidence. That reasoning is right but "
            "cannot be checked from inside the filter, so this pass drops the vocabulary, "
            "keeps only a structural identifier shape, and **measures** the coincidence "
            "rate instead of assuming it. The hash is 32 bits, so a literal hits a type's "
            "population by chance with probability population / 2^32 -- the expectation "
            "above is computed, not estimated.",
            "",
            f"Types named above chance: {', '.join('`' + t + '`' for t in report['broadNaming']['typesNamedAboveChance'])}. "
            f"Indistinguishable from chance and therefore **not** claimed: "
            f"{', '.join('`' + t + '`' for t in report['broadNaming']['typesIndistinguishableFromChance']) or 'none'}. "
            f"The bar is {report['broadNaming']['minimumRatio']:.0f} times the expectation, "
            "and the gate checks that the rule was applied to every type rather than "
            "only to the convenient ones.",
            "",
            f"Populations the literals never name at all: "
            f"{', '.join('`' + t + '`' for t in report['broadNaming'].get('populationsWithNoMatch') or []) or 'none'}. "
            "Those zeros are measured, not assumed, and they say something the hits do "
            "not: the ids of those types are **not** hashes of any string this build "
            "ships, so their anonymity is a property of the data rather than a gap in "
            "this search. Media ids are the notable one -- 61,333 of them, an expectation "
            "of 0.36 by chance, and nothing. The identifier chain therefore ends at an "
            "opaque media id and does not continue into a filename.",
            "",
            "Bank ids are a separate population from HIRC objects and are judged by the "
            "same arithmetic. They are named, and none of the named bank ids is also an "
            "object id, so bank names and event names are different strings rather than "
            "one name reused.",
            "",
            "Type `0x02` is the case that makes the test worth having. Its two matches "
            "look like names until the expectation is computed: with 142,815 objects it "
            "sits at its own coincidence rate, so it is reported and not claimed. Names "
            "that merely read plausibly are exactly what this rejects.",
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
    source_values = source_values_from_audit(audit)
    attribution = media_attribution(media, source_values)
    music_reach = music_reach_from_audit(audit)
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

    # A second pass with a broader, purely structural literal filter. Kept separate
    # from the claim above so that widening the filter cannot weaken it.
    from scripts.audio_semantics.identifiers import audio_hash_generator_compute

    wide = broad_literals(metadata_path)
    wide_index: dict[int, set[str]] = {}
    for value in wide:
        wide_index.setdefault(audio_hash_generator_compute(value), set()).add(value)
    wide_hash_file = intermediate_path.with_suffix(".broad-hashes.txt")
    wide_hash_file.write_text(
        "".join(f"{value:08X}" + chr(10) for value in sorted(wide_index)), encoding="utf-8"
    )
    wide_audit_path = intermediate_path.with_suffix(".broad.json")
    wide_command = list(command)
    wide_command[wide_command.index("--named-hash-file") + 1] = str(wide_hash_file)
    wide_command[wide_command.index("--output") + 1] = str(wide_audit_path)
    wide_result = subprocess.run(wide_command, cwd=ROOT, capture_output=True, text=True, check=False)
    if wide_result.returncode != 0:
        raise ValueError(
            f"AnimeStudio broad audio-audit failed: exit={wide_result.returncode} "
            f"stderr={wide_result.stderr[-800:]}"
        )
    wide_audit = json.loads(wide_audit_path.read_text(encoding="utf-8"))
    wide_rows = [row for row in wide_audit.get("rows", []) if row.get("status") == "verified"]
    wide_matches: dict[str, int] = {}
    populations: dict[str, int] = {}
    for row in wide_rows:
        package = row.get("package")
        if not isinstance(package, dict):
            continue
        for key, count in (package["hircNamedReachCensus"]["matchesByObjectType"] or {}).items():
            wide_matches[str(key)] = wide_matches.get(str(key), 0) + int(count)
        for key, count in (package.get("hircObjectTypeCounts") or {}).items():
            name = "type" + str(key)[2:].upper()
            populations[name] = populations.get(name, 0) + int(count)
    # Bank ids and media ids are separate id populations; the same arithmetic
    # judges them, so they join the table rather than getting a special case.
    banks_matched = banks_seen = media_matched = media_seen = 0
    for row in wide_rows:
        package = row.get("package")
        if not isinstance(package, dict):
            continue
        census = package["hircNamedReachCensus"]
        banks_matched += int(census.get("banksMatched") or 0)
        banks_seen += int(census.get("banksSeen") or 0)
        media_matched += int(census.get("mediaMatched") or 0)
        media_seen += int(census.get("mediaSeen") or 0)
    if banks_seen:
        wide_matches["bankId"] = banks_matched
        populations["bankId"] = banks_seen
    if media_seen:
        wide_matches["mediaId"] = media_matched
        populations["mediaId"] = media_seen
    table = coincidence_table(wide_matches, populations, len(wide))
    # A population with no matches is absent from the table, which would hide a
    # meaningful zero. Media ids matching nothing is a result, so state it.
    table["populationsWithNoMatch"] = sorted(
        name for name, size in populations.items() if size and not wide_matches.get(name)
    )
    if not the_music_family_is_not_entered_from_the_object_graph(music_reach):
        problems.append(
            "the music family's isolation no longer holds, which means either the "
            "walk lost its edges or an entry point has finally been found: "
            f"objects={music_reach.get('musicObjects')} "
            f"edges={music_reach.get('edges')} "
            f"entryEdges={music_reach.get('entryEdges')} "
            f"reachedSourceIds={music_reach.get('reachedSourceIdCount')}"
        )
    if not media_attribution_is_discriminated(attribution):
        problems.append(
            "the media attribution is not discriminated: "
            f"named={attribution['mediaIdsNamedBySomeRecord']} of "
            f"{attribution['mediaIdsDeclared']} "
            f"byType={attribution['mediaIdsNamedByType']} "
            f"controls={attribution['controlMediaIdsNamedByNeighbouringWords']}"
        )
    if not broad_naming_is_discriminated(table):
        problems.append(
            "the broad naming pass does not discriminate: "
            f"named={table['typesNamedAboveChance']} "
            f"coincidental={table['typesIndistinguishableFromChance']}"
        )

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
        "broadNaming": table,
        "mediaAttribution": attribution,
        "musicReach": music_reach,
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
