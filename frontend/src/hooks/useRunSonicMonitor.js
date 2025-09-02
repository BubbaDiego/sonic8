import { useCallback } from 'react';
import { runSonicCycle, runSonicMonitor } from 'api/sonicMonitor';
import { refreshPositions } from 'api/positions';
import { refreshMonitorStatus } from 'api/monitorStatus';

// ==============================|| USE RUN SONIC MONITOR ||============================== //
// Runs the Sonic cycle or monitor and refreshes dashboards on success.
// `type` selects the underlying API (cycle vs. monitor) and `delay` waits before refreshing.
export default function useRunSonicMonitor(type = 'cycle', delay = 0) {
  return useCallback(async () => {
    const runner = type === 'monitor' ? runSonicMonitor : runSonicCycle;
    const result = await runner();
    const triggerRefresh = () => {
      refreshPositions();
      refreshMonitorStatus();
    };
    if (delay > 0) {
      setTimeout(triggerRefresh, delay);
    } else {
      triggerRefresh();
    }
    return result;
  }, [type, delay]);
}
