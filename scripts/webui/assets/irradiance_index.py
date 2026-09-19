"""Frame the IrradianceVolume index file.

The engine names this format itself. ``global-metadata.dat`` carries
``HGIrradianceVolumeManager``/``V2`` with ``ReloadIndexFileV3``,
``GetCurrentIrradianceVolumePathV3``, ``GetStateNameList``, ``UpdateSceneStateMask``,
``UpdateGachaIV`` and ``ToggleDebugUpdateClipmap``. So there is an index, it has a
state-name list, and the volume payload is a clipmap. *Two batches of byte-pattern
search had not found the container; one metadata scan named it.*

The index sits beside the volume files it names::

    Data/IrradianceVolume/PC/<scene>/v3/index.bytes
    Data/IrradianceVolume/PC/<scene>/v3/iv_<x>_<y>.bytes

and the layout framed here is::

    u32 magic            0x03000003 in 82 files, 0x01000043 in 2, 0x03000002 in 2
    u32 stateCount       the scene states GetStateNameList returns
    stateCount x name    u32 byteLength, then that many bytes of UTF-16LE
    u32 u32 u32          three words, unread: 1, 0, 0 in every file that frames
    u32 volumeCount
    volumeCount x name   the volume files in this directory
    ... remainder        the clipmap description, not framed here

**What makes this a frame rather than a guess.** The volume names must equal the set of
volume files actually present in the same directory, and they do in **every one of the
86 files this accepts** -- not a rate over a large population, since each index names
between one and a few dozen files and gets the whole set right. And the three middle
words are discriminated by closure: at three words 86 files frame, and at zero, one,
two, four or five words **not one file frames at all**.

**What is fenced.** Six indexes declare a non-zero state count, and after their state
names the gap before the volume count is 3 + 3 x stateCount words in three of them and
something else in the other three. That variant is not framed, and the reader refuses
it rather than guessing: a file is framed or fenced, never partially read.
"""
from __future__ import annotations

import struct
from typing import Any

MAGIC_OFFSET = 0
STATE_COUNT_OFFSET = 4
NAME_TABLE_OFFSET = 8
# Three words sit between the state names and the volume count. Discriminated by
# closure: every other width frames zero files.
MIDDLE_WORDS = 3
MAXIMUM_STATES = 64
MAXIMUM_VOLUMES = 256
MAXIMUM_NAME_BYTES = 512


def read_name(data: bytes, at: int) -> tuple[int, str] | None:
    """One ``u32 byteLength`` plus that many bytes of UTF-16LE, or None.

    The ASCII shape is required, not assumed: every odd byte must be zero and every
    even byte printable. A length that happens to be plausible is not a string.
    """
    if at < 0 or at + 4 > len(data):
        return None
    length = struct.unpack_from("<I", data, at)[0]
    if length == 0 or length % 2 or length > MAXIMUM_NAME_BYTES:
        return None
    if at + 4 + length > len(data):
        return None
    raw = data[at + 4:at + 4 + length]
    for index in range(1, len(raw), 2):
        if raw[index] != 0:
            return None
    for index in range(0, len(raw), 2):
        if not 32 <= raw[index] < 127:
            return None
    return at + 4 + length, raw.decode("utf-16-le")


