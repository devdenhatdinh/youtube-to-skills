#!/usr/bin/env python3
"""
fetch_transcript.py — video/playlist YouTube → transcript sạch, có mốc thời gian,
dùng cho youtube-to-skill. Hỗ trợ video ở mọi ngôn ngữ (tiếng Việt, Anh, Nhật, ...).

Cần: yt-dlp trên PATH (https://github.com/yt-dlp/yt-dlp)

Kết quả (trong --workdir, mặc định <tempdir>/yt_skill_work):
  full_text.txt   — transcript gộp của mọi video, có header từng video,
                    mốc chương YouTube dạng dòng '## CHAPTER:',
                    và mốc thời gian [H:MM:SS] đầu mỗi đoạn.
  metadata.json   — metadata từng video (tiêu đề, kênh, thời lượng, chương,
                    loại phụ đề manual/auto/auto-translated, ngôn ngữ phụ đề,
                    số từ, ước tính token) + tổng.

Chọn phụ đề (--lang, mặc định "auto"):
  "auto"     → ngôn ngữ gốc của video, rồi vi, rồi en.
  "vi,en"    → danh sách ưu tiên, phân tách bằng dấu phẩy.
  Thứ tự: phụ đề thủ công theo ưu tiên → phụ đề tự động (ASR) của ngôn ngữ gốc
  → phụ đề thủ công bất kỳ. Phụ đề dịch máy của YouTube chỉ dùng khi có
  --allow-translated (chất lượng kém; agent tự dịch tốt hơn).

Cách dùng:
  python3 fetch_transcript.py URL [URL ...] [--lang auto] [--workdir DIR]
                              [--max-videos N] [--allow-translated] [--check]
  python3 fetch_transcript.py --search "TỪ KHÓA" [--max-results 8]
      → in kết quả tìm kiếm dạng JSON (không tải transcript); chọn URL
        rồi chạy lại với các URL đó.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PARA_GAP_S = 4.0      # start a new paragraph after a silence gap this long
PARA_MAX_S = 45.0     # or when the running paragraph exceeds this duration

DEFAULT_LANGS = ["vi", "en"]
# Scripts written without spaces between words: token cost tracks characters.
NO_SPACE_LANGS = {"zh", "ja", "th", "lo", "km", "my", "yue"}
# Approximate tokens per whitespace-separated word, by language.
TOKENS_PER_WORD = {"en": 1.35, "vi": 1.8}
TOKENS_PER_WORD_DEFAULT = 1.6
TOKENS_PER_CHAR_NO_SPACE = 1.0


def setup_utf8_io():
    # Windows consoles/pipes default to a legacy code page; Vietnamese and CJK
    # titles would raise UnicodeEncodeError without this.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def die(msg: str, code: int = 1):
    print(f"LỖI: {msg}", file=sys.stderr)
    sys.exit(code)


def fmt_ts(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def run(cmd: list) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def base_lang(code: str) -> str:
    """'en-US' → 'en', 'vi-orig' → 'vi', 'zh-Hans' → 'zh'."""
    return (code or "").split("-")[0].lower()


def check_env():
    ytdlp = shutil.which("yt-dlp")
    if not ytdlp:
        print("yt-dlp : THIẾU → cài bằng: winget install yt-dlp.yt-dlp  (Windows)"
              " | brew install yt-dlp  (macOS) | pipx install yt-dlp  (Linux)")
        sys.exit(1)
    ver = run(["yt-dlp", "--version"]).stdout.strip()
    print(f"yt-dlp : OK ({ver}) tại {ytdlp}")
    print("mạng   : chưa kiểm tra — lần tải thật đầu tiên sẽ cho biết")


def search_videos(query: str, max_results: int) -> list:
    """YouTube search via yt-dlp's ytsearch pseudo-URL; returns result dicts."""
    p = run(["yt-dlp", "--flat-playlist", "-J", "--no-warnings",
             f"ytsearch{max_results}:{query}"])
    if p.returncode != 0:
        die(f"tìm kiếm thất bại:\n{p.stderr.strip()[-800:]}")
    entries = [e for e in (json.loads(p.stdout).get("entries") or []) if e]
    return [{
        "title": e.get("title"),
        "channel": e.get("channel") or e.get("uploader"),
        "duration": fmt_ts(e["duration"]) if e.get("duration") else None,
        "views": e.get("view_count"),
        "url": e.get("url") or f"https://www.youtube.com/watch?v={e['id']}",
    } for e in entries]


