"""Local managed request/result facts from an independently admitted capture.

The adapter retains event ID and audio object ID at call entry, copies the
external string as bounded ASCII, and records the returned playing ID plus
callback-type argument at exit. The declared v3 external-post ABI additionally
retains the original cookie and raw Beyond codec argument; earlier recipes
do not. Neither recipe supplies an asynchronous native ownership join.
"""
from collections import Counter

from scripts.webui.audio.semantics import runtime_capture_import as payload


SCHEMA = "endfield.audio-managed-post-observations.v1"
BOUNDARY = (
    "Event ID, audio object ID and external-path projection belong to one managed call; "
    "the paired result records its returned playing ID and callback-type argument. "
    "A nonzero playing ID is not decoded PCM or audibility. Original external cookie and raw "
    "Beyond codec argument are reported only under the declared v3 external-post ABI; older "
    "recipes did not record them. These arguments do not identify a game codec instance. "
    "No asynchronous native entry is joined to these requests."
)


def summarize(pairs: dict[int, dict[int, dict]], hooks: list[dict], *, sample_limit: int = 32) -> dict:
    """Validate typed adapter pairs after the surrounding native/session gate."""
    if type(sample_limit) is not int or not 0 <= sample_limit <= 128:
        raise ValueError("managed post sample limit must be between zero and 128")
    counts, callback_types, path_states = Counter(), Counter(), Counter()
    event_ids, object_ids, paths, samples = set(), set(), set(), []
    declared = {hook["name"]: index for index, hook in enumerate(hooks)}

    def integer(row, name, maximum):
        value = row.get(name)
        if type(value) is not int or not 0 <= value <= maximum:
            raise ValueError(f"managed post {row.get('captureId')}: invalid {name}")
        return value

    for capture_id, phases in sorted(pairs.items()):
        if set(phases) != {payload.KIND_CALL, payload.KIND_RESULT}:
            raise ValueError(f"managed post {capture_id}: missing call/result phase")
        entry, result = phases[payload.KIND_CALL], phases[payload.KIND_RESULT]
        name = entry.get("hookName")
        if name not in (payload.POST_HOOK, payload.POST_EXTERNAL_HOOK) or name not in declared:
            raise ValueError(f"managed post {capture_id}: undeclared hook")
        for phase, row in phases.items():
            if row.get("captureId") != capture_id or row.get("kind") != phase:
                raise ValueError(f"managed post {capture_id}: phase identity differs")
            if row.get("hookName") != name or row.get("hookIndex") != declared[name]:
                raise ValueError(f"managed post {capture_id}: hook identity differs from recipe")
            for field, maximum in (("captureId", 2**64-1), ("parentCaptureId", 2**64-1),
                                   ("nestingId", 2**32-1), ("flags", 2**32-1)):
                integer(row, field, maximum)
        if (result["parentCaptureId"] != entry["parentCaptureId"]
                or result["nestingId"] != entry["nestingId"]
                or not result["flags"] & 4 or result["flags"] & 2):
            raise ValueError(f"managed post {capture_id}: unresolved or inconsistent adapter pair")
        event_id = integer(entry, "pointerFact0", 2**32-1)
        object_id = integer(entry, "pointerFact1", 2**64-1)
        playing_id = integer(result, "returnValue", 2**32-1)
        callback_type = integer(result, "resultCode", 2**32-1)
        path = entry.get("keyOrPath")
        if not isinstance(path, str) or result.get("keyOrPath") != path:
            raise ValueError(f"managed post {capture_id}: retained text differs")
        if len(path) >= payload.KEY_OR_PATH_BYTES or any(ord(char) > 127 for char in path):
            raise ValueError(f"managed post {capture_id}: invalid bounded ASCII projection")
        if name == payload.POST_HOOK and path:
            raise ValueError(f"managed post {capture_id}: regular post carries external text")
        counts["postPairs"] += 1
        counts["nonzeroPlayingIdPairs" if playing_id else "zeroPlayingIdPairs"] += 1
        event_ids.add(event_id); object_ids.add(object_id)
        callback_types[str(callback_type)] += 1
        sample = {"captureId": capture_id, "hookName": name, "eventId": event_id,
                  "audioObjectId": str(object_id), "returnedPlayingId": playing_id,
                  "callbackType": callback_type}
        if name == payload.POST_EXTERNAL_HOOK:
            counts["externalSourcePairs"] += 1
            state = ("unavailable" if not path else "lossyOrTruncated" if "?" in path
                     or len(path) >= payload.KEY_OR_PATH_BYTES - 1
                     or entry.get("truncated") or result.get("truncated")
                     else "completeAsciiProjection")
            path_states[state] += 1
            sample.update(externalPathProjection=path, externalPathState=state)
            if state == "completeAsciiProjection":
                paths.add(path)
            if hooks[declared[name]].get("abiId") == "win64.il2cpp_post_event_external_source.v3":
                sample["externalCookie"] = integer(result, "pointerFact0", 2**32-1)
                sample["rawBeyondCodecArgument"] = integer(result, "pointerFact1", 2**32-1)
                counts["recordedExternalArgumentPairs"] += 1
        if len(samples) < sample_limit:
            samples.append(sample)
    return {"schema": SCHEMA, "status": "validated", "counts": dict(counts),
            "distinctEventIdCount": len(event_ids), "distinctAudioObjectIdCount": len(object_ids),
            "distinctCompleteExternalPathCount": len(paths), "externalPathStates": dict(path_states),
            "callbackTypeCounts": dict(callback_types), "samples": samples,
            "samplesTruncated": len(pairs) > len(samples), "evidenceBoundary": BOUNDARY}
