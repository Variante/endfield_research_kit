from __future__ import annotations

from collections.abc import Callable


def rich_content_row_for_source(
    content_id: str,
    table_source: str,
    *,
    collection_table_payload: Callable[[str, str], dict],
    fallback_rich_content: dict,
) -> dict:
    content_key = str(content_id or "").strip()
    if not content_key:
        return {}
    payload = collection_table_payload(table_source, "RichContentTable.json")
    row = payload.get(content_key) if isinstance(payload, dict) else None
    if not isinstance(row, dict) and table_source != "streaming":
        row = fallback_rich_content.get(content_key)
    return row if isinstance(row, dict) else {}


def rich_content_title_text_for_source(
    content_id: str,
    table_source: str,
    *,
    collection_table_payload: Callable[[str, str], dict],
    fallback_rich_content: dict,
    translate: Callable[..., str],
) -> str:
    row = rich_content_row_for_source(
        content_id,
        table_source,
        collection_table_payload=collection_table_payload,
        fallback_rich_content=fallback_rich_content,
    )
    return (
        translate(
            (row.get("title") or {}).get("id"),
            preferred_source=table_source,
        )
        if row
        else ""
    )


def rich_content_lines_for_source(
    content_id: str,
    table_source: str,
    *,
    collection_table_payload: Callable[[str, str], dict],
    fallback_rich_content: dict,
    translate: Callable[..., str],
    source_ref: Callable[..., dict],
    pick_fields: Callable[..., dict],
    text_trace: Callable[..., dict],
    collection_source_label: Callable[[str], str],
) -> list[dict]:
    row = rich_content_row_for_source(
        content_id,
        table_source,
        collection_table_payload=collection_table_payload,
        fallback_rich_content=fallback_rich_content,
    )
    if not row:
        return []
    out: list[dict] = []
    for idx, item in enumerate(row.get("contentList") or [], start=1):
        if not isinstance(item, dict):
            continue
        content = item.get("content") or {}
        text = translate(content.get("id"), preferred_source=table_source)
        out.append({
            "id": f"{content_id}_{idx}",
            "text": text,
            "_debug": {
                **source_ref(
                    "RichContentTable.contentList",
                    str(content_id),
                    pick_fields(item, "content"),
                    nodeId=idx,
                    tableSource=collection_source_label(table_source),
                ),
                "fields": {
                    "text": text_trace(
                        "RichContentTable",
                        str(content_id),
                        "content",
                        content,
                        preferred_source=table_source,
                    ),
                },
            },
        })
    return out


def reading_content_refs(
    table_name: str,
    row_id: str,
    row: dict | None,
    *,
    table_source: str,
    translate: Callable[..., str],
    brace_text: Callable[[str], str],
    pick_fields: Callable[..., dict],
) -> list[dict]:
    if not isinstance(row, dict):
        return []
    refs: list[dict] = []
    if table_name == "PrtsReading.json":
        items = row.get("list") or {}
        if not isinstance(items, dict):
            return []
        sorted_items = sorted(
            (
                (node_id, node)
                for node_id, node in items.items()
                if isinstance(node, dict)
            ),
            key=lambda item: (
                int((item[1] or {}).get("order") or 0),
                str(item[0]),
            ),
        )
        for node_id, node in sorted_items:
            content_id = str(node.get("contentId") or "").strip()
            if not content_id:
                continue
            name = brace_text(
                translate(
                    (node.get("name") or {}).get("id"),
                    preferred_source=table_source,
                )
            )
            subtitle = brace_text(
                translate(
                    (node.get("subtitle") or {}).get("id"),
                    preferred_source=table_source,
                )
            )
            refs.append({
                "contentId": content_id,
                "label": name or subtitle or content_id,
                "subtitle": subtitle,
                "path": f"$.list.{node_id}.contentId",
                "nodeId": node_id,
                "source": pick_fields(
                    node,
                    "contentId",
                    "name",
                    "order",
                    "subtitle",
                    "uniqId",
                ),
            })
    elif table_name == "ReadingPopUpTable.json":
        content_id = str(row.get("contentId") or "").strip()
        if content_id:
            refs.append({
                "contentId": content_id,
                "label": (
                    brace_text(
                        translate(
                            (row.get("title") or {}).get("id"),
                            preferred_source=table_source,
                        )
                    )
                    or content_id
                ),
                "path": "$.contentId",
                "nodeId": 1,
                "source": pick_fields(
                    row,
                    "bgType",
                    "contentId",
                    "iconType",
                    "id",
                    "title",
                ),
            })
    return refs


