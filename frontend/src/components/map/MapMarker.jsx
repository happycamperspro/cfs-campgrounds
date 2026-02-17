import { Marker, Popup } from 'react-leaflet';
import { Link } from 'react-router-dom';

export default function MapMarker({ campground }) {
  const { name, slug, location } = campground;
  const { latitude, longitude, city, state } = location || {};

  if (!latitude || !longitude) return null;

  return (
    <Marker position={[latitude, longitude]}>
      <Popup>
        <div className="text-sm">
          <Link
            to={`/campground/${slug}`}
            className="font-semibold text-campfire-600 hover:text-campfire-700"
          >
            {name}
          </Link>
          {(city || state) && (
            <p className="text-gray-500 mt-1">
              {city}{city && state ? ', ' : ''}{state}
            </p>
          )}
        </div>
      </Popup>
    </Marker>
  );
}
