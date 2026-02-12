import React, { useState } from 'react';
import { Play, Check, AlertCircle, Terminal, Copy } from 'lucide-react';
import { api } from '../../services/api';

interface CodeBlockProps {
  language: string;
  value: string;
}

export default function CodeBlock({ language, value }: CodeBlockProps) {
  const [isRunning, setIsRunning] = useState(false);
  const [output, setOutput] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleRun = async () => {
    setIsRunning(true);
    setOutput(null);
    setError(null);

    const res = await api.runSandboxCode(value, language);
    
    if (res.success) {
      setOutput(res.result || '(No output)');
    } else {
      setError(res.error || 'Execution failed');
    }
    
    setIsRunning(false);
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Only show run button for supported languages
  const supportedLanguages = ['python', 'py', 'bash', 'sh', 'shell', 'powershell', 'ps1', 'cmd'];
  const canRun = supportedLanguages.includes((language || '').toLowerCase());

  return (
    <div className="rounded-lg overflow-hidden border border-gray-200 bg-gray-50 my-2 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-gray-100 border-b border-gray-200">
        <div className="flex items-center space-x-2">
          <span className="text-xs font-mono text-gray-500 uppercase">{language || 'text'}</span>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={handleCopy}
            className="p-1 text-gray-500 hover:text-gray-700 transition-colors rounded hover:bg-gray-200"
            title="复制"
          >
            {copied ? <Check size={14} className="text-green-500" /> : <Copy size={14} />}
          </button>
          
          {canRun && (
            <button
              onClick={handleRun}
              disabled={isRunning}
              className={`flex items-center space-x-1 px-2 py-1 rounded text-xs font-medium transition-colors ${
                isRunning 
                  ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                  : 'bg-green-100 text-green-700 hover:bg-green-200 border border-green-200'
              }`}
            >
              {isRunning ? (
                <div className="w-3 h-3 border-2 border-green-500 border-t-transparent rounded-full animate-spin" />
              ) : (
                <Play size={12} />
              )}
              <span>运行</span>
            </button>
          )}
        </div>
      </div>

      {/* Code */}
      <div className="p-3 overflow-x-auto bg-[#f8f9fa]">
        <code className="font-mono text-sm text-gray-800 whitespace-pre">{value}</code>
      </div>

      {/* Output */}
      {(output || error) && (
        <div className="border-t border-gray-200 bg-black text-white p-3 font-mono text-xs">
          <div className="flex items-center space-x-2 mb-2 opacity-50">
            <Terminal size={12} />
            <span>Console Output</span>
          </div>
          <div className="whitespace-pre-wrap break-words max-h-60 overflow-y-auto">
            {output && <span className="text-gray-300">{output}</span>}
            {error && <span className="text-red-400">{error}</span>}
          </div>
        </div>
      )}
    </div>
  );
}
