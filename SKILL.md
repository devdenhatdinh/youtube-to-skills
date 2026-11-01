---
name: youtube-to-skill
description: "Xem video và playlist YouTube (bài nói, bài giảng, khóa học, tutorial) ở mọi ngôn ngữ — tiếng Việt, tiếng Anh, Nhật, Trung, ... — bằng cách tải transcript qua yt-dlp: trả lời câu hỏi về video ngay trong chat (Xem nhanh), tìm video theo chủ đề, hoặc chuyển video thành agent skill có cấu trúc (framework, mô hình tư duy, kỹ thuật, anti-pattern) viết bằng tiếng Việt. Dùng khi người dùng gửi link YouTube, hỏi video nói/dạy gì, nói 'xem/tìm video về X', 'tóm tắt video này', hoặc muốn biến video/playlist thành kho kiến thức hay skill để học. Also triggers on English requests: 'watch/find videos about X', 'what does this video say', 'turn this playlist into a skill'."
argument-hint: <youtube-url>... [skill-name-slug] | "tìm video về <chủ đề>"
---

<!-- Đường dẫn script bên dưới tính từ thư mục của skill này. -->

# YouTube-to-Skill

Biến kiến thức trong video thành agent skill dùng được ngay — **trích xuất cấu trúc** từ transcript, không phải viết bản tóm tắt. Định dạng đầu ra theo quy ước của [book-to-skill](https://github.com/virgiliojr94/book-to-skill) (MIT, virgiliojr94) để skill từ sách và từ video đọc giống nhau; skill này tự chứa, không cần cài book-to-skill.

## Ngôn ngữ

Người dùng là người Việt; video có thể ở bất kỳ ngôn ngữ nào.

- **Giao tiếp và mọi file sinh ra mặc định viết bằng tiếng Việt.** Chỉ đổi ngôn ngữ khi người dùng viết bằng ngôn ngữ khác hoặc yêu cầu rõ (vd "viết skill bằng tiếng Anh").
- **Video ngôn ngữ nào cũng xem được.** Script tự chọn phụ đề (`--lang auto`, mặc định): phụ đề thủ công theo ngôn ngữ gốc của video → vi → en; nếu không có thì dùng phụ đề tự động (ASR) của ngôn ngữ gốc. Bạn đọc transcript gốc rồi tự dịch — tốt hơn nhiều so với phụ đề dịch máy của YouTube.
- **Giữ nguyên tên gốc của framework/thuật ngữ**, kèm diễn giải tiếng Việt: `**Tên gốc** (*nghĩa tiếng Việt*)`, vd `**Two-Phase Commit** (*cam kết hai pha*)`. Thuật ngữ kỹ thuật đã quen dùng trong cộng đồng dev Việt (API, cache, deploy, refactor, ...) thì giữ nguyên, không dịch gượng.
- **Trích dẫn nguyên văn** từ video không phải tiếng Việt: giữ câu gốc trong ngoặc kép, ngay sau là bản dịch: `"exact quote" — "câu dịch" (H:MM:SS)`. Chỉ trích khi câu nói thật sự đáng giữ nguyên văn.
- **Tìm kiếm**: chọn từ khóa theo ngôn ngữ phù hợp với nội dung. Chủ đề kỹ thuật/học thuật → tìm cả tiếng Anh (nguồn phong phú hơn) lẫn tiếng Việt; chủ đề gắn với Việt Nam (luật, thuế, thị trường, văn hóa) → ưu tiên tiếng Việt. Ghi rõ ngôn ngữ của từng video trong bảng kết quả.

## Triết lý

Bài nói hội thảo, chuỗi bài giảng và playlist khóa học chứa chuyên môn đã được chắt lọc. Skill này lấy transcript (ưu tiên phụ đề thủ công, nếu không có thì phụ đề tự động) cùng mốc chương YouTube, rồi trích xuất:
- Framework có tên (đúng cách diễn đạt và cách đặt tên của diễn giả)
- Nguyên tắc hành động được ("Dùng X khi Y")
- Kỹ thuật (phương pháp từng bước)
- Anti-pattern (điều cần tránh và vì sao)

**Nguyên tắc trung thực — video là nguồn bị mất thông tin.** Ba kiểu lỗi mà skill từ sách không có; luôn nói rõ với người dùng:
1. **Phụ đề tự động làm sai thuật ngữ** ("Raft" → "raft/rapht"). Với tiếng Việt còn hay **sai dấu, nhầm từ đồng âm, mất ranh giới câu**, và thuật ngữ tiếng Anh nói xen kẽ bị phiên âm lung tung ("deploy" → "đi lôi"). Sửa những lỗi ngữ cảnh đã rõ; đánh dấu chỗ không chắc bằng `(sp?)`.
2. **Slide, sơ đồ, code trên màn hình không bao giờ có trong transcript.** Bước **visual pass** tùy chọn (Bước 2.7) khôi phục chúng bằng cách trích keyframe mỗi lần đổi cảnh để agent đọc như ảnh. Không chạy bước này thì ghi chỗ thiếu là `[nội dung hình ảnh không được ghi lại]`, không tự bịa.
3. **Lời nói lặp và thiếu cấu trúc** — bài nói 60 phút thường ~9k từ mà chỉ có khoảng 3 framework thật. Không bao giờ độn nội dung mỏng cho giống một cuốn sách.

---

## Các chế độ

Định tuyến theo ý định — **mặc định dùng chế độ nhẹ nhất đủ trả lời người dùng**:

0. **Xem nhanh (Quick Watch)** — người dùng gửi URL kèm câu hỏi hoặc ý định thông thường ("video này nói gì về X?", "tóm tắt bài nói này") và KHÔNG yêu cầu tạo skill. Chỉ chạy Bước 2 (tải transcript), dò transcript (kiểu Bước 2.6) và trả lời **ngay trong cuộc trò chuyện** bằng tiếng Việt, kèm mốc `(H:MM:SS)`. Không tạo file, không hỏi loại nội dung, không ước tính chi phí. Nếu câu trả lời phụ thuộc vào hình ảnh, đề nghị chạy trích frame cho đoạn liên quan. Kết thúc bằng: "Muốn biến video này thành skill lâu dài không? Transcript đã tải sẵn rồi." — nếu đồng ý, tiếp tục từ Bước 2.5 với workdir hiện có.

0.5. **Tìm kiếm / Khám phá** — người dùng có chủ đề nhưng không có URL ("tìm/xem video về X"):
   ```bash
   python3 scripts/fetch_transcript.py --search "X" --max-results 8
   ```
   In kết quả JSON (title, channel, duration, views, url). "tìm video" → hiển thị bảng (kèm cột ngôn ngữ đoán từ tiêu đề), để người dùng chọn. "xem video về X" → tự chọn 2–3 video tốt nhất, ưu tiên bài nói dài từ kênh uy tín hơn video ngắn, nói rõ đã chọn gì, rồi làm như Xem nhanh (hoặc Chuyển đổi đầy đủ nếu họ muốn skill). Áp dụng chiến lược từ khóa ở mục **Ngôn ngữ**.

Các chế độ tạo skill:

1. **Chuyển đổi đầy đủ** — có URL và ý định tạo skill: chạy Bước 0–10.
2. **Chỉ phân tích** — người dùng nói "phân tích" / "chỉ trích xuất": chạy Bước 0–3, xuất báo cáo trích xuất rồi dừng.
3. **Tạo từ bản phân tích có sẵn** — bỏ qua Bước 0–3, chạy 4–10 từ ghi chú được cung cấp.
4. **Cập nhật / Gộp thêm** — URL video mới cho một skill đã có (slug tồn tại trong `SKILLS_HOME` hoặc người dùng nói cập nhật): tải transcript (Bước 1–2), rồi chạy **Quy trình Cập nhật / Gộp thêm** ở cuối file.

---

## Bước 0 — Kiểm tra phạm vi

Nếu không có URL: nếu người dùng đưa **chủ đề**, chuyển sang Tìm kiếm (Chế độ 0.5). Nếu không thì dừng với:
> "youtube-to-skill cần một URL YouTube hoặc một chủ đề để tìm. Cách dùng: `youtube-to-skill <url>... [ten-skill]` hoặc 'tìm video về <chủ đề>'"

Phân tích tham số:
- Chuỗi khớp URL YouTube (`youtube.com/watch`, `youtu.be/`, `youtube.com/playlist`) → `INPUT_URLS`.
- Một token cuối dạng chữ thường-gạch-nối, không phải URL → `SKILL_NAME`.
- Nếu `SKILL_NAME` trùng skill đã có trong `SKILLS_HOME` → Chế độ 4.

## Bước 1 — Kiểm tra môi trường

```bash
python3 scripts/fetch_transcript.py --check
```
Nếu thiếu yt-dlp, đưa người dùng lệnh cài đặt rồi dừng. (Trên Windows nếu `python3` không chạy được thì dùng `python` hoặc `py`.)

## Bước 1.5 — Xác định loại nội dung

Hỏi (bỏ qua nếu đã rõ từ URL/tiêu đề):
> "Video này thuộc loại nào?
> 1. **Kỹ thuật** — bài nói/bài giảng có code, kiến trúc, thuật ngữ chính xác
> 2. **Khái niệm** — chủ yếu ý tưởng, framework, nội dung nghề nghiệp/kỹ năng mềm"

Lưu vào `VIDEO_TYPE` (`technical` / `conceptual`) — dùng cho bảng ngân sách ở Bước 7.

Ngôn ngữ phụ đề **không cần hỏi**: để `--lang auto`. Chỉ truyền `--lang` khi người dùng muốn một phụ đề cụ thể (vd video có cả phụ đề Anh và Việt do tác giả làm, người dùng muốn bản Việt: `--lang vi`). Thêm `--allow-translated` chỉ khi người dùng chấp nhận phụ đề dịch máy của YouTube.

## Bước 2 — Tải transcript

```bash
python3 scripts/fetch_transcript.py <INPUT_URLS> --workdir "${TMPDIR:-/tmp}/yt_skill_work"
```

Tạo trong workdir:
- `full_text.txt` — mọi transcript, header từng video (`Captions: <loại> (<ngôn ngữ>)`), dòng `## CHAPTER:` từ dữ liệu chương YouTube, mốc `[H:MM:SS]` đầu mỗi đoạn.
- `metadata.json` — từng video: title/channel/duration/chapters, `captions` (`manual` / `auto` / `auto-translated`), `caption_lang`, `video_lang`, số từ, `estimated_tokens` + tổng.

Đọc `metadata.json`:
- **Video nào có `"captions": "auto"`, báo người dùng** transcript là phụ đề tự động, thuật ngữ sẽ phải sửa.
- **`"auto-translated"`** — phụ đề dịch máy, chất lượng thấp nhất; nói rõ với người dùng.
- **`caption_lang` khác tiếng Việt** — bình thường; bạn đọc bản gốc và viết đầu ra bằng tiếng Việt theo mục **Ngôn ngữ**. Nhắc người dùng một câu ngắn, vd "Video tiếng Anh, mình sẽ viết skill bằng tiếng Việt và giữ thuật ngữ gốc."
- `"captions": null` — báo video bị bỏ qua và tiếp tục với các video còn lại.

## Bước 2.5 — Ước tính chi phí trước khi chạy

Trình bày trước khi tạo; chờ xác nhận:
```
Video: <N>  (<danh sách: tiêu đề — thời lượng — phụ đề manual/auto — ngôn ngữ>)
Từ: ~<N> | Token: ~<N>K | Tổng thời lượng: <H:MM>
Ước tính: input ~<N>K + output ~<N>K token
(+ visual pass nếu chọn ở Bước 2.7: ~1.2K token input mỗi frame, dự kiến ~<N> frame)
Tiếp tục? (hoặc "chỉ phân tích" để xem trước)
```
Input ≈ `estimated_tokens` × 1.3; output ≈ số chương × ngân sách mỗi chương (bảng Bước 7) + 4k (SKILL.md) + 4.5k (file hỗ trợ). Đầu ra tiếng Việt tốn token hơn tiếng Anh cùng nội dung — nhân phần output thêm ~1.3.

## Bước 2.6 — Dò, đừng nuốt cả (transcript > 50k token)

Với playlist/khóa học dài, đừng `Read` toàn bộ `full_text.txt`. Dò nó:
```bash
grep -n "^=== VIDEO:\|^## CHAPTER:" "$WORKDIR/full_text.txt"   # bản đồ cấu trúc
sed -n '<start>,<end>p' "$WORKDIR/full_text.txt"               # một đoạn
grep -c -i "<tên framework>" "$WORKDIR/full_text.txt"          # kiểm chứng trước khi khẳng định
```
Với transcript tiếng Việt từ phụ đề tự động, grep có thể trượt vì sai dấu — thử thêm biến thể không dấu hoặc cách viết khác trước khi kết luận "không có".

## Bước 2.7 — Visual pass tùy chọn (slide / code trên màn hình / sơ đồ)

Đề nghị khi `VIDEO_TYPE=technical`, video trình bày bằng slide, hoặc người dùng muốn lấy hình ảnh:

> "Bạn có muốn lấy cả nội dung hình ảnh không? Mình sẽ tải video, trích một keyframe mỗi lần đổi slide/cảnh rồi đọc để chép code, bảng, sơ đồ vào các chương. Tốn thêm ~1.2K token mỗi frame (thường 30–60 frame mỗi bài nói)."

Nếu đồng ý, với từng video:
```bash
python3 scripts/extract_frames.py "<url>" --workdir "${TMPDIR:-/tmp}/yt_skill_work" --max-frames 60
```
Cần ffmpeg (`--check` in hướng dẫn cài). Tạo `frames_<id>/f*.jpg` + `frames.json` (`[{file, t_seconds, ts}]`).

**Chạy lệnh này ở foreground, chặn đến khi xong — không bao giờ chạy nền rồi poll.** Tải một bài giảng 60–90 phút có thể mất vài phút; vậy là bình thường, không phải bị treo. Đặt timeout Bash rộng (≥480000ms). Đã quan sát thấy agent chạy nền/Monitor lệnh này rồi bỏ cuộc, trả lời cuối cùng là "đang chờ trích frame" mà không hề đọc frame — kết quả trích xuất bị bỏ phí. Nếu bạn tự chạy (không giao cho subagent), quy tắc này áp dụng cho chính bạn.

**Mở rộng cho nhiều video (playlist/khóa học) — mẫu đáng tin cậy: luồng chính tải, subagent chỉ đọc.** KHÔNG giao cho subagent việc tự chạy `extract_frames.py` — subagent thường xuyên chạy nền lần tải dài rồi đứng hình (quan sát ~40–50% bị treo dù đã dặn; chỉ dặn thôi là không đủ). Thay vào đó:
1. **Luồng chính** trích frame cho mọi video trước — tự chạy từng `extract_frames.py` (ở *đây* thì dùng `run_in_background: true` cho mỗi video là được, vì bạn tự chờ và sẽ không bỏ cuộc; chờ từng lệnh xong và xác nhận `frames.json` không rỗng rồi mới đi tiếp). Nếu redirect shell ghi vào thư mục con (`> dir/out.json`), chạy `mkdir -p dir` trước — redirect được thiết lập trước khi lệnh chạy và sẽ lỗi im lặng nếu thiếu thư mục.
2. **Sau đó** giao mỗi chương cho một subagent, nhiệm vụ CHỈ là *đọc các frame đã trích sẵn tại `<workdir>/frames_<id>/frames.json` và sửa file chương* — nói rõ "frame ĐÃ ĐƯỢC TRÍCH SẴN — KHÔNG tải gì, KHÔNG chạy extract_frames.py." Không còn lần tải chặn trong subagent thì hết bị treo.
Chính cách chia này giúp visual pass lớn chạy xong; kiểu một agent làm hết thì không.

Script tự kiểm tra: so thời lượng file tải về với thời lượng yt-dlp báo (thử lại một lần nếu bị cụt) và chuyển sang lấy mẫu đều theo thời gian nếu dò đổi cảnh trả về quá ít/dồn cục (lỗi ffmpeg thật đã gặp: bắn vài frame gần đầu video rồi im lặng suốt phần còn lại). JSON đầu ra có `"fallback_uniform_sampling": true/false` — nếu true, frame được lấy cách đều thay vì theo đổi cảnh; vẫn ổn nhưng dễ rơi vào lúc đang chuyển cảnh hơn, ghi chú nếu chất lượng có vấn đề. Nếu nội dung frame vẫn không liên quan đến chủ đề (sai bài giảng, hỏng hình), đừng bịa — nói rõ trong ghi chú Phạm vi của chương và bỏ phần Ví dụ code/Bảng tham khảo thay vì tự chế nội dung từ frame lỗi.

Tinh chỉnh:
- Video cắt cảnh nhiều (diễn giả ↔ slide) sinh nhiều frame trùng — tăng `--scene` lên 0.4 nếu phần lớn frame là mặt diễn giả.
- Screencast dày đặc (live coding) có thể cần `--scene 0.2` và `--max-frames` cao hơn.
- Frame mặc định 720p; dùng `--height 1080` nếu code trên màn hình nhỏ.

**Dùng frame (trong Bước 7):** với mỗi chương, tra trong `frames.json` các frame có `t_seconds` nằm trong khoảng thời gian của chương, `Read` chúng (là ảnh), và:
- Bỏ qua frame chỉ có diễn giả/hội trường — không tốn output cho chúng.
- Chép **code** trên màn hình đúng như hiển thị vào Ví dụ code, trích `(slide @ 12:34)`. Code giữ nguyên, không dịch.
- Tái hiện **bảng/danh sách** từ slide trong Bảng tham khảo (dịch nội dung chữ sang tiếng Việt, giữ thuật ngữ gốc).
- **Sơ đồ**: mô tả cấu trúc gọn hoặc vẽ lại bằng ASCII/mermaid nếu đơn giản.
- Khi frame mâu thuẫn với phụ đề, slide thắng — sửa thuật ngữ theo slide.

## Bước 3 — Phân tích cấu trúc

Ánh xạ chương, theo thứ tự ưu tiên:
1. **Playlist** → mỗi video = một file chương.
2. **Một video có chương YouTube** (có dòng `## CHAPTER:`) → mỗi mốc = một phần; gộp các chương dưới 1 phút vào chương kề.
3. **Một video không có chương** → chia theo chỗ chuyển chủ đề trong transcript ("so now let's talk about…", "tiếp theo mình sẽ nói về…"); khoảng 3–8 phần cho một bài nói, nhiều hơn cho khóa học dài nhiều giờ.

Xác định: diễn giả, tiêu đề bài nói/khóa học, sự kiện/kênh, ngôn ngữ video, các chủ đề cốt lõi.

**Ở chế độ Chỉ phân tích**, xuất báo cáo này rồi dừng:
```
## Báo cáo trích xuất — <Tiêu đề>
**Ngôn ngữ video**: <vi/en/...> | **Phụ đề**: <manual/auto>
### Framework cốt lõi của diễn giả
- **<Tên gốc>** (*<nghĩa tiếng Việt>*): <là gì và khi nào áp dụng> (H:MM:SS)
### Nguyên tắc / Kỹ thuật / Anti-pattern chính
### Tên skill đề xuất: yt-<dien-gia>-<khai-niem>
### Các phần phát hiện được
| # | Tiêu đề | Mốc thời gian | Framework chính |
```

## Bước 4 — Hỏi mục đích

> "Bạn muốn skill này giúp làm gì?
> 1. Áp dụng framework của diễn giả khi làm việc
> 2. Tư duy bằng mô hình tư duy của diễn giả
> 3. Tra cứu nhanh các phần và khái niệm cụ thể
> 4. Tất cả các ý trên"

Suy ra `DEPTH`: chỉ chọn 3 → `DEPTH=reference` (chương gọn, tra nhanh); còn lại → `DEPTH=study` (chi tiết, ví dụ, lập luận). Ở Chế độ 3/4 mặc định `DEPTH=study`.

## Bước 5 — Đặt tên skill và nơi lưu

Slug mặc định: `yt-{họ-diễn-giả}-{khái-niệm-cốt-lõi}` (vd `yt-kleppmann-event-streams`); khóa học của kênh: `yt-{kênh-hoặc-khóa}-{chủ-đề}`. Slug chỉ dùng chữ thường ASCII không dấu và gạch nối (vd `yt-tony-buoi-sang-khoi-nghiep`, không phải `yt-tony-buổi-sáng`). Tiền tố `yt-` gom các skill từ video lại khi liệt kê — chỉ bỏ nếu người dùng yêu cầu. Nếu có `SKILL_NAME` thì dùng nó.

`SKILLS_HOME` mặc định là thư mục skill cá nhân dùng chung giữa các agent `~/.agents/skills`. Với skill riêng cho một project, dùng `.agents/skills` cho Codex hoặc `.claude/skills` cho Claude Code; hỏi host nào sẽ nạp skill nếu người dùng chưa nói. **KHÔNG lồng skill sinh ra vào thêm một thư mục con** (vd `~/.agents/skills/youtube-skills/<name>/`) vì host chỉ tìm thư mục skill nằm trực tiếp dưới thư mục gốc skill đã cấu hình.

Nếu `$SKILLS_HOME/<skill_name>/` đã tồn tại, hỏi: Cập nhật/Gộp thêm (Chế độ 4), Ghi đè, hay Đổi tên.

## Bước 6 — Tạo thư mục

```bash
mkdir -p "$SKILLS_HOME/<skill_name>/chapters"
```

## Bước 7 — Tạo các file chương

Ngân sách token mỗi chương (mục tiêu, không phải giới hạn cứng — mật độ hơn độ dài, không bao giờ độn):

| | `DEPTH=reference` | `DEPTH=study` |
|---|---|---|
| `conceptual` | 800–1,200 | 1,000–1,800 |
| `technical` | 1,200–1,800 | 2,000–3,000 |

(Viết tiếng Việt thì nới thêm ~30% so với bảng trên vì tiếng Việt tốn token hơn cho cùng lượng nội dung.)

Độ sâu `study` phải có nội dung thật: ví dụ được dựng lại, các bước "cách làm" chi tiết hơn cho từng framework, ghi chú kiểu thất bại cho các framework quan trọng nhất. Nếu một phần mỏng, để nó ngắn và nói rõ trong Ý chính.

Với MỖI chương/phần từ Bước 3, chỉ lấy đoạn transcript của nó (dò theo Bước 2.6) và các frame tương ứng (Bước 2.7), rồi tạo `chapters/ch<NN>-<slug>.md`:

```markdown
# Chương N: <Tiêu đề — dịch sang tiếng Việt, giữ tên riêng>

## Ý chính
<1–2 câu>
**Xem**: <url>&t=<giây-bắt-đầu>s

## Framework được giới thiệu
- **<Tên gốc>** (*<nghĩa tiếng Việt>*) (H:MM:SS): <diễn đạt chính xác theo diễn giả>
  - Khi nào dùng: <tình huống>
  - Cách làm: <các bước hoặc tiêu chí>

## Khái niệm chính
- **<Thuật ngữ>** (H:MM:SS): <định nghĩa một câu>

## Anti-pattern
- **<Điều cần tránh>**: <vì sao thất bại> (H:MM:SS)

## Ví dụ code  *(chỉ khi technical + visual pass)*
```<ngôn ngữ>
<code chép từ frame>
```
- Nguồn: (slide @ H:MM:SS)

## Bảng tham khảo  *(chỉ khi technical + visual pass)*
<bảng tái hiện từ slide>

## Ví dụ thực hành  *(chỉ khi DEPTH=study)*
<phần demo/walkthrough của diễn giả, dựng lại gọn;
 chỗ nào phụ thuộc hình ảnh không ghi được thì nói rõ>

## Điểm cần nhớ
1–5 nhận định hành động được, mỗi ý kèm mốc thời gian

## Liên kết
- **Ch N**: <quan hệ> | **<khái niệm bên ngoài>**: <quan hệ>
```

Mọi nội dung trích xuất đều kèm `(H:MM:SS)` — tương đương số trang của sách. Phần hỏi đáp (Q&A): chỉ lấy những câu hỏi tạo ra nội dung thật.

## Bước 8 — Tạo các file hỗ trợ

- **glossary.md** — thuật ngữ quan trọng, xếp theo ABC của tên gốc, `**Thuật ngữ gốc** (*tiếng Việt*) — định nghĩa (ch N, H:MM:SS)`. Tối đa ~1,500 token.
- **patterns.md** — kỹ thuật cụ thể: `## Pattern\n**Khi nào dùng** / **Cách làm** / **Đánh đổi**`. Tối đa ~2,000 token.
- **cheatsheet.md** — *khả năng phán đoán* của diễn giả, không phải danh sách từ khóa: quy tắc ra quyết định ("Khi X, làm Y, vì Z"), cây quyết định, bảng đánh đổi, ngưỡng và giá trị mặc định, dấu hiệu và "mùi" cần để ý. Mỗi dòng phải giúp người đọc quyết định được điều gì đó. Tối đa ~1,200 token.

## Bước 9 — Tạo SKILL.md chính

Giữ phần thân dưới ~4,000 token; nội dung quan trọng nhất đặt trước (khi nén ngữ cảnh, phần cuối bị cắt trước).

`description` trong frontmatter: viết tiếng Việt, nhưng thêm các từ khóa tiếng Anh của chủ đề (tên framework, tên diễn giả) để skill được kích hoạt dù người dùng hỏi bằng ngôn ngữ nào.

```markdown
---
name: <skill_name>
description: "Kho kiến thức từ \"<Tiêu đề bài nói/khóa học>\" của <Diễn giả> (<Kênh/Sự kiện>). Dùng khi áp dụng framework của <diễn giả> về <3–6 chủ đề chính>, học lại nội dung, hoặc tra cứu khái niệm. Keywords: <thuật ngữ gốc chính>."
---

# <Tiêu đề>
**Diễn giả**: <tên> | **Kênh/Sự kiện**: <tên> | **Thời lượng**: <H:MM> | **Số video**: <N> | **Ngôn ngữ video**: <vi/en/...> | **Nguồn**: <url> | **Tạo ngày**: <YYYY-MM-DD>

## Cách dùng skill này
- Không kèm tham số — nạp các framework cốt lõi
- Kèm chủ đề — mình tìm và đọc chương liên quan
- Kèm số chương — mình nạp chương đó
- Hỏi "có những chương nào?" để xem mục lục

## Framework & mô hình tư duy cốt lõi
<~2,000 token: các framework có tên quan trọng nhất của diễn giả.
 "Dùng X khi Y", "Ưu tiên X hơn Y vì Z". Một bộ công cụ, không phải bản tóm tắt.>

## Mục lục chương
| # | Tiêu đề | Mốc thời gian | Framework chính |
|---|---------|---------------|-----------------|
| [ch01](chapters/ch01-<slug>.md) | <Tiêu đề> | 0:00 | <framework> |

## Chỉ mục chủ đề
- **<Thuật ngữ>** → ch<N>[, ch<N>]

(Mỗi thuật ngữ ghi cả tên gốc và tiếng Việt nếu khác nhau, để tìm được bằng cả hai.)

## File hỗ trợ
- [glossary.md](glossary.md) | [patterns.md](patterns.md) | [cheatsheet.md](cheatsheet.md)

## Phạm vi & giới hạn
Xây dựng từ phụ đề <thủ công|tự động> tiếng <ngôn ngữ><, + visual pass (<N> frame được chép lại) | ; nội dung hình ảnh (slide, live code) không được ghi lại>. Chỉ bao gồm nội dung của tài liệu này.
```

## Bước 10 — Dọn dẹp và báo cáo

```bash
rm -rf "${TMPDIR:-/tmp}/yt_skill_work"
```

Báo cáo (bằng tiếng Việt): đường dẫn skill, video nguồn kèm thời lượng và ngôn ngữ, các file đã tạo với kích thước token xấp xỉ, ví dụ cách dùng ("hỏi <skill_name> về <chủ đề>"), và nhắc rằng cần khởi động lại phiên để skill mới được nạp.

---

## Quy trình Cập nhật / Gộp thêm (Chế độ 4)

1. Đọc `SKILL.md` của skill hiện có (mục lục chương, chỉ mục chủ đề, metadata), liệt kê `chapters/` để tìm số chương lớn nhất, và đọc ba file hỗ trợ. Viết phần mới cùng ngôn ngữ với skill hiện có.
2. Quyết định cho từng video/phần mới: **sửa đổi** một chương có sẵn (gộp vào file đó) hay **bổ sung** (file mới `ch<N+1>-*.md`, đánh số sau chương lớn nhất).
3. Tạo hoặc cập nhật file chương theo Bước 7.
4. Gộp file hỗ trợ: glossary (xếp lại ABC; thuật ngữ đã có thì thêm tham chiếu), patterns (thêm mới, giữ dưới ~2,500 token), cheatsheet (tích hợp quy tắc quyết định mới).
5. Tạo lại SKILL.md chính: tăng số video/thời lượng, thêm nguồn, đưa framework mới vào phần Cốt lõi (giữ dưới 4k token), bổ sung cả hai chỉ mục, cập nhật ngày tạo.
6. Dọn dẹp và báo cáo như Bước 10, nêu rõ phần nào thêm mới, phần nào gộp.

---

## Quy tắc chất lượng

1. **Trích xuất cấu trúc, không tóm tắt** — framework có tên, diễn đạt chính xác, anti-pattern; không kể lại.
2. **Giữ độ chính xác của diễn giả** — giữ nguyên cách họ đặt tên, kèm nghĩa tiếng Việt.
3. **Mật độ hơn đầy đủ** — một chương 1,000 token tốt hơn một đoạn trích 10,000 token.
4. **Giọng người làm nghề** — "Dùng X khi Y", không phải "Diễn giả giải thích X".
5. **Đặt nội dung quan trọng lên đầu SKILL.md.**
6. **File chương nạp theo yêu cầu** — không tốn gì cho đến khi được nạp.
7. **Không bao giờ chép nguyên transcript** — tổng hợp, lọc ra tín hiệu.
8. **Chỉ mục chủ đề là then chốt** — đó là cách agent tìm đúng chương; ghi cả tên gốc lẫn tên tiếng Việt.
9. **Mốc thời gian là trích dẫn** — mọi framework trích xuất đều kèm `(H:MM:SS)` nơi diễn giả nói ra.
10. **Sửa phụ đề, đừng tin phụ đề** — lặng lẽ sửa lỗi phụ đề mà ngữ cảnh đã chắc chắn (kể cả lỗi dấu tiếng Việt); tên thật sự mơ hồ thì đánh dấu `(sp?)` thay vì đoán.
11. **Frame là bằng chứng, không phải để độn** — chỉ chép frame có thêm nội dung; frame mặt diễn giả tốn một lần Read nhưng không được tốn token output nào. Chữ trên slide thắng âm thanh phụ đề tự động khi mâu thuẫn.
12. **Dịch ý, không dịch chữ** — viết tiếng Việt tự nhiên như người làm nghề nói với nhau; không dịch word-by-word, không dịch gượng thuật ngữ đã quen dùng.