def list_videos(url: str, max_videos: int) -> list:
    """Expand a URL (single video or playlist) into a list of video URLs."""
    p = run(["yt-dlp", "--flat-playlist", "-J", "--no-warnings", url])
    if p.returncode != 0:
        die(f"yt-dlp không đọc được {url}\n{p.stderr.strip()[-800:]}")
    info = json.loads(p.stdout)
    if info.get("_type") == "playlist":
        entries = [e for e in info.get("entries") or [] if e]
        urls = [e.get("url") or f"https://www.youtube.com/watch?v={e['id']}" for e in entries]
        if len(urls) > max_videos:
            print(f"LƯU Ý: playlist có {len(urls)} video; chỉ lấy {max_videos} video đầu "
                  f"(tăng bằng --max-videos)", file=sys.stderr)
            urls = urls[:max_videos]
        return urls
    return [url]


def get_info(url: str) -> dict:
    p = run(["yt-dlp", "-J", "--no-playlist", "--no-warnings", url])
    if p.returncode != 0:
        die(f"yt-dlp không lấy được metadata của {url}\n{p.stderr.strip()[-800:]}")
    return json.loads(p.stdout)


def resolve_langs(spec: str, video_lang: str = None) -> list:
    """Turn a --lang spec into an ordered, de-duplicated list of language codes.

    'auto' (anywhere in the list) expands to the video's original language
    followed by the defaults (vi, en).
    """
    out = []
    for part in (spec or "auto").split(","):
        part = part.strip()
        if not part:
            continue
        items = ([video_lang] if video_lang else []) + DEFAULT_LANGS if part == "auto" else [part]
        for code in items:
            if code and code not in out:
                out.append(code)
    return out


def _match(tracks: dict, lang: str):
    """Track key for `lang` in a subtitles dict: exact key first, then regional variants."""
    if lang in tracks:
        return lang
    want = base_lang(lang)
    for key in sorted(tracks):
        if base_lang(key) == want and not key.endswith("-orig"):
            return key
    return None


def source_asr_track(info: dict):
    """(key, lang) of the auto-caption track in the video's spoken language, if any.

    YouTube's automatic_captions holds the real speech recognition track plus
    machine translations of it into every other language. yt-dlp marks the
    real one with an '-orig' suffix; older outputs only have info['language'].
    """
    autos = info.get("automatic_captions") or {}
    for key in sorted(autos):
        if key.endswith("-orig"):
            return key, key[:-len("-orig")]
    orig = info.get("language")
    if orig:
        key = _match(autos, orig)
        if key:
            return key, orig
    return None, None


def select_caption_track(info: dict, langs: list, allow_translated: bool = False):
    """Pick the best caption track. Returns (key, kind, lang) or (None, None, None).

    kind is 'manual', 'auto' (speech recognition in the spoken language), or
    'auto-translated' (YouTube machine translation; only with allow_translated).
    """
    subs = {k: v for k, v in (info.get("subtitles") or {}).items() if k != "live_chat"}
    autos = info.get("automatic_captions") or {}
    asr_key, asr_lang = source_asr_track(info)

    # 1. Manual subtitles in a preferred language.
    for lang in langs:
        key = _match(subs, lang)
        if key:
            return key, "manual", key
    # 2. Speech recognition, if the video is spoken in a preferred language.
    if asr_key and any(base_lang(l) == base_lang(asr_lang) for l in langs):
        return asr_key, "auto", asr_lang
    # 3. Machine translation into a preferred language, only when asked for.
    if allow_translated and asr_key:
        for lang in langs:
            key = _match(autos, lang)
            if key:
                return key, "auto-translated", key
    # 4. Fallback: any real transcript beats nothing. The agent reads any
    #    language and answers in the user's language.
    orig = info.get("language")
    key = (_match(subs, orig) if orig else None) or _match(subs, "en")
    if key:
        return key, "manual", key
    if asr_key:
        return asr_key, "auto", asr_lang
    if subs:
        key = sorted(subs)[0]
        return key, "manual", key
    return None, None, None


