"""
API 호출 없이 배치 채점 경로를 점검하기 위한 가짜 Message Batches 클라이언트 (--mock, 단위 테스트 전용).
요청은 파일(환경변수 MOCK_BATCH_STORE, 기본 임시 폴더)에 저장해 submit 과 collect 를 다른 프로세스로 실행해도 이어진다.
응답 내용은 scoring/mock_anthropic.FakeAnthropic 과 같은 방식(키워드 사전 흉내)으로 만든다. 실험 결과에 쓰지 않는다.

조절(테스트용, 저장 파일의 "controls"): processing_polls(ended 전 retrieve 횟수), errored_custom_ids, expired_custom_ids,
stop_reason, create_error(배치 생성 시 던질 메시지).
"""
import hashlib
import json
import os
import tempfile
from types import SimpleNamespace

from scoring.mock_anthropic import FakeAnthropic


def _store_path():
    return os.environ.get("MOCK_BATCH_STORE", os.path.join(tempfile.gettempdir(), "mock_anthropic_batches.json"))


def _load():
    p = _store_path()
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {"batches": {}, "controls": {}}


def _save(s):
    json.dump(s, open(_store_path(), "w", encoding="utf-8"), ensure_ascii=False)


def set_controls(**kw):
    s = _load(); s["controls"].update(kw); _save(s)


def reset():
    if os.path.exists(_store_path()):
        os.remove(_store_path())


class _Batches:
    def create(self, requests):
        s = _load()
        if s["controls"].get("create_error"):
            raise RuntimeError(s["controls"]["create_error"])
        bid = "msgbatch_mock_" + hashlib.sha256(json.dumps(requests, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
        s["batches"][bid] = {"requests": requests, "polls": 0}
        _save(s)
        return SimpleNamespace(id=bid, processing_status="in_progress")

    def retrieve(self, bid):
        s = _load()
        b = s["batches"][bid]
        b["polls"] += 1
        _save(s)
        ended = b["polls"] > s["controls"].get("processing_polls", 0)
        n = len(b["requests"])
        return SimpleNamespace(id=bid, processing_status="ended" if ended else "in_progress", ended_at="mock-ended" if ended else None,
                               request_counts=SimpleNamespace(processing=0 if ended else n, succeeded=n if ended else 0,
                                                              errored=0, canceled=0, expired=0))

    def results(self, bid):
        s = _load()
        c = s["controls"]
        fake = FakeAnthropic()
        fake.stop_reason = c.get("stop_reason", "end_turn")
        for r in s["batches"][bid]["requests"]:
            cid = r["custom_id"]
            if cid in c.get("errored_custom_ids", []):
                yield SimpleNamespace(custom_id=cid, result=SimpleNamespace(
                    type="errored", error=SimpleNamespace(type="error", error=SimpleNamespace(type="api_error", message="mock"))))
            elif cid in c.get("expired_custom_ids", []):
                yield SimpleNamespace(custom_id=cid, result=SimpleNamespace(type="expired"))
            else:
                msg = fake.messages.create(**r["params"])
                yield SimpleNamespace(custom_id=cid, result=SimpleNamespace(type="succeeded", message=msg))


class FakeBatchAnthropic:
    _inst = None

    def __init__(self):
        self.messages = SimpleNamespace(batches=_Batches())

    @classmethod
    def _shared(cls):
        if cls._inst is None:
            cls._inst = cls()
        return cls._inst
