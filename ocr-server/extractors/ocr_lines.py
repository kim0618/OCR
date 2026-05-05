def _parse_ocr_lines(result):
    """Normalize PaddleOCR output to a list of (pts, text, conf)."""
    lines = []
    if not result or not result[0]:
        return lines
    r0 = result[0]
    if isinstance(r0, dict):
        for text, score, poly in zip(r0.get("rec_texts", []), r0.get("rec_scores", []), r0.get("rec_polys", [])):
            pts = poly.tolist()
            lines.append((pts, str(text).strip(), float(score)))
    else:
        for line in r0:
            pts = line[0]
            lines.append((pts, str(line[1][0]).strip(), float(line[1][1])))
    return lines
