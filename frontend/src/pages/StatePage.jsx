import { useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useFilters } from '../context/FilterContext';
import { useCampgrounds } from '../hooks/useCampgrounds';
import { US_STATES } from '../lib/constants';
import { pluralize } from '../lib/utils';
import CampgroundGrid from '../components/campground/CampgroundGrid';
import LoadingSpinner from '../components/ui/LoadingSpinner';

export default function StatePage() {
  const { state } = useParams();
  const { setFilters, resetFilters } = useFilters();
  const { campgrounds, loading, error, hasMore, loadMore } = useCampgrounds();

  const stateCode = state?.toUpperCase();
  const stateName = US_STATES[stateCode] || stateCode;

  // Set the state filter when the page mounts or state param changes
  useEffect(() => {
    if (stateCode) {
      setFilters((prev) => ({
        ...prev,
        states: [stateCode],
        region: '',
      }));
    }

    return () => {
      // Clean up the state filter when leaving the page
      resetFilters();
    };
  }, [stateCode, setFilters, resetFilters]);

  if (!stateCode || !US_STATES[stateCode]) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">State Not Found</h1>
        <p className="text-gray-600 mb-6">
          The state code &ldquo;{state}&rdquo; is not recognized.
        </p>
        <Link to="/browse" className="btn-primary">
          Browse All Campgrounds
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      {/* Breadcrumb */}
      <nav className="mb-4 text-sm text-gray-500">
        <Link to="/" className="hover:text-campfire-600 transition-colors">Home</Link>
        <span className="mx-2">/</span>
        <Link to="/browse" className="hover:text-campfire-600 transition-colors">Browse</Link>
        <span className="mx-2">/</span>
        <span className="text-gray-900 font-medium">{stateName}</span>
      </nav>

      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          Campgrounds in {stateName}
        </h1>
        {!loading && (
          <p className="text-gray-500 mt-2">
            {pluralize(campgrounds.length, 'campground')} found
          </p>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 mb-6">
          <p className="font-medium">Error loading campgrounds</p>
          <p className="text-sm mt-1">{error.message || 'Please try again later.'}</p>
        </div>
      )}

      {loading && campgrounds.length === 0 ? (
        <div className="flex justify-center py-20">
          <LoadingSpinner size="lg" />
        </div>
      ) : campgrounds.length === 0 ? (
        <div className="text-center py-20">
          <svg className="mx-auto h-12 w-12 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 21h18M5 21V7l7-4 7 4v14" />
          </svg>
          <h3 className="mt-4 text-lg font-medium text-gray-900">No campgrounds yet</h3>
          <p className="mt-2 text-gray-500">
            We don&apos;t have any campgrounds listed for {stateName} yet.
          </p>
          <Link to="/browse" className="mt-4 inline-block btn-primary">
            Browse All States
          </Link>
        </div>
      ) : (
        <>
          <CampgroundGrid campgrounds={campgrounds} />

          {hasMore && (
            <div className="mt-8 flex justify-center">
              <button
                type="button"
                className="btn-outline px-8 py-3"
                onClick={loadMore}
                disabled={loading}
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <LoadingSpinner size="sm" />
                    Loading...
                  </span>
                ) : (
                  'Load More'
                )}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
