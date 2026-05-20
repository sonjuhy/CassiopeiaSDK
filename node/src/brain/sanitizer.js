'use strict';

const MARKDOWN_SPECIAL = new Set([
  '\\', '`', '*', '_', '{', '}', '[', ']', '(', ')', '#', '+', '-', '.', '!', '|', '~', '>',
]);

function escapeMarkdown(text) {
  let result = '';
  for (const char of text) {
    if (MARKDOWN_SPECIAL.has(char)) result += '\\';
    result += char;
  }
  return result;
}

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;');
}

/**
 * LLM이 생성한 텍스트를 출력 채널에 맞게 이스케이핑합니다.
 *
 * 적용 대상: BrainDecision.suggested_reply, BrainDecision.reasoning
 * 제외 대상: BrainDecision.params (ActionAndParamsValidator로 구조 검증 완료)
 */
class OutputSanitizer {
  /**
   * @param {string} text
   * @param {'none'|'markdown'|'html'} policy
   * @returns {string}
   */
  static sanitize(text, policy) {
    if (policy === 'none') return text;
    if (policy === 'markdown') return escapeMarkdown(text);
    if (policy === 'html') return escapeHtml(text);
    return text;
  }
}

module.exports = { OutputSanitizer };
