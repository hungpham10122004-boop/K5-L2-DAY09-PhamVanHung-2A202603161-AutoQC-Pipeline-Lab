"""BƯỚC 2/4 — Tự sửa các lỗi bắt buộc có thể sửa an toàn."""
from collections import defaultdict
import yaml
from ..common import ERROR, parse_yolo_line



DROP_CODES = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}
REMOVE_CODES = {"DUP_IMAGE_EXACT", "DUP_IMAGE_NEAR", "LEAK_TEST", "CORRUPT_IMAGE", "BAD_SIZE"}


def fix(ds, issues, cfg):
    fixes = []
    errors = [i for i in issues if i.severity == ERROR]
    by_image = defaultdict(list)
    removed = set()
    for issue in errors:
        if issue.code in REMOVE_CODES:
            by_image[issue.image].append(issue)
            removed.add(issue.image)

    # Xóa ảnh và nhãn trước; các issue dòng của ảnh đã xóa sẽ được bỏ qua.
    for stem in sorted(removed):
        image = ds.image_path(stem)
        label = ds.label_path(stem)
        if image and image.exists():
            before = image.name
            image.unlink()
            fixes.append({"image": stem, "line": "", "action": "remove_image", "before": before, "after": "(đã xoá ảnh)"})
        if label.exists():
            label.unlink()

    grouped = defaultdict(list)
    for issue in errors:
        if issue.image in removed:
            continue
        grouped[issue.image].append(issue)

    for stem, group in grouped.items():
        # Lỗi dataset/class-name không thuộc file nhãn.
        if any(i.code == "BAD_CLASS_NAME" for i in group):
            if ds.yaml_path.exists():
                try:
                    data = yaml.safe_load(ds.yaml_path.read_text(encoding="utf-8")) or {}
                except Exception:
                    data = {}
                data["names"] = {i: name for i, name in enumerate(cfg["classes"])}
                ds.yaml_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
                fixes.append({"image": "data.yaml", "line": "", "action": "rename_classes", "before": "(tên lớp cũ)", "after": list(cfg["classes"])})
        if any(i.code == "MISSING_LABEL_FILE" for i in group):
            if not ds.label_path(stem).exists():
                fixes.append({"image": stem, "line": "", "action": "needs_label", "before": "(không có file)", "after": "chuyển người gán"})
        path = ds.label_path(stem)
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        line_issues = defaultdict(set)
        for i in group:
            if i.line is not None and i.code in DROP_CODES | {"BOX_OUT_OF_IMAGE"}:
                line_issues[i.line].add(i.code)
        if not line_issues:
            continue
        new_lines = []
        for original_no, text in enumerate(lines, 1):
            codes = line_issues.get(original_no, set())
            if codes & DROP_CODES:
                fixes.append({"image": stem, "line": original_no, "action": "drop_line", "before": text, "after": "(đã xoá dòng lỗi)"})
                continue
            if "BOX_OUT_OF_IMAGE" in codes:
                try:
                    cls, cx, cy, w, h = parse_yolo_line(text)
                    x1, y1, x2, y2 = cx-w/2, cy-h/2, cx+w/2, cy+h/2
                    x1, y1, x2, y2 = max(0.0, x1), max(0.0, y1), min(1.0, x2), min(1.0, y2)
                    if x2 <= x1 or y2 <= y1:
                        fixes.append({"image": stem, "line": original_no, "action": "drop_line", "before": text, "after": "(box nằm ngoài ảnh)"})
                        continue
                    ncx, ncy, nw, nh = (x1+x2)/2, (y1+y2)/2, x2-x1, y2-y1
                    after = f"{cls} {ncx:.6f} {ncy:.6f} {nw:.6f} {nh:.6f}"
                    new_lines.append(after)
                    fixes.append({"image": stem, "line": original_no, "action": "clip_box", "before": text, "after": after})
                    continue
                except (ValueError, TypeError, IndexError):
                    fixes.append({"image": stem, "line": original_no, "action": "drop_line", "before": text, "after": "(không thể clip dòng lỗi)"})
                    continue
            new_lines.append(text)
        path.write_text("\n".join(new_lines) + ("\n" if new_lines else ""), encoding="utf-8")
    return fixes
