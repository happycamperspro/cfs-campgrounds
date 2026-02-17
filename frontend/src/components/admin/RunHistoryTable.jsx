import { useState, useMemo } from 'react';
import RunStatusBadge from './RunStatusBadge';

function formatTimestamp(ts) {
  if (!ts) return '-';
  const date = ts.toDate ? ts.toDate() : new Date(ts);
  return date.toLocaleString();
}

function formatDuration(startTs, endTs) {
  if (!startTs || !endTs) return '-';
  const start = startTs.toDate ? startTs.toDate() : new Date(startTs);
  const end = endTs.toDate ? endTs.toDate() : new Date(endTs);
  const diffMs = end - start;

  if (diffMs < 1000) return '<1s';
  if (diffMs < 60000) return `${Math.round(diffMs / 1000)}s`;
  const minutes = Math.floor(diffMs / 60000);
  const seconds = Math.round((diffMs % 60000) / 1000);
  return `${minutes}m ${seconds}s`;
}

const SORTABLE_COLUMNS = ['spider', 'started_at', 'status'];

export default function RunHistoryTable({ runs = [] }) {
  const [sortColumn, setSortColumn] = useState('started_at');
  const [sortDirection, setSortDirection] = useState('desc');

  const handleSort = (column) => {
    if (!SORTABLE_COLUMNS.includes(column)) return;
    if (sortColumn === column) {
      setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortColumn(column);
      setSortDirection('desc');
    }
  };

  const sortedRuns = useMemo(() => {
    const sorted = [...runs].sort((a, b) => {
      let aVal, bVal;

      switch (sortColumn) {
        case 'spider':
          aVal = a.spider_name || a.spider || '';
          bVal = b.spider_name || b.spider || '';
          return sortDirection === 'asc'
            ? aVal.localeCompare(bVal)
            : bVal.localeCompare(aVal);
        case 'started_at': {
          const aTs = a.started_at?.toDate ? a.started_at.toDate() : new Date(a.started_at || 0);
          const bTs = b.started_at?.toDate ? b.started_at.toDate() : new Date(b.started_at || 0);
          return sortDirection === 'asc' ? aTs - bTs : bTs - aTs;
        }
        case 'status':
          aVal = a.status || '';
          bVal = b.status || '';
          return sortDirection === 'asc'
            ? aVal.localeCompare(bVal)
            : bVal.localeCompare(aVal);
        default:
          return 0;
      }
    });
    return sorted;
  }, [runs, sortColumn, sortDirection]);

  const SortIcon = ({ column }) => {
    if (sortColumn !== column) {
      return (
        <svg className="inline h-3 w-3 ml-1 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8l5-5 5 5M7 16l5 5 5-5" />
        </svg>
      );
    }
    return (
      <svg className="inline h-3 w-3 ml-1 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d={sortDirection === 'asc' ? 'M5 15l7-7 7 7' : 'M19 9l-7 7-7-7'}
        />
      </svg>
    );
  };

  if (runs.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 text-sm">
        No run history available.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th
              className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700"
              onClick={() => handleSort('spider')}
            >
              Spider <SortIcon column="spider" />
            </th>
            <th
              className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700"
              onClick={() => handleSort('started_at')}
            >
              Started <SortIcon column="started_at" />
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Duration
            </th>
            <th
              className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700"
              onClick={() => handleSort('status')}
            >
              Status <SortIcon column="status" />
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Found / Loaded
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Errors
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {sortedRuns.map((run, index) => (
            <tr key={run.id || index} className="hover:bg-gray-50">
              <td className="px-4 py-3 text-sm font-medium text-gray-900 whitespace-nowrap">
                {run.spider_name || run.spider || '-'}
              </td>
              <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">
                {formatTimestamp(run.started_at)}
              </td>
              <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">
                {formatDuration(run.started_at, run.finished_at)}
              </td>
              <td className="px-4 py-3 whitespace-nowrap">
                <RunStatusBadge status={run.status} />
              </td>
              <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">
                {run.items_found ?? 0} / {run.items_loaded ?? 0}
              </td>
              <td className="px-4 py-3 text-sm whitespace-nowrap">
                {run.error_count > 0 ? (
                  <span className="text-red-600 font-medium">{run.error_count}</span>
                ) : (
                  <span className="text-gray-400">0</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
