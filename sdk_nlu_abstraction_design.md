# Cassiopeia SDK NLU 추상화 설계 가이드 (v7 - Verified)

## 1. 배경 및 목적 (Background & Objectives)

현재 카시오페아(Cassiopeia) 시스템 내에서 개별 에이전트들은 자율성(Autonomy)을 확보하기 위해 내부적으로 LLM을 호출하여 의도를 파악하고 도구를 선택합니다.
하지만 이 과정에서 다음과 같은 문제점(Anti-patterns)이 지적되었습니다.

1. **결합도 증가 및 철학적 충돌**: 기존 `request_llm` 기반의 Gateway 방식(중앙 API 키 관리)과 에이전트가 직접 LLM을 호출하는 방식이 혼재되어 있습니다.
2. **로직 중복**: 프롬프트 구성, JSON 파싱, 재시도(Self-healing), 보안(인젝션 방어) 로직이 에이전트마다 중복됩니다.
3. **스키마 불일치**: LLM에게 도구를 설명할 때 문자열 리스트(`list[str]`)만 제공하여 정확한 파라미터 추출이 어렵습니다.

**목적**: 이러한 NLU 추론 기능을 `cassiopeia-sdk` 내의 `brain` 모듈로 완벽히 추상화하여, 타입 안정성, 보안 정책, 중앙 통제력을 제공하면서도 개발 생산성을 극대화합니다.

---

## 2. 핵심 아키텍처 의사결정 (Architecture Decisions)

### 2.1. Provider 추상화 (Gateway & Direct 동시 지원)
에이전트 배포 환경에 따라 LLM 호출 경로를 유연하게 선택할 수 있도록 Provider 인터페이스를 도입합니다.
- **`GatewayProvider`**: `AgentBase.request_llm`과 같은 **비동기 Callable 객체**를 주입받아 사용합니다. 이는 `CassiopeiaClient`만으로는 불가능한 '응답 대기(Future waiting)' 메커니즘을 에이전트 베이스 클래스로부터 위임받기 위함입니다.
- **`DirectProvider`**: Gemini, Claude 등 외부 API 직접 호출. (3rd-party 독립 에이전트용) API 키는 에이전트 범위 환경변수를 통해 격리 로드합니다.

### 2.2. Tool 객체 통합 (`ToolExecutor` 연동)
LLM에게 단순 액션 이름이 아닌, 명확한 JSON Schema가 포함된 `Tool` 객체 기반의 정보를 제공합니다. `analyze_task`는 `Tool` 객체나 `dict` 형태의 Schema 리스트를 유연하게 수용합니다.

### 2.3. Pydantic 기반의 엄격한 반환 타입 (`BrainDecision`)
파싱의 책임을 SDK가 전담합니다. 신뢰도(confidence) 미달 시 SDK가 스스로 `action="ask_clarification"` 형태로 반환하여 에이전트 코드의 복잡성을 줄입니다.

### 2.4. 보안 원칙
- **입력 검증**: `user_request`와 `history` 내 `role="user"` 메시지 양쪽 모두 인젝션 검사 수행
- **출력 검증**: LLM 생성 텍스트(`suggested_reply`, `reasoning`)는 사용 전 반드시 이스케이핑
- **출력 파라미터 검증**: LLM 생성 `params`는 Tool 스키마 및 `action` 유효성 대조 후 전달
- **최소 신뢰**: LLM 응답의 `confidence` 미반환 시 기본값을 `0.0`으로 처리 (최소 신뢰 원칙)
- **호출 제한**: Rate Limit 설정으로 비용 폭발 및 DoS 방어

---

## 3. SDK 내 신규 모듈 설계 (SDK Design)

