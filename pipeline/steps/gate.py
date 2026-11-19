"""BƯỚC 4 — Quyết định Release/Hold/Rework dựa trên lỗi và cảnh báo."""
from ..common import ERROR, WARN



def decide(issues, image_stems, cfg, reviewed=frozenset()):
    stems = set(image_stems)
    reviewed = set(reviewed or ())
    n_images = len(stems)
    errors = [i for i in issues if i.severity == ERROR]
    warn_images = {i.image for i in issues if i.severity == WARN and i.image in stems and i.image not in reviewed}
    n_warn_images = len(warn_images)
    ratio = round(n_warn_images / n_images, 4) if n_images else 0.0
    threshold = float(cfg["gate"]["warn_ratio_hold"])
    reasons = []
    if errors:
        decision = "Rework"
        reasons.append(f"Có {len(errors)} lỗi bắt buộc (ERROR), cần sửa trước khi tiếp tục.")
    elif ratio >= threshold and n_images:
        decision = "Hold"
        reasons.append(f"Có {n_warn_images}/{n_images} ảnh còn cảnh báo ({ratio:.1%}), đạt/vượt ngưỡng Hold {threshold:.1%}.")
    else:
        decision = "Release"
        reasons.append(f"Không còn lỗi bắt buộc; {n_warn_images}/{n_images} ảnh có cảnh báo chưa duyệt ({ratio:.1%}), thấp hơn ngưỡng Hold {threshold:.1%}.")
    return {"decision": decision, "n_errors": len(errors), "n_warn_images": n_warn_images, "n_images": n_images, "warn_ratio": ratio, "reasons": reasons}
