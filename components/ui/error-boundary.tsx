'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children?: ReactNode;
  fallbackTitle?: string;
  fallbackMessage?: string;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught component error:', error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="rounded-xl border border-red-500/20 bg-red-950/10 p-6 backdrop-blur-md">
          <div className="flex items-start gap-4">
            <div className="rounded-lg bg-red-500/10 p-2.5 text-red-400 border border-red-500/20">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div className="flex-1">
              <h3 className="text-base font-semibold text-white">
                {this.props.fallbackTitle || 'Component Rendering Error'}
              </h3>
              <p className="mt-1 text-sm text-white/60">
                {this.props.fallbackMessage || this.state.error?.message || 'An unexpected error occurred while displaying this section.'}
              </p>
              <button
                onClick={this.handleReset}
                className="mt-4 px-4 py-2 text-xs font-medium text-white bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 rounded-lg transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
