import { REGIONS } from '../../lib/constants';
import { useFilters, useFilterDispatch, SET_REGION } from '../../context/FilterContext';

export default function RegionFilter() {
  const { region } = useFilters();
  const dispatch = useFilterDispatch();

  const regionNames = Object.keys(REGIONS);

  return (
    <div>
      <h4 className="text-sm font-medium text-gray-700 mb-2">Region</h4>
      <div className="flex flex-wrap gap-2">
        {regionNames.map((name) => {
          const isActive = region === name;
          return (
            <button
              key={name}
              type="button"
              onClick={() =>
                dispatch({ type: SET_REGION, payload: isActive ? '' : name })
              }
              className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                isActive
                  ? 'bg-campfire-500 text-white border-campfire-500'
                  : 'bg-white text-gray-600 border-gray-300 hover:border-campfire-300 hover:text-campfire-600'
              }`}
            >
              {name}
            </button>
          );
        })}
      </div>
    </div>
  );
}
