import React from 'react';

interface State { hasError: boolean; error?: Error; }

class ErrorBoundary extends React.Component<{children: React.ReactNode}, State> {
    state: State = { hasError: false };
    static getDerivedStateFromError(error: Error) { return { hasError: true, error }; }
    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-dvh flex items-center justify-center bg-background p-8">
                    <div className="text-center max-w-md">
                        <div className="w-16 h-16 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-4">
                            <span className="text-2xl">⚠️</span>
                        </div>
                        <h2 className="text-xl font-bold text-slate-900 mb-2">Something went wrong</h2>
                        <p className="text-slate-500 mb-6">Please refresh the page to continue.</p>
                        <button onClick={() => window.location.reload()}
                            className="btn-primary px-6 py-3">
                            Refresh Page
                        </button>
                    </div>
                </div>
            );
        }
        return this.props.children;
    }
}
export default ErrorBoundary;
