import {
  useFilters,
  useFilterDispatch,
  SET_STATE,
  SET_REGION,
  TOGGLE_SITE_TYPE,
  TOGGLE_HOOKUP,
  TOGGLE_FACILITY,
  TOGGLE_ACTIVITY,
  SET_PETS,
  SET_ACCESSIBLE,
} from '../../context/FilterContext';
import { US_STATES } from '../../lib/constants';

export default function ActiveFilters() {
  const filters = useFilters();
  const dispatch = useFilterDispatch();

  const chips = [];

  if (filters.state) {
    chips.push({
      key: 'state',
      label: US_STATES[filters.state] || filters.state,
      onRemove: () => dispatch({ type: SET_STATE, payload: '' }),
    });
  }

  if (filters.region) {
    chips.push({
      key: 'region',
      label: filters.region,
      onRemove: () => dispatch({ type: SET_REGION, payload: '' }),
    });
  }

  filters.siteTypes.forEach((st) => {
    chips.push({
      key: `siteType-${st}`,
      label: st,
      onRemove: () => dispatch({ type: TOGGLE_SITE_TYPE, payload: st }),
    });
  });

  filters.hookups.forEach((h) => {
    chips.push({
      key: `hookup-${h}`,
      label: h,
      onRemove: () => dispatch({ type: TOGGLE_HOOKUP, payload: h }),
    });
  });

  filters.facilities.forEach((f) => {
    chips.push({
      key: `facility-${f}`,
      label: f,
      onRemove: () => dispatch({ type: TOGGLE_FACILITY, payload: f }),
    });
  });

  filters.activities.forEach((a) => {
    chips.push({
      key: `activity-${a}`,
      label: a,
      onRemove: () => dispatch({ type: TOGGLE_ACTIVITY, payload: a }),
    });
  });

  if (filters.petsAllowed !== null) {
    chips.push({
      key: 'pets',
      label: filters.petsAllowed ? 'Pets Allowed' : 'No Pets',
      onRemove: () => dispatch({ type: SET_PETS, payload: null }),
    });
  }

  if (filters.accessible !== null) {
    chips.push({
      key: 'accessible',
      label: filters.accessible ? 'Accessible' : 'Not Accessible',
      onRemove: () => dispatch({ type: SET_ACCESSIBLE, payload: null }),
    });
  }

  if (chips.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2 py-2">
      {chips.map((chip) => (
        <span
          key={chip.key}
          className="inline-flex items-center gap-1 badge bg-campfire-50 text-campfire-700 border border-campfire-200"
        >
          {chip.label}
          <button
            type="button"
            onClick={chip.onRemove}
            className="ml-0.5 hover:text-campfire-900 transition-colors"
            aria-label={`Remove ${chip.label} filter`}
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </span>
      ))}
    </div>
  );
}
