import { useState } from 'react';
import {
  useFilters,
  useFilterDispatch,
  RESET_ALL,
  SET_PETS,
  SET_ACCESSIBLE,
  TOGGLE_SITE_TYPE,
} from '../../context/FilterContext';
import {
  SITE_TYPES,
  HOOKUP_TYPES,
  FACILITY_TYPES,
  ACTIVITY_TYPES,
} from '../../lib/constants';
import StateFilter from './StateFilter';
import RegionFilter from './RegionFilter';
import AmenityFilter from './AmenityFilter';

function FilterSection({ title, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="border-b border-gray-200 py-4">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center justify-between w-full text-left"
      >
        <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
        <svg
          className={`h-4 w-4 text-gray-500 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && <div className="mt-3">{children}</div>}
    </div>
  );
}

function SiteTypeFilter() {
  const { siteTypes } = useFilters();
  const dispatch = useFilterDispatch();

  return (
    <div className="space-y-2">
      {SITE_TYPES.map(({ value, label }) => (
        <label key={value} className="flex items-center gap-2 cursor-pointer group">
          <input
            type="checkbox"
            checked={siteTypes.includes(value)}
            onChange={() => dispatch({ type: TOGGLE_SITE_TYPE, payload: value })}
            className="rounded border-gray-300 text-campfire-500 focus:ring-campfire-500"
          />
          <span className="text-sm text-gray-600 group-hover:text-gray-900">{label}</span>
        </label>
      ))}
    </div>
  );
}

function OtherFilters() {
  const { petsAllowed, accessible } = useFilters();
  const dispatch = useFilterDispatch();

  return (
    <div className="space-y-2">
      <label className="flex items-center gap-2 cursor-pointer group">
        <input
          type="checkbox"
          checked={petsAllowed === true}
          onChange={() =>
            dispatch({ type: SET_PETS, payload: petsAllowed === true ? null : true })
          }
          className="rounded border-gray-300 text-campfire-500 focus:ring-campfire-500"
        />
        <span className="text-sm text-gray-600 group-hover:text-gray-900">Pets Allowed</span>
      </label>
      <label className="flex items-center gap-2 cursor-pointer group">
        <input
          type="checkbox"
          checked={accessible === true}
          onChange={() =>
            dispatch({ type: SET_ACCESSIBLE, payload: accessible === true ? null : true })
          }
          className="rounded border-gray-300 text-campfire-500 focus:ring-campfire-500"
        />
        <span className="text-sm text-gray-600 group-hover:text-gray-900">Wheelchair Accessible</span>
      </label>
    </div>
  );
}

function FilterPanelContent() {
  const filters = useFilters();
  const dispatch = useFilterDispatch();

  // Count active filters
  let activeCount = 0;
  if (filters.state) activeCount++;
  if (filters.region) activeCount++;
  activeCount += filters.siteTypes.length;
  activeCount += filters.hookups.length;
  activeCount += filters.facilities.length;
  activeCount += filters.activities.length;
  if (filters.petsAllowed !== null) activeCount++;
  if (filters.accessible !== null) activeCount++;

  return (
    <div>
      <div className="flex items-center justify-between mb-2 px-1">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-bold text-gray-900">Filters</h2>
          {activeCount > 0 && (
            <span className="badge bg-campfire-500 text-white">{activeCount}</span>
          )}
        </div>
        {activeCount > 0 && (
          <button
            type="button"
            onClick={() => dispatch({ type: RESET_ALL })}
            className="text-sm text-campfire-600 hover:text-campfire-700 font-medium"
          >
            Clear All
          </button>
        )}
      </div>

      <FilterSection title="State">
        <StateFilter />
      </FilterSection>

      <FilterSection title="Region">
        <RegionFilter />
      </FilterSection>

      <FilterSection title="Site Types">
        <SiteTypeFilter />
      </FilterSection>

      <FilterSection title="Hookups">
        <AmenityFilter type="hookups" options={HOOKUP_TYPES} />
      </FilterSection>

      <FilterSection title="Facilities">
        <AmenityFilter type="facilities" options={FACILITY_TYPES} />
      </FilterSection>

      <FilterSection title="Activities">
        <AmenityFilter type="activities" options={ACTIVITY_TYPES} />
      </FilterSection>

      <FilterSection title="Other">
        <OtherFilters />
      </FilterSection>
    </div>
  );
}

export default function FilterPanel() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      {/* Mobile toggle button */}
      <button
        type="button"
        onClick={() => setMobileOpen(true)}
        className="lg:hidden btn-outline inline-flex items-center gap-2 mb-4"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
        </svg>
        Filters
      </button>

      {/* Desktop sidebar */}
      <aside className="hidden lg:block w-64 flex-shrink-0">
        <div className="sticky top-20">
          <FilterPanelContent />
        </div>
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          {/* Overlay */}
          <div
            className="fixed inset-0 bg-black/40"
            onClick={() => setMobileOpen(false)}
          />

          {/* Drawer */}
          <div className="fixed inset-y-0 left-0 w-80 max-w-full bg-white shadow-xl overflow-y-auto">
            <div className="p-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold text-gray-900">Filters</h2>
                <button
                  type="button"
                  onClick={() => setMobileOpen(false)}
                  className="p-2 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100"
                  aria-label="Close filters"
                >
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <FilterPanelContent />
            </div>
          </div>
        </div>
      )}
    </>
  );
}
