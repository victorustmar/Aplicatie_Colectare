import React from 'react';

type Props = { children: React.ReactNode };
type State = { error: any };

export default class ErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: any) {
    return { error };
  }

  componentDidCatch(error: any, info: any) {
    // eslint-disable-next-line no-console
    console.error('ErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 24 }}>
          <h2>UI error</h2>
          <pre style={{ whiteSpace: 'pre-wrap' }}>
            {String(this.state.error?.message || this.state.error)}
          </pre>
        </div>
      );
    }
    return this.props.children;
  }
}
