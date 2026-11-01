# Cài đặt youtube-to-skill — hướng dẫn cho AI agent

> **Bạn là AI agent (Claude Code, Codex, ...) và người dùng nhờ cài skill này?** Làm đúng các bước dưới đây. Skill này chỉ hỗ trợ **Windows**. Lệnh chạy không cần tương tác và chạy lại an toàn (lần sau sẽ cập nhật thay vì cài lại).

Nếu máy người dùng không phải Windows, dừng lại và báo rằng bản fork này chỉ hỗ trợ Windows.

## 1. Chạy installer

Chạy bằng **PowerShell** (không phải Git Bash):

```powershell
irm https://raw.githubusercontent.com/devdenhatdinh/youtube-to-skills/main/install.ps1 | iex
```

Installer sẽ:
1. Cài bằng `winget` những gì còn thiếu: Git, Python 3, `yt-dlp` (bắt buộc), `ffmpeg` (chỉ cần cho visual pass đọc slide).
2. Clone skill vào `%USERPROFILE%\.claude\skills\youtube-to-skill`, hoặc `git pull` nếu đã có.
3. Chạy `--check` của hai script để xác nhận.

Không muốn cài ffmpeg thì tải file về rồi chạy với `-NoFfmpeg`:

```powershell
irm https://raw.githubusercontent.com/devdenhatdinh/youtube-to-skills/main/install.ps1 -OutFile $env:TEMP\yts-install.ps1
powershell -ExecutionPolicy Bypass -File $env:TEMP\yts-install.ps1 -NoFfmpeg
```

## 2. Đọc kết quả

- Dòng cuối `DONE.` → xong.
- `yt-dlp is not reachable yet` → công cụ đã cài nhưng PATH của phiên hiện tại chưa cập nhật. Bình thường sau `winget`; khởi động lại Claude Code là hết.
- `ERROR: ... exists but is not a git clone` → đã có thư mục skill cài tay. Hỏi người dùng trước khi xóa/di chuyển nó.
- `ERROR: winget not found` → Windows quá cũ hoặc thiếu App Installer; hướng người dùng cài "App Installer" từ Microsoft Store, hoặc làm theo phần cài thủ công.

## 3. Báo cho người dùng

Nói ngắn gọn (bằng tiếng Việt): đã cài vào đâu, công cụ nào đã cài, và **cần khởi động lại Claude Code** để skill được nạp. Gợi ý thử: *"Tóm tắt video này: \<link YouTube\>"* hoặc *"Tìm video về \<chủ đề\>"*.

## Cài thủ công (nếu installer lỗi)

1. `winget install yt-dlp.yt-dlp` (tùy chọn: `winget install Gyan.FFmpeg`).
2. `git clone https://github.com/devdenhatdinh/youtube-to-skills "$env:USERPROFILE\.claude\skills\youtube-to-skill"` — tên thư mục đích phải là `youtube-to-skill` (số ít).
3. Kiểm tra: `py "$env:USERPROFILE\.claude\skills\youtube-to-skill\scripts\fetch_transcript.py" --check` (dùng `py` hoặc `python`; `python3` trên Windows có thể là stub của Microsoft Store).
