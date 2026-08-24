from __future__ import annotations

import unittest
from pathlib import Path

from scripts.audio_semantics import dialog_lifecycle


class DialogLifecycleAudioTests(unittest.TestCase):
    def test_projects_only_playable_exact_existing_conversations(self):
        base = {
            "semanticKind": "dialogLifecycle",
            "triggerRole": "DialogPostEnterAudioEvent",
            "situation": {"dialogId": "dlg_test", "lifecyclePhase": "postEnterEvents", "arrayIndex": 0, "eventId": "hashed-event:0x1", "eventHash": 1, "tablePath": "dlg_test.postEnterEvents[0]"},
            "action": {"runtimeMethod": "_OnPostEnterDialog", "runtimeMethodToken": "0x1"},
            "owner": {"ownerStatus": "exactDialogIdAndLifecycleField"},
            "selection": {"triggerBindingStatus": "exactAudioDialogCustomEventTable"},
            "evidence": {"requestEvidence": ["exactAudioDialogCustomEventTableField"]},
            "runtimeActivationStatus": "dialogLifecycleRuntimeExecutionNotObserved",
            "mediaRefs": [{"mediaId": 7, "src": "/audio/7.flac"}],
        }
        missing = {**base, "situation": {**base["situation"], "dialogId": "dlg_missing"}}
        no_media = {**base, "situation": {**base["situation"], "eventId": "hashed-event:0x2"}, "mediaRefs": []}
        result = dialog_lifecycle.project_story_lifecycle_audio(
            [base, missing, no_media], ["dlg_test"],
        )
        rows = result["conversations"]["dlg_test"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["lifecyclePhase"], "postEnterEvents")
        self.assertEqual(rows[0]["mediaRefs"][0]["mediaId"], 7)
        self.assertEqual(rows[0]["ownerStatus"], "exactDialogIdAndLifecycleField")
        self.assertEqual(result["counts"]["missingConversationContexts"], 1)

    def test_existing_story_conversation_renderer_exposes_lifecycle_rows(self):
        root = Path(__file__).resolve().parents[2]
        source = (root / "webui" / "app.js").read_text(encoding="utf-8")
        labels = (root / "webui" / "app_labels.js").read_text(encoding="utf-8")
        self.assertIn("renderDialogLifecycleAudioBlock", source)
        self.assertIn("dialogLifecycleAudio", source)
        self.assertIn("dialogLifecycleAudioNote", labels)


if __name__ == "__main__":
    unittest.main()
