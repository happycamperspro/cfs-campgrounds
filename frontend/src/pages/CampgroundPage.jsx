import { useParams, Link } from 'react-router-dom';
import { useCampground } from '../hooks/useCampground';
import CampgroundDetail from '../components/campground/CampgroundDetail';
import LoadingSpinner from '../components/ui/LoadingSpinner';

export default function CampgroundPage() {
  const { slug } = useParams();
  const { campground, loading, error } = useCampground(slug);

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center">
        <div className="max-w-md mx-auto">
          <svg className="mx-auto h-12 w-12 text-red-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
          <h1 className="text-2xl font-bold text-gray-900 mt-4 mb-2">
            Error Loading Campground
          </h1>
          <p className="text-gray-600 mb-6">
            {error.message || 'Something went wrong. Please try again later.'}
          </p>
          <Link to="/browse" className="btn-primary">
            Back to Browse
          </Link>
        </div>
      </div>
    );
  }

  if (!campground) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center">
        <div className="max-w-md mx-auto">
          <svg className="mx-auto h-12 w-12 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <h1 className="text-2xl font-bold text-gray-900 mt-4 mb-2">
            Campground Not Found
          </h1>
          <p className="text-gray-600 mb-6">
            We couldn&apos;t find a campground matching &ldquo;{slug}&rdquo;.
          </p>
          <Link to="/browse" className="btn-primary">
            Browse Campgrounds
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Breadcrumb */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6">
        <nav className="text-sm text-gray-500 mb-4">
          <Link to="/" className="hover:text-campfire-600 transition-colors">Home</Link>
          <span className="mx-2">/</span>
          <Link to="/browse" className="hover:text-campfire-600 transition-colors">Browse</Link>
          {campground.state && (
            <>
              <span className="mx-2">/</span>
              <Link
                to={`/browse/${campground.state}`}
                className="hover:text-campfire-600 transition-colors"
              >
                {campground.state}
              </Link>
            </>
          )}
          <span className="mx-2">/</span>
          <span className="text-gray-900 font-medium">{campground.name}</span>
        </nav>
      </div>

      <CampgroundDetail campground={campground} />
    </div>
  );
}
