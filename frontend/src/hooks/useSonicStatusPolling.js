import { useEffect, useState } from 'react';
import axios from 'utils/axios';
import { refreshPositions } from 'api/positions';
import { refreshMonitorStatus } from 'api/monitorStatus';

const POLL_MS = 5000;

let listeners = new Set();
let state = {
  sonicNextTs: Date.now(),
  snoozeEndTs: Date.now(),
  sonicActive: false,
  lastSonicComplete: null
};
let pollerStarted = false;
let lastSonicCompleteRef = null;

async function poll() {
  try {
    const { data } = await axios.get('/api/monitor-status/');
    const now = Date.now();
    state = {
      sonicNextTs: now + (data?.sonic_next ?? 0) * 1000,
      snoozeEndTs: now + (data?.liquid_snooze ?? 0) * 1000,
      sonicActive: data?.monitors?.['Sonic Monitoring']?.status === 'Healthy',
      lastSonicComplete: data?.sonic_last_complete ?? null
    };
    listeners.forEach((set) => set(state));
    if (lastSonicCompleteRef === null) {
      lastSonicCompleteRef = state.lastSonicComplete;
    } else if (state.lastSonicComplete && state.lastSonicComplete !== lastSonicCompleteRef) {
      lastSonicCompleteRef = state.lastSonicComplete;
      refreshPositions();
      refreshMonitorStatus();
    }
  } catch (err) {
    console.error('Failed to fetch monitor status:', err);
  } finally {
    setTimeout(poll, POLL_MS);
  }
}

function startPolling() {
  if (!pollerStarted) {
    pollerStarted = true;
    poll();
  }
}

export default function useSonicStatusPolling() {
  const [localState, setLocalState] = useState(state);

  useEffect(() => {
    listeners.add(setLocalState);
    startPolling();
    return () => {
      listeners.delete(setLocalState);
    };
  }, []);

  return localState;
}

