import RunStatusBadge from './RunStatusBadge';
import { SOURCE_LABELS } from '../../lib/constants';

const STATUS_INDICATORS = {
  idle: 'bg-green-500',
  running: 'bg-yellow-500 animate-pulse',
  failed: 'bg-red-500',
};

function formatTimestamp(ts) {
  if (!ts) return 'Never';
  const date = ts.toDate ? ts.toDate() : new Date(ts);
  return date.toLocaleString();
}

export default function SpiderCard({ config, onTrigger, onConfigure }) {
  const {
    id,
    spider_name,
    enabled,
    schedule,
    last_run_status,
    last_run_at,
    stats,
  } = config || {};

  const displayName = SOURCE_LABELS[id] || spider_name || id;
  const statusKey = last_run_status === 'running'
    ? 'running'
    : last_run_status === 'failed'
    ? 'failed'
    : 'idle';
  const indicatorClass = STATUS_INDICATORS[statusKey];

  return (
    <div className="card p-5">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`h-2.5 w-2.5 rounded-full flex-shrink-0 ${indicatorClass}`} />
          <h3 className="font-semibold text-gray-900">{displayName}</h3>
        </div>
        {last_run_status && <RunStatusBadge status={last_run_status} />}
      </div>

      {/* Info */}
      <div className="space-y-1 text-sm text-gray-600 mb-4">
        <p>
          <span className="font-medium text-gray-700">Schedule:</span>{' '}
          {schedule || 'Manual'}
        </p>
        <p>
          <span className="font-medium text-gray-700">Last Run:</span>{' '}
          {formatTimestamp(last_run_at)}
        </p>
        {stats && (
          <p>
            <span className="font-medium text-gray-700">Found:</span>{' '}
            {stats.items_found ?? 0} items
          </p>
        )}
        <p>
          <span className="font-medium text-gray-700">Status:</span>{' '}
          {enabled ? 'Enabled' : 'Disabled'}
        </p>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => onTrigger?.(config)}
          disabled={last_run_status === 'running'}
          className="btn-primary text-sm flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {last_run_status === 'running' ? 'Running...' : 'Run Now'}
        </button>
        <button
          type="button"
          onClick={() => onConfigure?.(config)}
          className="btn-outline text-sm"
        >
          Configure
        </button>
      </div>
    </div>
  );
}
