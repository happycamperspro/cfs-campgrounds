import { SOURCE_COLORS, SOURCE_LABELS } from '../../lib/constants';
import { getStateName } from '../../lib/utils';
import RatingStars from './RatingStars';
import PriceRange from './PriceRange';
import AmenityList from './AmenityList';
import ContactInfo from './ContactInfo';
import DetailMap from '../map/DetailMap';
import PhotoGallery from '../gallery/PhotoGallery';

// Format siteTypes whether it's an object {tentOnly: 5} or an array ['tent', 'rv']
function formatSiteTypes(siteTypes) {
  if (!siteTypes) return null;
  if (Array.isArray(siteTypes)) return siteTypes.length > 0 ? siteTypes.join(', ') : null;
  if (typeof siteTypes === 'object') {
    const entries = Object.entries(siteTypes).filter(([, v]) => v && v > 0);
    if (entries.length === 0) return null;
    return entries.map(([k, v]) => `${k}: ${v}`).join(', ');
  }
  return String(siteTypes);
}

// Convert hookups object {electric: true, water: false} to displayable string array
function formatHookups(hookups) {
  if (!hookups) return [];
  if (Array.isArray(hookups)) return hookups;
  if (typeof hookups === 'object') {
    return Object.entries(hookups)
      .filter(([, v]) => v === true)
      .map(([k]) => k.charAt(0).toUpperCase() + k.slice(1));
  }
  return [];
}

export default function CampgroundDetail({ campground }) {
  const {
    name,
    description,
    location,
    ratings,
    pricing,
    source,
    details,
    amenities,
    contact,
    reservationUrl,
    parkName,
  } = campground;

  // Ensure photos is always a safe array
  const photos = Array.isArray(campground.photos) ? campground.photos : [];
  const firstPhoto = photos.length > 0 ? photos[0] : null;
  const heroUrl = firstPhoto?.url || (typeof firstPhoto === 'string' ? firstPhoto : null);
  const sourceColor = SOURCE_COLORS[source] || 'bg-gray-100 text-gray-800';
  const sourceLabel = SOURCE_LABELS[source] || source;

  // Strict coordinate validation — must be finite numbers, not both zero
  const lat = Number(location?.latitude);
  const lng = Number(location?.longitude);
  const hasCoordinates = location && isFinite(lat) && isFinite(lng) && (lat !== 0 || lng !== 0);

  // Pre-process amenity data: hookups may be an object {electric: true} not an array
  const hookupList = formatHookups(amenities?.hookups);
  const facilitiesList = Array.isArray(amenities?.facilities) ? amenities.facilities : [];
  const activitiesList = Array.isArray(amenities?.activities) ? amenities.activities : [];

  return (
    <div className="max-w-4xl mx-auto">
      {/* Hero photo */}
      <div className="aspect-video relative overflow-hidden rounded-xl bg-gray-200 mb-6">
        {heroUrl ? (
          <img
            src={heroUrl}
            alt={name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <svg
              className="h-20 w-20 text-gray-400"
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
      </div>

      {/* Header */}
      <div className="mb-6">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{name}</h1>
            {parkName && (
              <p className="text-lg text-gray-600 mt-1">{parkName}</p>
            )}
          </div>
          {source && (
            <span className={`badge ${sourceColor} flex-shrink-0`}>
              {sourceLabel}
            </span>
          )}
        </div>

        <div className="flex items-center gap-4 mt-3 flex-wrap">
          <RatingStars average={ratings?.avgRating || ratings?.average} count={ratings?.totalReviews || ratings?.count} />
          <PriceRange min={pricing?.min} max={pricing?.max} />
        </div>
      </div>

      {/* Description */}
      {description && (
        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-3">About</h2>
          <p className="text-gray-600 leading-relaxed whitespace-pre-line">{description}</p>
        </section>
      )}

      {/* Location */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-3">Location</h2>
        {location && (
          <p className="text-gray-600 mb-4">
            {location.address && <span>{location.address}<br /></span>}
            {location.city}
            {location.city && location.state ? ', ' : ''}
            {location.state ? getStateName(location.state) : ''}
            {location.zip ? ` ${location.zip}` : ''}
          </p>
        )}
        {hasCoordinates && (
          <div className="rounded-xl overflow-hidden">
            <DetailMap
              latitude={lat}
              longitude={lng}
              name={name}
            />
          </div>
        )}
      </section>

      {/* Contact Info */}
      {contact && (
        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-3">Contact</h2>
          <ContactInfo contact={contact} />
        </section>
      )}

      {/* Site Details */}
      {details && (
        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-3">Site Details</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {details.totalSites > 0 && (
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-500">Total Sites</p>
                <p className="text-lg font-semibold text-gray-900">{details.totalSites}</p>
              </div>
            )}
            {formatSiteTypes(details.siteTypes) && (
              <div className="bg-gray-50 rounded-lg p-4 col-span-2">
                <p className="text-sm text-gray-500">Site Types</p>
                <p className="text-sm font-medium text-gray-900">{formatSiteTypes(details.siteTypes)}</p>
              </div>
            )}
            {details.maxRvLength > 0 && (
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-500">Max RV Length</p>
                <p className="text-lg font-semibold text-gray-900">{details.maxRvLength} ft</p>
              </div>
            )}
            {details.season && (
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-500">Season</p>
                <p className="text-lg font-semibold text-gray-900">{details.season}</p>
              </div>
            )}
            {(details.reservable || details.reservationType) && (
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-500">Reservations</p>
                <p className="text-lg font-semibold text-gray-900">
                  {details.reservationType || (details.reservable ? 'Reservable' : 'N/A')}
                </p>
              </div>
            )}
          </div>
        </section>
      )}

      {/* Amenities */}
      {amenities && (
        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-3">Amenities</h2>
          <AmenityList
            hookups={hookupList}
            facilities={facilitiesList}
            activities={activitiesList}
          />
          {amenities.petsAllowed && (
            <div className="mt-3">
              <span className="badge bg-blue-50 text-blue-700 border border-blue-200">
                Pets Allowed
              </span>
            </div>
          )}
          {amenities.accessibility && (
            <div className="mt-2">
              <span className="badge bg-blue-50 text-blue-700 border border-blue-200">
                Wheelchair Accessible
              </span>
            </div>
          )}
        </section>
      )}

      {/* Photo Gallery */}
      {photos.length > 1 && (
        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-3">Photos</h2>
          <PhotoGallery
            photos={photos.map((p) =>
              typeof p === 'string' ? { url: p, caption: '' } : p
            )}
          />
        </section>
      )}

      {/* Reservation Button */}
      {(reservationUrl || contact?.reservationUrl) && (
        <div className="sticky bottom-4 flex justify-center pb-4">
          <a
            href={reservationUrl || contact.reservationUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary text-lg px-8 py-3 shadow-lg"
          >
            Make Reservation
          </a>
        </div>
      )}
    </div>
  );
}
