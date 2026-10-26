"""Installed JSON block identities and their language path boundaries."""
from typing import Any


JSON_LIP_LANGUAGES = {105: "Chinese", 106: "English", 107: "Japanese", 108: "Korean"}
JSON_BLOCKS = {19: "JsonData", **{
    block: "JsonLip" + language for block, language in JSON_LIP_LANGUAGES.items()
}}


def is_jsondata_identity(row: dict[str, Any]) -> bool:
    block = row.get("blockTypeValue")
    if block not in JSON_BLOCKS or row.get("blockName") != JSON_BLOCKS[block]:
        return False
    language = JSON_LIP_LANGUAGES.get(block)
    if language and not str(row.get("virtualPath", "")).startswith(f"Data/Json/LipSync/{language}/"):
        raise ValueError(f"JsonLip language path mismatch: block={row['blockName']},path={row.get('virtualPath')!r}")
    return True
