import { formatPrice } from '../../lib/utils';

export default function PriceRange({ min, max }) {
  if (!min && !max) return null;

  return (
    <span className="text-sm font-medium text-gray-700">
      {formatPrice(min, max)}
      <span className="text-gray-400 font-normal"> /night</span>
    </span>
  );
}
