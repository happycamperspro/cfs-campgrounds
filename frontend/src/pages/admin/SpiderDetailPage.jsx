import { useParams, Link } from 'react-router-dom';
import { useScraperConfigs } from '../../hooks/useScraperConfigs';
import { useScraperRuns } from '../../hooks/useScraperRuns';
import { useAdminActions } from '../../hooks/useAdminActions';
import { SOURCE_LABELS } from '../../lib/constants';
import LoadingSpinner from '../../components/ui/LoadingSpinner';

function formatDuration(seconds) {
  if (!seconds && seconds !== 0) return 'N/A';
  if (seconds < 60) return `${seconds}s`;
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}m ${secs}s`;
}

function formatTimestamp(ts) {
  if (!ts) return 'N/A';
  if (ts.toDate) return ts.toDate().toLocaleString();
  if (ts instanceof Date) return ts.toLocaleString();
  return String(ts);
}

export default function SpiderDetailPage() {
  const { name } = useParams();
  const { configs, loading: configsLoading, toggleEnabled } = useScraperConfigs();
  const { runs, loading: runsLoading } = useScraperRuns({ spiderName: name, limit: 25 });
  const { runSpider, running } = useAdminActions();

  const loading = configsLoading || runsLoading;
  const config = configs.find((c) => c.name === name);

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!config) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">Spider Not Found</h1>
        <p className="text-gray-600 mb-6">
          No spider configuration found for &ldquo;{name}&rdquo;.
        </p>
        <Link to="/admin/scrapers" className="btn-primary">
          Back to Scrapers
        </Link>
      </div>
    );
  }

  const displayName = SOURCE_LABELS[config.name] || config.name;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Breadcrumb */}
      <nav className="text-sm text-gray-500 mb-4">
        <Link to="/admin" className="hover:text-campfire-600 transition-colors">Dashboard</Link>
        <span className="mx-2">/</span>
        <Link to="/admin/scrapers" className="hover:text-campfire-600 transition-colors">Scrapers</Link>
        <span className="mx-2">/</span>
        <span className="text-gray-900 font-medium">{displayName}</span>
      </nav>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{displayName}</h1>
          <div className="flex items-center gap-2 mt-1">
            <span
              className={`badge ${
                config.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
              }`}
            >
              {config.enabled ? 'Active' : 'Disabled'}
            </span>
            {config.schedule && (
              <span className="text-sm text-gray-500">Schedule: {config.schedule}</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            className="btn-outline text-sm"
            onClick={() => toggleEnabled(config.name, !config.enabled)}
          >
            {config.enabled ? 'Disable' : 'Enable'}
          </button>
          <button
            type="button"
            className="btn-primary text-sm flex items-center gap-1.5 disabled:opacity-50"
            onClick={() => runSpider(config.name)}
            disabled={running === config.name}
          >
            {running === config.name ? (
              <>
                <LoadingSpinner size="sm" />
                Running...
              </>
            ) : (
              'Run Now'
            )}
          </button>
        </div>
      </div>

      {/* Config details */}
      <div className="card p-5 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Configuration</h2>
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="text-gray-500">Spider Name</dt>
            <dd className="font-medium text-gray-900 mt-0.5">{config.name}</dd>
          </div>
          <div>
            <dt className="text-gray-500">Schedule</dt>
            <dd className="font-medium text-gray-900 mt-0.5">{config.schedule || 'Not set'}</dd>
          </div>
          <div>
            <dt className="text-gray-500">Target States</dt>
            <dd className="font-medium text-gray-900 mt-0.5">
              {config.states && config.states.length > 0
                ? config.states.join(', ')
                : 'All states'}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500">Item Limit</dt>
            <dd className="font-medium text-gray-900 mt-0.5">
              {config.item_limit || 'Unlimited'}
            </dd>
          </div>
        </dl>
      </div>

      {/* Run history */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Run History</h2>
        {runs.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No runs recorded for this spider.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left text-gray-500">
                  <th className="pb-3 pr-4 font-medium">Started At</th>
                  <th className="pb-3 pr-4 font-medium">Duration</th>
                  <th className="pb-3 pr-4 font-medium">Status</th>
                  <th className="pb-3 pr-4 font-medium">Items Found</th>
                  <th className="pb-3 pr-4 font-medium">Items Loaded</th>
                  <th className="pb-3 font-medium">Errors</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {runs.map((run) => (
                  <tr key={run.id} className="text-gray-700">
                    <td className="py-3 pr-4">{formatTimestamp(run.started_at)}</td>
                    <td className="py-3 pr-4">{formatDuration(run.duration_seconds)}</td>
                    <td className="py-3 pr-4">
                      <span
                        className={`badge ${
                          run.status === 'completed'
                            ? 'bg-green-100 text-green-800'
                            : run.status === 'failed'
                            ? 'bg-red-100 text-red-800'
                            : run.status === 'running'
                            ? 'bg-blue-100 text-blue-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {run.status}
                      </span>
                    </td>
                    <td className="py-3 pr-4">{run.items_found ?? '-'}</td>
                    <td className="py-3 pr-4">{run.items_loaded ?? '-'}</td>
                    <td className="py-3">{run.errors ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