### 3.1. 타입 정의 및 모델
```python
from __future__ import annotations

from collections.abc import Callable, Awaitable, Sequence
from typing import Any, Literal
from pydantic import BaseModel, Field
from cassiopeia_sdk.schemas import LLMResponse
from cassiopeia_sdk.tools import Tool

BackendType = Literal["gateway", "gemini", "claude", "local"]
OutputEscapePolicy = Literal["none", "markdown", "html"]
RateLimitBackend = Literal["memory", "redis"]

# GatewayProvider에 주입되는 llm_caller의 타입 별칭
LLMCallerType = Callable[..., Awaitable[LLMResponse]]


class BrainDecision(BaseModel):
    action: str                        # 실행할 도구 이름 (신뢰도 미달 시 'ask_clarification')
    params: dict[str, Any]             # Tool 스키마 검증 완료된 파라미터
    reasoning: str | None = None       # LLM이 해당 결정을 내린 이유 (이스케이핑 적용됨)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    # ↑ 보안: 기본값 0.0 (최소 신뢰 원칙). LLM 미반환 시 ask_clarification 자동 유도.
    #   Pydantic ge/le 제약으로 0.0~1.0 범위 외 값 차단.
    suggested_reply: str | None = None
    # ↑ ask_clarification 시 사용자에게 전달할 텍스트 (이스케이핑 적용됨).
    #   SDK가 confidence 미달 탐지 시 LLM reasoning 기반으로 자동 생성.
    #   None이면 에이전트에서 폴백 문구 처리.
```

### 3.2. `AgentBrainConfig` (정책 관리)
```python
class AgentBrainConfig(BaseModel):
    max_retries: int = 2
    # JSON 파싱 실패, UnknownActionError, ParamsValidationError 발생 시 최대 재시도 횟수.
    # 각 재시도는 지수 백오프(1s → 2s → 4s ...) 적용.
    # 재시도 시 이전 오류 내용을 프롬프트에 포함하여 LLM 자기 수정 유도.
    # ※ 재시도 LLM 호출은 rate_limit_per_minute 카운트에 포함되지 않음.

    confidence_threshold: float = 0.7
    # 이 수치 미만이면 SDK가 내부적으로 action="ask_clarification" 결정을 반환.
    # BrainDecision.confidence 기본값이 0.0이므로, LLM 미반환 시 항상 이 조건에 걸림.

    enable_injection_guard: bool = True
    # False로 설정 시 PromptInjectionGuard의 check() 호출을 비활성화.
    # ⚠️ check_static()은 enable_injection_guard 값과 무관하게 항상 실행됨.
    #   (개발자 실수로 인한 capabilities 오염 방지 목적)
    # 프로덕션 환경에서는 반드시 True 유지.

    injection_guard_policy: Literal["raise", "fallback"] = "fallback"
    # "raise"   : 인젝션 탐지 시 PromptInjectionError 예외 발생.
    # "fallback": 인젝션 탐지 시 예외 없이 confidence=0 + action="ask_clarification" 으로 강제 라우팅.

    enable_llm_secondary_guard: bool = False
    # True 설정 시 Step 1 정규식 검사 통과 후, 메인 LLM 호출 전에
    # 검증 전용 LLM 호출로 인젝션 2차 검증 수행 (입력 단계에서 실행).
    # 블랙리스트 우회(인코딩·유니코드 변형) 방어에 효과적.
    # 고위험 에이전트(금융, 개인정보 처리 등) 또는 외부 사용자 입력을 받는 에이전트에 권장.
    # 활성화 시 LLM 호출 1회 추가 발생 (이 호출은 rate_limit 카운트에 포함).

    rate_limit_per_minute: int | None = None
    # 에이전트 인스턴스 단위 분당 analyze_task 최대 호출 횟수 (per-agent-instance).
    # None이면 제한 없음. 외부 사용자 입력을 받는 에이전트는 반드시 설정 권장. (예: 60)
    # 초과 시 RateLimitExceededError 발생.
    # ※ 사용자별(per-user) 제한이 필요한 경우 호출자 레벨에서 별도 처리 필요.

    rate_limit_backend: RateLimitBackend = "memory"
    # "memory": 단일 프로세스 환경. 프로세스 재시작 시 카운터 초기화.
    #           ⚠️ scale-out(다중 인스턴스) 환경에서는 인스턴스마다 독립 카운터로
    #              실제 제한이 n배 증가하는 문제 발생. 단일 프로세스 배포 전용.
    # "redis" : 분산 환경. Redis 연결 필요 (BRAIN_RATE_LIMIT_REDIS_URL 환경변수).
    #           scale-out 시에도 전체 인스턴스 합산 정확한 제한 유지. 권장.

    output_escape_policy: OutputEscapePolicy = "markdown"
    # suggested_reply, reasoning 등 LLM 생성 텍스트의 출력 이스케이핑 정책.
    # "none"    : 이스케이핑 없음. 신뢰된 내부 채널 전용.
    # "markdown": Slack·노션 등 마크다운 채널용 특수문자 이스케이핑.
    # "html"    : 웹 UI 출력용 HTML 엔티티 이스케이핑.
```

