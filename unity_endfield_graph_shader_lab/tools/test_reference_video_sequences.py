import unittest

import reference_video_sequences as pipeline


class ReferenceVideoSequenceTests(unittest.TestCase):
    def test_markers_expand_to_next_marker_and_video_end(self):
        recording = {
            "id": "capture",
            "markers": [
                {"character": "alpha", "atSeconds": 2.5},
                {"character": "beta", "atSeconds": 5.0},
            ],
        }
        rows = pipeline.expand_segments(recording, 8.0)
        self.assertEqual((rows[0]["startSeconds"], rows[0]["endSeconds"]), (2.5, 5.0))
        self.assertEqual((rows[1]["startSeconds"], rows[1]["endSeconds"]), (5.0, 8.0))
        self.assertEqual(rows[0]["id"], "alpha_overview_01")

    def test_explicit_segment_preserves_behavior(self):
        recording = {
            "id": "focused",
            "segments": [{
                "id": "start_and_loop", "character": "endminf",
                "behavior": "ui_overview_start_then_loop",
                "startSeconds": 0, "endSeconds": 3,
            }],
        }
        row = pipeline.expand_segments(recording, 3.0)[0]
        self.assertEqual(row["behavior"], "ui_overview_start_then_loop")

    def test_explicit_segment_preserves_bounded_comparison_contract(self):
        comparison = {
            "bodyClipStartSourceFrame": 115,
            "firstVisibleSourceFrame": 114,
            "anchorUncertaintyFrames": 1,
            "unmaskedBodyStartSourceFrame": 472,
            "comparisonWidth": 1920,
            "comparisonHeight": 1080,
            "resamplingFilter": "lanczos",
        }
        recording = {
            "id": "focused",
            "segments": [{
                "id": "start_and_loop", "character": "endminf",
                "behavior": "ui_overview_start_then_loop",
                "startSeconds": 0, "endSeconds": 3,
                "comparison": comparison,
            }],
        }
        row = pipeline.expand_segments(recording, 3.0)[0]
        self.assertEqual(row["comparison"], comparison)

    def test_overlap_fails_closed(self):
        recording = {
            "id": "bad",
            "segments": [
                {"id": "one", "character": "a", "startSeconds": 0, "endSeconds": 2},
                {"id": "two", "character": "b", "startSeconds": 1, "endSeconds": 3},
            ],
        }
        with self.assertRaises(pipeline.PipelineError):
            pipeline.expand_segments(recording, 4.0)

    def test_marker_identity_evidence_is_preserved(self):
        recording = {
            "id": "capture",
            "markers": [{
                "character": "endmin", "atSeconds": 1,
                "identityStatus": "ambiguous_endminf_or_endminm",
            }],
        }
        row = pipeline.expand_segments(recording, 2.0)[0]
        self.assertEqual(row["identityStatus"], "ambiguous_endminf_or_endminm")

    def exact_frame_plan(self, fps=60.0):
        destination = pipeline.PROJECT_ROOT / "scratch" / "test-sequence"
        plan = {
            "recordingId": "focused",
            "source": pipeline.PROJECT_ROOT.parent / "videos" / "source.mkv",
            "sourceMetadata": {"width": 1920, "height": 1080, "fps": 60.0, "duration": 30.584},
            "segment": {"startFrame": 1109, "startSeconds": 18.4666667, "endSeconds": 30.584},
            "destination": destination,
            "fps": fps, "scale": None, "pixelFormat": "rgb24", "videoDecoder": "h264_cuvid",
        }
        plan["segment"].update({"id": "start_and_loop", "character": "endminf"})
        return plan

    def test_exact_start_frame_trims_before_resampling_and_enforces_end(self):
        plan = self.exact_frame_plan()
        command = pipeline.ffmpeg_command(plan, pipeline.PROJECT_ROOT / "partial")
        filters = command[command.index("-vf") + 1]
        self.assertEqual(filters, "trim=start_frame=1108:end=30.584,setpts=PTS-STARTPTS,fps=60")
        self.assertNotIn("-ss", command)
        self.assertEqual(command[command.index("-c:v") + 1], "h264_cuvid")

    def test_exact_start_frame_is_independent_of_output_rate(self):
        command = pipeline.ffmpeg_command(self.exact_frame_plan(10.0), pipeline.PROJECT_ROOT / "partial")
        filters = command[command.index("-vf") + 1]
        self.assertEqual(filters, "trim=start_frame=1108:end=30.584,setpts=PTS-STARTPTS,fps=10")

    def test_sidecar_contract_rejects_changed_segment(self):
        plan = self.exact_frame_plan()
        sidecar = pipeline.plan_contract(plan)
        sidecar["segment"] = {**sidecar["segment"], "startFrame": 1110}
        with self.assertRaisesRegex(pipeline.PipelineError, "sidecar segment"):
            pipeline.validate_sidecar_contract(plan, sidecar)

    def test_sidecar_contract_accepts_current_plan(self):
        plan = self.exact_frame_plan()
        pipeline.validate_sidecar_contract(plan, pipeline.plan_contract(plan))

    def test_sidecar_contract_rejects_changed_output_settings(self):
        plan = self.exact_frame_plan()
        sidecar = pipeline.plan_contract(plan)
        sidecar["output"] = {**sidecar["output"], "scale": "960:-2"}
        with self.assertRaisesRegex(pipeline.PipelineError, "sidecar output.scale"):
            pipeline.validate_sidecar_contract(plan, sidecar)


if __name__ == "__main__":
    unittest.main()
