"""Recover hash-only Wwise Event names by grammar-directed preimage search.

Shipped bank Events carry only a uint32 ``AudioHashGenerator`` identity.  The
authored name lives in the Wwise project, which is not shipped: an exhaustive
sweep of the IL2CPP string-literal blob and of every metadata type/field name
resolves only a handful of the hash-only Events, so no observed-string source
can close the remaining set.

Recovered Event names are, however, strongly templated
(``au_eny_0094_hsfly_skill03_charge``).  This module mines that grammar from
the names already recovered by exact evidence, regenerates sibling names, and
keeps only candidates whose ``AudioHashGenerator`` hash equals a current
hash-only Event id.

A hash equality on a *generated* string is weaker than a hash equality on a
*shipped* string: a 32-bit space admits coincidental preimages in proportion to
the candidate count.  This module therefore never promotes an isolated hit.
Authored names come in complete sibling sets (every panel transition for one
character, every phase of one enemy skill), while a coincidental preimage is a
singleton, so a recovered name is promoted only when its head and its tail are
each shared with another recovered Event.  The residual expectation is reported
alongside the entries rather than hidden.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, Sequence


SCHEMA_VERSION = 1

# Names shorter than this cannot be split into a head and a tail that each
# carry meaning, so they yield no template.
MIN_TOKEN_COUNT = 3

# Templates are mined per naming family (``au_eny``, ``vo_narrating``, ...).
# Crossing heads and tails between families would mint names the sound
# designers never used and would inflate the candidate space for no yield.
FAMILY_TOKEN_COUNT = 2

# A single family whose head/tail cross-product exceeds this is skipped whole:
# candidate volume drives the coincidental-preimage expectation, and no
# observed family needs anywhere near this many candidates.
MAX_FAMILY_CANDIDATES = 8_000_000

# Promotion requires the head and the tail each to recur across recovered
# Events. Two is the smallest count that distinguishes a set from a singleton.
MIN_SIBLING_CLUSTER = 2

# Promoted names re-enter the grammar once, so a recovered head can combine
# with a recovered tail. Further passes add candidates without adding families.
DEFAULT_MAX_PASSES = 2

FNV1_OFFSET_BASIS = 0x811C9DC5
FNV1_PRIME = 0x01000193

NAME_EVIDENCE = "exactFnv1HashPreimageFromObservedNamingGrammar"
PROMOTED_CORROBORATION = "siblingClusteredHeadAndTail"
ISOLATED_CORROBORATION = "isolatedHashPreimage"

EVIDENCE_BOUNDARY = (
    "A generated name whose AudioHashGenerator hash equals a current hash-only "
    "Wwise Event id recovers that Event's authored spelling, and with it the "
    "name-prefix owner and category the spelling encodes. The preimage is "
    "generated rather than shipped, so it is weaker than a metadata literal "
    "match: promotion additionally requires the head and tail to recur across "
    "recovered Events, and the residual coincidental-preimage expectation is "
    "reported. It does not prove a caller, a trigger, an execution, a selected "
    "Wwise branch, or audibility."
)


def _fold(code_unit: int) -> int:
    """Fold ASCII ``A``-``Z`` exactly as ``AudioHashGenerator.Compute`` does."""
    return code_unit + 0x20 if 0x41 <= code_unit <= 0x5A else code_unit


def _code_units(value: str) -> tuple[int, ...]:
    encoded = value.encode("utf-16-le", errors="surrogatepass")
    return tuple(
        _fold(encoded[offset] | (encoded[offset + 1] << 8))
        for offset in range(0, len(encoded), 2)
    )


def _hash_units(units: Iterable[int], state: int = FNV1_OFFSET_BASIS) -> int:
    for code_unit in units:
        state = ((state * FNV1_PRIME) & 0xFFFFFFFF) ^ code_unit
    return state


def split_tokens(name: str) -> list[str]:
    return str(name or "").strip().split("_")


def _family(tokens: Sequence[str]) -> str:
    return "_".join(token.casefold() for token in tokens[:FAMILY_TOKEN_COUNT])


def build_grammar(names: Iterable[str]) -> dict[tuple[str, int], tuple[dict[str, str], dict[str, str]]]:
    """Mine head/tail template slots from observed Event names.

    Every underscore boundary of every name becomes one template slot, keyed by
    naming family and split position.  Heads and tails are deduplicated
    case-insensitively while the first observed spelling is retained, so a
    regenerated name reuses authored casing instead of inventing one.
    """

    heads: dict[tuple[str, int], dict[str, str]] = defaultdict(dict)
    tails: dict[tuple[str, int], dict[str, str]] = defaultdict(dict)
    for name in names:
        tokens = split_tokens(name)
        if len(tokens) < MIN_TOKEN_COUNT or not all(tokens):
            continue
        key_family = _family(tokens)
        for position in range(FAMILY_TOKEN_COUNT, len(tokens)):
            head = "_".join(tokens[:position])
            tail = "_".join(tokens[position:])
            heads[(key_family, position)].setdefault(head.casefold(), head)
            tails[(key_family, position)].setdefault(tail.casefold(), tail)
    return {key: (heads[key], tails.get(key, {})) for key in heads}


def _search_pass(
    grammar: dict[tuple[str, int], tuple[dict[str, str], dict[str, str]]],
    target_hashes: set[int],
) -> tuple[dict[int, dict[str, str]], int, int]:
    """Return ``{hash: {foldedName: name}}``, candidates tried, families skipped.

    The FNV-1 state of each head is computed once and continued over each tail,
    so a family costs one pass over its heads plus one inner loop per pair.
    """

    matches: dict[int, dict[str, str]] = defaultdict(dict)
    tried = 0
    skipped = 0
    for key in sorted(grammar):
        head_map, tail_map = grammar[key]
        if not head_map or not tail_map:
            continue
        if len(head_map) * len(tail_map) > MAX_FAMILY_CANDIDATES:
            skipped += 1
            continue
        tails = [
            (_code_units("_" + tail), tail)
            for _, tail in sorted(tail_map.items())
        ]
        for _, head in sorted(head_map.items()):
            head_state = _hash_units(_code_units(head))
            for tail_units, tail in tails:
                tried += 1
                value = _hash_units(tail_units, head_state)
                if value in target_hashes:
                    name = f"{head}_{tail}"
                    matches[value].setdefault(name.casefold(), name)
    return matches, tried, skipped


def _corroborate(
    matches: dict[int, dict[str, str]],
) -> tuple[dict[int, str], dict[int, str], dict[int, tuple[int, int]]]:
    """Split unambiguous matches into sibling-clustered and isolated preimages.

    Head and tail recurrence is counted over the split position that produced
    each name, which is the same boundary the grammar generated it from.
    """

    resolved: dict[int, str] = {}
    ambiguous: set[int] = set()
    for event_hash, spellings in matches.items():
        if len(spellings) != 1:
            ambiguous.add(event_hash)
            continue
        resolved[event_hash] = next(iter(spellings.values()))

    head_counts: dict[str, int] = defaultdict(int)
    tail_counts: dict[str, int] = defaultdict(int)
    boundaries: dict[int, list[tuple[str, str]]] = {}
    for event_hash, name in resolved.items():
        tokens = split_tokens(name)
        splits = [
            ("_".join(tokens[:position]).casefold(), "_".join(tokens[position:]).casefold())
            for position in range(FAMILY_TOKEN_COUNT, len(tokens))
        ]
        boundaries[event_hash] = splits
        for head, tail in splits:
            head_counts[head] += 1
            tail_counts[tail] += 1

    promoted: dict[int, str] = {}
    isolated: dict[int, str] = {}
    cluster_sizes: dict[int, tuple[int, int]] = {}
    for event_hash, name in resolved.items():
        # Both sides must recur at one shared boundary. Counting the best head
        # and the best tail independently would pass on the family prefix
        # alone, which every candidate in the family shares by construction.
        shared = [
            (head_counts[head], tail_counts[tail])
            for head, tail in boundaries[event_hash]
            if head_counts[head] >= MIN_SIBLING_CLUSTER
            and tail_counts[tail] >= MIN_SIBLING_CLUSTER
        ]
        if shared:
            # The deepest qualifying boundary is the most specific subject and
            # action pair, so report that one.
            cluster_sizes[event_hash] = shared[-1]
            promoted[event_hash] = name
        else:
            cluster_sizes[event_hash] = (
                max((head_counts[head] for head, _ in boundaries[event_hash]), default=0),
                max((tail_counts[tail] for _, tail in boundaries[event_hash]), default=0),
            )
            isolated[event_hash] = name
    for event_hash in ambiguous:
        cluster_sizes.setdefault(event_hash, (0, 0))
    return promoted, isolated, cluster_sizes


def recover_event_names(
    known_event_names: Iterable[str],
    wwise_event_inventory: Iterable[dict[str, Any]],
    *,
    named_event_hashes: Iterable[int] = (),
    max_passes: int = DEFAULT_MAX_PASSES,
) -> dict[str, Any]:
    """Recover names for current Wwise Events that have no recovered name.

    ``named_event_hashes`` are the Events whose name is already proven by other
    exact evidence.  They seed the grammar and are excluded from the target set
    so a rediscovered name can never be counted as a recovery.
    """

    base: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "source": "observedWwiseEventNamingGrammar",
        "evidence": NAME_EVIDENCE,
        "status": "complete",
        "passes": 0,
        "targetHashCount": 0,
        "candidateCount": 0,
        "skippedFamilyCount": 0,
        "matchCount": 0,
        "ambiguousHashCount": 0,
        "promotedCount": 0,
        "isolatedCount": 0,
        "expectedCoincidentalPreimages": 0.0,
        "entries": [],
        "isolatedEntries": [],
        "evidenceBoundary": EVIDENCE_BOUNDARY,
    }

    seed_names = {
        str(name).strip()
        for name in known_event_names
        if str(name or "").strip()
        and not str(name).strip().casefold().startswith("hashed-event:0x")
    }
    resolved_hashes = {int(value) & 0xFFFFFFFF for value in named_event_hashes}
    resolved_hashes.update(_hash_units(_code_units(name)) for name in seed_names)

    targets = {
        int(row.get("eventHash")) & 0xFFFFFFFF
        for row in wwise_event_inventory
        if isinstance(row, dict) and isinstance(row.get("eventHash"), int)
    } - resolved_hashes
    base["targetHashCount"] = len(targets)
    if not targets or not seed_names:
        base["status"] = "degraded"
        base["reason"] = (
            "No hash-only Wwise Events were present."
            if not targets
            else "No recovered Event names were available to mine a grammar."
        )
        return base

    promoted: dict[int, str] = {}
    isolated: dict[int, str] = {}
    clusters: dict[int, tuple[int, int]] = {}
    ambiguous_total = 0
    matched_total = 0
    grammar_names = set(seed_names)
    remaining = set(targets)
    for _ in range(max(1, int(max_passes))):
        if not remaining:
            break
        grammar = build_grammar(sorted(grammar_names))
        matches, tried, skipped = _search_pass(grammar, remaining)
        base["passes"] += 1
        base["candidateCount"] += tried
        base["skippedFamilyCount"] += skipped
        base["expectedCoincidentalPreimages"] += tried * len(remaining) / float(1 << 32)
        if not matches:
            break
        matched_total += len(matches)
        pass_promoted, pass_isolated, pass_clusters = _corroborate(matches)
        ambiguous_total += len(matches) - len(pass_promoted) - len(pass_isolated)
        promoted.update(pass_promoted)
        isolated.update(pass_isolated)
        clusters.update(pass_clusters)
        remaining -= set(matches)
        if not pass_promoted:
            break
        grammar_names.update(pass_promoted.values())

    if base["skippedFamilyCount"]:
        # A skipped family leaves part of the grammar unsearched, so the run
        # cannot claim to have covered every template.
        base["status"] = "partial"
    base["matchCount"] = matched_total
    base["ambiguousHashCount"] = ambiguous_total
    base["promotedCount"] = len(promoted)
    base["isolatedCount"] = len(isolated)
    base["expectedCoincidentalPreimages"] = round(base["expectedCoincidentalPreimages"], 3)

    def row(event_hash: int, name: str, corroboration: str) -> dict[str, Any]:
        head_cluster, tail_cluster = clusters.get(event_hash, (0, 0))
        return {
            "eventHash": event_hash,
            "eventHashHex": f"0x{event_hash:08x}",
            "name": name,
            "namingFamily": _family(split_tokens(name)),
            "headSiblingCount": head_cluster,
            "tailSiblingCount": tail_cluster,
            "corroboration": corroboration,
            "source": base["source"],
            "evidence": base["evidence"],
        }

    base["entries"] = [
        row(event_hash, promoted[event_hash], PROMOTED_CORROBORATION)
        for event_hash in sorted(promoted, key=lambda value: promoted[value].casefold())
    ]
    base["isolatedEntries"] = [
        row(event_hash, isolated[event_hash], ISOLATED_CORROBORATION)
        for event_hash in sorted(isolated, key=lambda value: isolated[value].casefold())
    ]
    return base
