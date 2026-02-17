import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useScraperConfigs } from '../../hooks/useScraperConfigs';
import { useScraperRuns } from '../../hooks/useScraperRuns';
import { SOURCE_LABELS, SOURCE_COLORS } from '../../lib/constants';
import LoadingSpinner from '../../components/ui/LoadingSpinner';

function StatCard({ label, value, subtext, color = 'campfire' }) {
  const colorClasses = {
    campfire: 'bg-campfire-50 text-campfire-700 border-campfire-200',
    forest: 'bg-forest-50 text-forest-700 border-forest-200',
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    purple: 'bg-purple-50 text-purple-700 border-purple-200',
  };

  return (
    <div className={`rounded-xl border p-5 ${colorClasses[color] || colorClasses.campfire}`}>
      <p className="text-sm font-medium opacity-80">{label}</p>
      <p className="text-3xl font-bold mt-1">{value}</p>
      {subtext && <p className="text-xs mt-1 opacity-70">{subtext}</p>}
    </div>
  );
}

function SpiderCard({ config, latestRun }) {
  const sourceColor = SOURCE_COLORS[config.name] || 'bg-gray-100 text-gray-800';
  const statusColor = config.enabled
    ? 'bg-green-100 text-green-800'
    : 'bg-gray-100 text-gray-600';

  return (
    <Link
      to={`/admin/scrapers/${config.name}`}
      className="card p-4 hover:border-campfire-300 transition-colors"
    >
      <div className="flex items-start justify-between">
        <div>
          <span className={`badge ${sourceColor}`}>
            {SOURCE_LABELS[config.name] || config.name}
          </span>
          <span className={`badge ml-2 ${statusColor}`}>
            {config.enabled ? 'Active' : 'Disabled'}
          </span>
        </div>
      </div>
      <div className="mt-3 text-sm text-gray-600">
        {config.schedule && (
          <p>Schedule: <span className="font-medium">{config.schedule}</span></p>
        )}
        {config.states && config.states.length > 0 && (
          <p className="mt-1">
            States: <span className="font-medium">{config.states.join(', ')}</span>
          </p>
        )}
      </div>
      {latestRun && (
        <div className="mt-3 pt-3 border-t border-gray-100 text-xs text-gray-500">
          <p>
            Last run:{' '}
            <span className="font-medium">
              {latestRun.started_at?.toDate
                ? latestRun.started_at.toDate().toLocaleString()
                : 'N/A'}
            </span>
          </p>
          <p className="mt-0.5">
            Status:{' '}
            <span
              className={`font-medium ${
                latestRun.status === 'completed' ? 'text-green-600' :
                latestRun.status === 'failed' ? 'text-red-600' :
                'text-yellow-600'
              }`}
            >
              {latestRun.status}
            </span>
            {latestRun.items_found !== undefined && (
              <span className="ml-2">
                ({latestRun.items_found} found / {latestRun.items_loaded || 0} loaded)
              </span>
            )}
          </p>
        </div>
      )}
    </Link>
  );
}

export default function DashboardPage() {
  const { configs, loading: configsLoading } = useScraperConfigs();
  const { runs, loading: runsLoading } = useScraperRuns({ limit: 50 });

  const loading = configsLoading || runsLoading;

  // Compute stats
  const stats = useMemo(() => {
    const activeSpiders = configs.filter((c) => c.enabled).length;
    const totalSpiders = configs.length;

    // Latest run per spider
    const latestBySpider = {};
    for (const run of runs) {
      if (!latestBySpider[run.spider_name]) {
        latestBySpider[run.spider_name] = run;
      }
    }

    const recentRuns = runs.slice(0, 10);
    const failedRecent = recentRuns.filter((r) => r.status === 'failed').length;

    return { activeSpiders, totalSpiders, latestBySpider, recentRuns, failedRecent };
  }, [configs, runs]);

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">Manage scrapers and monitor data collection</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Total Sources"
          value={stats.totalSpiders}
          subtext={`${stats.activeSpiders} active`}
          color="campfire"
        />
        <StatCard
          label="Active Spiders"
          value={stats.activeSpiders}
          subtext={`of ${stats.totalSpiders} total`}
          color="forest"
        />
        <StatCard
          label="Recent Runs"
          value={stats.recentRuns.length}
          subtext="last 10 runs"
          color="blue"
        />
        <StatCard
          label="Recent Failures"
          value={stats.failedRecent}
          subtext="in last 10 runs"
          color="purple"
        />
      </div>

      {/* Quick actions */}
      <div className="flex flex-wrap gap-3 mb-8">
        <Link to="/admin/scrapers" className="btn-primary">
          Manage Scrapers
        </Link>
        <Link to="/admin/runs" className="btn-outline">
          View Run History
        </Link>
      </div>

      {/* Spider cards */}
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Data Sources</h2>
        <p className="text-sm text-gray-500">All configured spider sources</p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {configs.map((config) => (
          <SpiderCard
            key={config.name || config.id}
            config={config}
            latestRun={stats.latestBySpider[config.name]}
          />
        ))}
        {configs.length === 0 && (
          <p className="text-gray-500 col-span-full text-center py-8">
            No spider configurations found.
          </p>
        )}
      </div>
    </div>
  );
}
