import hashlib, hmac, json, os


class DispatchAuthError(Exception):
    pass


def verify_message(payload: dict, secret: str | None = None) -> None:
    """
    payload 안의 _hmac 필드를 검증합니다.
    DISPATCH_HMAC_SECRET 환경변수 또는 secret 인수가 없으면 검증을 건너뜁니다.

    Raises:
        DispatchAuthError: 서명이 유효하지 않을 때
    """
    secret = secret or os.environ.get("DISPATCH_HMAC_SECRET")
    if not secret:
        return  # 시크릿 없으면 하위호환 유지

    received_hmac = payload.get("_hmac")
    if not received_hmac:
        raise DispatchAuthError("서명(_hmac)이 없습니다")

    body = {k: v for k, v in payload.items() if k != "_hmac"}
    expected = hmac.new(
        secret.encode(),
        json.dumps(body, sort_keys=True, ensure_ascii=False).encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, received_hmac):
        raise DispatchAuthError("서명 불일치")
