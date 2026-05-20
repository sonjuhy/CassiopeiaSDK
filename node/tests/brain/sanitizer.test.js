'use strict';

const { OutputSanitizer } = require('../../src/brain/sanitizer');

describe('OutputSanitizer — none', () => {
  it('원본 반환', () => {
    expect(OutputSanitizer.sanitize('hello *world*', 'none')).toBe('hello *world*');
  });
  it('빈 문자열 반환', () => {
    expect(OutputSanitizer.sanitize('', 'none')).toBe('');
  });
  it('HTML 이스케이핑 안 함', () => {
    const t = "<b>bold</b> & 'quoted'";
    expect(OutputSanitizer.sanitize(t, 'none')).toBe(t);
  });
});

describe('OutputSanitizer — markdown', () => {
  it('* 이스케이핑', () => {
    expect(OutputSanitizer.sanitize('*bold*', 'markdown')).toContain('\\*');
  });
  it('_ 이스케이핑', () => {
    expect(OutputSanitizer.sanitize('_italic_', 'markdown')).toContain('\\_');
  });
  it('` 이스케이핑', () => {
    expect(OutputSanitizer.sanitize('`code`', 'markdown')).toContain('\\`');
  });
  it('[ 이스케이핑', () => {
    expect(OutputSanitizer.sanitize('[link](url)', 'markdown')).toContain('\\[');
  });
  it('# 이스케이핑', () => {
    expect(OutputSanitizer.sanitize('# heading', 'markdown')).toContain('\\#');
  });
  it('| 이스케이핑', () => {
    expect(OutputSanitizer.sanitize('col1 | col2', 'markdown')).toContain('\\|');
  });
  it('일반 한국어 텍스트 변경 없음', () => {
    expect(OutputSanitizer.sanitize('안녕하세요 반갑습니다', 'markdown')).toBe('안녕하세요 반갑습니다');
  });
  it('빈 문자열', () => {
    expect(OutputSanitizer.sanitize('', 'markdown')).toBe('');
  });
  it('이스케이핑 후 길이 증가', () => {
    const orig = '*bold* and _italic_';
    expect(OutputSanitizer.sanitize(orig, 'markdown').length).toBeGreaterThan(orig.length);
  });
});

describe('OutputSanitizer — html', () => {
  it('< 이스케이핑', () => {
    expect(OutputSanitizer.sanitize('<div>', 'html')).toContain('&lt;');
  });
  it('> 이스케이핑', () => {
    expect(OutputSanitizer.sanitize('</div>', 'html')).toContain('&gt;');
  });
  it('& 이스케이핑', () => {
    expect(OutputSanitizer.sanitize('A & B', 'html')).toContain('&amp;');
  });
  it('" 이스케이핑', () => {
    expect(OutputSanitizer.sanitize('say "hello"', 'html')).toContain('&quot;');
  });
  it("' 이스케이핑", () => {
    expect(OutputSanitizer.sanitize("it's", 'html')).toContain('&#x27;');
  });
  it('XSS 벡터 이스케이핑', () => {
    const result = OutputSanitizer.sanitize("<script>alert('xss')</script>", 'html');
    expect(result).not.toContain('<script>');
    expect(result).toContain('&lt;script&gt;');
  });
  it('한국어 텍스트 변경 없음', () => {
    expect(OutputSanitizer.sanitize('안녕하세요', 'html')).toBe('안녕하세요');
  });
  it('빈 문자열', () => {
    expect(OutputSanitizer.sanitize('', 'html')).toBe('');
  });
});
