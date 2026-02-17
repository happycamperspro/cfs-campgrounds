import { US_STATES } from '../../lib/constants';
import { useFilters, useFilterDispatch, SET_STATE } from '../../context/FilterContext';

export default function StateFilter() {
  const { state } = useFilters();
  const dispatch = useFilterDispatch();

  return (
    <div>
      <label htmlFor="state-filter" className="block text-sm font-medium text-gray-700 mb-1">
        State
      </label>
      <select
        id="state-filter"
        value={state}
        onChange={(e) => dispatch({ type: SET_STATE, payload: e.target.value })}
        className="w-full rounded-lg border-gray-300 shadow-sm text-sm focus:border-campfire-500 focus:ring-campfire-500"
      >
        <option value="">All States</option>
        {Object.entries(US_STATES).map(([code, name]) => (
          <option key={code} value={code}>
            {name}
          </option>
        ))}
      </select>
    </div>
  );
}
