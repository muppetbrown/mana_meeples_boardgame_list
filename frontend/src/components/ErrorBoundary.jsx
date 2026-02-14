import React from 'react';
import PropTypes from 'prop-types';

/**
 * ErrorBoundary component for catching and handling React errors gracefully.
 *
 * Note: React 19 still requires class components for error boundaries.
 * The getDerivedStateFromError and componentDidCatch lifecycle methods
 * have no hook equivalents.
 *
 * Features:
 * - Graceful fallback UI with retry and refresh options
 * - Accessible design with proper ARIA attributes and focus management
 * - Development mode debugging with full error stack traces
 * - Optional onError callback for external error reporting (e.g., Sentry)
 * - Optional custom fallback component
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
    this.retryButtonRef = React.createRef();
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

    // Call optional onError callback for external error reporting
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  componentDidUpdate(prevProps, prevState) {
    // Focus the retry button when error state changes for accessibility
    if (this.state.hasError && !prevState.hasError && this.retryButtonRef.current) {
      this.retryButtonRef.current.focus();
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  handleRefresh = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      // Allow custom fallback component
      if (this.props.fallback) {
        return this.props.fallback({
          error: this.state.error,
          errorInfo: this.state.errorInfo,
          onRetry: this.handleRetry,
          onRefresh: this.handleRefresh,
        });
      }

      // Default fallback UI
      return (
        <div
          className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4"
          role="alert"
          aria-live="assertive"
          aria-atomic="true"
        >
          <div className="max-w-md w-full bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <div
              className="flex items-center justify-center w-12 h-12 mx-auto bg-red-100 dark:bg-red-900/30 rounded-full mb-4"
              aria-hidden="true"
            >
              <svg
                className="w-6 h-6 text-red-600 dark:text-red-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L5.082 16.5c-.77.833.192 2.5 1.732 2.5z"
                />
              </svg>
            </div>

            <h2
              className="text-xl font-semibold text-gray-900 dark:text-gray-100 text-center mb-2"
              id="error-title"
            >
              Something went wrong
            </h2>

            <p className="text-gray-600 dark:text-gray-400 text-center mb-4">
              We encountered an unexpected error. Please try refreshing the page or contact support if the problem persists.
            </p>

            {this.state.error && (
              <div
                className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md"
                aria-label="Error details"
              >
                <p className="text-xs font-semibold text-red-800 dark:text-red-300 mb-1">Error Details:</p>
                <p className="text-xs text-red-600 dark:text-red-400 font-mono break-words">
                  {this.state.error.toString()}
                </p>
              </div>
            )}

            <div className="flex flex-col sm:flex-row gap-3">
              <button
                ref={this.retryButtonRef}
                onClick={this.handleRetry}
                className="flex-1 bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
                aria-describedby="error-title"
              >
                Try Again
              </button>
              <button
                onClick={this.handleRefresh}
                className="flex-1 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 px-4 py-2 rounded-md text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
              >
                Refresh Page
              </button>
            </div>

            {import.meta.env.DEV && this.state.error && (
              <details className="mt-6 p-4 bg-gray-50 dark:bg-gray-900 rounded-md">
                <summary className="text-sm font-medium text-gray-900 dark:text-gray-100 cursor-pointer">
                  Error Details (Development Mode)
                </summary>
                <div className="mt-2 text-xs text-gray-600 dark:text-gray-400 font-mono whitespace-pre-wrap overflow-auto max-h-64">
                  {this.state.error.toString()}
                  {this.state.errorInfo?.componentStack}
                </div>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

ErrorBoundary.propTypes = {
  children: PropTypes.node.isRequired,
  onError: PropTypes.func,
  fallback: PropTypes.func,
};

ErrorBoundary.defaultProps = {
  onError: null,
  fallback: null,
};

export default ErrorBoundary;
