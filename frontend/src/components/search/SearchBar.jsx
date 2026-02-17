import { useState, useCallback } from 'react';
import { useSearch } from '../../hooks/useSearch';
import SearchResults from './SearchResults';

export default function SearchBar({ onSearch }) {
  const { query, setQuery, results, loading } = useSearch();
  const [showResults, setShowResults] = useState(true);

  const handleChange = (e) => {
    setQuery(e.target.value);
    setShowResults(true);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      setQuery('');
      setShowResults(false);
      e.target.blur();
    }
  };

  const handleClose = useCallback(() => {
    setShowResults(false);
    onSearch?.();
  }, [onSearch]);

  return (
    <div className="relative">
      <div className="relative">
        {/* Search icon */}
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>

        <input
          type="text"
          value={query}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onFocus={() => setShowResults(true)}
          placeholder="Search campgrounds..."
          className="w-full pl-10 pr-4 py-2 text-sm rounded-lg border border-gray-300 bg-gray-50 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-campfire-500 focus:border-campfire-500 focus:bg-white transition-colors"
        />

        {/* Loading indicator */}
        {loading && (
          <svg
            className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 animate-spin"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        )}
      </div>

      {/* Dropdown results */}
      {showResults && query.trim() && results.length > 0 && (
        <SearchResults results={results} onClose={handleClose} />
      )}
    </div>
  );
}
