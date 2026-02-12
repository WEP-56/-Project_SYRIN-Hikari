import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
    this.setState({ errorInfo });
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg m-4">
          <h2 className="text-lg font-bold text-red-700 mb-2">出错了 (Something went wrong)</h2>
          <p className="text-red-600 mb-2">UI 渲染遇到问题，请尝试重启应用。</p>
          <div className="bg-white p-2 rounded border border-red-100 overflow-auto max-h-40 text-xs text-red-800 font-mono">
            {this.state.error?.toString()}
            <br />
            {this.state.errorInfo?.componentStack}
          </div>
          <button 
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
            onClick={() => window.location.reload()}
          >
            刷新页面 (Reload)
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
