import { usePositions } from '../api/hooks';
import { PositionsTable } from '../components/PositionsTable';
import { HedgeEvaluator } from '../components/HedgeEvaluator';

export default function HedgeReportPage() {
  const { data: positions = [] } = usePositions();

  return (
    <div className="hedge-report-panel">
      <div className="dual-table-wrapper">
        <PositionsTable positions={positions} type="SHORT" />
        <PositionsTable positions={positions} type="LONG" />
      </div>
      <HedgeEvaluator />
    </div>
  );
}
