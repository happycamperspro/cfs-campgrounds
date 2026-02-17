const SCHEDULE_OPTIONS = [
  { value: 'manual', label: 'Manual' },
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'monthly', label: 'Monthly' },
];

export default function ScheduleSelector({ value, onChange }) {
  return (
    <div>
      <label htmlFor="schedule-select" className="block text-sm font-medium text-gray-700 mb-1">
        Schedule
      </label>
      <select
        id="schedule-select"
        value={value || 'manual'}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border-gray-300 shadow-sm text-sm focus:border-campfire-500 focus:ring-campfire-500"
      >
        {SCHEDULE_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
