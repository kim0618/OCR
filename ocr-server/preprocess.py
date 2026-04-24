import cv2
import numpy as np


def _find_4corners(pts: np.ndarray) -> np.ndarray:
    """임의 개수의 점에서 4 꼭짓점(좌상·우상·우하·좌하) 추출"""
    pts = pts.reshape(-1, 2).astype(np.float32)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).flatten()
    return np.array([
        pts[np.argmin(s)],   # 좌상 (x+y 최소)
        pts[np.argmin(d)],   # 우상 (x-y 최소)
        pts[np.argmax(s)],   # 우하 (x+y 최대)
        pts[np.argmax(d)],   # 좌하 (x-y 최대)
    ], dtype=np.float32)


def _get_best_quad(contours, min_area_ratio: float, h: int, w: int):
    """컨투어 목록에서 가장 큰 4각형 후보 반환"""
    best_contour = None
    best_area = 0
    for cnt in contours[:15]:
        if cv2.contourArea(cnt) < h * w * min_area_ratio:
            continue
        hull = cv2.convexHull(cnt)
        peri = cv2.arcLength(hull, True)
        approx4 = None
        for eps in [0.02, 0.04, 0.06, 0.08, 0.12]:
            approx = cv2.approxPolyDP(hull, eps * peri, True)
            if len(approx) == 4:
                approx4 = approx
                break
        if approx4 is None:
            approx4 = _find_4corners(hull).reshape(-1, 1, 2).astype(np.int32)
        area = cv2.contourArea(approx4)
        if area > best_area and area > h * w * min_area_ratio:
            best_area = area
            best_contour = approx4
    return best_contour, best_area


def detect_document(image: np.ndarray) -> tuple[np.ndarray, dict]:
    """
    사진 속 문서 영역을 자동 감지하고 원근 보정(perspective correction).
    문서를 찾지 못하면 원본 그대로 반환.
    """
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    otsu_val, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    thresh_val = max(int(otsu_val), 150)
    _, bright = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)
    k_size = max(20, min(60, int(min(h, w) / 50)))
    k_close = cv2.getStructuringElement(cv2.MORPH_RECT, (k_size, k_size))
    bright = cv2.morphologyEx(bright, cv2.MORPH_CLOSE, k_close, iterations=2)
    k_open = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    bright = cv2.morphologyEx(bright, cv2.MORPH_OPEN, k_open)
    bright_cnts, _ = cv2.findContours(bright, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    bright_cnts = sorted(bright_cnts, key=cv2.contourArea, reverse=True) if bright_cnts else []
    best_contour, best_area = _get_best_quad(bright_cnts, 0.10, h, w)

    if best_area < h * w * 0.15:
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 50, 150)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        edged = cv2.dilate(edged, kernel, iterations=2)
        edged = cv2.erode(edged, kernel, iterations=1)
        edge_cnts, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        edge_cnts = sorted(edge_cnts, key=cv2.contourArea, reverse=True) if edge_cnts else []
        fallback, fallback_area = _get_best_quad(edge_cnts, 0.08, h, w)
        if fallback_area > best_area:
            best_contour = fallback
            best_area = fallback_area

    if best_contour is None:
        return image, {"status": "감지 안됨", "detail": "사각형 문서를 찾지 못함"}

    bx, by, bw, bh = cv2.boundingRect(best_contour)
    margin = int(min(h, w) * 0.02)
    borders = sum([bx <= margin, by <= margin, bx + bw >= w - margin, by + bh >= h - margin])
    if best_area > h * w * 0.85 or borders >= 3:
        return image, {
            "status": "감지 스킵",
            "detail": f"배경 포함 의심({round(best_area/(h*w)*100, 1)}%, 가장자리 {borders}면), 원본 유지",
        }

    ordered = _find_4corners(best_contour)

    tl, tr, br, bl = ordered
    width_top = np.linalg.norm(tr - tl)
    width_bot = np.linalg.norm(br - bl)
    height_left = np.linalg.norm(bl - tl)
    height_right = np.linalg.norm(br - tr)
    out_w = int(max(width_top, width_bot))
    out_h = int(max(height_left, height_right))

    if out_w < 100 or out_h < 100:
        return image, {"status": "감지 안됨", "detail": "감지된 영역이 너무 작음"}

    dst = np.array([
        [0, 0],
        [out_w - 1, 0],
        [out_w - 1, out_h - 1],
        [0, out_h - 1],
    ], dtype=np.float32)

    M = cv2.getPerspectiveTransform(ordered, dst)
    warped = cv2.warpPerspective(image, M, (out_w, out_h))

    area_pct = round(cv2.contourArea(best_contour) / (h * w) * 100, 1)

    return warped, {
        "status": "감지 완료",
        "detail": f"문서 영역 {area_pct}% ({out_w}x{out_h}으로 보정)",
    }


