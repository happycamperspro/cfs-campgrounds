import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useScraperConfigs } from '../../hooks/useScraperConfigs';
import { useScraperRuns } from '../../hooks/useScraperRuns';
import { useAdminActions } from '../../hooks/useAdminActions';
import { SOURCE_LABELS, US_STATES, REGIONS } from '../../lib/constants';
import LoadingSpinner from '../../components/ui/LoadingSpinner';

function formatTimestamp(ts) {
  if (!ts) return 'N/A';
  if (ts.toDate) return ts.toDate().toLocaleString();
  if (ts instanceof Date) return ts.toLocaleString();
  return String(ts);
}

const STATUS_COLORS = {
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  running: 'bg-blue-100 text-blue-800',
  pending: 'bg-yellow-100 text-yellow-800',
  cancelled: 'bg-gray-100 text-gray-600',
};

// ---------------------------------------------------------------------------
// Run Parameters Panel — shown before triggering
// ---------------------------------------------------------------------------
function RunParametersPanel({ config, onRun, running }) {
  const [targetStates, setTargetStates] = useState(
    config.targetStates?.join(', ') || config.states?.join(', ') || ''
  );
  const [itemLimit, setItemLimit] = useState(config.itemLimit || config.item_limit || 100);
  const [showRegions, setShowRegions] = useState(false);

  function handleRun() {
    const states = targetStates
      .split(',')
      .map((s) => s.trim().toUpperCase())
      .filter((s) => US_STATES[s]);

    onRun({
      targetStates: states.length > 0 ? states : null,
      itemLimit: parseInt(itemLimit, 10) || null,
    });
  }

  function addRegion(regionStates) {
    const current = targetStates
      .split(',')
      .map((s) => s.trim().toUpperCase())
      .filter(Boolean);
    const merged = [...new Set([...current, ...regionStates])];
    setTargetStates(merged.join(', '));
  }

  return (
    <div className="card p-5 mb-8 border-campfire-200 bg-campfire-50/30">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Run Parameters</h2>
      <p className="text-sm text-gray-600 mb-4">
        Configure what to scrape before starting. Set a state filter and item limit to avoid
        overwhelming the source API.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Target States (comma-separated)
          </label>
          <input
            type="text"
            value={targetStates}
            onChange={(e) => setTargetStates(e.target.value)}
            placeholder="CA, OR, WA"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-campfire-500 focus:border-campfire-500 outline-none"
          />
          <div className="mt-2 flex flex-wrap gap-1">
            <button
              type="button"
              onClick={() => setShowRegions(!showRegions)}
              className="text-xs text-campfire-600 hover:text-campfire-800 underline"
            >
              {showRegions ? 'Hide regions' : 'Add by region'}
            </button>
            {targetStates && (
              <button
                type="button"
                onClick={() => setTargetStates('')}
                className="text-xs text-red-500 hover:text-red-700 underline ml-2"
              >
                Clear all
              </button>
            )}
          </div>
          {showRegions && (
            <div className="mt-2 flex flex-wrap gap-1">
              {Object.entries(REGIONS).map(([region, states]) => (
                <button
                  key={region}
                  type="button"
                  onClick={() => addRegion(states)}
                  className="text-xs px-2 py-1 rounded bg-gray-100 hover:bg-campfire-100 text-gray-700 hover:text-campfire-700 transition-colors"
                >
                  {region} ({states.length})
                </button>
              ))}
            </div>
          )}
          {targetStates && (
            <p className="mt-2 text-xs text-gray-500">
              {targetStates.split(',').filter((s) => US_STATES[s.trim().toUpperCase()]).length} valid state(s)
            </p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Item Limit
          </label>
          <input
            type="number"
            value={itemLimit}
            onChange={(e) => setItemLimit(e.target.value)}
            min="1"
            max="10000"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-campfire-500 focus:border-campfire-500 outline-none"
          />
          <p className="mt-1 text-xs text-gray-500">
            Max campgrounds to fetch. 50-200 for testing, 500-2000 for full runs.
          </p>
        </div>
      </div>

      {!targetStates.trim() && (
        <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-800">
          Warning: No state filter set. This will attempt to pull ALL data from the source.
        </div>
      )}

      <button
        type="button"
        className="btn-primary text-sm flex items-center gap-1.5 disabled:opacity-50"
        onClick={handleRun}
        disabled={running}
      >
        {running ? (
          <>
            <LoadingSpinner size="sm" />
            Starting...
          </>
        ) : (
          <>
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
            </svg>
            Run Now
          </>
        )}
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Active Run Card — progress + cancel
// ---------------------------------------------------------------------------
function ActiveRunCard({ run, onCancel, cancelling }) {
  const stats = run.stats || {};
  const itemsFound = stats.itemsFound || 0;
  const itemsLoaded = stats.itemsLoaded || 0;
  const errors = stats.errors || 0;
  const configLimit = run.config?.itemLimit;
  const progress = configLimit ? Math.min(100, Math.round((itemsFound / configLimit) * 100)) : null;
  const targetStates = run.config?.targetStates;

  return (
    <div className="card p-5 mb-4 border-blue-200 bg-blue-50/40">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`badge ${STATUS_COLORS[run.status] || 'bg-gray-100 text-gray-800'}`}>
            {run.status}
          </span>
          <span className="text-sm text-gray-500">
            Started {formatTimestamp(run.startedAt)}
          </span>
        </div>
        {(run.status === 'pending' || run.status === 'running') && (
          <button
            type="button"
            onClick={() => onCancel(run.id)}
            disabled={cancelling}
            className="text-sm px-3 py-1.5 rounded-lg border border-red-300 text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50"
          >
            {cancelling ? 'Cancelling...' : 'Stop'}
          </button>
        )}
      </div>

      {/* Progress bar */}
      {progress !== null && (
        <div className="mb-3">
          <div className="flex justify-between text-xs text-gray-600 mb-1">
            <span>{itemsFound} / {configLimit} items</span>
            <span>{progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2.5">
            <div
              className="bg-blue-500 h-2.5 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* No limit — indeterminate indicator */}
      {progress === null && (run.status === 'running' || run.status === 'pending') && (
        <div className="mb-3">
          <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
            <div className="bg-blue-500 h-2.5 rounded-full w-1/3 animate-pulse" />
          </div>
          <p className="text-xs text-gray-500 mt-1">{itemsFound} items found so far</p>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 text-sm">
        <div>
          <span className="text-gray-500">Found</span>
          <p className="font-semibold text-gray-900">{itemsFound}</p>
        </div>
        <div>
          <span className="text-gray-500">Loaded</span>
          <p className="font-semibold text-gray-900">{itemsLoaded}</p>
        </div>
        <div>
          <span className="text-gray-500">Errors</span>
          <p className={`font-semibold ${errors > 0 ? 'text-red-600' : 'text-gray-900'}`}>{errors}</p>
        </div>
      </div>

      {/* Target states */}
      {targetStates && targetStates.length > 0 && (
        <div className="mt-3 pt-3 border-t border-blue-100">
          <span className="text-xs text-gray-500">Target states: </span>
          <span className="text-xs font-medium text-gray-700">{targetStates.join(', ')}</span>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------
export default function SpiderDetailPage() {
  const { name } = useParams();
  const { configs, loading: configsLoading, toggleEnabled } = useScraperConfigs();
  const { runs, loading: runsLoading } = useScraperRuns({ spiderName: name, limit: 25 });
  const { runSpider, cancelScraper, running } = useAdminActions();
  const [cancelling, setCancelling] = useState(null);

  const loading = configsLoading || runsLoading;
  const config = configs.find((c) => c.name === name);

  async function handleRun(params) {
    try {
      await runSpider(name, params);
    } catch (err) {
      // error displayed by hook
    }
  }

  async function handleCancel(runId) {
    setCancelling(runId);
    try {
      await cancelScraper(runId);
    } catch (err) {
      // error displayed by hook
    } finally {
      setCancelling(null);
    }
  }

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
        <h1 className="text-2xl font-bold text-gray-900 mb-4">Source Not Found</h1>
        <p className="text-gray-600 mb-6">
          No configuration found for &ldquo;{name}&rdquo;.
        </p>
        <Link to="/admin/scrapers" className="btn-primary">
          Back to Scrapers
        </Link>
      </div>
    );
  }

  const displayName = SOURCE_LABELS[config.name] || config.name;
  const activeRuns = runs.filter((r) => r.status === 'running' || r.status === 'pending');
  const completedRuns = runs.filter((r) => r.status !== 'running' && r.status !== 'pending');

  // Collect all unique states scraped across completed runs
  const scrapedStates = new Set();
  for (const run of completedRuns) {
    const states = run.config?.targetStates;
    if (states && Array.isArray(states)) {
      states.forEach((s) => scrapedStates.add(s));
    }
  }

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
        <button
          type="button"
          className="btn-outline text-sm"
          onClick={() => toggleEnabled(config.name, !config.enabled)}
        >
          {config.enabled ? 'Disable' : 'Enable'}
        </button>
      </div>

      {/* Active runs with cancel + progress */}
      {activeRuns.length > 0 && (
        <div className="mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Active Runs</h2>
          {activeRuns.map((run) => (
            <ActiveRunCard
              key={run.id}
              run={run}
              onCancel={handleCancel}
              cancelling={cancelling === run.id}
            />
          ))}
        </div>
      )}

      {/* Run parameters */}
      <RunParametersPanel config={config} onRun={handleRun} running={running} />

      {/* Config details */}
      <div className="card p-5 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Configuration</h2>
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="text-gray-500">Source Name</dt>
            <dd className="font-medium text-gray-900 mt-0.5">{config.name}</dd>
          </div>
          <div>
            <dt className="text-gray-500">Schedule</dt>
            <dd className="font-medium text-gray-900 mt-0.5">{config.schedule || 'Not set'}</dd>
          </div>
          <div>
            <dt className="text-gray-500">Default Target States</dt>
            <dd className="font-medium text-gray-900 mt-0.5">
              {(config.targetStates || config.states)?.length > 0
                ? (config.targetStates || config.states).join(', ')
                : 'All states'}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500">Default Item Limit</dt>
            <dd className="font-medium text-gray-900 mt-0.5">
              {config.itemLimit || config.item_limit || 'Unlimited'}
            </dd>
          </div>
        </dl>
      </div>

      {/* Scraped states coverage */}
      {scrapedStates.size > 0 && (
        <div className="card p-5 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">States Covered</h2>
          <p className="text-sm text-gray-500 mb-3">
            {scrapedStates.size} of {Object.keys(US_STATES).length} states scraped in past runs
          </p>
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(US_STATES).map(([code, fullName]) => (
              <span
                key={code}
                title={fullName}
                className={`text-xs px-2 py-1 rounded-full font-medium ${
                  scrapedStates.has(code)
                    ? 'bg-green-100 text-green-700'
                    : 'bg-gray-100 text-gray-400'
                }`}
              >
                {code}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Run history table */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Run History</h2>
        {completedRuns.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No completed runs recorded.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left text-gray-500">
                  <th className="pb-3 pr-4 font-medium">Started At</th>
                  <th className="pb-3 pr-4 font-medium">States</th>
                  <th className="pb-3 pr-4 font-medium">Status</th>
                  <th className="pb-3 pr-4 font-medium">Found</th>
                  <th className="pb-3 pr-4 font-medium">Loaded</th>
                  <th className="pb-3 font-medium">Errors</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {completedRuns.map((run) => {
                  const states = run.config?.targetStates;
                  const stats = run.stats || {};
                  return (
                    <tr key={run.id} className="text-gray-700">
                      <td className="py-3 pr-4">{formatTimestamp(run.startedAt)}</td>
                      <td className="py-3 pr-4 text-xs">
                        {states && states.length > 0
                          ? states.length <= 5
                            ? states.join(', ')
                            : `${states.slice(0, 5).join(', ')} +${states.length - 5}`
                          : 'All'}
                      </td>
                      <td className="py-3 pr-4">
                        <span className={`badge ${STATUS_COLORS[run.status] || 'bg-gray-100 text-gray-800'}`}>
                          {run.status}
                        </span>
                      </td>
                      <td className="py-3 pr-4">{stats.itemsFound ?? run.items_found ?? '-'}</td>
                      <td className="py-3 pr-4">{stats.itemsLoaded ?? run.items_loaded ?? '-'}</td>
                      <td className="py-3">{stats.errors ?? run.errors ?? 0}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
