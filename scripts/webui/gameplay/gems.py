"""Authored Energy Alluvium pools and exact three-term weapon compatibility."""
from __future__ import annotations

from typing import Any, Callable


TABLE_NAMES = (
    "GemTable.json", "GemTagIdTable.json", "WorldEnergyPointGroupTable.json",
    "WorldEnergyPointTable.json", "GameMechanicTable.json", "LevelDescTable.json",
    "DomainDataTable.json",
)
POOL_FIELDS = ("primAttrTermIds", "secAttrTermIds", "skillTermIds")


def build_gem_entries(
    tables: dict[str, Any], weapons: list[dict[str, Any]],
    localize: Callable[[Any], str],
) -> list[dict[str, Any]]:
    """Return Energy Alluvium entries and set ``gemSources`` on every weapon.

    Each weapon gets a fresh ``gemSources`` list (empty when nothing matches),
    in group-id order. Call it once, after the weapon entries are complete and
    before they are sorted or serialized; the computation itself is
    :func:`collect_gem_entries`, which leaves ``weapons`` untouched.
    """
    entries, sources = collect_gem_entries(tables, weapons, localize)
    for weapon in weapons:
        weapon["gemSources"] = sources.get(weapon["id"], [])
    return entries


def _table(tables: dict[str, Any], name: str) -> dict[str, Any]:
    value = tables.get(name) or {}
    return value if isinstance(value, dict) else {}


def _world_level_key(item: tuple[Any, Any]) -> tuple[int, int | str]:
    try:
        return 0, int(item[0])
    except (TypeError, ValueError):
        return 1, str(item[0])


def collect_gem_entries(
    tables: dict[str, Any], weapons: list[dict[str, Any]],
    localize: Callable[[Any], str],
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, str]]]]:
    """Return ``(entries, {weapon_id: [{id, title}, ...]})`` without mutation."""
    terms = _table(tables, "GemTable.json")
    tag_terms = _table(tables, "GemTagIdTable.json")
    points = _table(tables, "WorldEnergyPointTable.json")
    mechanics = _table(tables, "GameMechanicTable.json")
    levels = _table(tables, "LevelDescTable.json")
    domains = _table(tables, "DomainDataTable.json")
    level_domains: dict[str, set[str]] = {}
    for domain_id, domain in domains.items():
        if not isinstance(domain, dict):
            continue
        for level_id in domain.get("levelGroup") or []:
            level_domains.setdefault(level_id, set()).add(domain_id)
    requirements = {}
    sources: dict[str, list[dict[str, str]]] = {}
    for weapon in weapons:
        skills = weapon.get("skills") or []
        ids = []
        for index, skill in enumerate(skills):
            tags = {row.get("tagId") for row in skill.get("levels") or [] if row.get("tagId")}
            term_id = tag_terms.get(next(iter(tags))) if len(tags) == 1 else None
            term = terms.get(term_id) or {}
            if term_id and term.get("termType") == index:
                ids.append(term_id)
        # Missing, ambiguous or wrong-position tags never produce a match.
        if len(skills) == 3 and len(ids) == 3:
            requirements[weapon["id"]] = ids
    entries = []
    for group_id, group in sorted((tables.get("WorldEnergyPointGroupTable.json") or {}).items()):
        pools = []
        for index, field in enumerate(POOL_FIELDS):
            pools.append([
                {"id": term_id, "name": localize(terms[term_id].get("tagName")) or term_id}
                for term_id in group.get(field) or []
                if term_id in terms and terms[term_id].get("termType") == index
            ])
        stages = []
        for world_level, point_id in sorted((group.get("worldLevel2GameMechanicsIdMap") or {}).items(), key=_world_level_key):
            point = points.get(point_id) or {}
            if point.get("gameGroupId") != group_id:
                continue
            mechanic = mechanics.get(point_id) or {}
            if mechanic.get("gameGroupId") != group_id:
                mechanic = {}
            level_id = point.get("levelId") or ""
            stages.append({
                "id": point_id, "worldLevel": _world_level_key((world_level, None))[1], "levelId": level_id,
                "location": localize((levels.get(level_id) or {}).get("showName")) or level_id,
                "recommendLv": point.get("recommendLv"),
                "costStamina": mechanic.get("costStamina", point.get("costStamina")),
                "rewardId": mechanic.get("rewardId") or "",
            })
        locations = sorted({row["location"] for row in stages if row["location"]})
        name = localize(group.get("gameGroupName")) or group_id
        location = " / ".join(locations)
        owners = set().union(*(level_domains.get(row["levelId"], set()) for row in stages))
        domain_id = next(iter(owners)) if len(owners) == 1 and all(len(level_domains.get(row["levelId"], set())) == 1 for row in stages) else ""
        domain_row = domains.get(domain_id) or {}
        if not isinstance(domain_row, dict):
            domain_row = {}
        domain = {"id": domain_id, "name": localize(domain_row.get("domainName")) or domain_id,
                  "sortId": domain_row.get("sortId", 999)}
        title = f"{location} · {name}" if location else name
        pool_ids = [{row["id"] for row in pool} for pool in pools]
        compatible = [weapon for weapon in weapons if weapon["id"] in requirements
                      and all(term in pool for term, pool in zip(requirements[weapon["id"]], pool_ids))]
        for weapon in compatible:
            sources.setdefault(weapon["id"], []).append({"id": group_id, "title": title})
        entries.append({
            "id": group_id, "kind": "gem", "title": title, "subtitle": location,
            "group": location, "location": location, "termPools": pools,
            "domain": domain,
            "iconId": group.get("icon") or "",
            "stages": stages,
            "compatibleWeapons": [{"id": weapon["id"], "title": weapon["title"]} for weapon in compatible],
            "gemRandId": group.get("gemRandId") or "",
            "source": {"table": "WorldEnergyPointGroupTable.json", "id": group_id},
            "evidenceBoundary": "Authored term-pool membership permits the three terms; drop probabilities and guaranteed combinations are not established.",
            "search": " ".join([group_id, title, domain["name"], *(row["name"] for pool in pools for row in pool),
                                *(weapon["title"] for weapon in compatible)]),
        })
    return entries, sources
