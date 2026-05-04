'use strict';

const crypto = require('crypto');
const { verifyMessage, DispatchAuthError, pythonJsonDumps } = require('../src/auth');

const SECRET = 'test-secret-key-32bytes-padding!!';

function signPayload(payload, secret = SECRET) {
  const body = Object.fromEntries(
    Object.entries(payload).filter(([k]) => k !== '_hmac')
  );
  const bodyStr = pythonJsonDumps(body);
  return crypto.createHmac('sha256', secret).update(bodyStr).digest('hex');
}

describe('verifyMessage', () => {
  it('시크릿 미설정 시 검증을 건너뜁니다', () => {
    delete process.env.DISPATCH_HMAC_SECRET;
    expect(() => verifyMessage({ content: 'test' }, null)).not.toThrow();
  });

  it('유효한 서명은 통과합니다', () => {
    const payload = { task_id: 't1', content: 'hello' };
    payload._hmac = signPayload(payload);
    expect(() => verifyMessage(payload, SECRET)).not.toThrow();
  });

  it('_hmac 없으면 DispatchAuthError를 던집니다', () => {
    expect(() => verifyMessage({ content: 'no hmac' }, SECRET))
      .toThrow(DispatchAuthError);
  });

  it('변조된 payload는 DispatchAuthError를 던집니다', () => {
    const payload = { task_id: 't1', content: 'original' };
    payload._hmac = signPayload(payload);
    payload.content = 'tampered';
    expect(() => verifyMessage(payload, SECRET)).toThrow(DispatchAuthError);
  });

  it('잘못된 시크릿은 DispatchAuthError를 던집니다', () => {
    const payload = { task_id: 't1' };
    payload._hmac = signPayload(payload, 'correct-secret');
    expect(() => verifyMessage(payload, 'wrong-secret')).toThrow(DispatchAuthError);
  });

  it('환경변수 시크릿을 사용합니다', () => {
    process.env.DISPATCH_HMAC_SECRET = SECRET;
    const payload = { task_id: 't1' };
    payload._hmac = signPayload(payload);
    expect(() => verifyMessage(payload)).not.toThrow();
    delete process.env.DISPATCH_HMAC_SECRET;
  });
});

describe('pythonJsonDumps', () => {
  it('키를 알파벳순으로 정렬합니다', () => {
    const result = pythonJsonDumps({ z: 1, a: 2 });
    expect(result).toBe('{"a": 2, "z": 1}');
  });

  it('Python json.dumps 기본 포맷(공백 포함)과 일치합니다', () => {
    const result = pythonJsonDumps({ key: 'value', num: 42 });
    expect(result).toBe('{"key": "value", "num": 42}');
  });

  it('null, boolean, 배열을 올바르게 직렬화합니다', () => {
    expect(pythonJsonDumps(null)).toBe('null');
    expect(pythonJsonDumps(true)).toBe('true');
    expect(pythonJsonDumps([1, 2])).toBe('[1, 2]');
  });
});
