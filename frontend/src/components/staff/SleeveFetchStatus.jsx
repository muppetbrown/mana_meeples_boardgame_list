// src/components/staff/SleeveFetchStatus.jsx
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { getSleeveFetchStatus } from '../../api/client';

const POLL_INTERVAL_MS = 5000;
const MAX_POLLS = 36; // ~3 minutes

const STATUS_LABELS = {
  queued: { text: 'Queued...', className: 'text-gray-600' },
  in_progress: { text: 'Running...', className: 'text-blue-600' },
};

/**
 * Shows the status of the most recent "Fetch Sleeve Data" GitHub Actions run.
 * Pass a changing `pollToken` (e.g. a counter you bump) right after triggering
 * a fetch to start active polling; otherwise it just shows the last known
 * status with a manual refresh button.
 */
export default function SleeveFetchStatus({ pollToken }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [checking, setChecking] = useState(false);
  const pollCountRef = useRef(0);
  const intervalRef = useRef(null);

  const checkStatus = useCallback(async () => {
    setChecking(true);
    try {
      const result = await getSleeveFetchStatus();
      setData(result);
      setError(null);
      return result;
    } catch (err) {
      console.error('Failed to check sleeve fetch status:', err);
      setError('Failed to check status.');
      return null;
    } finally {
      setChecking(false);
    }
  }, []);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // Initial load
  useEffect(() => {
    checkStatus();
    return stopPolling;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Start active polling whenever pollToken changes (a fetch was just triggered)
  useEffect(() => {
    if (pollToken === undefined || pollToken === null) return;

    stopPolling();
    pollCountRef.current = 0;

    intervalRef.current = setInterval(async () => {
      pollCountRef.current += 1;
      const result = await checkStatus();
      if ((result && result.status === 'completed') || pollCountRef.current >= MAX_POLLS) {
        stopPolling();
      }
    }, POLL_INTERVAL_MS);

    return stopPolling;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pollToken]);

  if (error) {
    return (
      <div className="mt-2 text-sm text-red-600 flex items-center gap-2">
        {error}
        <button type="button" onClick={checkStatus} className="underline">Retry</button>
      </div>
    );
  }

  if (!data) {
    return <div className="mt-2 text-sm text-gray-500">Loading sleeve fetch status...</div>;
  }

  if (!data.workflow_configured) {
    return <div className="mt-2 text-sm text-gray-500">{data.message}</div>;
  }

  if (!data.status) {
    return (
      <div className="mt-2 text-sm text-gray-500 flex items-center gap-2">
        {data.message || 'No sleeve fetch runs found yet.'}
        <button type="button" onClick={checkStatus} className="underline" disabled={checking}>
          {checking ? 'Checking...' : 'Refresh'}
        </button>
      </div>
    );
  }

  let statusDisplay;
  if (data.status === 'completed') {
    if (data.conclusion === 'success') {
      statusDisplay = <span className="text-green-700 font-medium">✓ Last run succeeded</span>;
    } else {
      statusDisplay = <span className="text-red-600 font-medium">✗ Last run {data.conclusion || 'failed'}</span>;
    }
  } else {
    const info = STATUS_LABELS[data.status] || { text: data.status, className: 'text-gray-600' };
    statusDisplay = <span className={info.className}>{info.text}</span>;
  }

  return (
    <div className="mt-2 text-sm flex items-center gap-3 flex-wrap">
      {statusDisplay}
      {data.html_url && (
        <a
          href={data.html_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-purple-600 hover:text-purple-800 underline"
        >
          View run on GitHub
        </a>
      )}
      <button type="button" onClick={checkStatus} className="text-gray-500 hover:text-gray-700 underline" disabled={checking}>
        {checking ? 'Checking...' : 'Refresh'}
      </button>
      {intervalRef.current && <span className="text-xs text-gray-400">(auto-refreshing)</span>}
    </div>
  );
}