### 3.3. `PromptInjectionGuard` (보안 명세)
```python
class PromptInjectionGuard:
    """
    1차 방어: 정규식 기반 블랙리스트 탐지
    ──────────────────────────────────────
    탐지 패턴:
    - 시스템 프롬프트 구조 탈출 시도
      (예: `[현재 요청 종료]`, `</system>`, `<|im_end|>`)
    - 마크다운 헤더 기반 인젝션
      (예: `## New Instruction`, `Ignore previous instructions`)
    - 역할 전환 시도
      (예: `You are now`, `Act as`, `새로운 역할`)

    ⚠️ 블랙리스트 방식의 한계:
    정규식 탐지는 인코딩 변형(유니코드·Base64·공백 삽입 등)으로 우회될 수 있습니다.
    고위험 에이전트에는 AgentBrainConfig.enable_llm_secondary_guard=True 설정을 통해
    LLM 기반 2차 검증을 병행하여 방어 심도를 높이는 것을 강력히 권장합니다.

    검사 대상:
    - user_request (현재 사용자 입력)
    - history 내 role="user" 메시지의 content만 검사
      ※ role="assistant" 메시지는 SDK/에이전트 자신이 생성한 텍스트이므로 검사 제외.
        (포함 시 이전 응답에 인젝션 패턴이 포함된 경우 false positive 발생)
    - capabilities 문자열 (에이전트 초기화 시 check_static으로 1회 검사)

    처리 정책 (AgentBrainConfig.injection_guard_policy 에 따라 결정):
    - "raise"   : PromptInjectionError 예외 발생 → 호출자가 직접 처리
    - "fallback": confidence=0, action="ask_clarification" 으로 강제 라우팅
                  → 에이전트 코드 변경 없이 보안 위협 무력화
    """
    def __init__(self, enabled: bool = True, policy: Literal["raise", "fallback"] = "fallback"):
        self.enabled = enabled
        self.policy = policy

    def check(self, user_request: str, history: list[dict[str, str]] | None = None) -> None:
        """
        user_request와 history 내 role="user" 메시지를 검사합니다.
        enabled=False이면 즉시 반환 (검사 생략).
        탐지 시 policy에 따라 PromptInjectionError 발생 또는 fallback 처리.
        """
        ...

    def check_static(self, text: str, label: str = "input") -> None:
        """
        초기화 시점 정적 검사용 (capabilities 등 개발자 입력 검증).
        ※ AgentBrainConfig.enable_injection_guard 값과 무관하게 항상 실행됨.
        탐지 시 항상 ValueError 발생 (정책 무관).
        """
        ...
```

### 3.4. `ActionAndParamsValidator` (action 유효성 + 파라미터 검증)
```python
class ActionAndParamsValidator:
    """
    LLM이 생성한 BrainDecision.action과 params를 tools 목록 기준으로 검증합니다.
    executor.execute() 호출 전 반드시 수행하여 미등록 action 실행 및 2차 공격을 차단합니다.

    검증 순서:
    1. action이 tools 목록에 존재하는 이름인지 확인 (UnknownActionError)
    2. 해당 Tool의 parameters 스키마로 params 검증:
       - 필수 파라미터 존재 여부
       - 각 파라미터의 타입 일치 여부
       - 허용된 키 외의 추가 키 포함 여부 (extra 필드 차단)

    재시도 트리거 (analyze_task 내 max_retries 루프와 연동):
    - UnknownActionError    : LLM이 잘못된 action명 반환 → 오류 피드백 포함 재시도
    - ParamsValidationError : 파라미터 누락·타입 불일치 → 오류 피드백 포함 재시도
    - max_retries 소진 후에도 실패 → 최종 ParamsValidationError 발생 (재시도 없음)

    재시도 불가 케이스 (즉시 예외):
    - 보안 위반 (PromptInjectionError)
    - RateLimitExceededError
    """
    @staticmethod
    def validate(
        action: str,
        params: dict[str, Any],
        tools: Sequence[Tool | dict[str, Any]],
    ) -> tuple[Tool, dict[str, Any]]:
        """
        검증된 (Tool 객체, params)를 반환.
        tools 목록에서 action과 일치하는 Tool을 탐색한 후 params 검증 수행.
        실패 시 UnknownActionError 또는 ParamsValidationError 발생.
        """
        ...
```

### 3.5. `OutputSanitizer` (LLM 생성 텍스트 이스케이핑)
```python
class OutputSanitizer:
    """
    LLM이 생성한 텍스트를 출력 채널에 맞게 이스케이핑합니다.

    적용 대상:
    - BrainDecision.suggested_reply  : 사용자에게 직접 전달되는 텍스트
    - BrainDecision.reasoning        : 에이전트가 사용자에게 노출할 수 있는 추론 텍스트
    ※ BrainDecision.params 내부 문자열은 Tool executor가 직접 처리하므로
      OutputSanitizer 적용 범위에서 제외. (ActionAndParamsValidator로 구조 검증 완료)
    """
    @staticmethod
    def sanitize(text: str, policy: OutputEscapePolicy) -> str:
        """
        policy에 따라 이스케이핑된 텍스트 반환.
        - "none"    : 원본 반환 (내부 채널 전용)
        - "markdown": *, _, `, [, ] 등 마크다운 특수문자 이스케이핑
        - "html"    : <, >, &, ", ' HTML 엔티티 변환
        """
        ...
```

