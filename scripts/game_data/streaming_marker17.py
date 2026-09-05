"""Strict anonymous tag5 framing inside an authenticated marker17 byte range.

The selected native reader fixes the order and strides of six record groups.
It does not validate the final cursor: EOF and count checks here are parser
requirements, not attributed native safety checks. Record fields stay opaque.
"""
import struct

TAG5_RECORD_WIDTHS = (24, 52, 48, 28, 56, 56)
FIXED_BODY_PROFILES = {
    (2, 0x04000000): (1, 64),
    (5, 0x05000000): (4, 68),
    (7, 0x08000000): (6, 64),
}
TAG5_BODY_KEYS = {6: 0x09000000, 9: 0xFF030000}


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


def parse_marker17_body(
    data: bytes, *, source: str, selector: int, key: int,
    base_offset: int = 0, native_layout_validated: bool = False,
) -> dict:
    """Dispatch an already authenticated table-local key/context.

    Fixed lengths are strict profile policy, selected independently of native
    EOF behavior. The current-corpus gate tests that policy against every body.
    Native code proves only conditional read coverage, including an unread gap.
    The caller must authenticate family, root marker and full-key uniqueness;
    neither byte length nor a low selector byte can substitute for that join.
    """
    def fail(offset, expected, actual):
        raise ValueError(f'{source} at decoded offset {base_offset + offset}: expected {expected}, actual {actual}')
    if type(base_offset) is not int or base_offset < 0:
        raise ValueError(f'{source} at decoded offset {base_offset!r}: expected nonnegative integer body base, actual {base_offset!r}')
    if native_layout_validated is not True:
        fail(0, 'validated selected-build marker17 native layout', 'unvalidated')
    if any(type(value) is not int or not 0 <= value <= 0xFFFFFFFF for value in (selector, key)):
        fail(0, 'uint32 selector and full key', (selector, key))
    if TAG5_BODY_KEYS.get(selector) == key:
        return parse_marker17_tag5(data, source=source, base_offset=base_offset,
                                  native_layout_validated=True)
    profile = FIXED_BODY_PROFILES.get((selector, key))
    if profile is None:
        fail(0, 'supported exact selector/key profile', (selector, key))
    tag, length = profile
    if len(data) < 30:
        fail(len(data), 'at least 30 bytes before reading tag at body offset 28', len(data))
    actual_tag = struct.unpack_from('<h', data, 28)[0]
    if actual_tag != tag:
        fail(28, f'profile anonymous tag {tag}', actual_tag)
    if len(data) != length:
        fail(min(len(data), length), f'profile-enforced exact body EOF {base_offset + length}',
             f'body length {len(data)}; expected length {length}; trailing {max(0, len(data) - length)}')
    def span(start, end, status):
        return dict(start=base_offset + start, end=base_offset + end, contentStatus=status)
    return dict(
        status='exact-anonymous-fixed-profile-eof', evidenceLevel='structural-only',
        profile=dict(selector=selector, key=key, tag=tag, expectedBodyLength=length),
        bodyStart=base_offset, bodyEnd=base_offset + length, consumedBytes=length,
        tag=tag, tagOffset=base_offset + 28,
        nativeConditionalReadCoverage=[span(0, 30, 'anonymous'), span(32, length, 'anonymous')],
        partition=[span(0, 28, 'opaque-conditional-native-read'), span(28, 30, 'anonymous-tag'),
                   span(30, 32, 'opaque-not-read-by-reviewed-native'),
                   span(32, length, 'opaque-conditional-native-read')],
        opaqueUnreadRanges=[span(30, 32, 'opaque-not-read-by-reviewed-native')],
        recordFieldMeaning='unresolved', runtimeSelectionStatus='unresolved',
        exactLengthEvidence='strict context profile; independently tested by corpus gate; parser-enforced EOF',
        nativeFinalCursorStatus='not-checked-by-native; maximum read offset is not EOF',
    )
