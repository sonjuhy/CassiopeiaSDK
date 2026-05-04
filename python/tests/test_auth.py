"""auth.py — verify_message 단위 테스트"""
from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from cassiopeia_sdk.auth import DispatchAuthError, verify_message

_SECRET = "test-secret-key-32bytes-padding!!"


def _sign(payload: dict, secret: str = _SECRET) -> str:
    body = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class TestVerifyMessage:
    def test_no_secret_skips_verification(self):
        verify_message({"content": "test"}, secret=None)  # 예외 없어야 함

    def test_valid_signature_passes(self):
        payload = {"task_id": "t1", "content": "hello"}
        payload["_hmac"] = _sign(payload)
        verify_message(payload, secret=_SECRET)  # 예외 없어야 함

    def test_missing_hmac_raises(self):
        with pytest.raises(DispatchAuthError, match="서명"):
            verify_message({"content": "no hmac"}, secret=_SECRET)

    def test_tampered_payload_raises(self):
        payload = {"task_id": "t1", "content": "original"}
        payload["_hmac"] = _sign(payload)
        payload["content"] = "tampered"  # 서명 이후 변조
        with pytest.raises(DispatchAuthError, match="불일치"):
            verify_message(payload, secret=_SECRET)

    def test_wrong_secret_raises(self):
        payload = {"task_id": "t1"}
        payload["_hmac"] = _sign(payload, secret="correct-secret")
        with pytest.raises(DispatchAuthError):
            verify_message(payload, secret="wrong-secret")

    def test_env_secret_used_when_no_arg(self, monkeypatch):
        monkeypatch.setenv("DISPATCH_HMAC_SECRET", _SECRET)
        payload = {"task_id": "t1"}
        payload["_hmac"] = _sign(payload)
        verify_message(payload)  # secret 인수 없이 환경변수 사용