def append_linked_reading_content_lines(
    table_name: str,
    row_id: str,
    row: dict | None,
    *,
    table_source: str,
    lines: list[dict],
    seen_texts: set[tuple[str, str, str]],
    collection_table_payload: Callable[[str, str], dict],
    fallback_rich_content: dict,
    radio_row_lookup: dict,
    translate: Callable[..., str],
    source_ref: Callable[..., dict],
    pick_fields: Callable[..., dict],
    text_trace: Callable[..., dict],
    collection_source_label: Callable[[str], str],
    brace_text: Callable[[str], str],
    append_reference_line: Callable[..., None],
) -> tuple[list[dict], str]:
    linked_refs: list[dict] = []
    preview_text = ""
    for ref_index, ref in enumerate(
        reading_content_refs(
            table_name,
            row_id,
            row,
            table_source=table_source,
            translate=translate,
            brace_text=brace_text,
            pick_fields=pick_fields,
        ),
        start=1,
    ):
        content_id = str(ref.get("contentId") or "").strip()
        if not content_id:
            continue
        label = str(ref.get("label") or content_id)
        linked_from = source_ref(
            table_name.removesuffix(".json"),
            row_id,
            {
                "path": ref.get("path") or "$.contentId",
                "contentId": content_id,
                **(ref.get("source") or {}),
            },
            nodeId=ref.get("nodeId"),
            tableSource=collection_source_label(table_source),
        )
        rich_title = rich_content_title_text_for_source(
            content_id,
            table_source,
            collection_table_payload=collection_table_payload,
            fallback_rich_content=fallback_rich_content,
            translate=translate,
        )
        rich_lines = rich_content_lines_for_source(
            content_id,
            table_source,
            collection_table_payload=collection_table_payload,
            fallback_rich_content=fallback_rich_content,
            translate=translate,
            source_ref=source_ref,
            pick_fields=pick_fields,
            text_trace=text_trace,
            collection_source_label=collection_source_label,
        )
        if rich_title and rich_title != label:
            rich_row = rich_content_row_for_source(
                content_id,
                table_source,
                collection_table_payload=collection_table_payload,
                fallback_rich_content=fallback_rich_content,
            )
            append_reference_line(
                lines,
                seen_texts,
                f"{row_id}_linked_{ref_index}_title",
                rich_title,
                hint=f"{label} / Title",
                debug={
                    **source_ref(
                        "RichContentTable",
                        content_id,
                        {"title": (rich_row.get("title") or {})},
                        tableSource=collection_source_label(table_source),
                    ),
                    "linkedFrom": linked_from,
                    "fields": {
                        "text": text_trace(
                            "RichContentTable",
                            content_id,
                            "title",
                            (rich_row.get("title") or {}),
                            preferred_source=table_source,
                        ),
                    },
                },
            )
            preview_text = preview_text or rich_title
        if rich_lines:
            linked_refs.append({
                "contentId": content_id,
                "source": "RichContentTable",
                "lineCount": len(rich_lines),
                "label": label,
            })
            for content_index, content_line in enumerate(rich_lines, start=1):
                text = str(content_line.get("text") or "")
                debug = dict(content_line.get("_debug") or {})
                debug["linkedFrom"] = linked_from
                append_reference_line(
                    lines,
                    seen_texts,
                    f"{row_id}_linked_{ref_index}_{content_index}",
                    text,
                    hint=rich_title or label,
                    debug=debug,
                )
                if text:
                    preview_text = preview_text or text
            continue
        radio_row = radio_row_lookup.get(content_id)
        if radio_row:
            radio_lines = [
                line
                for line in (radio_row.get("lines") or [])
                if isinstance(line, dict)
            ]
            linked_refs.append({
                "contentId": content_id,
                "source": "RadioTable",
                "lineCount": len(radio_lines),
                "label": label,
            })
            for content_index, radio_line in enumerate(radio_lines, start=1):
                text = str(radio_line.get("text") or "")
                debug = dict(radio_line.get("_debug") or {})
                debug["linkedFrom"] = linked_from
                append_reference_line(
                    lines,
                    seen_texts,
                    f"{row_id}_linked_{ref_index}_{content_index}",
                    text,
                    hint=label,
                    actor=str(radio_line.get("actor") or ""),
                    aid=str(radio_line.get("aid") or ""),
                    debug=debug,
                )
                if text:
                    preview_text = preview_text or text
    return linked_refs, preview_text


__all__ = [
    "append_linked_reading_content_lines",
    "reading_content_refs",
    "rich_content_lines_for_source",
    "rich_content_row_for_source",
    "rich_content_title_text_for_source",
]
