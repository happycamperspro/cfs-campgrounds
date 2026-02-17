import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useScraperConfigs } from '../../hooks/useScraperConfigs';
import { useAdminActions } from '../../hooks/useAdminActions';
import { SOURCE_LABELS, US_STATES } from '../../lib/constants';
import LoadingSpinner from '../../components/ui/LoadingSpinner';

function SpiderConfigRow({ config, onToggle, onRunNow, onUpdateConfig, running }) {
  const [expanded, setExpanded] = useState(false);
  const [schedule, setSchedule] = useState(config.schedule || 'daily');
  const [stateFilter, setStateFilter] = useState(config.states?.join(', ') || '');
  const [itemLimit, setItemLimit] = useState(config.item_limit || 0);

  function handleSaveConfig() {
    const states = stateFilter
      .split(',')
      .map((s) => s.trim().toUpperCase())
      .filter((s) => US_STATES[s]);

    onUpdateConfig(config.name, {
      schedule,
      states,
      item_limit: parseInt(itemLimit, 10) || 0,
    });
  }

  return (
    <div className="card">
      <div className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setExpanded(!expanded)}
              className="text-gray-400 hover:text-gray-600 transition-colors"
              aria-label={expanded ? 'Collapse' : 'Expand'}
            >
              <svg
                className={`h-5 w-5 transition-transform ${expanded ? 'rotate-90' : ''}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
            <div>
              <Link
                to={`/admin/scrapers/${config.name}`}
                className="font-semibold text-gray-900 hover:text-campfire-600 transition-colors"
              >
                {SOURCE_LABELS[config.name] || config.name}
              </Link>
              <p className="text-xs text-gray-500 mt-0.5">
                {config.schedule || 'No schedule'} | {config.states?.length || 0} states
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Enable/Disable toggle */}
            <button
              type="button"
              role="switch"
              aria-checked={config.enabled}
              onClick={() => onToggle(config.name, !config.enabled)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                config.enabled ? 'bg-forest-500' : 'bg-gray-300'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
                  config.enabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>

            {/* Run Now button */}
            <button
              type="button"
              className="btn-primary text-sm px-3 py-1.5 flex items-center gap-1.5 disabled:opacity-50"
              onClick={() => onRunNow(config.name)}
              disabled={running === config.name}
            >
              {running === config.name ? (
                <>
                  <LoadingSpinner size="sm" />
                  Running...
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
        </div>
      </div>

      {/* Expanded config */}
      {expanded && (
        <div className="border-t border-gray-100 p-4 bg-gray-50 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Schedule
              </label>
              <select
                value={schedule}
                onChange={(e) => setSchedule(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-campfire-500 focus:border-campfire-500 outline-none"
              >
                <option value="hourly">Hourly</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="manual">Manual Only</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                State Filter (comma-separated)
              </label>
              <input
                type="text"
                value={stateFilter}
                onChange={(e) => setStateFilter(e.target.value)}
                placeholder="CA, OR, WA"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-campfire-500 focus:border-campfire-500 outline-none"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Item Limit (0 = unlimited)
              </label>
              <input
                type="number"
                value={itemLimit}
                onChange={(e) => setItemLimit(e.target.value)}
                min="0"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-campfire-500 focus:border-campfire-500 outline-none"
              />
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="button"
              className="btn-primary text-sm"
              onClick={handleSaveConfig}
            >
              Save Configuration
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ScrapersPage() {
  const { configs, loading, updateConfig, toggleEnabled } = useScraperConfigs();
  const { runSpider, running } = useAdminActions();

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <nav className="text-sm text-gray-500 mb-2">
            <Link to="/admin" className="hover:text-campfire-600 transition-colors">Dashboard</Link>
            <span className="mx-2">/</span>
            <span className="text-gray-900 font-medium">Scrapers</span>
          </nav>
          <h1 className="text-2xl font-bold text-gray-900">Spider Configurations</h1>
          <p className="text-sm text-gray-500 mt-1">
            Manage and run data collection spiders
          </p>
        </div>
        <Link to="/admin/runs" className="btn-outline text-sm">
          Run History
        </Link>
      </div>

      {/* Spider list */}
      <div className="space-y-3">
        {configs.map((config) => (
          <SpiderConfigRow
            key={config.name || config.id}
            config={config}
            onToggle={toggleEnabled}
            onRunNow={runSpider}
            onUpdateConfig={updateConfig}
            running={running}
          />
        ))}
        {configs.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            No spider configurations found.
          </div>
        )}
      </div>
    </div>
  );
}
