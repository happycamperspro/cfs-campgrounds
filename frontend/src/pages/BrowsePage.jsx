import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useFilters } from '../context/FilterContext';
import { useCampgrounds } from '../hooks/useCampgrounds';
import { REGIONS } from '../lib/constants';
import { pluralize } from '../lib/utils';
import CampgroundGrid from '../components/campground/CampgroundGrid';
import FilterPanel from '../components/filters/FilterPanel';
import LoadingSpinner from '../components/ui/LoadingSpinner';

export default function BrowsePage() {
  const [searchParams] = useSearchParams();
  const { filters, setFilters, resetFilters } = useFilters();
  const { campgrounds, loading, error, hasMore, loadMore, total } = useCampgrounds();
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Apply region from URL query params
  useEffect(() => {
    const region = searchParams.get('region');
    if (region && REGIONS[region]) {
      setFilters((prev) => ({ ...prev, region, states: [] }));
    }
  }, [searchParams, setFilters]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Browse Campgrounds</h1>
          {!loading && (
            <p className="text-sm text-gray-500 mt-1">
              {total !== undefined
                ? `${pluralize(total, 'campground')} found`
                : `${pluralize(campgrounds.length, 'campground')} loaded`}
            </p>
          )}
        </div>

        {/* Mobile filter button */}
        <button
          type="button"
          className="lg:hidden btn-outline flex items-center gap-2"
          onClick={() => setDrawerOpen(true)}
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
          </svg>
          Filters
        </button>
      </div>

      <div className="flex gap-8">
        {/* Desktop sidebar */}
        <aside className="hidden lg:block w-72 flex-shrink-0">
          <div className="sticky top-20">
            <FilterPanel />
          </div>
        </aside>

        {/* Mobile filter drawer */}
        {drawerOpen && (
          <div className="fixed inset-0 z-50 lg:hidden">
            <div
              className="absolute inset-0 bg-black/40"
              onClick={() => setDrawerOpen(false)}
            />
            <div className="absolute inset-y-0 left-0 w-80 max-w-full bg-white shadow-xl overflow-y-auto">
              <div className="flex items-center justify-between p-4 border-b border-gray-200">
                <h2 className="text-lg font-semibold">Filters</h2>
                <button
                  type="button"
                  className="p-1 text-gray-500 hover:text-gray-700"
                  onClick={() => setDrawerOpen(false)}
                >
                  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <div className="p-4">
                <FilterPanel onApply={() => setDrawerOpen(false)} />
              </div>
            </div>
          </div>
        )}

        {/* Main content */}
        <div className="flex-1 min-w-0">
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
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <h3 className="mt-4 text-lg font-medium text-gray-900">No campgrounds found</h3>
              <p className="mt-2 text-gray-500">
                Try adjusting your filters or search criteria.
              </p>
              <button
                type="button"
                className="mt-4 btn-primary"
                onClick={resetFilters}
              >
                Reset Filters
              </button>
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
      </div>
    </div>
  );
}
