const { ToolExecutor } = require('../src/tools');

describe('ToolExecutor', () => {
  it('should register and execute tools successfully', async () => {
    const executor = new ToolExecutor();
    
    const mockWeatherTool = {
      name: 'get_weather',
      description: 'Get current weather',
      parameters: { type: 'object', properties: { location: { type: 'string' } } }
    };
    
    const mockCallback = jest.fn().mockReturnValue('Weather in Seoul is sunny');
    
    executor.registerTool(mockWeatherTool, mockCallback);
    
    const result = await executor.execute('get_weather', { location: 'Seoul' });
    
    expect(result).toBe('Weather in Seoul is sunny');
    expect(mockCallback).toHaveBeenCalledWith({ location: 'Seoul' });
  });

  it('should throw error for unknown tool', async () => {
    const executor = new ToolExecutor();
    
    await expect(executor.execute('unknown_tool', {}))
      .rejects.toThrow("Tool 'unknown_tool' not found");
  });

  it('should return list of registered tools', () => {
    const executor = new ToolExecutor();
    
    const mockTool = {
      name: 'get_weather',
      description: 'Get weather',
      parameters: { type: 'object' }
    };
    
    executor.registerTool(mockTool, () => {});
    
    const tools = executor.getRegisteredTools();
    expect(tools).toHaveLength(1);
    expect(tools[0].name).toBe('get_weather');
  });
});
