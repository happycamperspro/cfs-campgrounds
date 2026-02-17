import { useState, useRef, useEffect } from 'react';
import { US_STATES } from '../../lib/constants';

export default function StateMultiSelect({ selected = [], onChange }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (ref.current && !ref.current.contains(event.target)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const toggleState = (code) => {
    const next = selected.includes(code)
      ? selected.filter((s) => s !== code)
      : [...selected, code];
    onChange(next);
  };

  const selectAll = () => onChange(Object.keys(US_STATES));
  const clearAll = () => onChange([]);

  return (
    <div ref={ref} className="relative">
      <label className="block text-sm font-medium text-gray-700 mb-1">
        Target States
      </label>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full text-left rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-campfire-500 focus:border-campfire-500"
      >
        {selected.length === 0
          ? 'Select states...'
          : selected.length === Object.keys(US_STATES).length
          ? 'All states'
          : `${selected.length} state${selected.length > 1 ? 's' : ''} selected`}
        <svg
          className={`float-right h-4 w-4 text-gray-500 transition-transform mt-0.5 ${open ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute z-20 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-64 overflow-y-auto">
          <div className="sticky top-0 bg-white border-b border-gray-100 px-3 py-2 flex gap-2">
            <button
              type="button"
              onClick={selectAll}
              className="text-xs text-campfire-600 hover:text-campfire-700 font-medium"
            >
              Select All
            </button>
            <span className="text-gray-300">|</span>
            <button
              type="button"
              onClick={clearAll}
              className="text-xs text-gray-500 hover:text-gray-700 font-medium"
            >
              Clear
            </button>
          </div>
          {Object.entries(US_STATES).map(([code, name]) => (
            <label
              key={code}
              className="flex items-center gap-2 px-3 py-1.5 hover:bg-gray-50 cursor-pointer"
            >
              <input
                type="checkbox"
                checked={selected.includes(code)}
                onChange={() => toggleState(code)}
                className="rounded border-gray-300 text-campfire-500 focus:ring-campfire-500"
              />
              <span className="text-sm text-gray-700">{name}</span>
              <span className="text-xs text-gray-400 ml-auto">{code}</span>
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
