import { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { getStateName } from '../../lib/utils';

export default function SearchResults({ results, onClose }) {
  const ref = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (ref.current && !ref.current.contains(event.target)) {
        onClose?.();
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  if (!results || results.length === 0) return null;

  return (
    <div
      ref={ref}
      className="absolute top-full left-0 right-0 mt-1 bg-white rounded-lg shadow-lg border border-gray-200 z-50 overflow-hidden max-h-96 overflow-y-auto"
    >
      <ul>
        {results.slice(0, 8).map((result) => (
          <li key={result.id}>
            <Link
              to={`/campground/${result.slug}`}
              onClick={onClose}
              className="block px-4 py-3 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0"
            >
              <p className="text-sm font-medium text-gray-900 line-clamp-1">
                {result.name}
              </p>
              {result.location && (
                <p className="text-xs text-gray-500 mt-0.5">
                  {result.location.city}
                  {result.location.city && result.location.state ? ', ' : ''}
                  {result.location.state ? getStateName(result.location.state) : ''}
                </p>
              )}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
