"""CHECK 6 — So sánh nhãn với dự đoán của model thứ hai."""
from ..common import WARN, Issue, iou_xywh, parse_yolo_line
from ..model_cache import get_preds



def run(ds, cfg, preds=None):
    if preds is None:
        preds = get_preds(ds, cfg, "checker")
    rules = cfg["second_opinion"]
    conf_thr = float(rules["conf"])
    min_area = float(rules["min_area_px"])
    fp_conf = float(rules["fp_conf"])
    iou_missing = float(rules["iou_missing"])
    iou_match = float(rules["iou_match"])
    iou_loose = float(rules["iou_loose"])
    issues = []

    for img_path in ds.image_files():
        stem = img_path.stem
        if stem not in preds or ds.read_label_lines(stem) is None:
            continue
        size = ds.image_size(stem)
        if not size:
            continue
        W, H = size
        raw_lines = ds.read_label_lines(stem) or []
        labels = []  # (line, class, box)
        for line_no, text in raw_lines:
            try:
                cls, cx, cy, w, h = parse_yolo_line(text)
                if 0 <= cls < len(ds.classes) and w > 0 and h > 0:
                    labels.append((line_no, cls, (cx, cy, w, h)))
            except (ValueError, TypeError, OverflowError):
                continue

        all_preds = []
        strong_preds = []
        for p in preds.get(stem, []):
            try:
                cls, conf, cx, cy, w, h = p
                cls, conf = int(cls), float(conf)
                box = (float(cx), float(cy), float(w), float(h))
                if w <= 0 or h <= 0:
                    continue
                all_preds.append((cls, conf, box))
                if conf >= conf_thr and w * W * h * H >= min_area:
                    strong_preds.append((cls, conf, box))
            except (ValueError, TypeError, IndexError, OverflowError):
                continue


        # Dự đoán mạnh: tìm box nhãn có IoU đạt ngưỡng; xử lý theo thứ tự ưu tiên trong spec.
        for p_cls, p_conf, p_box in strong_preds:
            candidates = [(l_cls, l_box, iou_xywh(p_box, l_box)) for _, l_cls, l_box in labels]
            candidates = [c for c in candidates if c[2] >= iou_missing]
            if not candidates:
                issues.append(Issue("second_opinion", WARN, "POSSIBLE_MISSING", stem, "Model phát hiện đối tượng chưa có box nhãn.", None, {"conf": p_conf}))
                continue
            same = [c for c in candidates if c[0] == p_cls]
            if same:
                best_iou = max(c[2] for c in same)
                if best_iou < iou_loose:
                    issues.append(Issue("second_opinion", WARN, "POSSIBLE_LOOSE_BOX", stem, "Box nhãn cùng lớp có thể quá lỏng hoặc lệch.", None, {"conf": p_conf, "iou": best_iou}))
                continue
            best_other = max(c[2] for c in candidates)
            if best_other >= iou_match:
                issues.append(Issue("second_opinion", WARN, "POSSIBLE_WRONG_CLASS", stem, "Model và nhãn có thể đang gán khác lớp cho cùng đối tượng.", None, {"conf": p_conf, "iou": best_other}))

        # FALSE_POS: không lọc min-area, dùng ngưỡng fp_conf, giữ nguyên số dòng gốc.
        fp_preds = [(c, b) for c, conf, b in all_preds if conf >= fp_conf]
        for line_no, l_cls, l_box in labels:
            if not any(iou_xywh(l_box, p_box) >= iou_missing for _, p_box in fp_preds):
                issues.append(Issue("second_opinion", WARN, "POSSIBLE_FALSE_POS", stem, "Box nhãn không khớp dự đoán nào đủ confidence; cần người kiểm tra.", line_no, {}))
    return issues
