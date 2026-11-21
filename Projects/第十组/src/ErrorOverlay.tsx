import { Component, useEffect, useState } from 'react';
import type { ErrorInfo, ReactNode } from 'react';

/**
 * 演示兜底：任何未捕获的异常都直接显示在页面上，
 * 避免现场出现"白屏但不知道为什么"。
 */

function Banner({ text }: { text: string }) {
  return (
    <div className="fatal">
      <strong>出错了</strong>
      <span>{text}</span>
      <button onClick={() => window.location.reload()}>刷新重试</button>
    </div>
  );
}

export function GlobalErrors({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const onError = (e: ErrorEvent) => setMessage(e.message || '脚本错误');
    const onReject = (e: PromiseRejectionEvent) => {
      const reason = e.reason;
      setMessage(reason instanceof Error ? reason.message : String(reason));
    };
    window.addEventListener('error', onError);
    window.addEventListener('unhandledrejection', onReject);
    return () => {
      window.removeEventListener('error', onError);
      window.removeEventListener('unhandledrejection', onReject);
    };
  }, []);

  return (
    <>
      {message && <Banner text={message} />}
      {children}
    </>
  );
}

interface BoundaryState {
  error: Error | null;
}

export class ErrorBoundary extends Component<{ children: ReactNode }, BoundaryState> {
  state: BoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): BoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(error, info);
  }

  render() {
    if (this.state.error) {
      return <Banner text={this.state.error.message} />;
    }
    return this.props.children;
  }
}