def download_captions(url: str, video_id: str, key: str, kind: str, workdir: Path):
    """Download one caption track as json3. Returns its path or None."""
    flag = "--write-subs" if kind == "manual" else "--write-auto-subs"
    target = workdir / f"{video_id}.{key}.json3"
    target.unlink(missing_ok=True)
    run(["yt-dlp", "--skip-download", "--no-playlist", "--no-warnings", flag,
         "--sub-langs", key, "--sub-format", "json3",
         "-o", str(workdir / "%(id)s.%(ext)s"), url])
    return target if target.exists() else None


def parse_json3(path: Path) -> list:
    """json3 → list of (start_seconds, text) caption events."""
    data = json.loads(path.read_text(encoding="utf-8"))
    events = []
    for ev in data.get("events", []):
        segs = ev.get("segs")
        if not segs or "tStartMs" not in ev:
            continue
        text = "".join(s.get("utf8", "") for s in segs)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            events.append((ev["tStartMs"] / 1000.0, text))
    return events


def events_to_paragraphs(events: list) -> list:
    """Group caption events into (start_ts, paragraph_text) chunks."""
    paras = []
    cur_start, cur_parts, last_t = None, [], None
    for t, text in events:
        if cur_start is None:
            cur_start, cur_parts = t, [text]
        elif (t - last_t) > PARA_GAP_S or (t - cur_start) > PARA_MAX_S:
            paras.append((cur_start, " ".join(cur_parts)))
            cur_start, cur_parts = t, [text]
        else:
            cur_parts.append(text)
        last_t = t
    if cur_parts:
        paras.append((cur_start, " ".join(cur_parts)))
    return paras


def estimate_tokens(text: str, lang: str) -> int:
    """Rough token count; Vietnamese and no-space scripts cost more than English."""
    base = base_lang(lang)
    if base in NO_SPACE_LANGS:
        return int(len(re.sub(r"\s+", "", text)) * TOKENS_PER_CHAR_NO_SPACE)
    return int(len(text.split()) * TOKENS_PER_WORD.get(base, TOKENS_PER_WORD_DEFAULT))


def render_video(info: dict, paras: list, kind: str, lang: str = None) -> str:
    """One video's section of full_text.txt, with chapter markers inlined."""
    title = info.get("title", "Untitled")
    chapters = info.get("chapters") or []
    lines = [
        "=" * 78,
        f"=== VIDEO: {title}",
        f"=== Channel: {info.get('uploader') or info.get('channel', '?')}"
        f" | Duration: {fmt_ts(info.get('duration') or 0)}"
        f" | Captions: {kind}" + (f" ({lang})" if lang else ""),
        f"=== URL: {info.get('webpage_url', '')}",
        "=" * 78,
        "",
    ]
    if chapters:
        lines.append("--- YouTube chapter map ---")
        for ch in chapters:
            lines.append(f"  [{fmt_ts(ch['start_time'])}] {ch.get('title', '')}")
        lines.append("")

    ch_iter = iter(chapters)
    next_ch = next(ch_iter, None)
    for start, text in paras:
        while next_ch and start >= next_ch["start_time"]:
            lines.append("")
            lines.append(f"## CHAPTER: {next_ch.get('title', '')} [{fmt_ts(next_ch['start_time'])}]")
            lines.append("")
            next_ch = next(ch_iter, None)
        lines.append(f"[{fmt_ts(start)}] {text}")
    lines.append("")
    return "\n".join(lines)


