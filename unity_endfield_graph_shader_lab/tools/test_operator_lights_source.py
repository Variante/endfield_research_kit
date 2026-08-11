#!/usr/bin/env python3
"""Tests for actor-scoped operator-light source hashing."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from operator_lights_source import scoped_payload, scoped_sha256


class OperatorLightsSourceTests(unittest.TestCase):
    def test_scope_is_deterministic_and_excludes_other_actors(self) -> None:
        payload = {
            "actors": {
                "wulfa": {"lights": [1, 2]},
                "liino": {"lights": [3]},
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "operator_lights.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            first = scoped_sha256(path, ("wulfa",))
            payload["actors"]["liino"]["lights"].append(4)
            path.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(first, scoped_sha256(path, ("wulfa",)))

    def test_missing_scoped_actor_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing scoped actors: wulfa"):
            scoped_payload({"actors": {}}, ("wulfa",))


if __name__ == "__main__":
    unittest.main()
