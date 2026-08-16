import React, { Component, ErrorInfo, ReactNode } from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.tsx';
import './index.css';

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen w-screen bg-background text-foreground p-8 flex flex-col justify-center items-center font-mono text-xs space-y-4">
          <div className="border border-destructive/30 bg-destructive/10 p-6 max-w-xl text-left">
            <h1 className="text-sm font-semibold mb-2 uppercase text-destructive">Application Render Crash</h1>
            <p className="leading-relaxed mb-4 text-xs">{this.state.error?.toString()}</p>
            <p className="text-[10px] text-muted-foreground">Please check the browser console for the full stack trace.</p>
          </div>
          <button 
            onClick={() => {
              localStorage.clear();
              window.location.reload();
            }}
            className="px-4 py-2 border border-border hover:bg-accent transition text-[10px] uppercase font-bold"
          >
            Reset Client Cache & Reload
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
);
