"""Complete authored speaker appearances, independent of Story publication.

Story locators are candidates, never evidence for character identity. The
browser validates the candidate against the last published conversation's
source row, speaker and text reference before offering navigation.
"""
from __future__ import annotations

import re
from typing import Any, Callable


TABLES = ("SNSDialogTable", "RemoteCommonTable", "MailTemplateTable")


def text_reference(node: Any) -> dict[str, str]:
    # Text hashes exceed JS's safe integer range. Keep their exact decimal form.
    return {"id": str(node.get("id") or ""), "text": str(node.get("text") or "")} if isinstance(node, dict) else {"text": str(node or "")}


def speaker_appearance(source: str, key: str, tables: dict[str, dict], localize: Callable[[Any], str]) -> dict | None:
    """Resolve the exact source path yielded by story_speakers.speaker_rows."""
    if source == "DialogTextTable":
        raw = tables[source][key]
        match = re.fullmatch(r"dlg_(.+)_(\d+)_(\d+)", key)
        if match:
            story_key = f"dlg_{match[1]}_{int(match[2])}"
        else:
            # Story's language bundle groups nonstandard DialogTextTable keys
            # by this exact suffix rule, including alphanumeric scene tokens
            # and utility dialogues. It is a locator candidate, not an order
            # or identity claim; the browser still authenticates its source.
            bucket = re.sub(r"_\d+(_\d+)?$", "", key) or "_misc"
            story_key = "misc_" + bucket
        return appearance(source, key, key, raw, "actorNameId", "dialogText", localize,
                          story_key=story_key, line_id=key, debug_table=source, debug_row=key)
    field = {"RadioTable": "radioSingleDataList", "EnvTalkTable": "envTalkDataList"}.get(source)
    if not field:
        return None  # A sender definition or auxiliary display label is not a line.
    match = re.fullmatch(r"(.+)\." + field + r"\[(\d+)\]", key)
    if not match:
        return None
    row_id, index = match[1], int(match[2])
    raw = tables[source][row_id][field][index]
    radio = source == "RadioTable"
    line_id = str(raw.get("id") or "") if radio else str(raw.get("envTalkId") or row_id)
    return appearance(source, key, row_id, raw, "actorNameId" if radio else "actorId",
                      "radioText" if radio else "text", localize,
                      story_key=row_id if radio else "env_" + row_id, line_id=line_id,
                      cid=None if radio else raw.get("index"), debug_table=source + "." + field,
                      debug_row=line_id, source_index=index)


def appearance(source: str, key: str, row_id: str, raw: dict, speaker_field: str,
               text_field: str, localize: Callable[[Any], str], *, story_key: str,
               debug_table: str, debug_row: str, line_id: str = "", cid: Any = None,
               source_index: int | None = None) -> dict:
    result = {
        "source": source, "key": key, "rowId": row_id,
        "speakerId": str(raw.get(speaker_field) or ""), "speakerField": speaker_field,
        "text": localize(raw.get(text_field)), "textField": text_field,
        "textReference": text_reference(raw.get(text_field)),
        "evidenceBoundary": "direct", "attribution": "authoredSpeaker",
    }
    if "actorName" in raw:
        result["speakerNameField"] = "actorName"
        result["speakerReference"] = text_reference(raw["actorName"])
    if story_key:
        result["story"] = {"key": story_key, "lineId": line_id, "cid": cid,
                           "table": debug_table, "rowId": debug_row}
    if source_index is not None:
        result["sourceIndex"] = source_index
    return result


def add_to_record(record: dict, item: dict | None, *, boundary: str = "direct",
                  attribution: str = "authoredSpeaker", label: str = "") -> None:
    if item is None:
        return
    row = {**item, "evidenceBoundary": boundary, "attribution": attribution}
    if label:
        row["speakerLabel"] = label
    record.setdefault("appearances", []).append(row)


def add_extra_appearances(catalog: Any, tables: dict[str, dict],
                          localize: Callable[[Any], str], language: str) -> list[dict]:
    """Follow SNS speaker, Remote middleId and Mail senderId; never actor names."""
    counts: dict[str, int] = {}

    def add(item: dict, raw: dict, name_field: str = "") -> None:
        speaker = item["speakerId"]
        if not speaker:
            return
        row = catalog.record(speaker, "actor")
        catalog.add_alias(row, speaker)
        if name_field:
            catalog.add_name(row, localize(raw.get(name_field)), item["source"], item["key"], language=language)
        add_to_record(row, item)
        counts[item["source"]] = counts.get(item["source"], 0) + 1

    for key, row in sorted(tables.get("SNSDialogTable", {}).items()):
        if not isinstance(row, dict):
            continue
        for node_key, raw in sorted((row.get("dialogContentData") or {}).items()):
            if not isinstance(raw, dict):
                continue
            item = appearance("SNSDialogTable", f"{key}.dialogContentData[{node_key}]", key, raw,
                              "speaker", "content", localize, story_key=key, cid=raw.get("contentId"),
                              debug_table="SNSDialogTable.dialogContentData", debug_row=key)
            item["contentType"] = raw.get("contentType")
            # Media/system nodes can carry a speaker without localized text.
            item["contentParameters"] = raw.get("contentParam") or []
            add(item, raw)
    for key, row in sorted(tables.get("RemoteCommonTable", {}).items()):
        if not isinstance(row, dict):
            continue
        for index, raw in enumerate(row.get("remoteCommSingleDataList") or []):
            if not isinstance(raw, dict):
                continue
            add(appearance("RemoteCommonTable", f"{key}.remoteCommSingleDataList[{index}]", key, raw,
                           "middleId", "remoteCommText", localize, story_key=key,
                           line_id=str(raw.get("singleId") or ""), cid=raw.get("index"),
                           debug_table="RemoteCommonTable.remoteCommSingleDataList", debug_row=key,
                           source_index=index), raw, "actorName")
    for key, raw in sorted(tables.get("MailTemplateTable", {}).items()):
        if isinstance(raw, dict):
            add(appearance("MailTemplateTable", key, key, raw, "senderId", "mailContent", localize,
                           story_key="mail_" + key, line_id=key, debug_table="MailTemplateTable", debug_row=key), raw)
    for row in catalog.records.values():
        own_counts: dict[str, int] = {}
        for item in row.get("appearances", []):
            if item["source"] in TABLES:
                own_counts[item["source"]] = own_counts.get(item["source"], 0) + 1
        for source, count in sorted(own_counts.items()):
            catalog.add_evidence(row, source, "story_speaker", row["id"],
                                 evidenceBoundary="direct", occurrenceCount=count,
                                 note="Complete authored speaker appearances; identity is not inferred from names.")
    return [{"source": source, "table": source + ".json", "rule": "explicit authored speaker appearances", "observations": count}
            for source, count in sorted(counts.items())]