### 3.6. `AgentBrain` 메인 인터페이스
```python
class AgentBrain:
    def __init__(self,
                 agent_name: str,
                 capabilities: str,
                 backend: BackendType = "gateway",
                 llm_caller: LLMCallerType | None = None,
                 config: AgentBrainConfig | None = None):
        """
        Args:
            agent_name:   에이전트 식별 이름
            capabilities: 에이전트가 수행할 수 있는 작업에 대한 자연어 설명.
                          시스템 프롬프트 조립에 사용됨.
                          check_static()으로 초기화 시 검증 (enable_injection_guard 무관).
            backend:      LLM 호출 경로 선택.
            llm_caller:   backend="gateway"일 때 필수.
                          AgentBase.request_llm 메서드를 직접 주입. (예: self.request_llm)
                          Future 대기 메커니즘을 AgentBase로부터 위임받기 위함.
            config:       정책 설정. 미전달 시 AgentBrainConfig 기본값 적용.

        Note:
            api_key는 생성자에 직접 전달하지 않습니다.
            DirectProvider는 에이전트 범위 환경변수를 통해 키를 격리 로드합니다.
            환경변수 명명 규칙: {AGENT_NAME}_{PROVIDER}_API_KEY
            (예: ARCHIVE_AGENT_GEMINI_API_KEY, RESEARCH_AGENT_ANTHROPIC_API_KEY)
        """
        self.agent_name = agent_name
        self.config = config or AgentBrainConfig()
        self.guard = PromptInjectionGuard(
            enabled=self.config.enable_injection_guard,
            policy=self.config.injection_guard_policy,
        )
        self.sanitizer = OutputSanitizer()

        # 보안: capabilities를 시스템 프롬프트에 삽입하기 전 정적 검증
        # enable_injection_guard 값과 무관하게 항상 실행
        self.guard.check_static(capabilities, label="capabilities")
        self.capabilities = capabilities

        if backend == "gateway":
            if not llm_caller:
                raise ValueError("Gateway backend requires an llm_caller (e.g., self.request_llm).")
            self.provider = GatewayProvider(caller=llm_caller)
        else:
            self.provider = LLMProviderFactory.create(backend, agent_name=agent_name)

        self._call_counter = RateLimiter(
            limit=self.config.rate_limit_per_minute,
            backend=self.config.rate_limit_backend,
        )

    async def analyze_task(self,
                           user_request: str,
                           tools: Sequence[Tool | dict[str, Any]],
                           history: list[dict[str, str]] | None = None) -> BrainDecision:
        """
        Args:
            user_request: 사용자의 자연어 요청.
            tools:        실행 가능한 Tool 객체 또는 dict Schema 리스트.
                          ToolExecutor.get_registered_tools() 반환값과 호환.
            history:      멀티턴 대화 히스토리. [{"role": "user"|"assistant", "content": "..."}]
                          role="user" 메시지만 인젝션 검사 대상 (assistant는 제외).
        """
        # Step 0. Rate Limit 검사 (per-agent-instance)
        #         초과 시 RateLimitExceededError 발생. 재시도 루프 진입 전에 수행.
        self._call_counter.check()

        # Step 1. 1차 인젝션 방어 (정규식 블랙리스트)
        #         user_request + history 내 role="user" 메시지만 검사.
        #         enable_injection_guard=False이면 생략.
        self.guard.check(user_request, history=history)

        # Step 1.5. 2차 인젝션 방어 (LLM 기반) — enable_llm_secondary_guard=True 시 실행
        #           메인 LLM 호출 전, 입력 내용을 검증 전용 LLM으로 별도 검사.
        #           인코딩·유니코드 변형 등 블랙리스트 우회 패턴 탐지.
        #           이 LLM 호출은 rate_limit_per_minute 카운트에 포함됨.

        # Step 2. 시스템 프롬프트 조립
        #         capabilities + tools의 JSON Schema 변환 + history 포함

        # Step 3. 메인 LLM 호출 (llm_caller 또는 DirectProvider 활용)

        # Step 4. JSON 안전 파싱 → ActionAndParamsValidator 실행
        #         - action이 tools 목록에 존재하는지 검증 (UnknownActionError)
        #         - Tool 스키마 기반 params 검증 (ParamsValidationError)
        #         - confidence 미반환 시 0.0 처리 (최소 신뢰 원칙)
        #         - 실패 시 오류 피드백 포함 프롬프트로 max_retries 횟수만큼 지수 백오프 재시도
        #           재시도 LLM 호출은 rate_limit 카운트에 포함되지 않음
        #         - max_retries 소진 후에도 실패 → ParamsValidationError 최종 발생

        # Step 5. 신뢰도 평가
        #         confidence < config.confidence_threshold
        #         → action="ask_clarification"
        #         → suggested_reply: LLM reasoning 기반 자동 생성. 생성 불가 시 None.

        # Step 6. OutputSanitizer 적용
        #         suggested_reply, reasoning에 config.output_escape_policy 이스케이핑 적용

        return BrainDecision(...)
```

