const { z } = require('zod');

// Tool schema definition
// 도구 정의 스키마
const ToolSchema = z.object({
  name: z.string(),
  description: z.string(),
  parameters: z.object({
    type: z.string(),
    properties: z.record(z.any()).optional(),
    required: z.array(z.string()).optional()
  })
});

/**
 * Manages registration and execution of tools.
 * 도구의 등록 및 실행을 관리합니다.
 */
class ToolExecutor {
  constructor() {
    this._tools = new Map();
    this._callbacks = new Map();
  }

  /**
   * Register a tool with its handler function.
   * 도구와 해당 핸들러 함수를 등록합니다.
   */
  registerTool(toolConfig, callback) {
    const validatedTool = ToolSchema.parse(toolConfig);
    this._tools.set(validatedTool.name, validatedTool);
    this._callbacks.set(validatedTool.name, callback);
  }

  /**
   * Execute a registered tool by name with the given parameters.
   * 이름으로 등록된 도구를 주어진 매개변수와 함께 실행합니다.
   */
  async execute(toolName, parameters) {
    if (!this._callbacks.has(toolName)) {
      throw new Error(`Tool '${toolName}' not found (도구 '${toolName}'을(를) 찾을 수 없습니다)`);
    }

    const callback = this._callbacks.get(toolName);
    // In a real implementation, you would validate `parameters` against the tool's parameter schema here
    // 실제 구현에서는 이 곳에서 tool의 파라미터 스키마를 사용해 `parameters`의 유효성을 검사합니다.
    return await callback(parameters);
  }

  /**
   * Return a list of all registered tools.
   * 등록된 모든 도구의 목록을 반환합니다.
   */
  getRegisteredTools() {
    return Array.from(this._tools.values());
  }
}

module.exports = { ToolExecutor };