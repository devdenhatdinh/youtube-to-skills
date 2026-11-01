#!/usr/bin/env python3
"""
extract_frames.py — tải video YouTube ở độ phân giải đủ đọc và trích keyframe
mỗi lần đổi slide/cảnh, phục vụ bước "visual pass" của youtube-to-skill.

Cần: yt-dlp VÀ ffmpeg trên PATH.

Agent sau đó đọc các frame như ảnh và chép lại slide, code trên màn hình,
bảng, sơ đồ vào các file chương.

Kết quả (trong --workdir/frames_<video_id>/):
  f0001.jpg, f0002.jpg, ...   — mỗi lần đổi cảnh một frame
  frames.json                 — [{file, t_seconds, ts}] ánh xạ frame → mốc thời gian

Cách dùng:
  python3 extract_frames.py URL [--workdir DIR] [--height 720]
                            [--scene 0.30] [--max-frames 60] [--keep-video] [--check]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def setup_utf8_io():
    # Windows consoles/pipes default to a legacy code page; non-ASCII output
    # would raise UnicodeEncodeError without this.
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


def check_env():
    ok = True
    hints = (("yt-dlp", "winget install yt-dlp.yt-dlp (Windows) | brew install yt-dlp (macOS)"
                        " | pipx install yt-dlp (Linux)"),
             ("ffmpeg", "winget install Gyan.FFmpeg (Windows) | brew install ffmpeg (macOS)"
                        " | sudo apt install ffmpeg (Linux)"))
    for tool, hint in hints:
        path = shutil.which(tool)
        if path:
            print(f"{tool} : OK tại {path}")
        else:
            print(f"{tool} : THIẾU → cài bằng: {hint}")
            ok = False
    sys.exit(0 if ok else 1)


def get_expected_duration(url: str) -> float | None:
    """Ask yt-dlp for the video's reported duration (seconds) without downloading."""
    p = subprocess.run(
        ["yt-dlp", "--no-playlist", "--no-warnings", "--print", "%(duration)s", url],
        capture_output=True, text=True)
    if p.returncode != 0:
        return None
    try:
        return float(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None


def probe_duration(video: Path) -> float | None:
    """Read the actual duration (seconds) of a downloaded file via ffprobe."""
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video)],
        capture_output=True, text=True)
    try:
        return float(p.stdout.strip())
    except ValueError:
        return None


def download_video(url: str, height: int, workdir: Path) -> Path:
    """Download video-only stream capped at `height` (no audio needed for frames).

    Verifies the download against yt-dlp's own reported duration and retries once
    on a truncated/corrupt result — long-lecture downloads over a real network
    intermittently truncate, which silently produces garbage/wrong-looking frames
    downstream if left unchecked (observed in production: a 66min video yielding
    6 frames of unrelated content).
    """
    expected = get_expected_duration(url)
    fmt = f"bv*[height<={height}]/b[height<={height}]/bv*/b"
    out_tpl = str(workdir / "video_%(id)s.%(ext)s")

    for attempt in (1, 2):
        p = subprocess.run(
            ["yt-dlp", "-f", fmt, "--no-playlist", "--no-warnings",
             "--retries", "5", "--fragment-retries", "5",
             "-o", out_tpl, "--print", "after_move:filepath", "--no-simulate", url],
            capture_output=True, text=True)
        if p.returncode != 0:
            if attempt == 1:
                continue
            die(f"tải video thất bại:\n{p.stderr.strip()[-800:]}")
        path = Path(p.stdout.strip().splitlines()[-1])
        if not path.exists():
            if attempt == 1:
                continue
            die(f"yt-dlp báo file {path} nhưng file không tồn tại")

        actual = probe_duration(path)
        if expected and actual and actual < 0.8 * expected:
            print(f"CẢNH BÁO: video tải về dài {actual:.0f}s, ngắn hơn nhiều so với "
                  f"{expected:.0f}s (lần {attempt}) — có thể tải bị cụt.",
                  file=sys.stderr)
            if attempt == 1:
                path.unlink(missing_ok=True)
                continue
            die(f"tải vẫn bị cụt sau khi thử lại: được {actual:.0f}s, cần ~{expected:.0f}s. "
                f"Chạy lại hoặc kiểm tra mạng/yt-dlp — KHÔNG tin các frame trích từ file này.")
        return path

    die("tải thất bại sau khi thử lại")


def detect_frames(video: Path, frames_dir: Path, scene: float) -> list:
    """Extract scene-change keyframes; return [(file, t_seconds)] from showinfo output."""
    frames_dir.mkdir(parents=True, exist_ok=True)
    p = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(video),
         "-vf", f"select='eq(n,0)+gt(scene,{scene})',showinfo",
         "-fps_mode", "vfr", "-q:v", "3", str(frames_dir / "f%04d.jpg")],
        capture_output=True, text=True)
    if p.returncode != 0:
        die(f"ffmpeg lỗi:\n{p.stderr.strip()[-800:]}")
    times = [float(m) for m in re.findall(r"pts_time:([0-9]+\.?[0-9]*)", p.stderr)]
    files = sorted(frames_dir.glob("f*.jpg"))
    if len(times) != len(files):
        die(f"ffmpeg ghi {len(files)} frame nhưng showinfo báo {len(times)} mốc thời gian — "
            f"không tin được việc ghép frame với mốc thời gian, trích dẫn slide sẽ sai. "
            f"Thử giá trị --scene khác, hoặc báo lỗi kèm URL video.")
    return list(zip(files, times))