def upscale_if_needed(image: np.ndarray, min_height: int = 1500) -> tuple[np.ndarray, dict]:
    """해상도가 낮으면 업스케일"""
    h, w = image.shape[:2]
    if h >= min_height:
        return image, {"status": "유지", "detail": f"{w}x{h} (충분)"}

    scale = min_height / h
    new_w = int(w * scale)
    new_h = int(h * scale)
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
    return resized, {"status": "업스케일", "detail": f"{w}x{h} -> {new_w}x{new_h} ({scale:.1f}배)"}


def detect_orientation(
    image: np.ndarray,
    ocr_engine,
    original_wh: tuple[int, int] | None = None,
) -> tuple[np.ndarray, dict]:
    """Detect the best reading orientation among 0/90/180/270 degrees."""
    h, w = image.shape[:2]

    short = min(h, w)
    target_short = 224
    scale = target_short / short if short > target_short else 1.0
    sm_h, sm_w = int(h * scale), int(w * scale)
    small = cv2.resize(image, (sm_w, sm_h), interpolation=cv2.INTER_AREA) if scale < 1.0 else image

    def _score_rotated(rot_img) -> dict:
        try:
            result = ocr_engine.ocr(rot_img)
            r0 = result[0] if result and result[0] else None
            if isinstance(r0, dict):
                parsed = list(zip(r0.get("rec_texts", []), r0.get("rec_scores", [])))
            elif r0:
                parsed = [(line[1][0], float(line[1][1])) for line in r0]
            else:
                parsed = []
        except Exception:
            parsed = []

        hangul_count = 0
        digit_count = 0
        conf_sum = 0.0
        char_count = 0
        line_count = len(parsed)
        for text, conf in parsed:
            text = str(text)
            conf = float(conf)
            hangul_count += sum(1 for c in text if "\uac00" <= c <= "\ud7a3")
            digit_count += sum(1 for c in text if c.isdigit())
            conf_sum += conf * len(text)
            char_count += len(text)
        avg_conf = conf_sum / char_count if char_count > 0 else 0.0
        text_signal = hangul_count * 1.2 + digit_count * 0.9
        score = text_signal * (0.8 + avg_conf) + line_count * 0.8
        return {
            "score": round(score, 1),
            "line_count": line_count,
            "digit_count": digit_count,
            "hangul_count": hangul_count,
            "avg_conf": round(avg_conf, 4),
        }

    original_landscape = None
    original_ratio = None
    if original_wh and len(original_wh) == 2:
        ow, oh = original_wh
        if ow > 0 and oh > 0:
            original_ratio = ow / oh
            original_landscape = ow > oh * 1.08

    cropped_landscape = w > h * 1.08
    crop_ratio = (w / h) if h > 0 else 1.0
    conflict_landscape_hint = (
        original_landscape is True
        and not cropped_landscape
        and original_ratio is not None
        and original_ratio > 1.12
        and crop_ratio < 0.95
    )
    landscape_first = cropped_landscape or bool(original_landscape)
    first_pass = (90, 270) if landscape_first else (0, 180)
    second_pass = (0, 180) if landscape_first else (90, 270)
    pass_strategy = "landscape_first" if landscape_first else "portrait_first"

    rotations_imgs = {0: small}
    score_meta: dict[int, dict] = {}
    scores: dict[int, float] = {}
    early_stopped = False
    bailout_reason = ""

    def _rotated(angle: int) -> np.ndarray:
        if angle not in rotations_imgs:
            if angle == 90:
                rotations_imgs[angle] = cv2.rotate(small, cv2.ROTATE_90_CLOCKWISE)
            elif angle == 180:
                rotations_imgs[angle] = cv2.rotate(small, cv2.ROTATE_180)
            elif angle == 270:
                rotations_imgs[angle] = cv2.rotate(small, cv2.ROTATE_90_COUNTERCLOCKWISE)
            else:
                rotations_imgs[angle] = small
        return rotations_imgs[angle]

    for angle in first_pass:
        meta = _score_rotated(_rotated(angle))
        score_meta[angle] = meta
        scores[angle] = meta["score"]

    first_scores = [scores[angle] for angle in first_pass]
    dominant = max(first_scores)
    other = min(first_scores)
    dominant_angle = max(first_pass, key=lambda angle: scores[angle])
    dominant_meta = score_meta[dominant_angle]
    diff = dominant - other
    ratio = (dominant / max(other, 0.1)) if dominant > 0 else 0.0
    low_signal_first_pass = dominant < 12.0 and other < 10.0 and dominant_meta["line_count"] <= 12
    dominant_signal = dominant_meta["hangul_count"] + dominant_meta["digit_count"]
    other_angle = first_pass[0] if dominant_angle == first_pass[1] else first_pass[1]
    other_meta = score_meta[other_angle]
    signal_gap = dominant_signal - (other_meta["hangul_count"] + other_meta["digit_count"])
    conf_gap = dominant_meta["avg_conf"] - other_meta["avg_conf"]
    strong_text_signal = (
        dominant_meta["line_count"] >= 9
        and dominant_signal >= 22
        and dominant_meta["avg_conf"] >= 0.72
    )
    landscape_hint_confident = (
        original_landscape is True
        and not conflict_landscape_hint
        and (
            cropped_landscape
            or crop_ratio <= 0.97
            or (original_ratio is not None and original_ratio >= 1.18)
        )
    )
    low_signal_landscape_bailout = (
        landscape_hint_confident
        and dominant >= 8.0
        and ratio >= 1.35
        and diff >= 3.5
        and dominant_meta["line_count"] >= 4
        and dominant_meta["avg_conf"] >= 0.55
    )

    if first_pass == (90, 270):
        can_early_stop = (
            dominant >= 110.0
            and diff >= 30.0
            and ratio >= 1.35
        ) or (
            dominant >= 70.0
            and diff >= 55.0
        ) or (
            landscape_hint_confident
            and dominant >= 56.0
            and diff >= 16.0
            and ratio >= 1.22
            and strong_text_signal
        ) or (
            landscape_hint_confident
            and dominant >= 44.0
            and diff >= 12.0
            and ratio >= 1.18
            and dominant_meta["line_count"] >= 8
            and signal_gap >= 8
            and conf_gap >= 0.05
        )
        if can_early_stop:
            bailout_reason = "strong_landscape_first_pass"
        elif low_signal_first_pass and landscape_hint_confident and ratio >= 1.2:
            can_early_stop = True
            bailout_reason = "low_signal_landscape_hint"
        elif low_signal_landscape_bailout:
            can_early_stop = True
            bailout_reason = "low_signal_landscape_hint"
    else:
        can_early_stop = (
            other > 0.0
            and dominant >= 18.0
            and ratio >= 2.4
            and diff >= 12.0
            and not conflict_landscape_hint
        ) or (
            dominant >= 18.0
            and ratio >= 1.55
            and diff >= 8.0
            and dominant_meta["hangul_count"] >= 3
            and signal_gap >= 6
            and dominant_meta["avg_conf"] >= 0.52
            and not conflict_landscape_hint
        )
        if original_landscape and dominant_angle in (0, 180):
            can_early_stop = False
        if can_early_stop:
            bailout_reason = "strong_portrait_first_pass"
        elif low_signal_first_pass and not original_landscape:
            can_early_stop = True
            bailout_reason = "low_signal_portrait_bailout"

    if can_early_stop:
        early_stopped = True
    else:
        for angle in second_pass:
            meta = _score_rotated(_rotated(angle))
            score_meta[angle] = meta
            scores[angle] = meta["score"]

    best_angle = max(scores, key=lambda angle: scores[angle])

    if best_angle == 0:
        rotated_full = image
    elif best_angle == 90:
        rotated_full = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    elif best_angle == 180:
        rotated_full = cv2.rotate(image, cv2.ROTATE_180)
    else:
        rotated_full = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)

    return rotated_full, {
        "status": "?? ??",
        "detail": (
            f"{best_angle}? ?? ?? "
            f"(scores={scores}, early_stop={early_stopped}, landscape_first={landscape_first}, bailout={bailout_reason or '-'})"
        ),
        "angle": best_angle,
        "early_stopped": early_stopped,
        "landscape_first": landscape_first,
        "original_landscape": original_landscape,
        "cropped_landscape": cropped_landscape,
        "conflict_landscape_hint": conflict_landscape_hint,
        "thumb_wh": [sm_w, sm_h],
        "pass_strategy": pass_strategy,
        "bailout_reason": bailout_reason,
        "first_pass_dominant": round(dominant, 1),
        "first_pass_other": round(other, 1),
        "first_pass_diff": round(diff, 1),
        "first_pass_ratio": round(ratio, 3),
        "first_pass_line_count": dominant_meta["line_count"],
        "first_pass_avg_conf": dominant_meta["avg_conf"],
    }


