# Báo cáo Day 09 — Phạm Văn Hùng - 2A202602A202603161

> Xoá mọi `TODO(học viên)` và dòng gợi ý. Mỗi ý trả lời bằng **số lấy từ `submission/reports/`**, kèm mẫu số. Cả báo cáo ~1–2 trang.

## 1. Kết luận trước

Với duplicates.phash_dist = 2,second_opinion.conf = 0.25
Kết luận: Hold, 224 ảnh vào, 205 ảnh giữ và export dạng bản nháp,60/205 ảnh chưa duyệt có cảnh báo (29.27%), vượt ngưỡng 10%
Lý do: Cảnh báo vượt ngưỡng Hold, vượt ngưỡng 10% nên chưa duyệt

## 2. Lỗi và phân việc
Lấy từ `02_error_list_v1` (gom theo mã lỗi). Cột "ai sửa": **máy** (autofix) hay **người** (hàng đợi); chỉ ghi những mã có mặt trong lô của bạn.

| Mã lỗi | Số ảnh/dòng | Ai sửa (máy/người) | Vì sao |
|---|---:|---|---|
| CORRUPT_IMAGE |   2 | Máy | Bỏ qua ảnh không đọc được nên ko cần sửa |
|BAD_SIZE|3|Máy|Không đánh nhãn ảnh có độ phân giải thấp|
|DUP_IMAGE_EXACT|8|Máy|Ko sửa, loại các ảnh trùng nhau
|LEAK_TEST|4|Máy|Ảnh trùng tập test, loại
|BAD_CLASS_ID|6|Máy|Máy xóa dòng có box id nằm ngoài danh sách liệt kê|
|BAD_FORMAT|3|Máy|Máy xó dòng sai định dạng YOLO|
|BOX_ZER0|4|MÁy|Xóa dòng có box là một số <0|
|DUP_BOX|7|Máy|Xóa dòng có box trùng|
|BOX_OUT_OF_IMAGE|8|Máy|Box ngoài phạm vi nên cần cắt về biên ảnh|
|BAD_CLASS_NAME|2|máy|Máy cập nhật danh sách tên lớp theo cấu hình trong 1 lần ghi|
|MISSING_LABEL_FILE |6|người| Người kiểm tra ảnh và gán nhãn nếu có đối tượng|
|POSSIBLE_MISSING| 86|người| Người xác nhận có vật thể bị bỏ sót và bổ sung box nếu cần.
|POSSIBLE_WRONG_CLASS|21|người| Người đối chiếu ảnh để xác nhận lớp đúng.
|POSSIBLE_LOOSE_BOX|37|người| Người kiểm tra độ sát của box và chỉnh lại nếu cần.
|POSSIBLE_FALSE_POS| 27|người| Người kiểm tra box có bao quanh vật thể hợp lệ hay là nhãn thừa.
|BOX_TINY|4|người| Người xem box nhỏ có phù hợp quy tắc gán nhãn không.
|BOX_HUGE| 3|người| Người xem vật thể thực sự chiếm phần lớn ảnh hay box bị vẽ quá rộng.
|EMPTY_LABEL|12|người| Người xác nhận ảnh nền hay ảnh có đối tượng nhưng thiếu nhãn.
|CLASS_RARE| 4|người|Người phụ trách xem phân bố lớp và cân nhắc bổ sung dữ liệu.




 vì sao `05_review_queue.csv` xếp ảnh đầu hàng như vậy? Với ngân sách 80 ảnh, người xem được bao nhiêu lỗi ngữ nghĩa?
img_0160 đứng đầu với 35,692 điểm (Điểm ưu tiên cao nhất) vì có 11 cảnh báo thiếu box và 1 cảnh báo sai lớp. Trong 80 ảnh được duyệt, 74 ảnh chứa 187/243 cảnh báo ngữ nghĩa.

## 3. Calibration (2 ngưỡng)
| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) | Lý do (đánh đổi) |
|---|---|---|---|---|
| `duplicates.phash_dist` | 2 | 4 | 100/50 lên 100/66.7 | bắt thêm 1 ảnh gần trùng |
| `second_opinion.conf` | 0.25 | 0.6 | 50/100  lên 57/100, sai lớp tăng 56/100 lên 62/100 | giảm báo nhầm cho hai nhóm này, đổi lại số ca box lỏng phát hiện được giảm từ 2/5 xuống 1/5 |

Khi tăng ngưỡng từ 2 lên 4, máy chỉ bắt thêm 1 ca (3/6 lên 4/6), nhưng recall tăng 16,7 điểm phần trăm.

## 4. Cửa chặn và điều pipeline KHÔNG bắt được
Chứng minh gate chặn đúng: Dùng kết quả lần chạy --budget 0. Có 0 ảnh được duyệt, còn 6/205 ảnh thiếu file nhãn, pipeline kết luận Rework, trả mã thoát 20 và chặn xuất dataset (exported: null).
hai điểm mù có bằng chứng:
- Ảnh gần trùng: phash_dist = 4 phát hiện 4/6 ca, bỏ sót 2 ca.
- Box lỏng: conf = 0.60 phát hiện 1/5 ca, bỏ sót 4 ca.
## 5. Train: raw vs clean (tùy chọn, chấm riêng)
| biến thể | #ảnh train | số seed | map50 (TB ± độ lệch) | map50_95 (TB ± độ lệch) | precision (TB ± độ lệch) | recall (TB ± độ lệch) |
|---|---|---|---|---|---|---|
| raw | 224 | 2 | 0.711 ± 0.015 | 0.492 ± 0.018 | 0.778 ± 0.005 | 0.611 ± 0.030 |
| clean | 205 | 2 | 0.716 ± 0.006 | 0.513 ± 0.004 | 0.795 ± 0.007 | 0.614 ± 0.011 |

Chênh mAP50 (clean − raw) = **+0.005**.

mAP50 của clean là 0,716 ± 0,006, của raw là 0,711 ± 0,015. Chênh lệch +0,005 nhỏ hơn độ lệch chuẩn giữa các seed của cả hai nhóm, nên ko đủ bằng chứng để kết luận clean tốt hơn theo mAP50.

## 6. Quyết định và ghi chú AI
Quyết định cuối: Giữ Hold. Sau hiệu chỉnh còn 0 lỗi bắt buộc, nhưng 38/205 ảnh chưa duyệt có cảnh báo (18,54%). Để đạt Release, cần xem xét và xử lý cảnh báo trên ít nhất 18 ảnh nữa nếu tổng số ảnh vẫn là 205, rồi chạy lại gate để xác nhận tỷ lệ xuống dưới 10%.

AI hỗ trợ triển khai 4 module, bản thân kiểm tra bằng pytest (79/79 pass), và AI từng lấy số sau hiệu chỉnh cho mục 1 khi cần số trước hiệu chỉnh, nên phải chạy lại với ngưỡng gốc để đối chiếu.

*(Thưởng +2, tùy chọn)* CVAT: lọc `width < 20`, ảnh/số box khớp, đối chiếu `BOX_TINY` (xem docs/CVAT_FILTER.md), 1 câu về `can_review`.
