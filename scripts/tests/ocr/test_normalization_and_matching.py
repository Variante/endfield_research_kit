import unittest

from scripts.story_recovery.ocr import extract, match


class OcrNormalizationAndMatchingTests(unittest.TestCase):
    def test_normalization_removes_markup_width_and_punctuation(self):
        self.assertEqual(match.normalize_text("<b>ＡＢＣ-123</b>"), "abc123")
        self.assertEqual(
            extract.normalize_ocr_text("  First   observed line  \nSecond line  "),
            "First observed line\nSecond line",
        )

    def test_exact_fragment_prefers_exact_corpus_line(self):
        corpus = [
            match.CorpusLine(
                key="dlg_e1_1",
                mission="e1",
                actual_mission="e1",
                link_reason="",
                kind="dlg",
                scene=1,
                line_id="dlg_e1_1_001",
                source="line",
                text="Mission start signal",
                norm="missionstartsignal",
            ),
            match.CorpusLine(
                key="dlg_e1_2",
                mission="e1",
                actual_mission="e1",
                link_reason="",
                kind="dlg",
                scene=2,
                line_id="dlg_e1_2_001",
                source="line",
                text="Mission end signal",
                norm="missionendsignal",
            ),
        ]
        rows = match.match_fragment(
            "Mission start signal",
            "missionstartsignal",
            corpus=corpus,
            gram_index=match.build_gram_index(corpus),
            topn=2,
        )
        self.assertEqual(rows[0]["key"], "dlg_e1_1")
        self.assertEqual(rows[0]["score"], 1.0)


if __name__ == "__main__":
    unittest.main()
