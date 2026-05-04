/**
 * HMAC 서명 검증 모듈
 *
 * Python 오케스트라의 dispatch_auth.sign_task()와 호환됩니다.
 * Python json.dumps(sort_keys=True, ensure_ascii=False) 포맷을 재현하여 동일한 HMAC을 생성합니다.
 */
'use strict';

const crypto = require('crypto');

class DispatchAuthError extends Error {
  constructor(message) {
    super(message);
    this.name = 'DispatchAuthError';
  }
}

/**
 * Python의 json.dumps(obj, sort_keys=True, ensure_ascii=False) 출력과 동일한 JSON 문자열을 생성합니다.
 * HMAC 크로스-언어 호환을 위해 필요합니다.
 * @param {*} obj
 * @returns {string}
 */
function pythonJsonDumps(obj) {
  if (obj === null) return 'null';
  if (typeof obj === 'boolean') return obj ? 'true' : 'false';
  if (typeof obj === 'number') return String(obj);
  if (typeof obj === 'string') return JSON.stringify(obj);
  if (Array.isArray(obj)) {
    return '[' + obj.map(pythonJsonDumps).join(', ') + ']';
  }
  if (typeof obj === 'object') {
    const sorted = Object.keys(obj).sort();
    return '{' + sorted.map(k => `${JSON.stringify(k)}: ${pythonJsonDumps(obj[k])}`).join(', ') + '}';
  }
  return JSON.stringify(obj);
}

/**
 * payload의 _hmac 필드를 검증합니다.
 * DISPATCH_HMAC_SECRET 환경변수 또는 secret 인수가 없으면 검증을 건너뜁니다.
 *
 * @param {Object} payload - 검증할 페이로드 (반드시 plain object)
 * @param {string|null} secret - HMAC 시크릿. null이면 환경변수 사용
 * @throws {DispatchAuthError} 서명이 없거나 불일치할 때
 */
function verifyMessage(payload, secret = null) {
  const effectiveSecret = secret || process.env.DISPATCH_HMAC_SECRET;
  if (!effectiveSecret) return; // 시크릿 없으면 하위호환 유지

  const receivedHmac = payload._hmac;
  if (!receivedHmac) {
    throw new DispatchAuthError('서명(_hmac)이 없습니다');
  }

  const body = Object.fromEntries(
    Object.entries(payload).filter(([k]) => k !== '_hmac')
  );

  const bodyStr = pythonJsonDumps(body);
  const expected = crypto
    .createHmac('sha256', effectiveSecret)
    .update(bodyStr)
    .digest('hex');

  // timing-safe 비교
  const expBuf = Buffer.from(expected, 'hex');
  const recBuf = Buffer.from(receivedHmac, 'hex');
  if (expBuf.length !== recBuf.length || !crypto.timingSafeEqual(expBuf, recBuf)) {
    throw new DispatchAuthError('서명 불일치');
  }
}

module.exports = { verifyMessage, DispatchAuthError, pythonJsonDumps };
