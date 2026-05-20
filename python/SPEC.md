# Spec: Cassiopeia Agent SDK

## 1. Objective (목적)
별도 프로젝트의 에이전트 개발자가 **`cassiopeia-sdk` 하나만 설치**해 오케스트라 네트워크에 에이전트를 연결할 수 있도록 합니다. Redis 통신, 메시지 서명 검증, LLM 게이트웨이 호출 등의 복잡성을 SDK가 완전히 추상화하여 개발자는 비즈니스 로직에만 집중할 수 있어야 합니다.

## 2. Tech Stack (기술 스택)
- **Python SDK:** Python 3.10+
  - `redis` — 비동기 Pub/Sub 통신
  - `pydantic` — 메시지 스키마 유효성 검증
  - `httpx` — 오케스트라 HTTP API 호출 (에이전트 등록)
  - `pytest`, `pytest-asyncio` — TDD 테스트

## 3. Commands (실행 명령어)
```bash
# 환경 설정
python -m venv venv && venv\Scripts\activate   # Windows
python -m venv venv && source venv/bin/activate # Linux/Mac

# 의존성 설치
pip install -r requirements.txt

# 테스트
pytest tests/ -v
```

## 4. Project Structure (프로젝트 구조)
```text
python/
├── cassiopeia_sdk/
│   ├── __init__.py     # public API re-export (버전 0.3.0)
│   ├── client.py       # CassiopeiaClient, AgentMessage — Redis Pub/Sub
│   ├── tools.py        # Tool, ToolExecutor — 로컬 도구 등록/실행
│   ├── auth.py         # verify_message, DispatchAuthError — HMAC 검증
│   ├── schemas.py      # AgentResult, OrchestraTask, LLMRequest, LLMResponse
│   ├── agent.py        # AgentBase — 에이전트 기본 클래스
│   └── brain/          # NLU 추상화 (v0.3.0 신규)
│       ├── __init__.py         # brain 공개 API 재수출
│       ├── _brain.py           # AgentBrain — 6단계 분석 파이프라인
│       ├── _models.py          # BrainDecision, AgentBrainConfig (Pydantic)
│       ├── _exceptions.py      # PromptInjectionError, UnknownActionError, ParamsValidationError, RateLimitExceededError
│       ├── _guard.py           # PromptInjectionGuard — 정규식 + check_static
│       ├── _validator.py       # ActionAndParamsValidator — action/params JSON Schema 검증
│       ├── _sanitizer.py       # OutputSanitizer — none/markdown/html 이스케이핑
│       ├── _rate_limiter.py    # RateLimiter — memory deque / redis 비동기 백엔드
│       └── _providers.py       # GatewayProvider, DirectProvider, LLMProviderFactory
├── tests/
│   ├── test_client.py          # CassiopeiaClient 단위 테스트
│   ├── test_tools.py           # ToolExecutor 단위 테스트
│   ├── test_auth.py            # verify_message 단위 테스트
│   ├── test_agent_base.py      # AgentBase 단위 테스트
│   └── brain/
│       ├── test_brain.py       # AgentBrain 통합 테스트
│       ├── test_guard.py       # PromptInjectionGuard 단위 테스트
│       ├── test_models.py      # BrainDecision / AgentBrainConfig 단위 테스트
│       ├── test_rate_limiter.py # RateLimiter 단위 테스트
│       ├── test_sanitizer.py   # OutputSanitizer 단위 테스트
│       └── test_validator.py   # ActionAndParamsValidator 단위 테스트
├── pyproject.toml
└── requirements.txt
```

## 5. Module Responsibilities (모듈 책임)

