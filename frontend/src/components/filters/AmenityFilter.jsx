import {
  useFilters,
  useFilterDispatch,
  TOGGLE_HOOKUP,
  TOGGLE_FACILITY,
  TOGGLE_ACTIVITY,
} from '../../context/FilterContext';

const DISPATCH_TYPES = {
  hookups: TOGGLE_HOOKUP,
  facilities: TOGGLE_FACILITY,
  activities: TOGGLE_ACTIVITY,
};

export default function AmenityFilter({ type, options }) {
  const filters = useFilters();
  const dispatch = useFilterDispatch();

  const selected = filters[type] || [];
  const actionType = DISPATCH_TYPES[type];

  if (!actionType) return null;

  return (
    <div className="space-y-2">
      {options.map(({ value, label }) => (
        <label
          key={value}
          className="flex items-center gap-2 cursor-pointer group"
        >
          <input
            type="checkbox"
            checked={selected.includes(value)}
            onChange={() => dispatch({ type: actionType, payload: value })}
            className="rounded border-gray-300 text-campfire-500 focus:ring-campfire-500"
          />
          <span className="text-sm text-gray-600 group-hover:text-gray-900">
            {label}
          </span>
        </label>
      ))}
    </div>
  );
}
