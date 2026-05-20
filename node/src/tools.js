'use strict';

const { z } = require('zod');

// Tool JSON Schema 정의
const ToolSchema = z.object({
  name: z.string(),
  description: z.string(),
  parameters: z.object({
    type: z.string(),
    properties: z.record(z.any()).optional(),
    required: z.array(z.string()).optional(),
  }).passthrough(),
});

/**
 * 에이전트가 실행할 수 있는 도구의 정의입니다.
 * Python cassiopeia_sdk.tools.Tool과 동일한 구조입니다.
 */
class Tool {
  /**
   * @param {{ name: string, description: string, parameters: object }} config
   */
  constructor(config) {
    const validated = ToolSchema.parse(config);
    this.name = validated.name;
    this.description = validated.description;
    this.parameters = validated.parameters;
  }

  /** plain object로 직렬화합니다. */
  toObject() {
    return { name: this.name, description: this.description, parameters: this.parameters };
  }
}

/**
 * 도구의 등록 및 실행을 관리합니다.
 */
class ToolExecutor {
  constructor() {
    /** @type {Map<string, Tool>} */
    this._tools = new Map();
    /** @type {Map<string, Function>} */
    this._callbacks = new Map();
  }

  /**
   * 도구와 해당 핸들러 함수를 등록합니다.
   * @param {Tool|object} toolConfig
   * @param {Function} callback
   */
  registerTool(toolConfig, callback) {
    const tool = toolConfig instanceof Tool ? toolConfig : new Tool(toolConfig);
    this._tools.set(tool.name, tool);
    this._callbacks.set(tool.name, callback);
  }

  /**
   * 이름으로 등록된 도구를 주어진 매개변수와 함께 실행합니다.
   * @param {string} toolName
   * @param {object} parameters
   */
  async execute(toolName, parameters) {
    if (!this._callbacks.has(toolName)) {
      throw new Error(`Tool '${toolName}' not found (도구 '${toolName}'을(를) 찾을 수 없습니다)`);
    }
    return await this._callbacks.get(toolName)(parameters);
  }

  /**
   * 등록된 모든 도구의 목록을 반환합니다. (Tool 인스턴스 배열)
   * @returns {Tool[]}
   */
  getRegisteredTools() {
    return Array.from(this._tools.values());
  }
}

module.exports = { Tool, ToolSchema, ToolExecutor };