def uniform_sample(video: Path, frames_dir: Path, duration: float, count: int) -> list:
    """Fallback: sample `count` frames evenly across the video's full duration.

    The scene-change filter (detect_frames) has a known failure mode on some
    streams where it fires a handful of times near frame 0 and then goes silent
    for the rest of a long video (observed on a 66min lecture: 6 frames, all in
    the first 6 seconds). When that happens, scene detection is silently useless
    rather than loudly broken, so callers must check coverage and fall back.
    """
    for f in frames_dir.glob("f*.jpg"):
        f.unlink()
    times = [round(duration * i / (count - 1), 1) for i in range(count)] if count > 1 else [0.0]
    files = []
    for i, t in enumerate(times, start=1):
        out = frames_dir / f"f{i:04d}.jpg"
        p = subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", str(t), "-i", str(video),
             "-frames:v", "1", "-q:v", "3", str(out)],
            capture_output=True, text=True)
        if p.returncode == 0 and out.exists():
            files.append(out)
        else:
            times = times[:len(files)]
    return list(zip(files, times[:len(files)]))


def subsample(frames: list, max_frames: int) -> list:
    """Evenly subsample to max_frames, always keeping first and last; delete the rest."""
    if len(frames) <= max_frames:
        return frames
    n = len(frames)
    keep_idx = sorted({round(i * (n - 1) / (max_frames - 1)) for i in range(max_frames)})
    keep = [frames[i] for i in keep_idx]
    kept_files = {f for f, _ in keep}
    for f, _ in frames:
        if f not in kept_files:
            f.unlink(missing_ok=True)
    return keep


def main():
    setup_utf8_io()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", nargs="?", help="URL một video YouTube")
    ap.add_argument("--workdir", default=None)
    ap.add_argument("--height", type=int, default=720,
                    help="chiều cao video tối đa; 720 đủ đọc code trên màn hình (mặc định: 720)")
    ap.add_argument("--scene", type=float, default=0.30,
                    help="ngưỡng đổi cảnh 0..1; thấp hơn = nhiều frame hơn (mặc định: 0.30)")
    ap.add_argument("--max-frames", type=int, default=60,
                    help="số frame tối đa; vượt thì lấy mẫu đều (mặc định: 60)")
    ap.add_argument("--keep-video", action="store_true",
                    help="giữ lại file video sau khi trích frame")
    ap.add_argument("--check", action="store_true", help="kiểm tra môi trường rồi thoát")
    args = ap.parse_args()

    if args.check:
        check_env()
    if not args.url:
        ap.error("cần URL video (hoặc dùng --check)")
    for tool in ("yt-dlp", "ffmpeg"):
        if not shutil.which(tool):
            die(f"không tìm thấy {tool} trên PATH (chạy --check để xem cách cài)")

    workdir = Path(args.workdir) if args.workdir else Path(tempfile.gettempdir()) / "yt_skill_work"
    workdir.mkdir(parents=True, exist_ok=True)

    print("Đang tải video…", file=sys.stderr)
    video = download_video(args.url, args.height, workdir)
    vid_id = re.sub(r"^video_|\.[^.]+$", "", video.name)
    frames_dir = workdir / f"frames_{vid_id}"

    duration = probe_duration(video) or 0.0

    print("Đang dò các lần đổi cảnh…", file=sys.stderr)
    frames = detect_frames(video, frames_dir, args.scene)
    total_detected = len(frames)
    fallback_used = False

    # Known ffmpeg failure mode: the scene filter fires a handful of times near
    # frame 0 then goes silent for the rest of a long video, leaving scene
    # detection silently useless rather than loudly broken. Detect that and
    # fall back to evenly-spaced sampling across the full duration instead.
    last_t = max((t for _, t in frames), default=0.0)
    coverage_ratio = (last_t / duration) if duration else 1.0
    too_sparse = duration > 300 and len(frames) < max(3, round(duration / 600))
    if duration > 60 and (too_sparse or coverage_ratio < 0.5):
        print(f"CẢNH BÁO: dò đổi cảnh chỉ được {total_detected} frame, phủ "
              f"{coverage_ratio:.0%} của video {duration:.0f}s — chuyển sang lấy mẫu đều "
              f"theo thời gian thay vì tin kết quả dò cảnh thưa/dồn cục.",
              file=sys.stderr)
        target = min(args.max_frames, max(10, round(duration / 90)))
        frames = uniform_sample(video, frames_dir, duration, target)
        total_detected = len(frames)
        fallback_used = True

    frames = subsample(frames, args.max_frames)

    index = [{"file": str(f), "t_seconds": round(t, 1), "ts": fmt_ts(t)} for f, t in frames]
    (frames_dir / "frames.json").write_text(json.dumps(index, indent=2), encoding="utf-8")

    if not args.keep_video:
        video.unlink(missing_ok=True)

    print(json.dumps({"frames_dir": str(frames_dir), "frames": len(index),
                      "detected": total_detected, "fallback_uniform_sampling": fallback_used,
                      "index": str(frames_dir / "frames.json")}))


if __name__ == "__main__":
    main()
