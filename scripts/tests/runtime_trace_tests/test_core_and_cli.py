import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from scripts.story_recovery import runtime_trace
from scripts.story_recovery import runtime_trace_audio_import as audio_import
from scripts.story_recovery import runtime_trace_core as core
from scripts.story_recovery import runtime_trace_mission_import as mission_import


class RuntimeTraceCoreTests(unittest.TestCase):
    def test_file_hash_verification_is_profile_independent(self):
        for profile in ("mission", "audio"):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                content = profile.encode("ascii")
                (root / "binary.dat").write_bytes(content)
                manifest = {
                    "files": {
                        "binary": {
                            "relativePath": "binary.dat",
                            "bytes": len(content),
                            "sha256": hashlib.sha256(content).hexdigest(),
                        }
                    }
                }
                self.assertEqual(
                    core.verify_game_files(root, manifest)["binary"],
                    (root / "binary.dat").resolve(),
                )

    def test_jsonl_reader_reports_profile_and_line(self):
        for profile, error_type, normalize in (
            ("mission", mission_import.TraceValidationError, mission_import.normalize_event),
            ("audio", audio_import.AudioTraceValidationError, audio_import.normalize_event),
        ):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / "bad.jsonl"
                path.write_text("{bad}\n", encoding="utf-8")
                with self.assertRaisesRegex(error_type, r"bad\.jsonl:1: invalid JSON"):
                    core.read_jsonl(
                        [path],
                        label=profile,
                        normalize=normalize,
                        validation_error=error_type,
                    )


class RuntimeTraceCliTests(unittest.TestCase):
    def test_every_action_profile_pair_builds_one_parser(self):
        for action in runtime_trace.ACTIONS:
            for profile in runtime_trace.PROFILES:
                with self.subTest(action=action, profile=profile):
                    parser = runtime_trace.command_parser(action, profile)
                    self.assertIn(f"--profile {profile}", parser.usage)

    def test_profile_is_required(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            runtime_trace.parse_args(["capture"])

    def test_audio_capture_pid_is_an_explicit_attach_to_existing_process_path(self):
        parser = runtime_trace.command_parser("capture", "audio")
        help_text = parser.format_help()
        self.assertIn("already-running PID", help_text)
        self.assertIn("without attaching", help_text)
        args = runtime_trace.parse_args(
            ["capture", "--profile", "audio", "--pid", "1234", "--duration", "30"]
        )
        self.assertEqual(args.pid, 1234)
        self.assertEqual(args.duration, 30.0)

    def test_import_failure_is_reported_by_single_cli(self):
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "missing.jsonl"
            with redirect_stderr(io.StringIO()):
                result = runtime_trace.main(
                    ["import", "--profile", "mission", str(missing)]
                )
        self.assertEqual(result, 1)

    def test_both_import_profiles_publish_through_single_cli(self):
        schemas = {
            "mission": mission_import.EVENT_SCHEMA,
            "audio": audio_import.EVENT_SCHEMA,
        }
        for profile, schema in schemas.items():
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                trace = root / "capture.jsonl"
                output = root / "bundle.json"
                rows = [
                    {
                        "schema": schema,
                        "sessionId": "fixture",
                        "seq": 0,
                        "monotonicMs": 0,
                        "kind": "session_start",
                        "gameBuild": "fixture",
                        "captureTool": "fixture",
                    },
                    {
                        "schema": schema,
                        "sessionId": "fixture",
                        "seq": 1,
                        "monotonicMs": 1,
                        "kind": "session_end",
                    },
                ]
                trace.write_text(
                    "\n".join(json.dumps(row) for row in rows) + "\n",
                    encoding="utf-8",
                )
                arguments = [
                    "import",
                    "--profile",
                    profile,
                    str(trace),
                    "--output",
                    str(output),
                ]
                if profile == "audio":
                    arguments.extend(
                        [
                            "--audio-index",
                            str(root / "missing-audio-index.json"),
                            "--trigger-contexts",
                            str(root / "missing-trigger-contexts.json"),
                        ]
                    )
                with redirect_stdout(io.StringIO()):
                    result = runtime_trace.main(arguments)
                self.assertEqual(result, 0)
                self.assertTrue(output.is_file())
                self.assertTrue(output.with_suffix(".md").is_file())


if __name__ == "__main__":
    unittest.main()
