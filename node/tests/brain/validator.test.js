'use strict';

const { ActionAndParamsValidator } = require('../../src/brain/validator');
const { UnknownActionError, ParamsValidationError } = require('../../src/brain/exceptions');
const { Tool } = require('../../src/tools');

const SEARCH_TOOL = new Tool({
  name: 'search_file',
  description: '파일 검색',
  parameters: {
    type: 'object',
    properties: {
      query: { type: 'string', description: '검색어' },
      limit: { type: 'integer', description: '최대 결과 수' },
    },
    required: ['query'],
  },
});

const SEND_TOOL = new Tool({
  name: 'send_message',
  description: '메시지 전송',
  parameters: {
    type: 'object',
    properties: {
      to: { type: 'string' },
      body: { type: 'string' },
      urgent: { type: 'boolean' },
    },
    required: ['to', 'body'],
  },
});

const ALL_TOOLS = [SEARCH_TOOL, SEND_TOOL];

describe('ActionAndParamsValidator — action 유효성', () => {

  it('유효한 action은 Tool 반환', () => {
    const [tool] = ActionAndParamsValidator.validate('search_file', { query: '보고서' }, ALL_TOOLS);
    expect(tool.name).toBe('search_file');
  });

  it('미등록 action은 UnknownActionError', () => {
    expect(() => ActionAndParamsValidator.validate('do_magic', {}, ALL_TOOLS)).toThrow(UnknownActionError);
  });

  it('에러 메시지에 사용 가능한 action 목록 포함', () => {
    expect(() => ActionAndParamsValidator.validate('unknown', {}, ALL_TOOLS))
      .toThrow(/search_file/);
  });

  it('dict 형태 tools 허용', () => {
    const dictTools = ALL_TOOLS.map((t) => t.toObject());
    const [tool] = ActionAndParamsValidator.validate('send_message', { to: 'bob', body: 'hi' }, dictTools);
    expect(tool.name).toBe('send_message');
  });

  it('빈 tools 배열은 UnknownActionError', () => {
    expect(() => ActionAndParamsValidator.validate('any', {}, [])).toThrow(UnknownActionError);
  });
});

describe('ActionAndParamsValidator — params 검증', () => {

  it('유효한 params는 정규화된 값 반환', () => {
    const [, params] = ActionAndParamsValidator.validate('search_file', { query: 'test' }, ALL_TOOLS);
    expect(params.query).toBe('test');
  });

  it('필수 파라미터 누락 시 ParamsValidationError', () => {
    expect(() => ActionAndParamsValidator.validate('search_file', {}, ALL_TOOLS))
      .toThrow(ParamsValidationError);
  });

  it('허용되지 않은 추가 키 시 ParamsValidationError', () => {
    expect(() => ActionAndParamsValidator.validate(
      'search_file', { query: 'test', evil: 'hack' }, ALL_TOOLS
    )).toThrow(ParamsValidationError);
  });

  it('타입 불일치 시 ParamsValidationError', () => {
    expect(() => ActionAndParamsValidator.validate(
      'search_file', { query: 12345 }, ALL_TOOLS
    )).toThrow(ParamsValidationError);
  });

  it('integer 스키마에 float 정수값 정규화 (5.0 → 5)', () => {
    const [, params] = ActionAndParamsValidator.validate(
      'search_file', { query: 'test', limit: 5.0 }, ALL_TOOLS
    );
    expect(params.limit).toBe(5);
    expect(Number.isInteger(params.limit)).toBe(true);
  });

  it('optional 파라미터 생략 가능', () => {
    const [, params] = ActionAndParamsValidator.validate(
      'search_file', { query: 'test' }, ALL_TOOLS
    );
    expect('limit' in params).toBe(false);
  });

  it('boolean 타입 허용', () => {
    const [, params] = ActionAndParamsValidator.validate(
      'send_message', { to: 'alice', body: 'hi', urgent: true }, ALL_TOOLS
    );
    expect(params.urgent).toBe(true);
  });

  it('에러 메시지에 action 이름 포함', () => {
    expect(() => ActionAndParamsValidator.validate('search_file', {}, ALL_TOOLS))
      .toThrow(/search_file/);
  });

  it('properties 없는 Tool은 빈 params 허용', () => {
    const pingTool = new Tool({ name: 'ping', description: '연결 확인', parameters: { type: 'object' } });
    const [, params] = ActionAndParamsValidator.validate('ping', {}, [pingTool]);
    expect(params).toEqual({});
  });
});