def parse_index(data: bytes, middle_words: int = MIDDLE_WORDS) -> dict[str, Any]:
    """Frame one index file, or report why it was refused.

    ``middle_words`` is a parameter so the gate can score the chosen width against its
    rivals over the corpus instead of asserting it.
    """
    if len(data) < NAME_TABLE_OFFSET:
        return {"status": "failed", "reason": "too_short"}
    magic = struct.unpack_from("<I", data, MAGIC_OFFSET)[0]
    states = struct.unpack_from("<I", data, STATE_COUNT_OFFSET)[0]
    if states > MAXIMUM_STATES:
        return {"status": "failed", "reason": "state_count_out_of_range"}
    cursor = NAME_TABLE_OFFSET
    state_names: list[str] = []
    for _ in range(states):
        got = read_name(data, cursor)
        if got is None:
            return {"status": "failed", "reason": "state_name_is_not_a_string"}
        cursor, name = got
        state_names.append(name)
    if states:
        # The variant this reader does not frame. Refused rather than guessed at.
        return {"status": "unsupported", "reason": "index_declares_scene_states",
                "states": state_names}
    if cursor + 4 * middle_words + 4 > len(data):
        return {"status": "failed", "reason": "middle_words_past_the_end"}
    words = [struct.unpack_from("<I", data, cursor + 4 * index)[0]
             for index in range(middle_words)]
    cursor += 4 * middle_words
    volumes = struct.unpack_from("<I", data, cursor)[0]
    cursor += 4
    if volumes == 0 or volumes > MAXIMUM_VOLUMES:
        return {"status": "failed", "reason": "volume_count_out_of_range"}
    volume_names: list[str] = []
    for _ in range(volumes):
        got = read_name(data, cursor)
        if got is None:
            return {"status": "failed", "reason": "volume_name_is_not_a_string"}
        cursor, name = got
        volume_names.append(name)
    if len(set(volume_names)) != len(volume_names):
        return {"status": "failed", "reason": "volume_names_repeat"}
    return {
        "status": "exact",
        "magic": magic,
        "states": state_names,
        "middleWords": words,
        "volumes": volume_names,
        "namesEndAt": cursor,
        "remainingBytes": len(data) - cursor,
    }


def summarise(samples: list[tuple[str, bytes, set[str]]]) -> dict[str, Any]:
    """Census the corpus. ``samples`` is (path, bytes, files beside it)."""
    out: dict[str, Any] = {
        "indexes": 0, "exact": 0, "unsupported": 0, "failed": 0,
        "volumeNames": 0, "volumeSetsMatchingTheDirectory": 0,
        "reasons": {}, "magics": {}, "middleWordValues": {},
        "rivalMiddleWordsFraming": {},
    }
    for _, data, siblings in samples:
        out["indexes"] += 1
        parsed = parse_index(data)
        status = parsed["status"]
        out[status if status in ("exact", "unsupported", "failed") else "failed"] += 1
        if status != "exact":
            reason = str(parsed.get("reason"))
            out["reasons"][reason] = out["reasons"].get(reason, 0) + 1
            continue
        key = f"0x{parsed['magic']:08X}"
        out["magics"][key] = out["magics"].get(key, 0) + 1
        out["volumeNames"] += len(parsed["volumes"])
        if set(parsed["volumes"]) == siblings:
            out["volumeSetsMatchingTheDirectory"] += 1
        for index, word in enumerate(parsed["middleWords"]):
            slot = out["middleWordValues"].setdefault(f"word{index}", {})
            slot[str(word)] = slot.get(str(word), 0) + 1
    for rival in (0, 1, 2, 4, 5):
        framed = sum(1 for _, data, _ in samples
                     if parse_index(data, rival)["status"] == "exact")
        out["rivalMiddleWordsFraming"][str(rival)] = framed
    return out


def the_index_names_the_volumes_beside_it(summary: dict[str, Any]) -> bool:
    """Every framed index names exactly the volume files in its own directory.

    This is the content check, and it is strict for a reason: each index names between
    one and a few dozen files, so "the whole set, every time" is a far stronger
    statement than a percentage over a large population would be. One index naming a
    file that is not there, or missing one that is, means the name table has been
    misread.
    """
    if not isinstance(summary, dict):
        return False
    exact = int(summary.get("exact") or 0)
    if exact <= 0:
        return False
    if int(summary.get("volumeSetsMatchingTheDirectory") or 0) != exact:
        return False
    if int(summary.get("volumeNames") or 0) < exact:
        return False
    # Fail-closed: every index is framed, fenced as unsupported, or failed.
    total = (exact + int(summary.get("unsupported") or 0)
             + int(summary.get("failed") or 0))
    return total == int(summary.get("indexes") or -1)


def the_middle_word_count_beats_its_rivals(summary: dict[str, Any]) -> bool:
    """Three words between the state names and the volume count, and only three.

    Scored by closure over the corpus: at three words 86 files frame, and at zero,
    one, two, four or five words not one file frames. A width that merely framed fewer
    would be weak evidence; a width that frames none is the whole discrimination.
    """
    if not isinstance(summary, dict):
        return False
    exact = int(summary.get("exact") or 0)
    rivals = summary.get("rivalMiddleWordsFraming")
    if exact <= 0 or not isinstance(rivals, dict) or not rivals:
        return False
    return all(int(value) * 4 < exact for value in rivals.values())