| 모듈 | 책임 |
|------|------|
| `client.py` | Redis Pub/Sub 연결, 메시지 발행/구독, `AgentMessage` 직렬화 |
| `tools.py` | 로컬 도구 등록 및 동기 실행 |
| `auth.py` | HMAC-SHA256 서명 검증, 시크릿 미설정 시 건너뜀 |
| `schemas.py` | 오케스트라 프로토콜 TypedDict 정의 (런타임 영향 없음) |
| `agent.py` | 수신 루프, 서명 검증, LLM 게이트웨이(model 파라미터 지원), 결과 반환, 등록 HTTP 호출 |
| `brain/_brain.py` | `AgentBrain` — 자연어 요청 → `BrainDecision` 6단계 파이프라인 |
| `brain/_models.py` | `BrainDecision`(confidence 기본값 0.0, Pydantic ge/le), `AgentBrainConfig`(8개 snake_case 필드) |
| `brain/_guard.py` | `PromptInjectionGuard` — 12개 정규식 패턴; `check()`는 enabled 존중, `check_static()`은 항상 실행 |
| `brain/_validator.py` | `ActionAndParamsValidator` — action 조회 + JSON Schema 타입/필수/추가키 검증, float→int 정규화 |
| `brain/_sanitizer.py` | `OutputSanitizer` — none/markdown/html 이스케이핑 정책 |
| `brain/_rate_limiter.py` | `RateLimiter` — memory deque 슬라이딩 윈도우(60초) 또는 redis 비동기 백엔드 |
| `brain/_providers.py` | `GatewayProvider`(caller 위임), `DirectProvider`(환경변수 API 키), `LLMProviderFactory` |
| `brain/_exceptions.py` | `PromptInjectionError`, `UnknownActionError`, `ParamsValidationError`, `RateLimitExceededError` |

## 6. AgentBase 내부 동작 흐름

```
start()
  └─ client.connect()
  └─ async for msg in client.listen():
        ├─ action == "llm_result" → _resolve_llm(payload) [Future 해소]
        ├─ verify_message(payload) [실패 시 무시]
        └─ asyncio.create_task(handle(msg))

request_llm()
  └─ Future 생성 → _pending_llm[task_id] = fut
  └─ send_message(action="llm_call", receiver="orchestra")
  └─ asyncio.wait_for(fut, timeout)
     ← "llm_result" 수신 시 Future 해소
```

## 7. Testing Strategy (테스트 전략)
- TDD: 실패 테스트(RED) → 최소 구현(GREEN) → 리팩토링
- 모든 async 테스트는 `pytest-asyncio` (`asyncio_mode = auto`) 사용
- 외부 의존성(Redis, HTTP) 전부 Mock 처리
- 커버리지 대상: 인증 실패, rate_limited, timeout, 정상 흐름

## 8. Boundaries (경계 및 규칙)
- **항상:** 시크릿/URL을 코드에 하드코딩하지 않습니다. 환경변수로만 주입합니다.
- **금지:** SDK 내부에서 오케스트라 Redis 키 구조에 직접 의존하지 않습니다. (Pub/Sub만 사용)
- **참고 (v0.3.0 변경):** `request_llm()`은 `system` role 메시지를 허용합니다. `AgentBrain`이 시스템 프롬프트를 포함한 메시지를 LLM에 전달해야 하기 때문입니다. 프롬프트 인젝션 방어는 `PromptInjectionGuard`가 담당합니다.

## 9. Success Criteria (성공 기준)
- [x] `AgentBase` 상속만으로 동작하는 에이전트 작성 가능
- [x] `request_llm()` — API 키 없이 LLM 호출 가능 (오케스트라 게이트웨이 경유), model 파라미터 지원
- [x] `verify_message()` 로 수신 메시지 HMAC 검증 가능
- [x] `register()` 로 오케스트라에 에이전트 등록 가능
- [x] `AgentBrain` — 자연어 요청 분석 → `BrainDecision` (v0.3.0 신규)
- [x] `PromptInjectionGuard` — 13개 패턴 정규식 + LLM 2차 방어
- [x] `ActionAndParamsValidator` — JSON Schema 기반 action/params 검증
- [x] `OutputSanitizer` — none/markdown/html 이스케이핑
- [x] `RateLimiter` — memory/redis 백엔드 슬라이딩 윈도우
- [x] 151개 테스트 전체 통과 (pytest 기준)
- [x] `GUIDE.md`에 AgentBrain 포함 전체 사용법 문서화
