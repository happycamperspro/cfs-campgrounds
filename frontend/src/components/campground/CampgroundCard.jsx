import { Link } from 'react-router-dom';
import { SOURCE_COLORS, SOURCE_LABELS } from '../../lib/constants';
import { getStateName } from '../../lib/utils';
import RatingStars from './RatingStars';
import PriceRange from './PriceRange';

export default function CampgroundCard({ campground }) {
  const {
    slug,
    name,
    photos,
    location,
    ratings,
    pricing,
    source,
  } = campground;

  const firstPhoto = photos && photos.length > 0 ? photos[0] : null;
  const photoUrl = firstPhoto?.url || firstPhoto;
  const sourceColor = SOURCE_COLORS[source] || 'bg-gray-100 text-gray-800';
  const sourceLabel = SOURCE_LABELS[source] || source;

  return (
    <Link to={`/campground/${slug}`} className="card group block">
      {/* Photo */}
      <div className="aspect-video relative overflow-hidden bg-gray-200">
        {photoUrl ? (
          <img
            src={photoUrl}
            alt={name}
            loading="lazy"
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <svg
              className="h-12 w-12 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
          </div>
        )}

        {/* Source badge */}
        {source && (
          <span className={`absolute top-2 right-2 badge ${sourceColor}`}>
            {sourceLabel}
          </span>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        <h3 className="text-base font-semibold text-gray-900 group-hover:text-campfire-600 transition-colors line-clamp-1">
          {name}
        </h3>

        {location && (
          <p className="text-sm text-gray-500 mt-1">
            {location.city}
            {location.city && location.state ? ', ' : ''}
            {location.state ? getStateName(location.state) : ''}
          </p>
        )}

        <div className="mt-3 flex items-center justify-between">
          <RatingStars
            average={ratings?.average}
            count={ratings?.count}
          />
          <PriceRange
            min={pricing?.min}
            max={pricing?.max}
          />
        </div>
      </div>
    </Link>
  );
}