def deskew(image: np.ndarray) -> tuple[np.ndarray, dict]:
    """기울기 보정"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) == 0:
        return image, {"status": "보정 불필요", "detail": "텍스트 영역 없음"}

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle
    elif angle > 45:
        angle = angle - 90

    if abs(angle) < 0.5:
        return image, {"status": "보정 불필요", "detail": f"기울기 {abs(angle):.2f}도 (기준 미만)"}

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        image, M, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return rotated, {"status": "보정 완료", "detail": f"{abs(angle):.2f}도 회전 보정"}


def denoise(image: np.ndarray) -> tuple[np.ndarray, dict]:
    """노이즈 제거"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    noise_level = float(np.std(cv2.Laplacian(gray, cv2.CV_64F)))

    denoised = cv2.fastNlMeansDenoisingColored(
        image, None, h=10, hColor=10, templateWindowSize=7, searchWindowSize=21
    )

    if noise_level < 5:
        label = "낮음"
    elif noise_level < 20:
        label = "보통"
    else:
        label = "높음"

    return denoised, {"status": "제거 완료", "detail": f"노이즈 수준 {label} ({noise_level:.1f})"}


def enhance_contrast(image: np.ndarray) -> tuple[np.ndarray, dict]:
    """대비 강화 (CLAHE)"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    before_std = float(np.std(gray))

    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge((l, a, b))
    enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    gray_after = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
    after_std = float(np.std(gray_after))
    improvement = after_std - before_std

    if improvement < 1:
        label = "변화 미미"
    elif improvement < 5:
        label = "소폭 개선"
    else:
        label = "대폭 개선"

    return enhanced, {"status": "강화 완료", "detail": f"대비 {label} (+{improvement:.1f})"}


def sharpen(image: np.ndarray) -> tuple[np.ndarray, dict]:
    """텍스트 선명화 (언샤프 마스크)"""
    gaussian = cv2.GaussianBlur(image, (0, 0), 3)
    sharpened = cv2.addWeighted(image, 1.5, gaussian, -0.5, 0)
    return sharpened, {"status": "완료", "detail": "언샤프 마스크 적용"}


def binarize_for_ocr(image: np.ndarray) -> tuple[np.ndarray, dict]:
    """OCR용 적응형 이진화"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=21,
        C=10,
    )
    kernel = np.ones((2, 2), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    result = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
    black_ratio = np.sum(binary == 0) / binary.size * 100
    return result, {"status": "완료", "detail": f"텍스트 밀도 {black_ratio:.1f}%"}


def preprocess(image: np.ndarray) -> tuple[np.ndarray, dict]:
    """전체 전처리 파이프라인"""
    h, w = image.shape[:2]
    result = {"image_size": f"{w} x {h}"}

    detected, doc_info = detect_document(image)
    result["document"] = doc_info
    image = detected

    upscaled, upscale_info = upscale_if_needed(image)
    result["upscale"] = upscale_info

    deskewed, deskew_info = deskew(upscaled)
    result["deskew"] = deskew_info

    result["denoise"] = {"status": "건너뜀", "detail": "OCR 품질을 위해 생략"}

    enhanced, contrast_info = enhance_contrast(deskewed)
    result["contrast"] = contrast_info

    return enhanced, result


def downscale_if_large(image: np.ndarray, max_width: int = 640) -> tuple[np.ndarray, dict]:
    """속도 개선: 너무 큰 이미지를 축소"""
    h, w = image.shape[:2]
    if w <= max_width:
        return image, {"status": "유지", "detail": f"{w}x{h}"}

    scale = max_width / w
    new_w = max_width
    new_h = int(h * scale)
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return resized, {"status": "축소", "detail": f"{w}x{h} -> {new_w}x{new_h} ({scale:.2f}배)"}


def preprocess_for_ocr(image: np.ndarray) -> tuple[np.ndarray, dict]:
    """OCR 전용 전처리 파이프라인 (속도 우선)"""
    h, w = image.shape[:2]
    result = {"image_size": f"{w} x {h}"}

    detected, doc_info = detect_document(image)
    result["document"] = doc_info
    image = detected
    h, w = image.shape[:2]

    max_w = 640
    if w > max_w:
        scale = max_w / w
        new_h = int(h * scale)
        image = cv2.resize(image, (max_w, new_h), interpolation=cv2.INTER_AREA)
        result["resize"] = {"status": "축소", "detail": f"{w}x{h} -> {max_w}x{new_h}"}
    else:
        result["resize"] = {"status": "유지", "detail": f"{w}x{h}"}

    deskewed, deskew_info = deskew(image)
    result["deskew"] = deskew_info

    return deskewed, result