def main():
    setup_utf8_io()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("urls", nargs="*", help="URL video hoặc playlist YouTube")
    ap.add_argument("--lang", default="auto",
                    help="ngôn ngữ phụ đề ưu tiên, vd 'vi,en' hoặc 'auto' "
                         "(= ngôn ngữ gốc của video, rồi vi, en; mặc định: auto)")
    ap.add_argument("--allow-translated", action="store_true",
                    help="cho phép dùng phụ đề dịch máy của YouTube khi không có phụ đề "
                         "gốc theo ngôn ngữ ưu tiên")
    ap.add_argument("--workdir", default=None, help="thư mục làm việc")
    ap.add_argument("--max-videos", type=int, default=25, help="giới hạn số video playlist (mặc định: 25)")
    ap.add_argument("--search", default=None, metavar="QUERY",
                    help="tìm trên YouTube và in kết quả JSON (không tải transcript)")
    ap.add_argument("--max-results", type=int, default=8, help="số kết quả tìm kiếm (mặc định: 8)")
    ap.add_argument("--check", action="store_true", help="kiểm tra môi trường rồi thoát")
    args = ap.parse_args()

    if args.check:
        check_env()
        return
    if not shutil.which("yt-dlp"):
        die("không tìm thấy yt-dlp trên PATH (chạy --check để xem cách cài)")
    if args.search:
        print(json.dumps(search_videos(args.search, args.max_results),
                         indent=2, ensure_ascii=False))
        return
    if not args.urls:
        ap.error("cần ít nhất một URL (hoặc dùng --search / --check)")

    workdir = Path(args.workdir) if args.workdir else Path(tempfile.gettempdir()) / "yt_skill_work"
    workdir.mkdir(parents=True, exist_ok=True)

    video_urls = []
    for u in args.urls:
        video_urls.extend(list_videos(u, args.max_videos))
    print(f"Số video cần xử lý: {len(video_urls)}", file=sys.stderr)

    sections, sources = [], []
    for i, vurl in enumerate(video_urls, 1):
        info = get_info(vurl)
        vid, title = info.get("id", f"v{i}"), info.get("title", "Untitled")
        video_lang = info.get("language")
        print(f"[{i}/{len(video_urls)}] {title}", file=sys.stderr)
        source = {"id": vid, "title": title, "url": info.get("webpage_url", vurl),
                  "channel": info.get("uploader"), "duration_s": info.get("duration"),
                  "video_lang": video_lang,
                  "chapters": [c.get("title") for c in info.get("chapters") or []]}

        langs = resolve_langs(args.lang, video_lang)
        key, kind, cap_lang = select_caption_track(info, langs, args.allow_translated)
        cap_path = download_captions(vurl, vid, key, kind, workdir) if key else None
        if not cap_path:
            print("  CẢNH BÁO: video không có phụ đề nào (thủ công hay tự động) — bỏ qua",
                  file=sys.stderr)
            sources.append({**source, "captions": None, "caption_lang": None,
                            "words": 0, "estimated_tokens": 0})
            continue
        if not any(base_lang(l) == base_lang(cap_lang) for l in langs):
            print(f"  LƯU Ý: không có phụ đề {','.join(langs)}; dùng phụ đề gốc '{cap_lang}'",
                  file=sys.stderr)

        paras = events_to_paragraphs(parse_json3(cap_path))
        sections.append(render_video(info, paras, kind, cap_lang))
        text = " ".join(t for _, t in paras)
        sources.append({**source, "captions": kind, "caption_lang": cap_lang,
                        "words": len(text.split()),
                        "estimated_tokens": estimate_tokens(text, cap_lang)})

    if not sections:
        die("không lấy được transcript cho URL nào")

    full_text = workdir / "full_text.txt"
    full_text.write_text("\n".join(sections), encoding="utf-8")

    total_words = sum(s["words"] for s in sources)
    meta = {
        "total_sources": len(sources),
        "total_words": total_words,
        "estimated_tokens": sum(s["estimated_tokens"] for s in sources),
        "total_duration_s": sum(s.get("duration_s") or 0 for s in sources),
        "lang": args.lang,
        "caption_langs": sorted({s["caption_lang"] for s in sources if s["caption_lang"]}),
        "sources": sources,
        "full_text_path": str(full_text),
    }
    (workdir / "metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False),
                                           encoding="utf-8")

    print(json.dumps({"workdir": str(workdir), "videos": len(sources),
                      "words": total_words, "estimated_tokens": meta["estimated_tokens"],
                      "caption_langs": meta["caption_langs"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
