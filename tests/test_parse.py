#!/usr/bin/env python3
"""Offline unit tests — no network, no yt-dlp/ffmpeg required."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sample.json3"


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ft = load_script("fetch_transcript")
ef = load_script("extract_frames")


class TestFmtTs(unittest.TestCase):
    def test_hours(self):
        self.assertEqual(ft.fmt_ts(3725), "1:02:05")

    def test_minutes(self):
        self.assertEqual(ft.fmt_ts(65), "1:05")

    def test_zero(self):
        self.assertEqual(ft.fmt_ts(0), "0:00")


class TestParseJson3(unittest.TestCase):
    def test_fixture(self):
        events = ft.parse_json3(FIXTURE)
        # whitespace-only and segs-less events are dropped
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0], (0.0, "hello world"))
        # segments joined, internal whitespace collapsed
        self.assertEqual(events[1], (2.5, "this is a test"))
        self.assertEqual(events[2], (9.0, "after a gap"))


class TestParagraphs(unittest.TestCase):
    def test_gap_splits(self):
        events = ft.parse_json3(FIXTURE)
        paras = ft.events_to_paragraphs(events)
        # 6.5s silence > PARA_GAP_S starts a new paragraph
        self.assertEqual(len(paras), 2)
        self.assertEqual(paras[0], (0.0, "hello world this is a test"))
        self.assertEqual(paras[1], (9.0, "after a gap"))

    def test_duration_splits(self):
        events = [(0.0, "a"), (2.0, "b"), (2.0 + ft.PARA_MAX_S, "c")]
        paras = ft.events_to_paragraphs(events)
        self.assertEqual(len(paras), 2)

    def test_empty(self):
        self.assertEqual(ft.events_to_paragraphs([]), [])


class TestResolveLangs(unittest.TestCase):
    def test_auto_puts_video_lang_first(self):
        self.assertEqual(ft.resolve_langs("auto", "ja"), ["ja", "vi", "en"])

    def test_auto_without_video_lang(self):
        self.assertEqual(ft.resolve_langs("auto", None), ["vi", "en"])

    def test_explicit_list_dedupes(self):
        self.assertEqual(ft.resolve_langs("ko, auto", "en"), ["ko", "en", "vi"])


def _info(lang=None, subs=(), autos=()):
    return {"language": lang,
            "subtitles": {k: [] for k in subs},
            "automatic_captions": {k: [] for k in autos}}


class TestSelectCaptionTrack(unittest.TestCase):
    def test_manual_in_preferred_lang(self):
        info = _info("en", subs=["en", "vi"], autos=["en-orig", "en", "vi"])
        self.assertEqual(ft.select_caption_track(info, ["vi", "en"]), ("vi", "manual", "vi"))

    def test_regional_variant_matches(self):
        info = _info("en", subs=["en-US"])
        self.assertEqual(ft.select_caption_track(info, ["en"]), ("en-US", "manual", "en-US"))

    def test_asr_in_spoken_lang(self):
        info = _info("vi", autos=["vi-orig", "vi", "en"])
        self.assertEqual(ft.select_caption_track(info, ["vi", "en"]), ("vi-orig", "auto", "vi"))

    def test_asr_without_orig_suffix(self):
        info = _info("vi", autos=["vi", "en"])
        self.assertEqual(ft.select_caption_track(info, ["vi"]), ("vi", "auto", "vi"))

    def test_no_translation_by_default(self):
        # English talk, user prefers Vietnamese: use English ASR, not machine-translated vi.
        info = _info("en", autos=["en-orig", "en", "vi"])
        self.assertEqual(ft.select_caption_track(info, ["vi"]), ("en-orig", "auto", "en"))

    def test_translation_when_allowed(self):
        info = _info("en", autos=["en-orig", "en", "vi"])
        self.assertEqual(ft.select_caption_track(info, ["vi"], allow_translated=True),
                         ("vi", "auto-translated", "vi"))

    def test_fallback_prefers_manual_original(self):
        info = _info("ja", subs=["ja", "fr"], autos=["ja-orig"])
        self.assertEqual(ft.select_caption_track(info, ["vi"]), ("ja", "manual", "ja"))

    def test_live_chat_ignored(self):
        info = _info(None, subs=["live_chat"])
        self.assertEqual(ft.select_caption_track(info, ["vi", "en"]), (None, None, None))


class TestEstimateTokens(unittest.TestCase):
    def test_vietnamese_costs_more_than_english(self):
        text = "một hai ba bốn năm"
        self.assertGreater(ft.estimate_tokens(text, "vi"), ft.estimate_tokens(text, "en"))

    def test_no_space_scripts_count_characters(self):
        self.assertEqual(ft.estimate_tokens("日本語 です", "ja"), 5)

    def test_regional_code(self):
        self.assertEqual(ft.estimate_tokens("a b", "en-US"), ft.estimate_tokens("a b", "en"))


class TestSubsample(unittest.TestCase):
    def test_keeps_first_last_and_deletes_rest(self):
        with tempfile.TemporaryDirectory() as td:
            frames = []
            for i in range(10):
                f = Path(td) / f"f{i:04d}.jpg"
                f.touch()
                frames.append((f, float(i)))
            kept = ef.subsample(frames, 4)
            self.assertEqual(len(kept), 4)
            self.assertEqual(kept[0][1], 0.0)
            self.assertEqual(kept[-1][1], 9.0)
            self.assertEqual(len(list(Path(td).glob("*.jpg"))), 4)

    def test_under_cap_untouched(self):
        frames = [(Path(f"f{i}.jpg"), float(i)) for i in range(3)]
        self.assertEqual(ef.subsample(frames, 4), frames)


if __name__ == "__main__":
    unittest.main(verbosity=2)
