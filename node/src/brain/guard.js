'use strict';

const { PromptInjectionError } = require('./exceptions');

// ---------------------------------------------------------------------------
// 인젝션 탐지 패턴 목록
// ---------------------------------------------------------------------------

const PATTERNS = [
  // 시스템 프롬프트 구조 탈출
  /<\/?(?:system|prompt|instruction)\b/i,
  /<\|im_(?:start|end)\|>/i,
  /\[(?:현재|이전|지금).*?(?:요청|지시|명령).*?(?:종료|무시|끝)\]/is,

  // 역할 전환 시도
  /\byou\s+are\s+now\b/i,
  /\bact\s+as\b/i,
  /새로운\s*(?:역할|지시|명령|시스템\s*프롬프트)/,

  // 이전 지시 무력화
  /ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions?/i,
  /(?:forget|disregard)\s+(?:all\s+)?(?:previous|prior|your)(?:\s+previous)?\s+(?:instructions?|prompt)/i,
  /(?:이전|모든)\s*(?:지시|명령|프롬프트)\s*(?:무시|잊어|ignore)/i,

  // 마크다운 헤더 인젝션
  /^#{1,6}\s+(?:new\s+instruction|system\s+prompt|override|jailbreak)/im,

  // 알려진 탈옥 키워드
  /\bjailbreak\b/i,
  /\bDAN\s*(?:mode|prompt)\b/i,
];

function detectPattern(text) {
  for (const pattern of PATTERNS) {
    if (pattern.test(text)) return pattern;
  }
  return null;
}

// ---------------------------------------------------------------------------
// PromptInjectionGuard
// ---------------------------------------------------------------------------

class PromptInjectionGuard {
  /**
   * @param {boolean} [enabled=true]
   * @param {'raise'|'fallback'} [policy='fallback']
   */
  constructor(enabled = true, policy = 'fallback') {
    this.enabled = enabled;
    this.policy = policy;
  }

  /**
   * user_request와 history 내 role="user" 메시지를 검사합니다.
   * enabled=false이면 즉시 반환 (검사 생략).
   * 탐지 시 PromptInjectionError 발생 (policy 분기는 AgentBrain에서 처리).
   *
   * @param {string} userRequest
   * @param {Array<{role:string, content:string}>|null} [history=null]
   */
  check(userRequest, history = null) {
    if (!this.enabled) return;

    let matched = detectPattern(userRequest);
    if (matched) {
      throw new PromptInjectionError(
        `[user_request] 프롬프트 인젝션이 탐지되었습니다: ${matched.source}`
      );
    }

    if (history) {
      history.forEach((msg, i) => {
        if (msg.role === 'user') {
          matched = detectPattern(msg.content || '');
          if (matched) {
            throw new PromptInjectionError(
              `[history[${i}]] 프롬프트 인젝션이 탐지되었습니다: ${matched.source}`
            );
          }
        }
      });
    }
  }

  /**
   * 초기화 시점 정적 검사 (capabilities 등 개발자 입력 검증).
   * enableInjectionGuard 값과 무관하게 항상 실행됩니다.
   * 탐지 시 Error 발생 (injectionGuardPolicy 무관).
   *
   * @param {string} text
   * @param {string} [label='input']
   */
  checkStatic(text, label = 'input') {
    const matched = detectPattern(text);
    if (matched) {
      throw new Error(
        `[${label}] 인젝션 패턴이 감지되었습니다: ${matched.source}\n` +
        'capabilities에 시스템 지시 패턴이 포함되어 있는지 확인해주세요.'
      );
    }
  }
}

module.exports = { PromptInjectionGuard };
