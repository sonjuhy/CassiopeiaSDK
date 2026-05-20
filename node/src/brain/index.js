'use strict';

/**
 * cassiopeia-sdk brain 모듈
 *
 * Usage:
 *   const { AgentBrain, AgentBrainConfig, BrainDecision } = require('cassiopeia-sdk/brain');
 *
 *   const brain = new AgentBrain({
 *     agentName: 'my_agent',
 *     capabilities: '파일 검색 및 노트 관리',
 *     backend: 'gateway',
 *     llmCaller: agent.requestLlm.bind(agent),
 *     config: new AgentBrainConfig({ rateLimitPerMinute: 60, outputEscapePolicy: 'markdown' }),
 *   });
 *
 *   const decision = await brain.analyzeTask(userRequest, tools, history);
 */

const { PromptInjectionError, UnknownActionError, ParamsValidationError, RateLimitExceededError } = require('./exceptions');
const { BrainDecision, BrainDecisionSchema, AgentBrainConfig, AgentBrainConfigSchema } = require('./models');
const { PromptInjectionGuard } = require('./guard');
const { ActionAndParamsValidator } = require('./validator');
const { OutputSanitizer } = require('./sanitizer');
const { RateLimiter } = require('./rateLimiter');
const { GatewayProvider, DirectProvider, LLMProviderFactory } = require('./providers');
const { AgentBrain } = require('./brain');

module.exports = {
  // 예외
  PromptInjectionError,
  UnknownActionError,
  ParamsValidationError,
  RateLimitExceededError,
  // 모델
  BrainDecision,
  BrainDecisionSchema,
  AgentBrainConfig,
  AgentBrainConfigSchema,
  // 보안 컴포넌트
  PromptInjectionGuard,
  ActionAndParamsValidator,
  OutputSanitizer,
  RateLimiter,
  // Provider
  GatewayProvider,
  DirectProvider,
  LLMProviderFactory,
  // 메인
  AgentBrain,
};
