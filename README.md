# youtube-to-skill (bản tiếng Việt)

Một skill cho [Claude Code](https://claude.com/claude-code) biến video và playlist YouTube thành agent skill có cấu trúc, dùng lại được — hoặc chỉ trả lời câu hỏi về một video mà không tạo file nào.

## Cài nhanh

Dán vào Claude Code:

```
Cài skill này giúp mình: https://github.com/devdenhatdinh/youtube-to-skills
```

Claude sẽ tự cài theo [INSTALL.md](INSTALL.md). Hoặc tự chạy một lệnh trong PowerShell:

```powershell
irm https://raw.githubusercontent.com/devdenhatdinh/youtube-to-skills/main/install.ps1 | iex
```

Bản fork này chỉ hỗ trợ **Windows**.

Xong thì khởi động lại Claude Code và thử: *"Tóm tắt video này: \<link YouTube\>"*.

> **AI agent:** nếu người dùng nhờ cài skill này, làm theo [INSTALL.md](INSTALL.md).

Đây là bản fork của [EftikharAzim/youtube-to-skill](https://github.com/EftikharAzim/youtube-to-skill), được Việt hóa cho người dùng Việt:

- **Giao tiếp và skill sinh ra bằng tiếng Việt**, giữ nguyên tên framework/thuật ngữ gốc kèm diễn giải tiếng Việt.
- **Xem được video ở mọi ngôn ngữ** — tiếng Việt, tiếng Anh, Nhật, Trung, Hàn, ... Script tự chọn phụ đề tốt nhất (`--lang auto`): phụ đề thủ công theo ngôn ngữ gốc của video → tiếng Việt → tiếng Anh, nếu không có thì phụ đề tự động (ASR) của ngôn ngữ gốc. Agent đọc bản gốc rồi tự dịch, thay vì dùng phụ đề dịch máy của YouTube.
- Ước tính token theo ngôn ngữ (tiếng Việt và chữ CJK tốn token hơn tiếng Anh).
- In tiếng Việt và ký tự Unicode an toàn trên console Windows.

Skill tải transcript bằng yt-dlp (ưu tiên phụ đề thủ công, phụ đề tự động làm dự phòng), ánh xạ mốc chương YouTube thành các phần, và có thể trích keyframe slide bằng ffmpeg để agent đọc được code, bảng, sơ đồ trên màn hình — những thứ không bao giờ xuất hiện trong transcript.

## Vì sao

Một bài nói hội thảo hay chuỗi bài giảng bạn xem tháng trước đã trôi khỏi trí nhớ. Chatbot nào cũng tóm tắt được video khi được hỏi, nhưng bản tóm tắt là văn xuôi dùng một lần — phải đọc lại từ đầu, và nó chìm trong lịch sử chat. Một skill là file mà coding agent nạp khi cần trong lúc bạn làm việc: hỏi về một khái niệm, agent mở đúng chương nói về nó, trích mốc thời gian diễn giả nói câu đó, và đưa link tới đúng giây đó trong video. Một khóa học mười hai bài chỉ tốn một chương cho mỗi câu hỏi, không phải cả khóa.

Chỉ có transcript thì mất hết những gì trên màn hình. Visual pass tùy chọn đọc keyframe slide, nên code, bảng, sơ đồ mà diễn giả trình chiếu — nhưng không đọc thành lời — cũng có trong các chương.

Chuyển playlist một lần; từ đó agent trả lời dựa trên nó, có nguồn.

## Kết quả tạo ra

Một skill cùng cấu trúc với đầu ra của [book-to-skill](https://github.com/virgiliojr94/book-to-skill), để kho kiến thức từ sách và từ video đọc giống nhau:

```
yt-dien-gia-chu-de/
├── SKILL.md          framework cốt lõi, mục lục chương, chỉ mục chủ đề
├── chapters/         mỗi video (playlist) hoặc mỗi mốc chương một file
├── glossary.md       thuật ngữ gốc + tiếng Việt, có trích dẫn (ch N, H:MM:SS)
├── patterns.md       kỹ thuật: khi nào dùng / cách làm / đánh đổi
└── cheatsheet.md     quy tắc quyết định, ngưỡng, bảng đánh đổi
```

Mọi nội dung trích xuất đều kèm mốc thời gian nơi diễn giả nói ra, và mỗi chương có link `<url>&t=<giây>s` để nhảy tới đúng khoảnh khắc trong video.

## Cách dùng

| Bạn nói | Điều xảy ra |
|---|---|
| "Bài nói này nói gì về leader election? \<url\>" | Trả lời trong chat bằng tiếng Việt, có mốc thời gian. Không tạo file. |
| "Tóm tắt video này \<url của video tiếng Anh/Nhật/...\>" | Đọc phụ đề gốc, trả lời bằng tiếng Việt. |
| "Tìm video về Raft consensus" | Tìm trên YouTube, hiện tiêu đề/kênh/thời lượng/lượt xem, bạn chọn. |
| "Xem video về X" | Tự chọn 2–3 bài nói tốt nhất và trả lời từ transcript của chúng. |
| `/youtube-to-skill <url>` | Chuyển đổi đầy đủ: hỏi loại nội dung → ước tính chi phí → tạo skill. |
| `/youtube-to-skill <playlist-url> ten-skill` | Như trên, mỗi video trong playlist thành một chương. |
| "Thêm video này vào yt-khoa-hoc-cua-toi: \<url\>" | Bổ sung chương mới vào skill đã tạo. |

Chuyển đổi luôn hiện ước tính token và chờ xác nhận trước khi tạo gì. Sau khi chuyển đổi, khởi động lại Claude Code để nạp skill mới.

## Yêu cầu

- Windows 10/11 có `winget`
- Claude Code
- Python 3.8+
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — tải transcript và tìm kiếm
- [ffmpeg](https://ffmpeg.org/) — chỉ cần cho visual pass tùy chọn

Script chỉ dùng thư viện chuẩn của Python; không cần `pip install` gì cho bản thân skill.

## Cài đặt thủ công

Không cần đọc phần này nếu đã dùng [Cài nhanh](#cài-nhanh). Installer làm đúng các bước dưới đây.

Claude Code trên Windows chạy lệnh shell qua Git Bash, các lệnh của skill này được viết cho nó. Cài công cụ bằng winget, rồi clone vào thư mục người dùng (PowerShell):

```powershell
winget install yt-dlp.yt-dlp Gyan.FFmpeg
git clone https://github.com/devdenhatdinh/youtube-to-skills "$env:USERPROFILE\.claude\skills\youtube-to-skill"
```

Khởi động lại Claude Code, rồi kiểm tra (dùng `py` hoặc `python`; `python3` trên Windows có thể là stub của Microsoft Store):

```powershell
py "$env:USERPROFILE\.claude\skills\youtube-to-skill\scripts\fetch_transcript.py" --check
py "$env:USERPROFILE\.claude\skills\youtube-to-skill\scripts\extract_frames.py" --check
```

## Cách hoạt động

1. **Transcript** — `scripts/fetch_transcript.py` phân giải URL (video, playlist, hoặc `--search "từ khóa"`), đọc danh sách phụ đề có sẵn của video, chọn track tốt nhất theo ngôn ngữ ưu tiên, tải phụ đề json3 qua yt-dlp, rồi ghi một file `full_text.txt` có header từng video, dòng `## CHAPTER:` lấy từ dữ liệu chương của YouTube, mốc `[H:MM:SS]` đầu mỗi đoạn, cùng `metadata.json` chứa số từ/token, loại phụ đề (thủ công / tự động / dịch máy) và ngôn ngữ phụ đề.
2. **Visual pass (tùy chọn)** — `scripts/extract_frames.py` tải luồng video (mặc định 720p, chỉ hình), chạy dò đổi cảnh của ffmpeg để lấy một keyframe mỗi lần đổi slide/màn hình, và ghi `frames.json` ánh xạ frame → mốc thời gian. Agent đọc frame như ảnh và chép code, bảng, sơ đồ vào các chương. Khi slide và phụ đề tự động mâu thuẫn về một thuật ngữ, slide thắng.
3. **Tạo skill** — agent phân tích cấu trúc (video trong playlist → chương; nếu không thì theo mốc chương YouTube; nếu không nữa thì chia theo chỗ chuyển chủ đề), rồi viết các file skill bằng tiếng Việt theo ngân sách token từng chương. Transcript dài được dò bằng grep/sed thay vì nạp toàn bộ.

Cả hai script dùng độc lập được nếu bạn chỉ cần transcript hoặc keyframe:

```sh
python scripts/fetch_transcript.py "https://youtube.com/watch?v=..."              # tự chọn ngôn ngữ
python scripts/fetch_transcript.py "https://youtube.com/watch?v=..." --lang vi,en  # ưu tiên Việt rồi Anh
python scripts/fetch_transcript.py --search "raft consensus" --max-results 8
python scripts/extract_frames.py "https://youtube.com/watch?v=..." --max-frames 60
```

Tham số hữu ích:

| Tham số | Ý nghĩa |
|---|---|
| `--lang` | Ngôn ngữ phụ đề ưu tiên. `auto` (mặc định) = ngôn ngữ gốc của video → vi → en. Hoặc danh sách như `vi,en`, `ja,en`. Có thể trộn: `ko,auto`. |
| `--allow-translated` | Cho dùng phụ đề dịch máy của YouTube khi không có phụ đề gốc theo ngôn ngữ ưu tiên. Mặc định tắt vì agent dịch tốt hơn. |
| `--max-videos` | Giới hạn số video của playlist (mặc định 25). |
| `--scene` | Ngưỡng đổi cảnh; tăng lên 0.4 cho bài nói cắt cảnh nhiều, giảm xuống 0.2 cho screencast. |
| `--height` | Độ phân giải frame (mặc định 720). |

## Giới hạn

- **Không có phụ đề thì không có transcript.** Video không có cả phụ đề thủ công lẫn tự động sẽ bị bỏ qua. Không tích hợp Whisper.
- **Phụ đề tự động làm sai thuật ngữ.** Với tiếng Việt còn hay sai dấu, nhầm từ đồng âm, và phiên âm lung tung các từ tiếng Anh nói xen. Quy trình sửa những lỗi mà ngữ cảnh đã rõ và đánh dấu `(sp?)` chỗ mơ hồ, nhưng hãy dè chừng glossary sinh từ phụ đề tự động. `metadata.json` cho biết bạn nhận được loại nào.
- **Hình ảnh tốn token.** Visual pass đọc mỗi frame như một ảnh (~1.2K token mỗi frame, thường 30–60 frame mỗi bài nói). Tính năng này phải bật mới chạy và được tính vào ước tính chi phí.
- **Độ đọc được của slide phụ thuộc nguồn.** Slide toàn màn hình và screencast đọc rõ ở 720p; slide nhỏ dạng picture-in-picture trong webcast cũ có thể không đọc được.
- **yt-dlp xuống cấp theo thời gian.** YouTube thay đổi làm nó hỏng định kỳ; hãy cập nhật thường xuyên.
- **Quy mô.** Bài nói đơn lẻ và khóa học tới ~25 video chuyển được trong một phiên (giới hạn playlist mặc định 25; tăng bằng `--max-videos`). Playlist dài hơn chạy theo đợt qua chế độ cập nhật, nhưng tải phụ đề quá nhiều video một lúc có thể bị YouTube giới hạn tốc độ, và chi phí tăng tuyến tính theo thời lượng — khoảng 12–15K token transcript mỗi giờ nói tiếng Anh (tiếng Việt cao hơn), chưa tính chi phí tạo skill.
- **Định dạng quan trọng.** Nội dung có cấu trúc (bài giảng, bài nói hội thảo, khóa học) trích xuất tốt. Nội dung dạng trò chuyện — podcast, phỏng vấn, vlog — cho skill mỏng vì ít cấu trúc có tên để trích. Video riêng tư, dành cho hội viên và giới hạn độ tuổi không được hỗ trợ.

## Sử dụng có trách nhiệm

Công cụ này tải phụ đề và (tùy chọn) luồng video từ YouTube, điều mà Điều khoản dịch vụ của YouTube có hạn chế; hãy dùng cho mục đích học tập và nghiên cứu cá nhân, và lưu ý dùng nhiều có thể khiến IP bị giới hạn tốc độ. Skill sinh ra là tác phẩm phái sinh từ video gốc — giữ riêng tư trừ khi giấy phép của video (vd Creative Commons) cho phép phân phối lại, và luôn ghi nguồn diễn giả. Bạn chịu trách nhiệm về cách mình sử dụng công cụ này.

## Ghi công

Fork từ [EftikharAzim/youtube-to-skill](https://github.com/EftikharAzim/youtube-to-skill) (MIT). Định dạng đầu ra và phương pháp tạo skill phỏng theo [book-to-skill](https://github.com/virgiliojr94/book-to-skill) của virgiliojr94 (MIT). Skill này tự chứa và không phụ thuộc vào nó.

## Giấy phép

MIT
