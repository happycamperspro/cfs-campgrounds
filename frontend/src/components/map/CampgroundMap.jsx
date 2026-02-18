import { MapContainer, TileLayer } from 'react-leaflet';
import MapMarker from './MapMarker';
import 'leaflet/dist/leaflet.css';

// Fix default marker icon issue with webpack/vite bundlers
import L from 'leaflet';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

const US_CENTER = [39.8, -98.5];
const DEFAULT_ZOOM = 4;

export default function CampgroundMap({ campgrounds = [] }) {
  const validCampgrounds = campgrounds.filter(
    (c) => c.location?.latitude && c.location?.longitude
  );

  const markers = validCampgrounds.map((campground) => (
    <MapMarker key={campground.id} campground={campground} />
  ));

  return (
    <MapContainer
      center={US_CENTER}
      zoom={DEFAULT_ZOOM}
      className="w-full h-full min-h-[500px] rounded-xl z-0"
      scrollWheelZoom={true}
      attributionControl={false}
    >
      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      {markers}
    </MapContainer>
  );
}
