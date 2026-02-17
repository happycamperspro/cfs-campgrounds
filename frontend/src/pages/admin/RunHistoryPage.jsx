import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useScraperRuns } from '../../hooks/useScraperRuns';
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

const STATUS_OPTIONS = ['all', 'completed', 'failed', 'running', 'pending'];
const PAGE_SIZE = 20;

export default function RunHistoryPage() {
  const { runs, loading, hasMore, loadMore } = useScraperRuns({ limit: 100 });
  const [spiderFilter, setSpiderFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [page, setPage] = useState(0);

  // Unique spider names from loaded runs
  const spiderNames = useMemo(() => {
    const names = new Set(runs.map((r) => r.spider_name).filter(Boolean));
    return Array.from(names).sort();
  }, [runs]);

  // Filtered runs
  const filtered = useMemo(() => {
    return runs.filter((run) => {
      if (spiderFilter !== 'all' && run.spider_name !== spiderFilter) return false;
      if (statusFilter !== 'all' && run.status !== statusFilter) return false;
      return true;
    });
  }, [runs, spiderFilter, statusFilter]);

  // Paginated
  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Breadcrumb */}
      <nav className="text-sm text-gray-500 mb-4">
        <Link to="/admin" className="hover:text-campfire-600 transition-colors">Dashboard</Link>
        <span className="mx-2">/</span>
        <span className="text-gray-900 font-medium">Run History</span>
      </nav>

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Run History</h1>
          <p className="text-sm text-gray-500 mt-1">
            {filtered.length} run{filtered.length !== 1 ? 's' : ''} found
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div>
          <label htmlFor="spider-filter" className="block text-xs font-medium text-gray-500 mb-1">
            Spider
          </label>
          <select
            id="spider-filter"
            value={spiderFilter}
            onChange={(e) => {
              setSpiderFilter(e.target.value);
              setPage(0);
            }}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-campfire-500 focus:border-campfire-500 outline-none"
          >
            <option value="all">All Spiders</option>
            {spiderNames.map((name) => (
              <option key={name} value={name}>
                {SOURCE_LABELS[name] || name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="status-filter" className="block text-xs font-medium text-gray-500 mb-1">
            Status
          </label>
          <select
            id="status-filter"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(0);
            }}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-campfire-500 focus:border-campfire-500 outline-none"
          >
            {STATUS_OPTIONS.map((status) => (
              <option key={status} value={status}>
                {status === 'all' ? 'All Statuses' : status.charAt(0).toUpperCase() + status.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Table */}
      {loading && runs.length === 0 ? (
        <div className="flex justify-center py-16">
          <LoadingSpinner size="lg" />
        </div>
      ) : paged.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          No runs match the current filters.
        </div>
      ) : (
        <>
          <div className="overflow-x-auto bg-white rounded-xl border border-gray-200">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50 text-left text-gray-500">
                  <th className="px-4 py-3 font-medium">Spider</th>
                  <th className="px-4 py-3 font-medium">Started At</th>
                  <th className="px-4 py-3 font-medium">Duration</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Items Found</th>
                  <th className="px-4 py-3 font-medium">Items Loaded</th>
                  <th className="px-4 py-3 font-medium">Errors</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {paged.map((run) => (
                  <tr key={run.id} className="text-gray-700 hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3">
                      <Link
                        to={`/admin/scrapers/${run.spider_name}`}
                        className="font-medium text-campfire-600 hover:text-campfire-700 transition-colors"
                      >
                        {SOURCE_LABELS[run.spider_name] || run.spider_name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {formatTimestamp(run.started_at)}
                    </td>
                    <td className="px-4 py-3">{formatDuration(run.duration_seconds)}</td>
                    <td className="px-4 py-3">
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
                    <td className="px-4 py-3">{run.items_found ?? '-'}</td>
                    <td className="px-4 py-3">{run.items_loaded ?? '-'}</td>
                    <td className="px-4 py-3">{run.errors ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between mt-4">
            <p className="text-sm text-gray-500">
              Showing {page * PAGE_SIZE + 1}
              {' '}-{' '}
              {Math.min((page + 1) * PAGE_SIZE, filtered.length)} of {filtered.length}
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="btn-outline text-sm px-3 py-1.5 disabled:opacity-40"
                onClick={() => setPage((p) => p - 1)}
                disabled={page === 0}
              >
                Previous
              </button>
              <span className="text-sm text-gray-600">
                Page {page + 1} of {totalPages || 1}
              </span>
              <button
                type="button"
                className="btn-outline text-sm px-3 py-1.5 disabled:opacity-40"
                onClick={() => setPage((p) => p + 1)}
                disabled={page >= totalPages - 1}
              >
                Next
              </button>
            </div>
          </div>

          {/* Load more from Firestore if available */}
          {hasMore && page >= totalPages - 1 && (
            <div className="mt-4 flex justify-center">
              <button
                type="button"
                className="btn-outline text-sm"
                onClick={loadMore}
                disabled={loading}
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <LoadingSpinner size="sm" />
                    Loading more...
                  </span>
                ) : (
                  'Load More Runs'
                )}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
