import { SOURCE_LABELS } from '../../lib/constants';

function StatCard({ label, value, sublabel }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
      <p className="text-sm text-gray-500 mb-1">{label}</p>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      {sublabel && <p className="text-xs text-gray-400 mt-1">{sublabel}</p>}
    </div>
  );
}

function formatTimestamp(ts) {
  if (!ts) return 'Never';
  const date = ts.toDate ? ts.toDate() : new Date(ts);
  return date.toLocaleString();
}

export default function StatsOverview({ configs }) {
  if (!configs || Object.keys(configs).length === 0) {
    return null;
  }

  const spiders = Object.values(configs);

  // Total campgrounds across all spiders
  const totalCampgrounds = spiders.reduce(
    (sum, c) => sum + (c.stats?.total_items ?? 0),
    0
  );

  // Breakdown by source
  const bySource = spiders.map((c) => ({
    name: SOURCE_LABELS[c.id] || c.id,
    count: c.stats?.total_items ?? 0,
  }));

  // Most recent sync
  const lastSync = spiders.reduce((latest, c) => {
    if (!c.last_run_at) return latest;
    const ts = c.last_run_at.toDate ? c.last_run_at.toDate() : new Date(c.last_run_at);
    if (!latest || ts > latest) return ts;
    return latest;
  }, null);

  return (
    <div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard
          label="Total Campgrounds"
          value={totalCampgrounds.toLocaleString()}
        />
        <StatCard
          label="Data Sources"
          value={spiders.length}
        />
        <StatCard
          label="Active Spiders"
          value={spiders.filter((c) => c.enabled).length}
          sublabel={`of ${spiders.length} total`}
        />
        <StatCard
          label="Last Sync"
          value={lastSync ? formatTimestamp(lastSync) : 'Never'}
        />
      </div>

      {/* Source breakdown */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">By Source</h3>
        <div className="space-y-2">
          {bySource.map(({ name, count }) => (
            <div key={name} className="flex items-center justify-between">
              <span className="text-sm text-gray-600">{name}</span>
              <span className="text-sm font-medium text-gray-900">
                {count.toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
