import { useState, useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useCampgroundInventory } from '../../hooks/useCampgroundInventory';
import { SOURCE_LABELS, SOURCE_COLORS, US_STATES } from '../../lib/constants';
import LoadingSpinner from '../../components/ui/LoadingSpinner';

const ALL_SOURCES = [
  'recreation_gov', 'nps', 'koa', 'hipcamp',
  'good_sam', 'thousand_trails', 'state_parks',
];

function StatCard({ label, value, subtext, color = 'campfire', onClick, active }) {
  const colorClasses = {
    campfire: 'bg-campfire-50 text-campfire-700 border-campfire-200',
    forest: 'bg-forest-50 text-forest-700 border-forest-200',
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    purple: 'bg-purple-50 text-purple-700 border-purple-200',
  };

  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-xl border p-4 text-left transition-all ${
        colorClasses[color] || colorClasses.campfire
      } ${active ? 'ring-2 ring-campfire-500 shadow-md' : 'hover:shadow-sm'}`}
    >
      <p className="text-xs font-medium opacity-80">{label}</p>
      <p className="text-2xl font-bold mt-0.5">{value}</p>
      {subtext && <p className="text-xs mt-0.5 opacity-70">{subtext}</p>}
    </button>
  );
}

export default function InventoryPage() {
  const [searchParams] = useSearchParams();
  const [sourceFilter, setSourceFilter] = useState(searchParams.get('source') || '');
  const [stateFilter, setStateFilter] = useState(searchParams.get('state') || '');

  const filters = useMemo(
    () => ({
      source: sourceFilter || undefined,
      state: stateFilter || undefined,
    }),
    [sourceFilter, stateFilter]
  );

  const { stats, campgrounds, loading, listLoading, error, loadMore, hasMore } =
    useCampgroundInventory(filters);

  // Compute state counts from loaded campgrounds (approximate — from current view)
  const stateCounts = useMemo(() => {
    const counts = {};
    for (const cg of campgrounds) {
      const st = cg.location?.state;
      if (st) counts[st] = (counts[st] || 0) + 1;
    }
    return counts;
  }, [campgrounds]);

  function handleSourceClick(src) {
    setSourceFilter((prev) => (prev === src ? '' : src));
    setStateFilter('');
  }

  function handleStateClick(st) {
    setStateFilter((prev) => (prev === st ? '' : st));
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Breadcrumb */}
      <nav className="text-sm text-gray-500 mb-4">
        <Link to="/admin" className="hover:text-campfire-600 transition-colors">
          Dashboard
        </Link>
        <span className="mx-2">/</span>
        <span className="text-gray-900 font-medium">Inventory</span>
      </nav>

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Campground Inventory</h1>
          <p className="text-sm text-gray-500 mt-1">
            All campground data collected across sources
          </p>
        </div>
      </div>

      {/* Stats cards */}
      {stats && (
        <div className="mb-8">
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
            <StatCard
              label="Total"
              value={stats.total.toLocaleString()}
              color="campfire"
              onClick={() => { setSourceFilter(''); setStateFilter(''); }}
              active={!sourceFilter}
            />
            {ALL_SOURCES.map((src) => {
              const count = stats.sourceCounts[src] || 0;
              if (count === 0) return null;
              return (
                <StatCard
                  key={src}
                  label={SOURCE_LABELS[src] || src}
                  value={count.toLocaleString()}
                  subtext={`${((count / stats.total) * 100).toFixed(1)}%`}
                  color="blue"
                  onClick={() => handleSourceClick(src)}
                  active={sourceFilter === src}
                />
              );
            })}
          </div>
        </div>
      )}

      {/* Active filters */}
      {(sourceFilter || stateFilter) && (
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <span className="text-sm text-gray-500">Filtering:</span>
          {sourceFilter && (
            <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-700">
              {SOURCE_LABELS[sourceFilter] || sourceFilter}
              <button type="button" onClick={() => setSourceFilter('')} className="hover:text-blue-900">
                &times;
              </button>
            </span>
          )}
          {stateFilter && (
            <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-green-100 text-green-700">
              {stateFilter} — {US_STATES[stateFilter]}
              <button type="button" onClick={() => setStateFilter('')} className="hover:text-green-900">
                &times;
              </button>
            </span>
          )}
          <button
            type="button"
            onClick={() => { setSourceFilter(''); setStateFilter(''); }}
            className="text-xs text-red-500 hover:text-red-700 underline"
          >
            Clear all
          </button>
        </div>
      )}

      {/* State coverage badges */}
      {!stateFilter && campgrounds.length > 0 && (
        <div className="card p-4 mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">
            States in current view ({Object.keys(stateCounts).length})
          </h3>
          <div className="flex flex-wrap gap-1">
            {Object.entries(US_STATES).map(([code, name]) => {
              const count = stateCounts[code] || 0;
              return (
                <button
                  key={code}
                  type="button"
                  onClick={() => handleStateClick(code)}
                  title={`${name}: ${count} campground${count !== 1 ? 's' : ''}`}
                  className={`text-xs px-2 py-0.5 rounded-full font-medium transition-colors ${
                    count > 0
                      ? 'bg-green-100 text-green-700 hover:bg-green-200'
                      : 'bg-gray-50 text-gray-300'
                  } ${stateFilter === code ? 'ring-2 ring-green-500' : ''}`}
                >
                  {code}
                  {count > 0 && <span className="ml-0.5 text-green-500">({count})</span>}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Error display */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800">
          {error.message}
        </div>
      )}

      {/* Campground table */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <LoadingSpinner size="lg" />
        </div>
      ) : campgrounds.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <p className="text-lg font-medium">No campgrounds found</p>
          <p className="text-sm mt-1">
            {sourceFilter || stateFilter
              ? 'Try adjusting your filters.'
              : 'Run a scraper to start collecting data.'}
          </p>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left text-gray-500">
                  <th className="pb-3 pr-4 font-medium">Name</th>
                  <th className="pb-3 pr-4 font-medium">Source</th>
                  <th className="pb-3 pr-4 font-medium">State</th>
                  <th className="pb-3 pr-4 font-medium">City</th>
                  <th className="pb-3 pr-4 font-medium">Sites</th>
                  <th className="pb-3 pr-4 font-medium">Photos</th>
                  <th className="pb-3 font-medium">Last Synced</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {campgrounds.map((cg) => (
                  <tr key={cg.id} className="text-gray-700 hover:bg-gray-50">
                    <td className="py-3 pr-4 max-w-xs">
                      <Link
                        to={`/campground/${cg.slug || cg.id}`}
                        className="text-campfire-600 hover:text-campfire-800 font-medium hover:underline"
                      >
                        {cg.name || 'Unnamed'}
                      </Link>
                    </td>
                    <td className="py-3 pr-4">
                      <span className={`badge ${SOURCE_COLORS[cg.source] || 'bg-gray-100 text-gray-800'}`}>
                        {SOURCE_LABELS[cg.source] || cg.source}
                      </span>
                    </td>
                    <td className="py-3 pr-4">
                      <button
                        type="button"
                        onClick={() => handleStateClick(cg.location?.state)}
                        className="text-gray-700 hover:text-campfire-600"
                      >
                        {cg.location?.state || '-'}
                      </button>
                    </td>
                    <td className="py-3 pr-4 text-gray-500">{cg.location?.city || '-'}</td>
                    <td className="py-3 pr-4">{cg.details?.totalSites || '-'}</td>
                    <td className="py-3 pr-4">{cg.photos?.length || 0}</td>
                    <td className="py-3 text-xs text-gray-400">
                      {cg.metadata?.lastSyncedAt?.toDate
                        ? cg.metadata.lastSyncedAt.toDate().toLocaleDateString()
                        : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Load more */}
          {hasMore && (
            <div className="mt-4 text-center">
              <button
                type="button"
                onClick={loadMore}
                disabled={listLoading}
                className="btn-outline text-sm disabled:opacity-50"
              >
                {listLoading ? (
                  <span className="flex items-center gap-2">
                    <LoadingSpinner size="sm" /> Loading...
                  </span>
                ) : (
                  `Load more (${campgrounds.length} shown)`
                )}
              </button>
            </div>
          )}

          {!hasMore && campgrounds.length > 0 && (
            <p className="mt-4 text-center text-xs text-gray-400">
              Showing all {campgrounds.length} campground{campgrounds.length !== 1 ? 's' : ''}
              {sourceFilter ? ` from ${SOURCE_LABELS[sourceFilter] || sourceFilter}` : ''}
              {stateFilter ? ` in ${stateFilter}` : ''}
            </p>
          )}
        </>
      )}
    </div>
  );
}
