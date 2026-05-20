# 테스트 데이터 설계 문서 — LLM Gateway 모델 선택 기능

## 개요
- **대상**: `LLMRequest`, `LLMResponse` (schemas.py) / `AgentBase.request_llm()` (agent.py)
- **변경 명세**: LLM Gateway 모델 선택 기능 추가 안내 (2026-05-07)
- **입력 명세**:
  - `LLMRequest.model`: `str | None` — 모델 오버라이드 (선택, 기본 None)
  - `LLMRequest.messages`: `system` role 추가 허용
  - `LLMResponse.model`: `str | None` — 실제 사용된 모델명 반환
  - `AgentBase.request_llm(model=)`: `str | None` 파라미터 추가
- **출력 명세**: 기존 동작 하위 호환, model 미지정 시 None
- **적용 기법**: 동등 분할(Equivalence Partitioning), 경계값 분석(Boundary Value Analysis)

---

## 동등 분할 구간 (Equivalence Classes)

| 구간 ID | 구간 설명 | 대표값 | 유효/무효 |
|---------|-----------|--------|-----------|
| EC-01 | model 미지정 (None) | `None` | 유효 — 기존 동작 유지 |
| EC-02 | 유효한 model 문자열 | `"gemini-1.5-pro"` | 유효 |
| EC-03 | system role 메시지 | `{"role": "system", "content": "..."}` | 유효 (신규 허용) |
| EC-04 | user role 메시지 | `{"role": "user", "content": "..."}` | 유효 (기존) |
| EC-05 | assistant role 메시지 | `{"role": "assistant", "content": "..."}` | 유효 (기존) |

---

## 경계값 목록 (Boundary Values)

| 경계 ID | 경계 조건 | 경계값 | 설명 |
|---------|-----------|--------|------|
| BV-01 | max_tokens 기본값 | `500` | 명세 기본값 유지 확인 |
| BV-02 | temperature 기본값 | `0.7` | 명세 기본값 유지 확인 |
| BV-03 | model 최소 유효값 | `"a"` (1자) | 1~100자 규칙의 최솟값 |
| BV-04 | model 최대 유효값 | `"a" * 100` (100자) | 1~100자 규칙의 최댓값 |

---

## 테스트 케이스 상세

| TC-ID | 분류 | 설명 | Input | Expected | 커버하는 구간/경계 |
|-------|------|------|-------|----------|--------------------|
| TC-01 | Happy Path | LLMRequest model 미지정 시 None | model 생략 | `model == None` | EC-01 |
| TC-02 | Happy Path | LLMRequest model 지정 시 값 설정 | `model="gemini-1.5-pro"` | `model == "gemini-1.5-pro"` | EC-02 |
| TC-03 | Happy Path | LLMResponse model 필드 None 가능 | `model=None` | `model == None` | EC-01 |
| TC-04 | Happy Path | LLMResponse model 필드 값 설정 가능 | `model="gemini-1.5-pro"` | `model == "gemini-1.5-pro"` | EC-02 |
| TC-05 | Happy Path | messages에 system role 포함 가능 | `role="system"` | 정상 설정 | EC-03 |
| TC-06 | Boundary | max_tokens 기본값 500 유지 | 생략 | `max_tokens == 500` | BV-01 |
| TC-07 | Boundary | temperature 기본값 0.7 유지 | 생략 | `temperature == 0.7` | BV-02 |
| TC-08 | Happy Path | request_llm model=None 시 payload에 model 없거나 None | `model=None` | payload에 model 키 없거나 None | EC-01 |
| TC-09 | Happy Path | request_llm model 지정 시 payload에 model 포함 | `model="gemini-1.5-pro"` | `payload["model"] == "gemini-1.5-pro"` | EC-02 |
| TC-10 | Happy Path | system role 포함 메시지로 request_llm 정상 호출 | system role 메시지 포함 | 정상 전송 완료 | EC-03 |
| TC-11 | Business Rule | model 파라미터 없이 호출 — 하위 호환 | model 파라미터 미전달 | 기존과 동일 동작 | EC-01 |

---

## 커버리지 체크
- [x] 모든 동등 분할 구간에 최소 1개 케이스 존재
- [x] 모든 경계값에 케이스 존재 (BV-01, BV-02)
- [x] 명세에 명시된 model 필드 신규 추가 케이스 포함
- [x] system role 신규 허용 케이스 포함
- [x] 하위 호환성(model 미지정) 케이스 포함
- [x] LLMRequest / LLMResponse / AgentBase 세 대상 모두 커버
