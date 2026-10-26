"""Read protobuf message schemas out of IL2CPP metadata.

A generated protobuf message class states its own wire contract inside
``global-metadata.dat``: every field's wire tag is a ``<Name>FieldNumber``
static literal carrying a compressed int32 default, and the storage behind it
is a ``<Name>k__BackingField`` auto-property (scalar members) or a
``__pbn__<Name>`` pooled member (message / repeated members in the
protobuf-net pooled messages this client uses). Older builds spelled the
storage ``<name>_``. Matching the two sides on the normalized member name
recovers tag -> field -> C# storage with no descriptor blob and no running
game.

Evidence tier: metadata-only. These rows state what a message class can
carry, never that a sender is active, that the server fills a field, or that
the message is used at all. The network lane joins them to observed bodies
and states its own tier there.

Field type indices are runtime ``Il2CppType`` indices, not TypeDef indices,
so a readable type name needs the selected ``GameAssembly.dll``: resolve the
index through ``NativeImage`` with
:func:`scripts.game_data.il2cpp.protocol.runtime_type_name`.
"""
from __future__ import annotations

from typing import Any

from scripts.game_data.il2cpp import protocol as il2cpp

FIELD_NUMBER_SUFFIX = "FieldNumber"
POOLED_MEMBER_PREFIX = "__pbn__"
BACKING_FIELD_SUFFIX = ">k__BackingField"
# Pooled-message bookkeeping, never a wire field.
NON_WIRE_FIELDS = frozenset(
    {
        "__pbn__extensionData",
        "__pbn__isInPool",
        "<global::Proto.IProtoPooledMessage.IsFactoryPool>k__BackingField",
    }
)


def storage_member_name(field_name: str) -> str | None:
    """The message member a storage field belongs to, if it is one."""
    if field_name in NON_WIRE_FIELDS or field_name == "value__":
        return None
    if field_name.startswith(POOLED_MEMBER_PREFIX):
        return field_name[len(POOLED_MEMBER_PREFIX) :] or None
    if field_name.startswith("<") and field_name.endswith(BACKING_FIELD_SUFFIX):
        return field_name[1 : field_name.index(">")] or None
    if field_name.endswith("_") and not field_name.startswith("__"):
        return field_name[:-1] or None
    return None


def tag_member_name(field_name: str) -> str | None:
    """The message member a ``<Name>FieldNumber`` literal belongs to."""
    if not field_name.endswith(FIELD_NUMBER_SUFFIX):
        return None
    return field_name[: -len(FIELD_NUMBER_SUFFIX)] or None


def message_fields(
    metadata: Any, defaults: dict[int, tuple[int, int]], type_def: Any
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Split one type's fields into wire-tag literals and storage fields.

    Keys are the normalized member name, so ``ClientTsFieldNumber`` and
    ``<ClientTs>k__BackingField`` land on the same entry whatever spelling a
    build used. Each side keeps its raw member name for reporting.
    """
    tags: dict[str, dict[str, Any]] = {}
    storage: dict[str, dict[str, Any]] = {}
    for field in metadata.fields_for(type_def):
        name = metadata.string(field.name_index)
        tag_member = tag_member_name(name)
        if tag_member is not None:
            tags[il2cpp.normalized_field_name(tag_member)] = {
                "member": tag_member,
                "constantName": name,
                "tag": il2cpp.constant_value(metadata, defaults, field),
            }
            continue
        storage_member = storage_member_name(name)
        if storage_member is not None:
            storage[il2cpp.normalized_field_name(storage_member)] = {
                "member": storage_member,
                "storageName": name,
                "storageTypeIndex": field.type_index,
                "metadataType": metadata.metadata_type_name(field.type_index),
            }
    return tags, storage


def is_message_type(metadata: Any, type_def: Any) -> bool:
    """True when the class states wire tags or pooled message storage."""
    tags, storage = message_fields(metadata, {}, type_def)
    return bool(tags or storage)


def find_type(metadata: Any, type_name: str) -> Any:
    for type_def in metadata.types:
        if metadata.type_full_name(type_def) == type_name:
            return type_def
    raise RuntimeError(f"metadata type not found: {type_name}")


def message_schema(
    metadata: Any, defaults: dict[int, tuple[int, int]], type_name: str
) -> dict[str, Any]:
    """The wire contract a named message class states for itself.

    Row shape is the one the Story-side protocol registry consumes: ``name``
    is the message member, ``tag`` the declared wire tag, ``storageName`` the
    C# field holding it, and ``matchedTagAndStorage`` says both halves joined.
    """
    type_def = find_type(metadata, type_name)
    tags, storage = message_fields(metadata, defaults, type_def)
    fields: list[dict[str, Any]] = []
    for key in set(tags) | set(storage):
        tag_row = tags.get(key, {})
        storage_row = storage.get(key, {})
        row: dict[str, Any] = {
            "name": tag_row.get("member") or storage_row.get("member"),
            "matchedTagAndStorage": key in tags and key in storage,
        }
        row.update(storage_row)
        row.update(tag_row)
        fields.append(row)
    fields.sort(
        key=lambda row: (row.get("tag") is None, row.get("tag") or 0, row.get("name") or "")
    )
    return {
        "type": type_name,
        "token": f"0x{type_def.token:08x}",
        "fields": fields,
    }
