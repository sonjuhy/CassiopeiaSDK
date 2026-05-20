'use strict';

const { Tool } = require('../tools');
const { UnknownActionError, ParamsValidationError } = require('./exceptions');

// JSON Schema type → JS 타입 검사 함수
const TYPE_CHECKERS = {
  string:  (v) => typeof v === 'string',
  number:  (v) => typeof v === 'number',
  integer: (v) => Number.isInteger(v) || (typeof v === 'number' && Number.isFinite(v) && Math.floor(v) === v),
  boolean: (v) => typeof v === 'boolean',
  array:   (v) => Array.isArray(v),
  object:  (v) => typeof v === 'object' && v !== null && !Array.isArray(v),
  null:    (v) => v === null,
};

/**
 * LLM이 생성한 action과 params를 tools 목록 기준으로 검증합니다.
 */
class ActionAndParamsValidator {
  /**
   * 검증된 [Tool, params] 쌍을 반환합니다.
   *
   * @param {string} action
   * @param {object} params
   * @param {Array<Tool|object>} tools
   * @returns {[Tool, object]}
   * @throws {UnknownActionError}    action이 tools 목록에 없을 때
   * @throws {ParamsValidationError} 파라미터 누락·타입 불일치·허용되지 않은 키
   */
  static validate(action, params, tools) {
    const tool = findTool(action, tools);
    const validated = validateParams(action, params, tool.parameters);
    return [tool, validated];
  }
}

// ---------------------------------------------------------------------------
// 내부 헬퍼
// ---------------------------------------------------------------------------

function findTool(action, tools) {
  const toolNames = [];
  for (const t of tools) {
    const tool = t instanceof Tool ? t : new Tool(t);
    toolNames.push(tool.name);
    if (tool.name === action) return tool;
  }
  throw new UnknownActionError(
    `등록되지 않은 action: ${JSON.stringify(action)}. 사용 가능한 action 목록: ${JSON.stringify(toolNames)}`
  );
}

function validateParams(action, params, schema) {
  const properties = schema.properties || {};
  const required = schema.required || [];

  // 1. 필수 파라미터 누락 검사
  const missing = required.filter((k) => !(k in params));
  if (missing.length > 0) {
    throw new ParamsValidationError(`[${action}] 필수 파라미터 누락: ${JSON.stringify(missing)}`);
  }

  // 2. 허용되지 않은 추가 키 검사 (properties 정의된 경우)
  if (Object.keys(properties).length > 0) {
    const extraKeys = Object.keys(params).filter((k) => !(k in properties));
    if (extraKeys.length > 0) {
      throw new ParamsValidationError(`[${action}] 허용되지 않은 파라미터 키: ${JSON.stringify(extraKeys)}`);
    }
  }

  // 3. 타입 검사 및 정규화
  const normalized = { ...params };
  for (const [key, value] of Object.entries(params)) {
    if (!(key in properties)) continue;
    const expectedType = properties[key].type;
    if (!expectedType || !(expectedType in TYPE_CHECKERS)) continue;

    if (TYPE_CHECKERS[expectedType](value)) continue;

    // 특수 케이스: integer 스키마에 소수점 없는 float 허용 (예: 5.0 → 5)
    if (expectedType === 'integer' && typeof value === 'number' && Number.isFinite(value) && Math.floor(value) === value) {
      normalized[key] = Math.floor(value);
      continue;
    }

    throw new ParamsValidationError(
      `[${action}] 파라미터 타입 불일치: ${JSON.stringify(key)} (기대: ${expectedType}, 실제: ${Array.isArray(value) ? 'array' : typeof value})`
    );
  }

  return normalized;
}

module.exports = { ActionAndParamsValidator };