---

## 4. 에이전트 코드 변화 (Before vs After)

### Before (현재 모노리포 방식의 문제점)
```python
# shared_core에 강결합, 프롬프트 관리 부담, 모호한 dict 반환
from shared_core.llm import ClaudeProvider
import json

class ArchiveAgent:
    def __init__(self):
        self.llm = ClaudeProvider()

    async def handle_dispatch(self, msg):
        prompt = f"다음 문장을 분석해줘. {msg.get('content')}"
        res, _ = await self.llm.generate_response(prompt)
        data = json.loads(res)       # 파싱 에러 발생 가능성 높음
        action = data.get("action")  # 타입 보장 안 됨
        # ...
```

### After (SDK 기반 우아한 추상화 - 최종형)
```python
# 오직 SDK에만 의존, 프롬프트 엔지니어링 생략, 타입 안전성 + 보안 보장
from cassiopeia_sdk.brain import AgentBrain, AgentBrainConfig, BrainDecision

class ArchiveAgent(AgentBase):
    def __init__(self, ...):
        super().__init__(...)
        self.brain = AgentBrain(
            agent_name="archive_agent",
            capabilities="노션 및 옵시디언 데이터 관리",
            backend="gateway",
            llm_caller=self.request_llm,
            config=AgentBrainConfig(
                rate_limit_per_minute=60,           # per-agent-instance DoS 방어
                rate_limit_backend="redis",         # scale-out 환경 대응
                output_escape_policy="markdown",    # Slack 채널 이스케이핑
                enable_llm_secondary_guard=False,   # 내부 에이전트는 비활성화
            ),
        )

    async def handle_dispatch(self, msg):
        # SDK가 보안(입력·출력·action·파라미터 검증), 재시도, 스키마 변환,
        # Future 대기, 신뢰도 평가, Rate Limit을 모두 관리
        decision: BrainDecision = await self.brain.analyze_task(
            user_request=msg.get("content"),
            tools=self.executor.get_registered_tools(),  # Tool 객체·dict 모두 호환
            history=msg.get("context", []),              # user role만 인젝션 검사
        )

        # SDK가 신뢰도 미달·인젝션 탐지 시 ask_clarification을 자동 반환
        # suggested_reply, reasoning은 SDK가 이스케이핑 완료한 상태로 전달됨
        # decision.params는 action 유효성 + Tool 스키마 검증 완료 상태
        if decision.action == "ask_clarification":
            return self.request_clarification(
                decision.suggested_reply or "요청을 좀 더 구체적으로 말씀해주세요."
            )

        return await self.executor.execute(decision.action, decision.params)
```

