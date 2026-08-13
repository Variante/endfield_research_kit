from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.story_builder.object_index_io import iter_gzip_jsonl_objects


class ObjectIndexIoTests(unittest.TestCase):
    def test_reads_objects_and_rejects_non_object_rows(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            path = Path(raw_root) / "objects.jsonl.gz"
            with gzip.open(path, "wt", encoding="utf-8") as stream:
                stream.write(json.dumps({"id": 1}) + "\n\n")
            self.assertEqual(list(iter_gzip_jsonl_objects(path)), [{"id": 1}])

            with gzip.open(path, "wt", encoding="utf-8") as stream:
                stream.write("[]\n")
            with self.assertRaisesRegex(RuntimeError, "row is not an object"):
                list(iter_gzip_jsonl_objects(path, error_type=RuntimeError))


if __name__ == "__main__":
    unittest.main()
