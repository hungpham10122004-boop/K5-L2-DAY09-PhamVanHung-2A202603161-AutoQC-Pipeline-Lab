"""CHECK 2 — Kiểm tra định dạng và hình học nhãn YOLO."""
from ..common import ERROR, WARN, Issue, iou_xywh, parse_yolo_line



def run(ds, cfg):
    issues = []
    rules = cfg["label_format"]
    tol = float(rules["overflow_tol"])
    min_px = float(rules["min_box_px"])
    max_frac = float(rules["max_box_frac"])
    dup_thr = float(rules["dup_box_iou"])

    for path in ds.label_files():
        stem = path.stem
        size = ds.image_size(stem)
        W, H = size if size else (None, None)
        seen = []  # (class_id, box, line)
        for line_no, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if not raw.strip():
                continue
            try:
                cls, cx, cy, w, h = parse_yolo_line(raw)
            except (ValueError, TypeError, OverflowError):
                issues.append(Issue("label_format", ERROR, "BAD_FORMAT", stem, "Dòng nhãn không đúng định dạng YOLO gồm 5 giá trị số.", line_no))
                continue
            if cls < 0 or cls >= len(ds.classes):
                issues.append(Issue("label_format", ERROR, "BAD_CLASS_ID", stem, f"ID lớp {cls} nằm ngoài phạm vi 0..{len(ds.classes)-1}.", line_no, {"class_id": cls}))
                continue
            if w <= 0 or h <= 0:
                issues.append(Issue("label_format", ERROR, "BOX_ZERO", stem, "Chiều rộng và chiều cao box phải lớn hơn 0.", line_no, {"w": w, "h": h}))
                continue

            box = (cx, cy, w, h)
            edges = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
            overflow = max(0.0, -edges[0], -edges[1], edges[2] - 1.0, edges[3] - 1.0)
            if overflow > tol:
                issues.append(Issue("label_format", ERROR, "BOX_OUT_OF_IMAGE", stem, f"Box vượt biên ảnh tối đa {overflow:.6f} (tỉ lệ chuẩn hoá).", line_no, {"overflow": overflow}))

            if size:
                short_side_px = min(w * W, h * H)
                if short_side_px < min_px:
                    issues.append(Issue("label_format", WARN, "BOX_TINY", stem, f"Cạnh ngắn của box chỉ {short_side_px:.2f}px, nhỏ hơn ngưỡng {min_px}px.", line_no, {"short_side_px": short_side_px}))
            if w * h > max_frac:
                issues.append(Issue("label_format", WARN, "BOX_HUGE", stem, f"Box chiếm {w*h:.4f} diện tích chuẩn hoá, vượt ngưỡng {max_frac}.", line_no, {"area_frac": w*h}))
            for prev_cls, prev_box, _prev_line in seen:
                if prev_cls == cls and iou_xywh(box, prev_box) > dup_thr:
                    issues.append(Issue("label_format", ERROR, "DUP_BOX", stem, "Box trùng hoặc gần trùng với box cùng lớp ở dòng trước.", line_no, {"iou": iou_xywh(box, prev_box)}))
                    break
            seen.append((cls, box, line_no))
    return issues
