"""
정답 라벨 3층 로더 (E7 에서 사용, API 호출 없음).

  load_labels(layer, viewport="1280") → {(page_id, defect_type): 0 / 1 / None}
    layer = "nominal"            dataset_metadata 의 주입 기록
            "effective"          E0 결정적 검사 (viewport 1280 또는 390)
            "guideline_grounded" guideline_grounded 판정이 true 인 유형만 effective 값, 그 밖의 유형은 None (평가에서 제외)
  None 셀은 해당 층의 지표 계산에서 분모·분자 모두에서 빠진다.

guideline_grounded 판정이 아직 pending 인 유형이 있으면 load_labels("guideline_grounded") 는 그 유형을 None 으로 두고
경고 목록을 함께 돌려준다(strict=True 이면 예외).
"""
import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GT = os.path.join(ROOT, "results", "revision", "ground_truth.csv")
LAYERS = ("nominal", "effective", "guideline_grounded")


class PendingDecisionError(RuntimeError):
    pass


def load_labels(layer, viewport="1280", path=GT, strict=False, grounded_override=None):
    """grounded_override: {defect_type: True/False} — guideline_grounded 판정을 이 호출에서만 바꾼다
    (사전 지정된 민감도 분석: 버튼 잘림 true/false 양쪽 보고). 파일은 바꾸지 않는다."""
    if layer not in LAYERS:
        raise ValueError(f"layer must be one of {LAYERS}")
    if viewport not in ("1280", "390"):
        raise ValueError("viewport must be '1280' or '390'")
    out, pending = {}, set()
    for r in csv.DictReader(open(path, encoding="utf-8")):
        key = (r["page_id"], r["defect_type"])
        if layer == "nominal":
            out[key] = int(r["nominal_injected"])
        elif layer == "effective":
            out[key] = int(r[f"effective_{viewport}"])
        else:
            g = r.get("guideline_grounded", "pending")
            if grounded_override and r["defect_type"] in grounded_override:
                g = "true" if grounded_override[r["defect_type"]] else "false"
            if g == "true":
                out[key] = int(r[f"effective_{viewport}"])
            else:
                out[key] = None
                if g != "false":
                    pending.add(r["defect_type"])
    if layer == "guideline_grounded" and pending and strict:
        raise PendingDecisionError(f"guideline_grounded decision pending for: {sorted(pending)}")
    return out, sorted(pending)
