"""Strict anonymous tag5 framing inside an authenticated marker17 byte range.

The selected native reader fixes the order and strides of six record groups.
It does not validate the final cursor: EOF and count checks here are parser
requirements, not attributed native safety checks. Record fields stay opaque.
"""
import struct

TAG5_RECORD_WIDTHS = (24, 52, 48, 28, 56, 56)


def parse_marker17_tag5(
    data: bytes, *, source: str, base_offset: int = 0,
    native_layout_validated: bool = False,
) -> dict:
    """Parse only a source-authenticated, independently native-gated body.

    Negative counts and non-binary first selectors are rejected even though
    the native reader can skip those groups. Empty groups own no bytes. Record
    i occupies [start + i * recordWidth, start + (i + 1) * recordWidth).
    """
    def fail(offset, expected, actual):
        raise ValueError(f'{source} at decoded offset {base_offset + offset}: expected {expected}, actual {actual}')
    if native_layout_validated is not True:
        fail(0, 'validated selected-build marker17 tag5 native layout', 'unvalidated')
    if base_offset < 0:
        fail(0, 'nonnegative decoded body base', base_offset)
    if len(data) < 64:
        fail(len(data), 'at least 64 header bytes', len(data))
    tag = struct.unpack_from('<h', data, 28)[0]
    if tag != 5:
        fail(28, 'anonymous tag 5', tag)
    counts = struct.unpack_from('<6i', data, 40)
    if counts[0] not in (0, 1):
        fail(40, 'optional-record selector 0 or 1', counts[0])
    cursor = 64
    arrays = []
    for index, (count, width) in enumerate(zip(counts, TAG5_RECORD_WIDTHS)):
        if count < 0 or count > (len(data) - cursor) // width:
            fail(40 + index * 4, f'count 0..{(len(data) - cursor) // width} for width {width} at body cursor {cursor}', count)
        end = cursor + count * width
        arrays.append(dict(index=index, countOffset=base_offset + 40 + 4 * index,
                           kind='optional-record' if index == 0 else 'record-array',
                           count=count, recordWidth=width, start=base_offset + cursor,
                           end=base_offset + end, contentStatus='opaque'))
        cursor = end
    if cursor != len(data):
        fail(cursor, f'exact body EOF {base_offset + len(data)}', f'cursor {base_offset + cursor}; trailing {len(data) - cursor} bytes')
    return dict(status='exact-anonymous-tag5-eof', evidenceLevel='structural-only',
                bodyStart=base_offset, bodyEnd=base_offset + len(data), tag=tag,
                tagOffset=base_offset + 28, headerEnd=base_offset + 64,
                opaqueHeaderRanges=[dict(start=base_offset, end=base_offset + 28),
                                    dict(start=base_offset + 30, end=base_offset + 40)],
                arrays=arrays, consumedBytes=cursor,
                recordFieldMeaning='unresolved', runtimeSelectionStatus='unresolved',
                nativeFinalCursorStatus='not-checked-by-native; parser-enforced-EOF')
