'use strict';

class PromptInjectionError extends Error {
  constructor(message) {
    super(message);
    this.name = 'PromptInjectionError';
  }
}

class UnknownActionError extends Error {
  constructor(message) {
    super(message);
    this.name = 'UnknownActionError';
  }
}

class ParamsValidationError extends Error {
  constructor(message) {
    super(message);
    this.name = 'ParamsValidationError';
  }
}

class RateLimitExceededError extends Error {
  constructor(message) {
    super(message);
    this.name = 'RateLimitExceededError';
  }
}

module.exports = {
  PromptInjectionError,
  UnknownActionError,
  ParamsValidationError,
  RateLimitExceededError,
};
