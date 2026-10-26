"""Apply installed localization overrides to semantic views, preserving source tables."""
from pathlib import Path
import json
from scripts.common import read_json

HOTFIX_TABLE = 'I18nHotFix.json'
LANGUAGE_TYPES = dict(CN=0,EN=1,JP=2,KR=3,TC=4,MX=5,BR=6,FR=7,DE=8,RU=9,IT=10,ID=11,TH=12,VN=13)


def text_hotfixes(rows: dict, language: str) -> list[tuple[str, str]]:
    if not isinstance(rows, dict):
        raise ValueError('I18nHotFix must be an object')
    kind = LANGUAGE_TYPES.get(language)
    if kind is None:
        return []
    patches = []
    for row_id, row in rows.items():
        if not isinstance(row, dict):
            continue
        for item in row.get('list') or []:
            if not isinstance(item, dict) or item.get('type') != kind or item.get('text') is None:
                continue
            key = str(item.get('id') or row_id)
            if key:
                patches.append((key, str(item['text'])))
    return patches


def localize(texts: dict, rows: dict, language: str) -> dict:
    if not isinstance(texts, dict):
        raise ValueError('I18n text table must be an object')
    result = dict(texts)
    result.update(text_hotfixes(rows, language))
    return result


def read_text_table(path: Path, language: str) -> dict:
    return localize(json.loads(path.read_text(encoding='utf-8-sig')),
                    read_json(path.parent / HOTFIX_TABLE, {}), language)
