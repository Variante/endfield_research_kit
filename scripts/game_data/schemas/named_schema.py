"""The one validator behind every reviewed named JSON schema contract.

Three JsonData families (polymorphic GameplayConfig tables, main
MissionRuntimeAsset bodies, and the remaining textual JsonData tables) each
ship a reviewed schema contract with the same shape: ``nodes`` keyed by a
schema path, ``taggedObjects`` keyed by ``$type``, and
``dynamicDictionaries`` keyed by the path of a dictionary whose keys match a
pattern.  Each family keeps its own contract pin, path predicate, cross-field
relations, and result shape; the walk that checks a document against the
declared shapes is this module, so a rule such as the nesting limit or the
``keyEqualsField`` check exists in one place.

Every check fails closed through the family's own error class, so a failure
still names the family that raised it.
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable

MAX_DEPTH = 128
COUNTER_KEYS = ("objectCount", "taggedObjectCount", "arrayCount", "scalarCount", "maxDepth")
SECTION_KEYS = ("nodes", "taggedObjects", "dynamicDictionaries")


def make_fail(error: type[ValueError]) -> Callable[[str, Any, Any], None]:
    def fail(path: str, expected: Any, actual: Any) -> None:
        raise error(f"{path}: expected={expected!r} actual={actual!r}")

    return fail


def json_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if type(value) is bool:
        return "boolean"
    if type(value) is int:
        return "integer"
    if type(value) is float:
        return "number"
    if type(value) is str:
        return "string"
    if type(value) is list:
        return "array"
    if type(value) is dict:
        return "object"
    return type(value).__name__


def load_schema_contract(
    path: Any,
    *,
    schema: str,
    error: type[ValueError],
    tables: frozenset[str] | None = None,
) -> dict[str, Any]:
    """Read a reviewed schema contract and check its identity and top-level shape.

    With ``tables`` the contract must declare exactly that table set, each
    with the three schema sections; without it the contract itself carries
    the sections.
    """
    fail = make_fail(error)
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise error(f"cannot read schema contract: {exc}") from exc
    try:
        contract = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise error(f"invalid schema contract: {exc}") from exc
    if not isinstance(contract, dict) or contract.get("schema") != schema or contract.get("status") != "named_exact":
        fail("schemaContract", (schema, "named_exact"), contract.get("schema") if isinstance(contract, dict) else type(contract).__name__)
    if tables is not None:
        declared = contract.get("tables")
        if not isinstance(declared, dict) or set(declared) != tables:
            fail("schemaContract.tables", sorted(tables), sorted(declared) if isinstance(declared, dict) else type(declared).__name__)
        sections = declared.values()
    else:
        sections = (contract,)
    for section in sections:
        if not isinstance(section, dict) or any(not isinstance(section.get(key), dict) for key in SECTION_KEYS):
            fail("schemaContract.sections", list(SECTION_KEYS), section if not isinstance(section, dict) else sorted(section))
    return contract


def parse_utf8_json(data: bytes, *, source: str, error: type[ValueError]) -> Any:
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise error(f"{source}: invalid UTF-8 JSON: {exc}") from exc


def validate_document(root: Any, table: dict[str, Any], *, source: str, error: type[ValueError]) -> dict[str, int]:
    """Walk ``root`` against ``table`` from schema path ``$`` and return the counters."""
    fail = make_fail(error)
    counters = {key: 0 for key in COUNTER_KEYS}

    def visit(value: Any, schema_path: str, display_path: str, depth: int) -> None:
        if depth > MAX_DEPTH:
            fail(display_path, f"nesting depth <= {MAX_DEPTH}", depth)
        counters["maxDepth"] = max(counters["maxDepth"], depth)
        node = table["nodes"].get(schema_path)
        if not isinstance(node, dict):
            fail(display_path, f"declared schema node {schema_path}", "undeclared")
        actual_type = json_type_name(value)
        allowed_types = node.get("types")
        if not isinstance(allowed_types, list) or actual_type not in allowed_types:
            fail(display_path + ".type", allowed_types, actual_type)

        if isinstance(value, list):
            counters["arrayCount"] += 1
            for index, child in enumerate(value):
                visit(child, schema_path + "[]", f"{display_path}[{index}]", depth + 1)
            return
        if not isinstance(value, dict):
            counters["scalarCount"] += 1
            return

        counters["objectCount"] += 1
        tag = value.get("$type")
        if isinstance(tag, str):
            allowed_tags = node.get("allowedTags")
            if not isinstance(allowed_tags, list) or tag not in allowed_tags:
                fail(display_path + ".$type", allowed_tags, tag)
            tagged = table["taggedObjects"].get(tag)
            if not isinstance(tagged, dict):
                fail(display_path + ".$type", "declared tagged object", tag)
            shapes = tagged.get("shapes")
            if not isinstance(shapes, list) or list(value) not in shapes:
                fail(display_path + ".fields", shapes, list(value))
            counters["taggedObjectCount"] += 1
            for key, child in value.items():
                if key != "$type":
                    visit(child, f"@{tag}.{key}", f"{display_path}.{key}", depth + 1)
            return

        dynamic = table["dynamicDictionaries"].get(schema_path)
        if dynamic is not None:
            key_pattern = dynamic.get("keyPattern")
            value_path = dynamic.get("valuePath")
            if not isinstance(key_pattern, str) or not isinstance(value_path, str):
                fail(schema_path, "valid dynamic dictionary declaration", dynamic)
            key_field = dynamic.get("keyEqualsField")
            for key, child in value.items():
                if not isinstance(key, str) or re.fullmatch(key_pattern, key) is None:
                    fail(display_path + ".key", key_pattern, key)
                if key_field is not None and (not isinstance(child, dict) or child.get(key_field) != key):
                    fail(
                        f"{display_path}[{key!r}].{key_field}",
                        key,
                        child.get(key_field) if isinstance(child, dict) else type(child).__name__,
                    )
                visit(child, value_path, f"{display_path}[{key!r}]", depth + 1)
            return

        shapes = node.get("shapes")
        if not isinstance(shapes, list) or list(value) not in shapes:
            fail(display_path + ".fields", shapes, list(value))
        for key, child in value.items():
            visit(child, f"{schema_path}.{key}", f"{display_path}.{key}", depth + 1)

    visit(root, "$", source, 0)
    return counters


def section_counts(table: dict[str, Any]) -> dict[str, int]:
    return {
        "schemaNodeCount": len(table["nodes"]),
        "typedSchemaCount": len(table["taggedObjects"]),
        "dynamicDictionaryCount": len(table["dynamicDictionaries"]),
    }
