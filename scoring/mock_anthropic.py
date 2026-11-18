"""
API 호출 없이 의미 채점기를 점검하기 위한 가짜 Anthropic 클라이언트 (--mock, 단위 테스트 전용).
라벨은 기존 키워드 사전으로 흉내 낸다(semantic_issue_classifier.keyword_label). 실험 결과에 쓰지 않는다.
"""
import json
import re
from types import SimpleNamespace

from experiments import semantic_issue_classifier as sic


class _Messages:
    def __init__(self, parent):
        self.parent = parent

    def create(self, **kw):
        self.parent.calls.append(kw)
        if self.parent.fail_times > 0:
            self.parent.fail_times -= 1
            raise RuntimeError("529 overloaded (mock)")
        content = kw["messages"][0]["content"]
        m = re.search(r"\[설명문\]\n(.*)\n\nJSON으로만", content, re.S)
        label = sic.keyword_label(m.group(1) if m else "")
        text = json.dumps({"label": label})
        stop = self.parent.stop_reason
        if stop == "max_tokens":
            text = text[:8]
        elif stop == "refusal":
            text = ""
        return SimpleNamespace(
            model="mock-claude-0", stop_reason=stop,
            content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
            usage=SimpleNamespace(input_tokens=len(content) // 2, output_tokens=12))


class FakeAnthropic:
    def __init__(self, *a, **k):
        self.calls = []
        self.fail_times = 0
        self.stop_reason = "end_turn"
        self.messages = _Messages(self)
        self.beta = SimpleNamespace(messages=self.messages)


class StrictOldSDK(FakeAnthropic):
    """thinking/output_config 인자를 모르는 SDK 흉내: 이 인자가 오면 TypeError, extra_body 는 받는다."""

    def __init__(self):
        super().__init__()
        inner = self.messages.create

        def create(model, max_tokens, messages, temperature=None, extra_body=None):
            kw = {"model": model, "max_tokens": max_tokens, "messages": messages}
            if extra_body:
                kw["extra_body"] = extra_body
            return inner(**kw)
        self.messages = SimpleNamespace(create=create)


class FailingAfter(FakeAnthropic):
    """처음 ok_calls 번은 정상 응답, 그 뒤에는 message 로 예외를 던진다 (결제 오류 중단·재개 테스트용)."""

    def __init__(self, ok_calls, message):
        super().__init__()
        self.ok_calls, self.message = ok_calls, message
        inner = self.messages.create

        def create(**kw):
            if self.ok_calls <= 0:
                self.calls.append(kw)
                raise RuntimeError(self.message)
            self.ok_calls -= 1
            return inner(**kw)
        self.messages = type("M", (), {"create": staticmethod(create)})()
