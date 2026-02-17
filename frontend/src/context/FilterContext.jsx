import React, { createContext, useContext, useReducer } from 'react';

// --- Action types ---
const SET_STATE = 'SET_STATE';
const SET_REGION = 'SET_REGION';
const TOGGLE_SITE_TYPE = 'TOGGLE_SITE_TYPE';
const TOGGLE_HOOKUP = 'TOGGLE_HOOKUP';
const TOGGLE_FACILITY = 'TOGGLE_FACILITY';
const TOGGLE_ACTIVITY = 'TOGGLE_ACTIVITY';
const SET_PETS = 'SET_PETS';
const SET_ACCESSIBLE = 'SET_ACCESSIBLE';
const SET_MANAGED_BY = 'SET_MANAGED_BY';
const SET_SORT = 'SET_SORT';
const RESET_ALL = 'RESET_ALL';

// --- Initial state ---
const initialState = {
  state: '',
  region: '',
  siteTypes: [],
  hookups: [],
  facilities: [],
  activities: [],
  petsAllowed: null,
  accessible: null,
  managedBy: '',
  sortBy: 'name',
};

/**
 * Toggle helper: if value is in array remove it, otherwise add it.
 */
function toggleInArray(arr, value) {
  return arr.includes(value) ? arr.filter((v) => v !== value) : [...arr, value];
}

// --- Reducer ---
function filterReducer(state, action) {
  switch (action.type) {
    case SET_STATE:
      return { ...state, state: action.payload };
    case SET_REGION:
      return { ...state, region: action.payload };
    case TOGGLE_SITE_TYPE:
      return { ...state, siteTypes: toggleInArray(state.siteTypes, action.payload) };
    case TOGGLE_HOOKUP:
      return { ...state, hookups: toggleInArray(state.hookups, action.payload) };
    case TOGGLE_FACILITY:
      return { ...state, facilities: toggleInArray(state.facilities, action.payload) };
    case TOGGLE_ACTIVITY:
      return { ...state, activities: toggleInArray(state.activities, action.payload) };
    case SET_PETS:
      return { ...state, petsAllowed: action.payload };
    case SET_ACCESSIBLE:
      return { ...state, accessible: action.payload };
    case SET_MANAGED_BY:
      return { ...state, managedBy: action.payload };
    case SET_SORT:
      return { ...state, sortBy: action.payload };
    case RESET_ALL:
      return { ...initialState };
    default:
      return state;
  }
}

// --- Context ---
const FilterContext = createContext(null);
const FilterDispatchContext = createContext(null);

/**
 * Provider that wraps children with filter state and dispatch.
 */
export function FilterProvider({ children }) {
  const [state, dispatch] = useReducer(filterReducer, initialState);

  return (
    <FilterContext.Provider value={state}>
      <FilterDispatchContext.Provider value={dispatch}>
        {children}
      </FilterDispatchContext.Provider>
    </FilterContext.Provider>
  );
}

/**
 * Hook to read current filter state.
 */
export function useFilters() {
  const context = useContext(FilterContext);
  if (context === null) {
    throw new Error('useFilters must be used within a FilterProvider');
  }
  return context;
}

/**
 * Hook to get the filter dispatch function.
 */
export function useFilterDispatch() {
  const context = useContext(FilterDispatchContext);
  if (context === null) {
    throw new Error('useFilterDispatch must be used within a FilterProvider');
  }
  return context;
}

// Export action types for consumers
export {
  SET_STATE,
  SET_REGION,
  TOGGLE_SITE_TYPE,
  TOGGLE_HOOKUP,
  TOGGLE_FACILITY,
  TOGGLE_ACTIVITY,
  SET_PETS,
  SET_ACCESSIBLE,
  SET_MANAGED_BY,
  SET_SORT,
  RESET_ALL,
};
