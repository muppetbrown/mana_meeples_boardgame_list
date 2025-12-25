import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Log the error details
    console.error('Error boundary caught an error:', error, errorInfo);
    
    this.setState({
      error: error,
      errorInfo: errorInfo
    });
    
    // You can also log the error to an error reporting service here
    // Example: logErrorToService(error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      // Fallback UI
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-center w-12 h-12 mx-auto bg-red-100 rounded-full mb-4">
              <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L5.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            
            <h2 className="text-xl font-semibold text-gray-900 text-center mb-2">
              Something went wrong
            </h2>

            <p className="text-gray-600 text-center mb-4">
              We encountered an unexpected error. Please try refreshing the page or contact support if the problem persists.
            </p>

            {this.state.error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
                <p className="text-xs font-semibold text-red-800 mb-1">Error Details:</p>
                <p className="text-xs text-red-600 font-mono break-words">
                  {this.state.error.toString()}
                </p>
              </div>
            )}
            
            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={this.handleRetry}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
              >
                Try Again
              </button>
              <button
                onClick={() => window.location.reload()}
                className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-2 rounded-md text-sm font-medium transition-colors"
              >
                Refresh Page
              </button>
            </div>
            
            {import.meta.env.DEV && this.state.error && (
              <div className="mt-6 p-4 bg-gray-50 rounded-md">
                <h3 className="text-sm font-medium text-gray-900 mb-2">Error Details (Development Mode)</h3>
                <div className="text-xs text-gray-600 font-mono whitespace-pre-wrap">
                  {this.state.error.toString()}
                  {this.state.errorInfo.componentStack}
                </div>
              </div>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;