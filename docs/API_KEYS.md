# 配置说明 - API Keys

## 需要的 API Keys

### 1. LLM API Key（必需）
在设置页面配置：
- **OpenAI**: https://platform.openai.com/api-keys
- **DeepSeek**: https://platform.deepseek.com/
- **Anthropic**: https://console.anthropic.com/

### 2. Web 搜索 API Key（可选）
如需使用搜索功能，需要配置 Brave Search API：

1. 访问 https://api.search.brave.com/
2. 注册并获取 API Key
3. 在 `python-server/workspace/yandere_config.json` 中添加：

```json
{
  "provider": "openai",
  "model": "gpt-4o-mini",
  "api_key": "your-llm-api-key",
  "brave_api_key": "your-brave-api-key"
}
```

或者通过 API 更新：
```bash
curl -X POST http://localhost:8888/config \
  -H "Content-Type: application/json" \
  -d '{"brave_api_key": "your-key"}'
```

### 3. 环境变量方式
也可以在启动前设置环境变量：
```bash
# Windows PowerShell
$env:BRAVE_API_KEY="your-key"
python api_server.py
```

## 注意事项

- 如果没有配置 Brave API Key，搜索功能将无法使用
- LLM API Key 是必需的，否则无法进行对话
- 所有的 API Key 都存储在本地，不会上传到任何服务器
