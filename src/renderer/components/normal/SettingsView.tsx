import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Save, RefreshCw, Check, AlertCircle, 
  Monitor, Cpu, Shield, User, Brain, Globe, Info,
  LogOut, Trash2
} from 'lucide-react';
import { useAppStore } from '../../stores/appStore';
import { api } from '../../services/api';

type SettingsTab = 'display' | 'system' | 'auth' | 'assistant' | 'model' | 'external' | 'about';

export default function SettingsView() {
  const { settings, updateSettings, connectionStatus } = useAppStore();
  const [activeTab, setActiveTab] = useState<SettingsTab>('display');
  const [localSettings, setLocalSettings] = useState(settings);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [testTgStatus, setTestTgStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle');
  const [testTgMsg, setTestTgMsg] = useState('');

  // Sync local settings when store settings change
  useEffect(() => {
    setLocalSettings(settings);
  }, [settings]);

  const handleChange = (key: keyof typeof settings, value: any) => {
    setLocalSettings(prev => ({ ...prev, [key]: value }));
    setSaveStatus('idle');
  };

  const handleSave = async () => {
    setSaveStatus('saving');
    
    const success = await api.updateConfig({
      provider: localSettings.provider,
      model: localSettings.model,
      api_key: localSettings.apiKey,
      api_base: localSettings.apiBase,
      max_iterations: localSettings.maxIterations,
      brave_api_key: localSettings.braveApiKey,
      search_provider: localSettings.search_provider,
      telegram_token: localSettings.telegramToken,
      telegram_enabled: localSettings.telegramEnabled,
      user_name: localSettings.user_name,
      role_name: localSettings.role_name,
      emotionEnabled: localSettings.emotionEnabled,
      autoExecute: localSettings.autoExecute,
      enableUserModeling: localSettings.enableUserModeling,
      proactive_enabled: localSettings.proactiveEnabled,
    });

    if (success) {
      updateSettings(localSettings);
      setSaveStatus('saved');
      setTimeout(() => setSaveStatus('idle'), 2000);
    } else {
      setSaveStatus('error');
    }
  };

  const handleRestart = async () => {
    if (!confirm('确定要重启后端服务吗？')) return;
    await api.restartServer();
  };

  const handleTestTelegram = async () => {
    setTestTgStatus('testing');
    const res = await api.testTelegram();
    if (res.success) {
      setTestTgStatus('success');
      setTestTgMsg(res.message || '连接成功');
    } else {
      setTestTgStatus('error');
      setTestTgMsg(res.error || '连接失败');
    }
    setTimeout(() => {
        if (testTgStatus !== 'error') setTestTgMsg('');
    }, 5000);
  };

  const handleResetSystem = async () => {
    if (!confirm('警告：此操作将删除所有本地数据（会话、记忆、配置等），且不可恢复！\n\n您确定要按下这个“大红按钮”吗？')) {
        return;
    }
    
    // Double confirm
    if (!confirm('再次确认：这真的会清空一切。您确定吗？')) {
        return;
    }

    setSaveStatus('saving'); // Re-use saving status for visual feedback
    try {
        const res = await api.resetSystem();
        if (res.success) {
            alert('系统已重置。应用将自动刷新。');
            window.location.reload();
        } else {
            alert(`重置失败: ${res.error}`);
            setSaveStatus('error');
        }
    } catch (e) {
        alert(`重置出错: ${e}`);
        setSaveStatus('error');
    }
    setTimeout(() => setSaveStatus('idle'), 3000);
  };

  const menuItems: { id: SettingsTab; label: string; icon: React.ReactNode }[] = [
    { id: 'display', label: '显示', icon: <Monitor size={18} /> },
    { id: 'system', label: '系统', icon: <Cpu size={18} /> },
    { id: 'auth', label: '执行授权', icon: <Shield size={18} /> },
    { id: 'assistant', label: '助手', icon: <User size={18} /> },
    { id: 'model', label: '模型', icon: <Brain size={18} /> },
    { id: 'external', label: '外部应用', icon: <Globe size={18} /> },
    { id: 'about', label: '关于', icon: <Info size={18} /> },
  ];

  return (
    <div className="flex h-full bg-white/50 rounded-2xl overflow-hidden backdrop-blur-sm border border-white/20 shadow-xl">
      {/* Sidebar */}
      <div className="w-48 bg-gray-50/80 border-r border-gray-200/50 flex flex-col p-4">
        <div className="mb-6 px-2">
          <h2 className="text-lg font-bold text-gray-800">设置</h2>
          <p className="text-xs text-gray-500">Settings</p>
        </div>
        
        <nav className="flex-1 space-y-1">
          {menuItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center space-x-3 px-3 py-2 rounded-xl text-sm transition-all duration-200 ${
                activeTab === item.id
                  ? 'bg-white shadow-sm text-pink-600 font-medium'
                  : 'text-gray-600 hover:bg-white/50 hover:text-gray-900'
              }`}
            >
              {item.icon}
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        {/* Save Button Area */}
        <div className="mt-4 pt-4 border-t border-gray-200/50 space-y-3">
          <div className="flex items-center justify-between px-2 mb-2">
             <span className="text-xs text-gray-500">服务状态</span>
             <div className={`w-2 h-2 rounded-full ${
                connectionStatus === 'connected' ? 'bg-green-500' : 
                connectionStatus === 'error' ? 'bg-red-500' : 'bg-yellow-500 animate-pulse'
             }`} />
          </div>

          <motion.button
            onClick={handleSave}
            disabled={saveStatus === 'saving'}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className={`w-full flex items-center justify-center space-x-2 px-4 py-2.5 rounded-xl text-sm font-medium text-white shadow-sm transition-all ${
              saveStatus === 'saved' ? 'bg-green-500' : 
              saveStatus === 'error' ? 'bg-red-500' : 
              'bg-gradient-to-r from-pink-500 to-rose-500 hover:shadow-md'
            }`}
          >
            {saveStatus === 'saving' ? (
              <RefreshCw className="animate-spin" size={16} />
            ) : saveStatus === 'saved' ? (
              <Check size={16} />
            ) : saveStatus === 'error' ? (
              <AlertCircle size={16} />
            ) : (
              <Save size={16} />
            )}
            <span>
              {saveStatus === 'saving' ? '保存中...' : 
               saveStatus === 'saved' ? '已保存' : 
               saveStatus === 'error' ? '失败' : '保存设置'}
            </span>
          </motion.button>
          
          <button 
            onClick={handleRestart}
            className="w-full flex items-center justify-center space-x-2 px-4 py-2 text-xs text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <RefreshCw size={12} />
            <span>重启后端服务</span>
          </button>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto bg-white/30 p-8">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
            transition={{ duration: 0.2 }}
            className="max-w-2xl mx-auto"
          >
            {activeTab === 'display' && <DisplaySettings />}
            {activeTab === 'system' && <SystemSettings onReset={handleResetSystem} />}
            {activeTab === 'auth' && <AuthSettings settings={localSettings} onChange={handleChange} />}
            {activeTab === 'assistant' && <AssistantSettings settings={localSettings} onChange={handleChange} />}
            {activeTab === 'model' && <ModelSettings settings={localSettings} onChange={handleChange} />}
            {activeTab === 'external' && (
              <ExternalSettings 
                settings={localSettings} 
                onChange={handleChange} 
                testStatus={testTgStatus}
                testMsg={testTgMsg}
                onTest={handleTestTelegram}
              />
            )}
            {activeTab === 'about' && <AboutSettings />}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}

// --- Sub-components ---

function SectionHeader({ title, description }: { title: string, description: string }) {
  return (
    <div className="mb-6">
      <h3 className="text-xl font-bold text-gray-800">{title}</h3>
      <p className="text-sm text-gray-500 mt-1">{description}</p>
    </div>
  );
}

function Card({ children, title, className = "" }: { children: React.ReactNode, title?: string, className?: string }) {
  return (
    <div className={`bg-white/70 rounded-2xl p-6 shadow-sm border border-white/50 backdrop-blur-sm ${className}`}>
      {title && <h4 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wider">{title}</h4>}
      {children}
    </div>
  );
}

function Toggle({ label, description, checked, onChange }: { label: string, description?: string, checked: boolean, onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-start justify-between py-3">
      <div className="flex-1 pr-4">
        <div className="text-sm font-medium text-gray-800">{label}</div>
        {description && <div className="text-xs text-gray-500 mt-1 leading-relaxed">{description}</div>}
      </div>
      <button
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
          checked ? 'bg-pink-500' : 'bg-gray-200'
        }`}
      >
        <span
          className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
            checked ? 'translate-x-5' : 'translate-x-0'
          }`}
        />
      </button>
    </div>
  );
}

function Input({ label, value, onChange, type = "text", placeholder, className = "" }: any) {
  return (
    <div className={`space-y-1.5 ${className}`}>
      <label className="block text-sm font-medium text-gray-700">{label}</label>
      <input
        type={type}
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-white/50 border border-gray-200 rounded-xl px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-pink-500 focus:ring-2 focus:ring-pink-500/10 transition-all"
      />
    </div>
  );
}

function Select({ label, value, onChange, options }: any) {
  return (
    <div className="space-y-1.5">
      <label className="block text-sm font-medium text-gray-700">{label}</label>
      <div className="relative">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full bg-white/50 border border-gray-200 rounded-xl px-3 py-2 text-sm text-gray-900 appearance-none focus:outline-none focus:border-pink-500 focus:ring-2 focus:ring-pink-500/10 transition-all"
        >
          {options.map((opt: any) => (
            <option key={opt.value} value={opt.value} className="text-gray-900">{opt.label}</option>
          ))}
        </select>
        <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-500">
          <svg className="h-4 w-4 fill-current" viewBox="0 0 20 20">
            <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" />
          </svg>
        </div>
      </div>
    </div>
  );
}

// --- Section Components ---

function DisplaySettings() {
  return (
    <div className="space-y-6">
      <SectionHeader title="显示设置" description="自定义界面的外观和感觉" />
      <Card>
        <div className="text-center py-8 text-gray-500">
          <Monitor size={48} className="mx-auto mb-4 opacity-20" />
          <p>当前使用系统默认主题</p>
          <p className="text-xs mt-2">更多个性化选项即将推出...</p>
        </div>
      </Card>
    </div>
  );
}

function SystemSettings({ onReset }: { onReset: () => void }) {
  return (
    <div className="space-y-6">
      <SectionHeader title="系统设置" description="管理存储和缓存" />
      <Card title="存储位置">
        <div className="space-y-4">
          <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
             <div className="flex justify-between items-center mb-1">
               <div className="text-xs text-gray-500">工作区路径</div>
               <button className="text-xs text-pink-500 hover:text-pink-600" onClick={() => alert('自定义路径功能开发中...')}>修改</button>
             </div>
             <div className="text-sm font-mono text-gray-700 break-all">
               ./workspace
             </div>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
             <div className="text-xs text-gray-500 mb-1">记忆数据库</div>
             <div className="text-sm font-mono text-gray-700 break-all">
               ./workspace/memory/memories.db
             </div>
          </div>
          <div className="text-xs text-gray-400 px-1">
            * 目前版本为便携模式，数据默认存储在程序目录下，暂不支持迁移。
          </div>
        </div>
      </Card>
      <Card title="危险区域">
        <div className="space-y-2">
            <p className="text-xs text-red-500">警告：以下操作不可逆！</p>
            <button 
                onClick={onReset}
                className="w-full flex items-center justify-center space-x-2 bg-red-50 text-red-600 hover:bg-red-600 hover:text-white px-4 py-3 rounded-lg transition-all border border-red-200 hover:border-red-600 hover:shadow-lg group"
            >
              <Trash2 size={18} className="group-hover:animate-bounce" />
              <span className="font-bold">大红按钮 (核平所有数据)</span>
            </button>
        </div>
      </Card>
    </div>
  );
}

function AuthSettings({ settings, onChange }: any) {
  return (
    <div className="space-y-6">
      <SectionHeader title="执行授权" description="控制 AI 执行敏感操作的权限" />
      <Card>
        <Toggle
          label="自动执行命令"
          description="允许 AI 无需确认即可执行系统命令（如打开应用、文件操作等）。关闭后，所有高风险命令（如打开应用、写文件、执行脚本）需要您确认后才能执行。"
          checked={settings.autoExecute}
          onChange={(v) => onChange('autoExecute', v)}
        />
      </Card>
    </div>
  );
}

function AssistantSettings({ settings, onChange }: any) {
  return (
    <div className="space-y-6">
      <SectionHeader title="助手设置" description="定制助手的称呼和行为模式" />
      <Card title="基本信息">
        <div className="grid grid-cols-2 gap-4">
          <Input 
            label="您的称呼" 
            value={settings.user_name} 
            onChange={(v: string) => onChange('user_name', v)} 
            placeholder="User"
          />
          <Input 
            label="助手称呼" 
            value={settings.role_name} 
            onChange={(v: string) => {
              if (v !== 'Hikari' && v !== 'Hikari (光)') {
                alert('Hikari (光)就是我的名字，为什么要修改呢🤨');
                return;
              }
              onChange('role_name', v);
            }} 
            placeholder="Assistant"
          />
        </div>
      </Card>

      <Card title="高级功能">
        <div className="space-y-4">
          <Toggle
            label="用户建模收集"
            description="允许助手在对话中分析您的性格、喜好和习惯，并建立长期的用户画像。开启后将大幅增强角色扮演的沉浸感和个性化体验。数据完全存储在本地，开启后可能会略微增加 Token 消耗。"
            checked={settings.enableUserModeling}
            onChange={(v) => onChange('enableUserModeling', v)}
          />
          <div className="border-t border-gray-100 my-2"></div>
          <Toggle
            label="情绪系统"
            description="允许助手根据对话内容产生情绪波动，并影响其回复风格和表情。"
            checked={settings.emotionEnabled}
            onChange={(v) => onChange('emotionEnabled', v)}
          />
          <div className="border-t border-gray-100 my-2"></div>
          <Toggle
            label="主动交互模式 (Proactive Mode)"
            description="允许助手主动发起对话或发送通知（例如日程提醒、问候）。如果不开启，助手仅在您说话时回复。通知将以系统弹窗形式出现，不会干扰您的工作。"
            checked={settings.proactiveEnabled}
            onChange={(v) => onChange('proactiveEnabled', v)}
          />
        </div>
      </Card>
    </div>
  );
}

function ModelSettings({ settings, onChange }: any) {
  const providers = [
    { value: 'openai', label: 'OpenAI' },
    { value: 'anthropic', label: 'Anthropic (Claude)' },
    { value: 'deepseek', label: 'DeepSeek' },
    { value: 'gemini', label: 'Google Gemini' },
    { value: 'openrouter', label: 'OpenRouter' },
    { value: 'zhipu', label: '智谱 AI (Zhipu)' },
    { value: 'dashscope', label: '阿里云 (DashScope)' },
    { value: 'moonshot', label: '月之暗面 (Moonshot)' },
    { value: 'groq', label: 'Groq' },
    { value: 'aihubmix', label: 'AiHubMix' },
    { value: 'vllm', label: 'vLLM (Local)' },
  ];

  return (
    <div className="space-y-6">
      <SectionHeader title="模型配置" description="选择和配置 LLM 提供商" />
      <Card>
        <div className="space-y-4">
          <Select
            label="提供商"
            value={settings.provider}
            onChange={(v: string) => onChange('provider', v)}
            options={providers}
          />
          
          <Input 
            label="模型名称" 
            value={settings.model} 
            onChange={(v: string) => onChange('model', v)} 
            placeholder="例如: gpt-4o, claude-3-5-sonnet-20240620"
          />
          
          <Input 
            label="API Key" 
            type="password"
            value={settings.apiKey} 
            onChange={(v: string) => onChange('apiKey', v)} 
            placeholder="sk-..."
          />
          
          <Input 
            label="API Base URL (可选)" 
            value={settings.apiBase} 
            onChange={(v: string) => onChange('apiBase', v)} 
            placeholder="默认留空即可"
          />

          <div className="pt-2">
            <Input 
              label="单次对话最大迭代次数" 
              type="number"
              value={settings.maxIterations} 
              onChange={(v: string) => onChange('maxIterations', parseInt(v))} 
              placeholder="20"
            />
            <p className="text-xs text-gray-500 mt-1">控制助手在单次回复中调用工具的最大次数。</p>
          </div>
        </div>
      </Card>
    </div>
  );
}

function ExternalSettings({ settings, onChange, testStatus, testMsg, onTest }: any) {
  return (
    <div className="space-y-6">
      <SectionHeader title="外部应用" description="集成第三方服务和工具" />
      
      <Card title="Telegram 集成">
        <div className="space-y-4">
          <Toggle
            label="启用 Telegram 机器人"
            description="允许通过 Telegram 与助手进行对话。"
            checked={settings.telegramEnabled}
            onChange={(v) => onChange('telegramEnabled', v)}
          />
          
          {settings.telegramEnabled && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="space-y-4 pt-2"
            >
              <Input 
                label="Bot Token" 
                type="password"
                value={settings.telegramToken} 
                onChange={(v: string) => onChange('telegramToken', v)} 
                placeholder="123456:ABC-..."
              />
              
              <div className="flex items-center space-x-3 pt-2">
                <button
                  onClick={onTest}
                  disabled={testStatus === 'testing' || !settings.telegramToken}
                  className="px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:opacity-50 text-white rounded-xl text-sm transition-colors flex items-center space-x-2"
                >
                  {testStatus === 'testing' && <RefreshCw className="animate-spin" size={14} />}
                  <span>{testStatus === 'testing' ? '连接中...' : '测试连接'}</span>
                </button>
                
                {testMsg && (
                  <span className={`text-sm ${testStatus === 'success' ? 'text-green-500' : 'text-red-500'}`}>
                    {testMsg}
                  </span>
                )}
              </div>
            </motion.div>
          )}
        </div>
      </Card>

      <Card title="网络搜索">
        <div className="space-y-4">
          <Select
            label="搜索引擎"
            value={settings.search_provider || 'brave'}
            onChange={(v: string) => onChange('search_provider', v)}
            options={[
              { value: 'brave', label: 'Brave Search (需要 API Key)' },
              { value: 'duckduckgo', label: 'DuckDuckGo (免费)' },
            ]}
          />
          
          {(!settings.search_provider || settings.search_provider === 'brave') && (
            <Input 
              label="Brave Search API Key" 
              type="password"
              value={settings.braveApiKey} 
              onChange={(v: string) => onChange('braveApiKey', v)} 
              placeholder="BSA-..."
            />
          )}
        </div>
      </Card>
    </div>
  );
}

function AboutSettings() {
  return (
    <div className="space-y-6">
      <SectionHeader title="关于" description="版本信息与更新" />
      <Card>
        <div className="flex flex-col items-center py-6 space-y-4">
          <div className="w-16 h-16 bg-gradient-to-br from-pink-400 to-red-500 rounded-2xl shadow-lg flex items-center justify-center text-3xl">
            💝
          </div>
          <div className="text-center">
            <h3 className="text-xl font-bold text-gray-800">Hikari</h3>
            <p className="text-sm text-gray-500">Project SYRIN</p>
          </div>
          <div className="flex items-center space-x-2 text-sm text-gray-600 bg-gray-100 px-3 py-1 rounded-full">
            <span>Version 1.0.0</span>
          </div>
          <div className="text-xs text-gray-400 text-center max-w-xs leading-relaxed">
            Project SYRIN 核心组件。<br/>
            基于 Nanobot 框架构建。
          </div>
          <button className="text-xs text-green-600 hover:underline">
            检查更新 (Check for Updates)
          </button>
        </div>
      </Card>
    </div>
  );
}