---

## 5. 구현 우선순위 (Implementation Checklist)

1. **`cassiopeia-sdk` 확장**
   - `brain/` 디렉토리 구조 셋업
   - `BrainDecision`, `AgentBrainConfig` Pydantic 모델 작성

2. **보안 컴포넌트 구현** *(기능 구현 전 선행)*
   - `PromptInjectionGuard`: role="user" 메시지만 검사, `check_static()` enabled 독립 실행
   - `ActionAndParamsValidator`: action 유효성 + Tool 룩업 + 파라미터 스키마 검증
   - `OutputSanitizer`: suggested_reply, reasoning 대상 markdown / html 이스케이핑
   - `RateLimiter`: memory / redis 백엔드 선택 가능, per-agent-instance 제한

3. **Provider 추상화 구현**
   - `GatewayProvider` (llm_caller 주입 방식) 최우선 구현
   - `DirectProvider` 구현 시 에이전트 범위 환경변수 명명 규칙 준수
     (`{AGENT_NAME}_{PROVIDER}_API_KEY`)
   - `optional extras` 설정 (`pip install cassiopeia-sdk[brain]`)

4. **Core 로직 개발**
   - `Sequence[Tool | dict]` 호환 JSON Schema 변환기 작성
   - `max_retries` 지수 백오프 루프 및 JSON 안전 파싱 구현
     (재시도 시 오류 피드백 포함 프롬프트 재조립)
   - 신뢰도 자동 평가 및 `ask_clarification` 라우팅 + `suggested_reply` 자동 생성
   - `enable_llm_secondary_guard` Step 1.5 구현

5. **리팩토링**
   - `archive_agent` 등에 신규 SDK 시범 적용 및 동작 검증

---

## 6. 보안 위협 모델 요약

| 위협 | 방어 수단 | 적용 범위 |
|---|---|---|
| 직접 프롬프트 인젝션 | `PromptInjectionGuard.check(user_request)` | `enable_injection_guard=True` |
| 간접 인젝션 (history 경유) | history 내 `role="user"` 메시지만 검사 | 항상 적용 |
| 블랙리스트 우회 (인코딩 변형) | LLM 기반 2차 검증 (Step 1.5) | `enable_llm_secondary_guard=True` |
| `capabilities` 개발자 실수 | `check_static()` 초기화 시 검사 | `enable_injection_guard` 무관, 항상 적용 |
| 미등록 action 실행 | `ActionAndParamsValidator` action 유효성 검증 | 항상 적용 |
| LLM 생성 params 2차 공격 | `ActionAndParamsValidator` Tool 스키마 대조 | 항상 적용 |
| LLM 생성 텍스트 마크다운·HTML 인젝션 | `OutputSanitizer` (suggested_reply, reasoning) | `output_escape_policy` |
| 신뢰도 검사 우회 (confidence 미반환) | `confidence` 기본값 `0.0` + Pydantic 범위 제약 | 항상 적용 |
| DoS / 비용 폭발 (단일 인스턴스) | `RateLimiter` memory 백엔드 | `rate_limit_per_minute` |
| DoS / 비용 폭발 (분산 환경) | `RateLimiter` redis 백엔드 | `rate_limit_backend="redis"` |
| API 키 프로세스 간 누출 | 에이전트 범위 환경변수 명명 규칙 | `{AGENT_NAME}_{PROVIDER}_API_KEY` |

---

## 7. 구현 가이드 요약

1. **결합도 최적화**: `GatewayProvider`는 `AgentBase` 전체를 알 필요 없이 오직 `llm_caller` 함수 인터페이스에만 의존하여 가장 낮은 결합도를 유지합니다.
2. **책임의 분리**: Future 관리와 통신은 `AgentBase`가, 의도 분석과 데이터 정제는 `AgentBrain`이 담당합니다.
3. **보안 심층 방어(Defense in Depth)**: 입력(Guard) → 처리(Validator) → 출력(Sanitizer) 3단계로 각기 다른 공격 면을 독립적으로 방어합니다.
4. **확장성**: 새로운 LLM 공급자 추가 시 `DirectProvider` 구현체만 추가하면 모든 에이전트가 즉시 혜택을 받습니다.
