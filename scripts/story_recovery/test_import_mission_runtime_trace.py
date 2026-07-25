import json
import tempfile
import unittest
from pathlib import Path


from scripts.story_recovery import import_mission_runtime_trace as runtime_trace


SCHEMA = runtime_trace.EVENT_SCHEMA


def event(kind, seq, **values):
    return {
        "schema": SCHEMA,
        "sessionId": "capture-1",
        "seq": seq,
        "monotonicMs": seq * 10,
        "kind": kind,
        **values,
    }


class MissionRuntimeTraceTests(unittest.TestCase):
    def write_trace(self, rows):
        temporary = tempfile.TemporaryDirectory()
        path = Path(temporary.name) / "trace.jsonl"
        path.write_text(
            "\n".join(json.dumps(row) for row in rows) + "\n",
            encoding="utf-8",
        )
        self.addCleanup(temporary.cleanup)
        return path

    def test_exact_chain_keeps_active_quest_as_observed_context_only(self):
        path = self.write_trace([
            event("session_start", 0, gameBuild="1.0", captureTool="fixture"),
            event(
                "mission_state", 1, missionId="e11m1", state="Processing", active=True,
            ),
            event(
                "quest_state", 2, missionId="e11m1", questId="e11m1_q1",
                state="Processing", active=True,
            ),
            event(
                "levelscript_event", 3, chainId="chain-1", levelId="map_test",
                scriptId="7001", headerLocalId=4, eventName="LevelEvent_OnBattleSignal",
                selector={"signalId": "story_start"},
            ),
            event(
                "action_enter", 4, chainId="chain-1", levelId="map_test",
                scriptId="7001", headerLocalId=4, actionLocalId=5,
                actionType="PlayRadio",
            ),
            event(
                "story_playback", 5, chainId="chain-1", storyKey="radio_e11m1_1",
                playbackType="radio",
            ),
            event("session_end", 6),
        ])

        bundle = runtime_trace.normalize_files([path])

        observation = bundle["storyObservations"]["radio_e11m1_1"][0]
        self.assertEqual(observation["triggerStatus"], "exact_event_action_chain")
        self.assertEqual(observation["ownershipStatus"], "observed_active_quest_context")
        self.assertEqual(observation["activeQuests"][0]["questId"], "e11m1_q1")
        self.assertEqual([row["kind"] for row in observation["route"]], [
            "levelscript_event", "action_enter",
        ])
        self.assertIn("not authored ownership", bundle["evidencePolicy"]["ownership"])

    def test_observed_sequence_aggregates_forks_without_authored_promotion(self):
        rows = [
            event("session_start", 0, gameBuild="1.0", captureTool="fixture"),
            event(
                "mission_state", 1, missionId="e11m1", state="Processing", active=True,
            ),
            event(
                "story_playback", 2, chainId=None, storyKey="dlg_e11m1_1",
                playbackType="dialog",
            ),
            event(
                "story_playback", 3, chainId=None, storyKey="dlg_e11m1_2",
                playbackType="dialog",
            ),
            event("session_end", 4),
        ]
        second = [dict(row, sessionId="capture-2") for row in rows]
        second[3]["storyKey"] = "dlg_e11m1_3"
        first_path = self.write_trace(rows)
        second_path = self.write_trace(second)

        bundle = runtime_trace.normalize_files([first_path, second_path])

        self.assertEqual(bundle["summary"]["sessions"], 2)
        self.assertEqual(bundle["summary"]["observedForks"], 1)
        self.assertEqual(bundle["observedForks"], [{
            "source": "dlg_e11m1_1",
            "targets": ["dlg_e11m1_2", "dlg_e11m1_3"],
        }])
        self.assertTrue(all(
            edge["evidence"] == "observed_runtime_sequence"
            for edge in bundle["observedEdges"]
        ))

    def test_missing_explicit_chain_id_is_rejected(self):
        path = self.write_trace([
            event("session_start", 0, gameBuild="1.0", captureTool="fixture"),
            event(
                "story_playback", 1, storyKey="dlg_e11m1_1", playbackType="dialog",
            ),
        ])

        with self.assertRaisesRegex(runtime_trace.TraceValidationError, "chainId must be present"):
            runtime_trace.normalize_files([path])

    def test_unknown_runtime_header_id_must_be_explicit_null(self):
        path = self.write_trace([
            event("session_start", 0, gameBuild="1.0", captureTool="fixture"),
            event(
                "levelscript_event", 1, chainId="chain-1", levelId="map_test",
                scriptId="7001", headerLocalId=None,
                eventName="GameScriptEvent#42",
            ),
        ])

        bundle = runtime_trace.normalize_files([path])

        self.assertEqual(bundle["summary"]["events"], 2)

    def test_levelscript_task_events_preserve_identity_without_ownership_promotion(self):
        path = self.write_trace([
            event("session_start", 0, gameBuild="1.0", captureTool="fixture"),
            event(
                "levelscript_task", 1,
                taskEvent="objective_progress_send",
                direction="client_to_server",
                messageId=105,
                message="CS_SCENE_UPDATE_SCRIPT_TASK_PROGRESS",
                sceneNumId=12,
                scriptId="7001",
                taskId="task-a",
                conditionId="condition-b",
                progress=1,
            ),
            event(
                "levelscript_event", 2, chainId="chain-1", levelId="map_test",
                scriptId="7001", headerLocalId=None,
                eventName="GameScriptEvent#42",
                selector={
                    "gameScriptEventValue": 42,
                    "taskContext": {
                        "taskEvent": "state_update",
                        "messageId": 813,
                        "taskId": "task-a",
                    },
                },
            ),
            event(
                "levelscript_task", 3,
                taskEvent="condition_completion_applied",
                direction="server_to_client",
                messageId=815,
                message="SC_SCENE_LEVEL_SCRIPT_TASK_PROGRESS_UPDATE",
                sceneNumId=12,
                scriptId="7001",
                taskId="task-a",
                conditionId="condition-b",
                conditionCompleted=True,
            ),
            event("session_end", 4),
        ])

        bundle = runtime_trace.normalize_files([path])

        self.assertEqual(bundle["summary"]["levelScriptTaskEvents"], 2)
        self.assertEqual(bundle["summary"]["exactTaskIdentityEvents"], 2)
        task = bundle["levelScriptTaskEvents"]["capture-1"][0]
        self.assertEqual(task["taskId"], "task-a")
        self.assertEqual(task["conditionId"], "condition-b")
        self.assertNotIn("missionId", task)
        completion = bundle["levelScriptTaskEvents"]["capture-1"][1]
        self.assertTrue(completion["conditionCompleted"])
        self.assertIn("no mission or quest", bundle["evidencePolicy"]["tasks"])

    def test_non_script_done_task_event_requires_explicit_task_id(self):
        path = self.write_trace([
            event("session_start", 0, gameBuild="1.0", captureTool="fixture"),
            event(
                "levelscript_task", 1,
                taskEvent="state_update",
                direction="server_to_client",
                messageId=813,
                sceneNumId=12,
                scriptId="7001",
                taskId=None,
                taskState=2,
            ),
        ])

        with self.assertRaisesRegex(runtime_trace.TraceValidationError, "requires taskId"):
            runtime_trace.normalize_files([path])

    def test_non_increasing_sequence_is_rejected(self):
        path = self.write_trace([
            event("session_start", 1, gameBuild="1.0", captureTool="fixture"),
            event(
                "mission_state", 1, missionId="e11m1", state="Processing", active=True,
            ),
        ])

        with self.assertRaisesRegex(runtime_trace.TraceValidationError, "not strictly increasing"):
            runtime_trace.normalize_files([path])


if __name__ == "__main__":
    unittest.main()
