import { useState, useEffect } from 'react';
import { Settings, ConnectionStatus } from '../types';
import { api } from '../services/api';

interface SettingsPanelProps {
  settings: Settings;
  onSettingsChange: (settings: Settings) => void;
  connectionStatus: ConnectionStatus;
}

export default function SettingsPanel({
  settings,
  onSettingsChange,
  connectionStatus,
}: SettingsPanelProps) {
  const [localSettings, setLocalSettings] = useState<Settings>(settings);
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');
  const [tools, setTools] = useState<Array<{ name: string; description: string }>>([]);

  useEffect(() => {
    setLocalSettings(settings);
  }, [settings]);

  useEffect(() => {
    // Load available tools
    api.getTools().then(setTools);
  }, []);

  const handleChange = (key: keyof Settings, value: any) => {
    setLocalSettings(prev => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    setIsSaving(true);
    setSaveMessage('');

    const success = await api.updateConfig({
      provider: localSettings.provider,
      model: localSettings.model,
      api_key: localSettings.apiKey,
      api_base: localSettings.apiBase,
      max_iterations: localSettings.maxIterations,
    });

    if (success) {
      onSettingsChange(localSettings);
      setSaveMessage('保存成功！✓');
      setTimeout(() => setSaveMessage(''), 3000);
    } else {
      setSaveMessage('保存失败，请检查连接');
    }

    setIsSaving(false);
  };

  const handleRestartServer = async () => {
    if (!confirm('确定要重启后端服务吗？这将中断当前对话。')) return;
    
    setSaveMessage('正在重启服务...');
    const result = await api.restartServer();
    
    if (result.success) {
      setSaveMessage('服务重启成功！');
    } else {
      setSaveMessage(`重启失败: ${result.error}`);
    }
    
    setTimeout(() => setSaveMessage(''), 5000);
  };

  return (
    <div className="h-full overflow-y-auto p-6 scrollbar-thin">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-white">设置</h2>
          <div className="flex items-center space-x-2">
            {saveMessage && (
              <span className={`text-sm ${saveMessage.includes('失败') ? 'text-red-400' : 'text-green-400'}`}>
                {saveMessage}
              </span>
            )}
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="px-4 py-2 bg-yandere-600 hover:bg-yandere-500 disabled:bg-gray-700 text-white rounded-lg text-sm font-medium transition-colors"
            >
              {isSaving ? '保存中...' : '保存设置'}
            </button>
          </div>
        </div>

        {/* LLM Configuration */}
        <section className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
            <span>🤖</span>
            <span>AI 模型配置</span>
          </h3>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                提供商
              </label>
              <select
                value={localSettings.provider}
                onChange={(e) => handleChange('provider', e.target.value)}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-yandere-500"
              >
                <option value="openai">OpenAI</option>
                <option value="deepseek">DeepSeek</option>
                <option value="anthropic">Anthropic</option>
                <option value="azure">Azure OpenAI</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                模型
              </label>
              <input
                type="text"
                value={localSettings.model}
                onChange={(e) => handleChange('model', e.target.value)}
                placeholder="gpt-4o-mini"
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-yandere-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                推荐：gpt-4o-mini, deepseek-chat, claude-3-haiku
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                API Key
              </label>
              <input
                type="password"
                value={localSettings.apiKey}
                onChange={(e) => handleChange('apiKey', e.target.value)}
                placeholder="sk-..."
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-yandere-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                API Base URL (可选)
              </label>
              <input
                type="text"
                value={localSettings.apiBase}
                onChange={(e) => handleChange('apiBase', e.target.value)}
                placeholder="https://api.openai.com/v1"
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-yandere-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                最大迭代次数
              </label>
              <input
                type="number"
                min={1}
                max={50}
                value={localSettings.maxIterations}
                onChange={(e) => handleChange('maxIterations', parseInt(e.target.value))}
                className="w-32 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-yandere-500"
              />
            </div>
          </div>
        </section>

        {/* Behavior Settings */}
        <section className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
            <span>💕</span>
            <span>行为设置</span>
          </h3>

          <div className="space-y-4">
            <label className="flex items-center justify-between p-3 bg-gray-900 rounded-lg cursor-pointer hover:bg-gray-850 transition-colors">
              <div>
                <span className="text-sm font-medium text-gray-200">情绪系统</span>
                <p className="text-xs text-gray-500">根据对话内容自动调整情绪状态</p>
              </div>
              <input
                type="checkbox"
                checked={localSettings.emotionEnabled}
                onChange={(e) => handleChange('emotionEnabled', e.target.checked)}
                className="w-5 h-5 rounded border-gray-600 text-yandere-600 focus:ring-yandere-500"
              />
            </label>

            <label className="flex items-center justify-between p-3 bg-gray-900 rounded-lg cursor-pointer hover:bg-gray-850 transition-colors">
              <div>
                <span className="text-sm font-medium text-gray-200">自动执行</span>
                <p className="text-xs text-gray-500">允许AI自动执行系统命令（需谨慎）</p>
              </div>
              <input
                type="checkbox"
                checked={localSettings.autoExecute}
                onChange={(e) => handleChange('autoExecute', e.target.checked)}
                className="w-5 h-5 rounded border-gray-600 text-yandere-600 focus:ring-yandere-500"
              />
            </label>
          </div>
        </section>

        {/* Tools */}
        <section className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
            <span>🛠️</span>
            <span>可用工具</span>
          </h3>

          <div className="space-y-2 max-h-64 overflow-y-auto scrollbar-thin">
            {tools.length === 0 ? (
              <p className="text-sm text-gray-500">加载中...</p>
            ) : (
              tools.map((tool) => (
                <div key={tool.name} className="p-3 bg-gray-900 rounded-lg">
                  <div className="font-medium text-sm text-gray-200">{tool.name}</div>
                  <div className="text-xs text-gray-500 mt-1">{tool.description}</div>
                </div>
              ))
            )}
          </div>
        </section>

        {/* System */}
        <section className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
            <span>⚙️</span>
            <span>系统</span>
          </h3>

          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-gray-900 rounded-lg">
              <div>
                <span className="text-sm font-medium text-gray-200">后端服务</span>
                <p className="text-xs text-gray-500">
                  状态: {connectionStatus === 'connected' ? '运行中' : connectionStatus === 'connecting' ? '连接中' : '错误'}
                </p>
              </div>
              <button
                onClick={handleRestartServer}
                className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg transition-colors"
              >
                重启服务
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
