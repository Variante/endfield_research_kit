import unittest

from scripts.story_recovery import build_lua_audio_event_audit as audit


class LuaAudioEventAuditTests(unittest.TestCase):
    def test_exact_hash_resolution_and_similarity_never_create_alias(self) -> None:
        cache = {"references": [
            {"kind": "luaPostEvent", "name": "au_int_template_silence", "source": "a.lua", "line": 1},
            {"kind": "luaPostEvent", "name": "au_int_template_slience", "source": "b.lua", "line": 2},
        ]}
        resolved_hash = audit.fnv1_32("au_int_template_silence")
        index = {
            "wwiseEventInventory": [{"eventHash": resolved_hash, "mediaIds": [7]}],
            "eventEvidence": [{"eventId": "au_int_template_silence", "eventHash": resolved_hash}],
        }

        payload = audit.build_payload(cache, index)
        rows = {row["name"]: row for row in payload["events"]}

        self.assertEqual(rows["au_int_template_silence"]["status"], "resolvedWwiseEventObject")
        typo = rows["au_int_template_slience"]
        self.assertEqual(typo["status"], "absentWithVeryCloseResolvedName")
        self.assertEqual(typo["eventObjectOccurrences"], 0)
        self.assertEqual(typo["nearResolvedNames"][0]["name"], "au_int_template_silence")
        self.assertEqual(typo["nearResolvedNames"][0]["evidenceBoundary"], "nameSimilarityOnlyNotAnAlias")


if __name__ == "__main__":
    unittest.main()
