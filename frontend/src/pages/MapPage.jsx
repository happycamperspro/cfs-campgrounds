import { lazy, Suspense } from 'react';
import LoadingSpinner from '../components/ui/LoadingSpinner';

const CampgroundMap = lazy(() => import('../components/map/CampgroundMap'));

export default function MapPage() {
  return (
    <div className="flex flex-col" style={{ height: 'calc(100vh - 4rem)' }}>
      <div className="px-4 sm:px-6 lg:px-8 py-3 bg-white border-b border-gray-200">
        <h1 className="text-lg font-semibold text-gray-900">Campground Map</h1>
        <p className="text-sm text-gray-500">
          Explore campgrounds across the United States
        </p>
      </div>
      <div className="flex-1 relative">
        <Suspense
          fallback={
            <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
              <LoadingSpinner size="lg" />
            </div>
          }
        >
          <CampgroundMap />
        </Suspense>
      </div>
    </div>
  );
}
