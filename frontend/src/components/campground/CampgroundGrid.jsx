import CampgroundCard from './CampgroundCard';
import LoadingSpinner from '../ui/LoadingSpinner';
import EmptyState from '../ui/EmptyState';
import Pagination from '../ui/Pagination';

export default function CampgroundGrid({ campgrounds, loading, hasMore, onLoadMore }) {
  if (loading && campgrounds.length === 0) {
    return <LoadingSpinner size="lg" message="Loading campgrounds..." />;
  }

  if (!loading && campgrounds.length === 0) {
    return <EmptyState />;
  }

  return (
    <div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {campgrounds.map((campground) => (
          <CampgroundCard key={campground.id} campground={campground} />
        ))}
      </div>

      <Pagination
        onLoadMore={onLoadMore}
        loading={loading}
        hasMore={hasMore}
      />
    </div>
  );
}
